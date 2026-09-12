#!/usr/bin/env python3
"""SERP API benchmark harness.

Runs a fixed query set against multiple SERP API providers, records latency /
success / parse-completeness, writes raw JSON per query and appends to a
normalized CSV. Python 3 stdlib only.

Usage:
    python3 rig/benchmark.py --wave 1
    python3 rig/benchmark.py --wave 2 --providers serpapi,serpdog --repeats 1

API keys are read from (in order):
    1. environment variables (SEARCHAPI_API_KEY, SERPAPI_API_KEY, SERPDOG_API_KEY, SCRAPERAPI_API_KEY)
    2. ~/.config/serp-rig.env  (KEY=VALUE lines, chmod 600)

Providers without a key present are skipped. No retries are attempted on
purpose — retry logic would hide the success-rate signal we are measuring.
"""
import argparse
import concurrent.futures
import csv
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from queries import QUERY_SET

ROOT = Path(__file__).resolve().parent.parent
KEYS_FILE = Path.home() / ".config/serp-rig.env"
TIMEOUT = 30  # seconds — hard cap; a timeout is recorded as a failure

# --------------------------------------------------------------------------- keys


def load_keys():
    keys = {}
    if KEYS_FILE.exists():
        for line in KEYS_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()
    for name in ("SEARCHAPI_API_KEY", "SERPAPI_API_KEY", "SERPDOG_API_KEY", "SCRAPERAPI_API_KEY"):
        if os.environ.get(name):
            keys[name] = os.environ[name].strip()
    return keys


# --------------------------------------------------------------------------- providers

def _pick(d, *names):
    """Return the first non-empty value among candidate field names."""
    for n in names:
        v = d.get(n)
        if v:
            return v
    return None


def _organics(payload, *containers):
    for c in containers:
        if isinstance(payload.get(c), list) and payload[c]:
            return payload[c]
    return []


def _normalize(raw_organics):
    """Map provider-specific organic dicts to {position,title,url,description}."""
    out = []
    for i, r in enumerate(raw_organics, start=1):
        if not isinstance(r, dict):
            continue
        row = {
            "position": r.get("position") or r.get("rank") or i,
            "title": _pick(r, "title", "name"),
            "url": _pick(r, "link", "url", "url_str"),
            "description": _pick(r, "description", "snippet", "text"),
        }
        out.append(row)
    return out


def google_common(extra):
    """Standard fairness params every provider receives where supported."""
    return {"gl": "us", "hl": "en", "num": "10", **extra}


PROVIDERS = {
    "searchapi": {
        "env": "SEARCHAPI_API_KEY",
        "url": lambda key, q: "https://www.searchapi.io/api/v1/search?" + urllib.parse.urlencode(
            google_common({"engine": "google", "q": q, "api_key": key})),
        "extract": lambda p: _organics(p, "organic_results"),
    },
    "serpapi": {
        "env": "SERPAPI_API_KEY",
        "url": lambda key, q: "https://serpapi.com/search?" + urllib.parse.urlencode(
            google_common({"engine": "google", "q": q, "api_key": key})),
        "extract": lambda p: _organics(p, "organic_results"),
    },
    "serpdog": {
        "env": "SERPDOG_API_KEY",
        "url": lambda key, q: "https://api.serpdog.io/search?" + urllib.parse.urlencode(
            google_common({"api_key": key, "q": q})),
        "extract": lambda p: _organics(p, "organic_results"),
    },
    "scraperapi": {
        "env": "SCRAPERAPI_API_KEY",
        # ScraperAPI structured Google endpoint
        "url": lambda key, q: "https://api.scraperapi.com/?" + urllib.parse.urlencode(
            google_common({"api_key": key, "q": q, "google_domain": "google.com", "output": "json"})),
        "extract": lambda p: _organics(p, "organic_results", "results"),
    },
}


def fetch(url):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "serp-benchmark-rig/1.0 (methodology: github.com/herky-jerky/serp-benchmark-rig)"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
            latency = (time.perf_counter() - t0) * 1000
            return latency, resp.status, body
    except Exception as e:  # timeout, HTTP error, anything — recorded, not retried
        latency = (time.perf_counter() - t0) * 1000
        return latency, getattr(e, "code", 0), str(e).encode()


def run_one(provider, key, qclass, query, attempt):
    p = PROVIDERS[provider]
    url = p["url"](key, query)
    latency, status, body = fetch(url)
    row = {
        "run_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": provider,
        "query_class": qclass,
        "query": query,
        "attempt": attempt,
        "latency_ms": round(latency, 1),
        "http_status": status,
        "success": False,
        "n_organic": 0,
        "fields_complete_pct": 0.0,
        "error": None,
    }
    raw_path = None
    if status == 200:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            row["error"] = f"json decode: {e}"
            payload = None
        if payload is not None:
            organics = _normalize(p["extract"](payload))
            row["n_organic"] = len(organics)
            if organics:
                complete = sum(1 for o in organics if o["title"] and o["url"] and o["description"])
                row["fields_complete_pct"] = round(100 * complete / len(organics), 1)
                row["success"] = row["n_organic"] >= 5 and row["fields_complete_pct"] >= 90
            else:
                row["error"] = "200 but no organic_results parsed"
            raw_path = payload
    else:
        row["error"] = f"HTTP {status}: {body[:180].decode('utf-8', 'replace') if isinstance(body, bytes) else body}"
    return row, raw_path


# --------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description="SERP API benchmark rig")
    ap.add_argument("--wave", type=int, required=True)
    ap.add_argument("--providers", default="searchapi,serpapi,serpdog,scraperapi",
                    help="comma-separated subset")
    ap.add_argument("--repeats", type=int, default=2, help="runs per query (quota math in README)")
    ap.add_argument("--outdir", default=str(ROOT / "data"))
    args = ap.parse_args()

    keys = load_keys()
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    active = [p for p in providers if p in PROVIDERS and PROVIDERS[p]["env"] in keys]
    skipped = [p for p in providers if p not in active]
    if skipped:
        print(f"skipped (no key): {', '.join(skipped)}")
    if not active:
        sys.exit("no providers with keys — add keys to ~/.config/serp-rig.env or environment")

    wave_dir = Path(args.outdir) / f"wave_{args.wave}"
    wave_dir.mkdir(parents=True, exist_ok=True)
    csv_path = Path(args.outdir) / "normalized.csv"
    new_rows = []

    print(f"wave {args.wave}: {len(active)} providers x {len(QUERY_SET)} queries x {args.repeats} repeats")
    for provider in active:
        key = keys[PROVIDERS[provider]["env"]]
        for qclass, query in QUERY_SET:
            for attempt in range(1, args.repeats + 1):
                row, raw = run_one(provider, key, qclass, query, attempt)
                new_rows.append(row)
                slug = query.replace(" ", "_").replace("/", "-")[:40]
                if raw is not None:
                    rdir = wave_dir / provider
                    rdir.mkdir(parents=True, exist_ok=True)
                    (rdir / f"{qclass}__{slug}__a{attempt}.json").write_text(
                        json.dumps(raw, ensure_ascii=False)[:2_000_000])
                flag = "ok " if row["success"] else "FAIL"
                print(f"  [{flag}] {provider:10s} {row['latency_ms']:7.1f}ms  n={row['n_organic']:2d}  {query[:38]}")
            time.sleep(0.4)  # politeness gap between queries

    # aggregate summary for this wave
    print("\n=== WAVE SUMMARY ===")
    for provider in active:
        rs = [r for r in new_rows if r["provider"] == provider]
        lat = [r["latency_ms"] for r in rs]
        ok = [r for r in rs if r["success"]]
        p50 = statistics.median(lat) if lat else 0
        p95 = statistics.quantiles(lat, n=20)[-1] if len(lat) >= 2 else (lat[0] if lat else 0)
        print(f"{provider:10s}  calls={len(rs):3d}  success={len(ok)}/{len(rs)}  "
              f"p50={p50:7.1f}ms  p95={p95:7.1f}ms  "
              f"avg_fields={statistics.mean(r['fields_complete_pct'] for r in rs if r['success']):.1f}%" if ok else
              f"{provider:10s}  calls={len(rs):3d}  success=0/{len(rs)}")

    # append to normalized CSV
    fields = ["run_ts", "provider", "query_class", "query", "attempt", "latency_ms",
              "http_status", "success", "n_organic", "fields_complete_pct", "error"]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        for r in new_rows:
            w.writerow(r)
    print(f"\ncsv: {csv_path} (+{len(new_rows)} rows)")
    print(f"raw: {wave_dir}/")


if __name__ == "__main__":
    main()
