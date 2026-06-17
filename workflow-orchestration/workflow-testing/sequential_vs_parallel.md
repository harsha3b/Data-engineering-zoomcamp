# EachSequential vs EachParallel in Kestra

## EachSequential

Runs one item at a time. The next item only starts after the current one fully completes.

```
Item 1 → [download → upload GCS → load BQ] → done
Item 2 → [download → upload GCS → load BQ] → done
Item 3 → [download → upload GCS → load BQ] → done
...
```

### Pros
- Predictable GCP resource usage — no throttling or quota issues
- Easy to debug — failures are isolated to one combination at a time
- If it fails at item 20, you know exactly where it stopped
- No risk of concurrent writes conflicting in BigQuery

### Cons
- Slow — 48 subflows run one after another (could take hours)
- Idle resources — GCP sits waiting while Kestra downloads the next file

---

## EachParallel

Launches all items at the same time. All subflows run concurrently.

```
Item 1  → [download → upload GCS → load BQ]
Item 2  → [download → upload GCS → load BQ]
Item 3  → [download → upload GCS → load BQ]
...all 48 running simultaneously
```

### Pros
- Much faster — all 48 combinations load in roughly the time of one
- Better resource utilization overall

### Cons
- 48 simultaneous downloads, GCS uploads, and BigQuery queries — risk of hitting GCP rate limits/quotas
- Harder to debug — multiple failures can happen at once
- If BigQuery gets overwhelmed, many subflows fail together
- Higher cost spike (all resources consumed at once vs spread over time)

### Failure behavior
- Already-running subflows are **not interrupted** when another one fails
- The **parent flow** will end up in a `FAILED` state once all finish
- `transmitFailed: true` on the subflow call is what causes the parent to inherit the failed status

---

## Middle Ground: EachParallel with `concurrencyLimit`

```yaml
type: io.kestra.plugin.core.flow.EachParallel
concurrencyLimit: 4
```

```
Item 1,2,3,4 → run together → finish
Item 5,6,7,8 → run together → finish
...
```

Runs a fixed number of subflows at a time instead of all at once.
Best of both worlds — faster than sequential, controlled enough that GCP is not overwhelmed.
For this use case, a `concurrencyLimit` of 4–6 is a safe starting point.

---

## Summary

| | Sequential | Parallel | Parallel + limit |
|---|---|---|---|
| Speed | Slowest | Fastest | Middle |
| GCP load | Low | Very high | Controlled |
| Debuggability | Easy | Hard | Medium |
| Risk of failure | Low | High | Low-medium |
| Recommended for | Testing / small runs | Rarely | Production backfills |
