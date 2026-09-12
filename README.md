# SERP Benchmark Rig

An independent, methodology-public benchmark of real-time SERP APIs — run over time,
with raw data published, **including unflattering results for any provider**.

Built as a working demonstration of how we think benchmark content should be made:
the tests are coded, the queries are fixed and public, the runs are timestamped,
the failures stay in the dataset, and the method is reproducible from scratch on
a free tier. Inspired by job postings that say things like "AI-native,
verify-everything, publish unflattering truths" — this rig is that sentence,
compiled.

## Providers (v1)

| Provider | Access tier |
|---|---|
| SearchApi | free trial |
| SerpApi | free tier (~100 searches/mo) |
| Serpdog | free tier |
| ScraperAPI | free trial (1,000 credits) |

DataForSEO (pay-per-use) is planned but not wired in v1 (different auth model).

## Method

- **Query set:** 20 fixed queries across five difficulty classes — navigational,
  informational-short, local, long-tail question, shopping. Identical strings every
  wave (see `rig/queries.py`).
- **Fairness params:** every provider receives `gl=us&hl=en&num=10` where supported.
  Rotating headers/UA held constant; a descriptive UA identifies the rig.
- **Metrics per provider, per wave:**
  - latency: p50 / p95 (ms)
  - success rate: HTTP 200 + ≥5 organic results + ≥90% field completeness
  - parse completeness: % of organic results with position + title + url + description
  - published price per 1K queries on the tier used (manual, in results.md)
- **Cadence:** wave 1 on build day; waves 2–3 at +24h/+48h; then periodic re-runs.
- **No retries.** A failed call is recorded as a failure. Retrying would hide the
  success-rate signal that is one of the things being measured.

## Reproduce from scratch

```bash
git clone https://github.com/herky-jerky/serp-benchmark-rig
cd serp-benchmark-rig
# 1. create free accounts with each provider
# 2. store keys (never in the repo):
cat > ~/.config/serp-rig.env <<'EOF'
SEARCHAPI_API_KEY=...
SERPAPI_API_KEY=...
SERPDOG_API_KEY=...
SCRAPERAPI_API_KEY=...
EOF
chmod 600 ~/.config/serp-rig.env
# 3. run a wave
python3 rig/benchmark.py --wave 1
```

Outputs: `data/wave_<N>/<provider>/*.json` (raw responses) and
`data/normalized.csv` (one row per call). Summary tables land in `results.md`.

## Quota math on free tiers

Default is 2 repeats × 20 queries = 40 calls/provider/wave. SerpApi's free tier is
~100/month, so three full waves exhaust it — for waves 2–3 either run
`--providers searchapi,serpdog,scraperapi --repeats 1`, or accept the upgrade. We
note every quota decision in results.md rather than quietly skipping calls.

## Limitations (read before quoting any number here)

- Providers execute searches from their own infrastructure; result *content* varies
  by their IP geolocation. We compare **API service quality** (latency, uptime, parse
  quality, price) — not result parity across providers.
- Single run location, single search vertical (Google organic), small query set.
- No retries is a measurement choice, not negligence.
- The harness is stdlib-only on purpose: zero dependencies between this repo and a
  clean `python3` install.

## Results

See [results.md](results.md). Numbers publish as-run — including the ones providers
would prefer we didn't chart.

## License

MIT.
