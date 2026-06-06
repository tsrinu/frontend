# Load tests

Uses [k6](https://k6.io/docs/get-started/installation/) — install on Windows with:
```cmd
winget install k6.k6
```

Or just download the binary from the release page.

## Run

```cmd
REM Single service
k6 run -e BASE_URL=http://localhost:8001 tests\load\k6-auth.js

REM Whole stack via gateway
k6 run -e BASE_URL=http://localhost:8080/api/v1 tests\load\k6-auth.js
```

## What good looks like

- **p95 latency < 500ms** on auth endpoints (set in `thresholds`)
- **<1% error rate** (the test will fail loudly otherwise)
- **At 50 VUs**, you should see ~25-50 req/s without crashing

## When it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| All requests 429 | Rate limiter saturated | This is correct behavior — single IP from k6. To test real-world load, run k6 from multiple machines/regions |
| p95 > 1000ms | scrypt PIN hashing dominates | Move PIN ops to a background worker, or use bcrypt with lower work factor |
| Errors spike to 100% | Service crashed (OOM, deadlock) | Check `docker logs <service>`, raise memory limit |
| Throughput plateaus | Single worker uvicorn | Run with `--workers 4` to use multiple processes |
