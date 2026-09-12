# Results — SERP Benchmark Rig

> Numbers publish as-run. If a provider (including SearchApi) looks bad on a metric,
> the bad number ships. That is the point of the rig.

**Wave 1 — 2026-09-12.** 160 calls, four providers, 20 fixed queries × 2 repeats,
Google organic, `gl=us&hl=en&num=10`, no retries (failures are data). Every raw response
in [`data/wave_1/`](data/wave_1/), every call in [`data/normalized.csv`](data/normalized.csv).

## Wave 1 — summary

| Provider | Calls | Success | p50 latency | p95 latency | Parse completeness |
|---|---|---|---|---|---|
| **searchapi** | 40 | 40/40 (100%) | 3,635 ms | 14,459 ms | 100% |
| **serpapi** | 40 | 36/40 (90%) | **66 ms** | 29,799 ms | 100% |
| **scraperapi** | 40 | 37/40 (92.5%) | 3,284 ms | 20,087 ms | 100% |
| **zenserp** | 40 | 22/40 (55%) | 1,956 ms | 26,084 ms | 100% |

### Observations per provider (as measured, not adjudicated)

- **searchapi** — 100% reliable and the slowest median of the wave (3.6 s, worst call 22.6 s).
  Trial-tier throttling is visible in the latency profile; whether paid tiers behave differently
  is a question for their docs, not for this free-tier dataset.
- **serpapi** — the fastest median by ~50x (66 ms) with a violent tail: both attempts on
  "can you file taxes late without a penalty" ran to the 30-second timeout, and "github"
  returned only 4 organic results (below the rig's 5-result success bar).
- **scraperapi** — 92.5% success, 3.3 s median. Their response also includes an `ai_box`
  (AI Overview data) — the only provider of the four exposing it. Note: their legacy
  `?q=` endpoint is deprecated (40/40 HTTP 400s on first contact); the rig was re-wired to
  the current structured endpoint (`/structured/google/search?query=…`) and re-run the same
  day — the failed calls are preserved in git history.
- **zenserp** — 55% success. Failure signature: fast ~250 ms API-error responses clustered
  on consecutive calls, interleaved with slow successes — consistent with free-tier rate
  limiting. Wave 2 adds inter-call spacing to test whether 55% → ~90%+; if it does, that is
  a finding about the tier, not the API.

### Cross-provider oddity worth watching

The "github" query returned **fewer than 5 organic results on two different providers**
(SerpApi and ScraperAPI) — suggesting the SERP itself (feature boxes crowding out organic
slots) rather than a parsing defect in either API. Both providers' raw JSON for that query
is in the data directory for inspection.

## Quota & methodology notes

- 2 repeats per query (40 calls/provider/wave), free tiers throughout, single run location.
- SerpApi's free tier is ~100/mo: waves 2–3 either run `--providers searchapi,scraperapi,zenserp`
  or drop to 1 repeat — documented, never silently skipped.
- Result-content parity across providers is out of scope (providers search from their own
  infrastructure; we measure API service quality — see README limitations).

## Waves

| Wave | Date | Status |
|---|---|---|
| 1 | 2026-09-12 | ✅ complete — table above |
| 2 | +24h | planned (adds zenserp spacing test) |
| 3 | +48h | planned |
