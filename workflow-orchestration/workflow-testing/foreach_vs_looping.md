# ForEach (Flat List) vs Nested Loops in Kestra

## Overview

Both approaches iterate over the same 48 combinations (2 taxi types x 2 years x 12 months)
and call the same subflow. The difference is in how the combinations are structured and managed.

---

## Nested Loops (`gcp_taxi_backfill.yaml`)

Three levels of `EachSequential`, one per dimension (taxi → year → month).
Kestra manages the cartesian product implicitly through nesting.

```yaml
- id: each_taxi          # outer loop:  yellow, green
  type: io.kestra.plugin.core.flow.EachSequential
  value: ["yellow", "green"]
  tasks:
    - id: each_year      # middle loop: 2019, 2020
      type: io.kestra.plugin.core.flow.EachSequential
      value: ["2019", "2020"]
      tasks:
        - id: each_month # inner loop:  01 - 12
          type: io.kestra.plugin.core.flow.EachSequential
          value: ["01", ..., "12"]
          tasks:
            - id: load_data
              inputs:
                taxi:  "{{parents[1].taskrun.value}}"  # two levels up
                year:  "{{parents[0].taskrun.value}}"  # one level up
                month: "{{taskrun.value}}"             # current level
```

### How parent values are accessed in nested loops

| Variable | Resolves to |
|---|---|
| `{{taskrun.value}}` | current month (innermost loop) |
| `{{parents[0].taskrun.value}}` | current year (one level up) |
| `{{parents[1].taskrun.value}}` | current taxi type (two levels up) |

### Pros
- No extra script step — starts running immediately
- Straightforward to read if you think in terms of nested dimensions

### Cons
- Kestra tracks 3 levels of task runs internally — more metadata overhead
- `parents[X].taskrun.value` syntax is harder to read and error-prone
- Adding a new dimension (e.g. a third year) requires editing multiple `value` lists
- Cannot easily switch to parallel without restructuring all three loop levels

---

## ForEach with Flat List (`gcp_taxi_backfill_for_each.yaml`)

A Python script generates all combinations upfront as a flat list of dicts.
A single `EachSequential` (or `EachParallel`) iterates over that list.

```yaml
- id: generate_combinations
  type: io.kestra.plugin.scripts.python.Script
  script: |
    from kestra import Kestra
    combinations = [
        {"taxi": t, "year": y, "month": m}
        for t in ["yellow", "green"]
        for y in ["2019", "2020"]
        for m in ["01", ..., "12"]
    ]
    Kestra.outputs({"combinations": combinations})

- id: for_each_combination
  type: io.kestra.plugin.core.flow.EachSequential  # or EachParallel
  value: "{{outputs.generate_combinations.vars.combinations}}"
  tasks:
    - id: load_data
      inputs:
        taxi:  "{{taskrun.value.taxi}}"   # directly from the dict
        year:  "{{taskrun.value.year}}"
        month: "{{taskrun.value.month}}"
```

### Pros
- Only 1 level of task runs — lighter for Kestra to manage
- `taskrun.value.taxi` is cleaner and easier to read than `parents[1].taskrun.value`
- To add a new year or taxi type, edit one Python list — no YAML restructuring
- Trivial to switch between `EachSequential` and `EachParallel` (one word change)
- `concurrencyLimit` can be added to `EachParallel` in one place

### Cons
- Requires a Python script step (~1 second overhead before the loop starts)
- Slightly more complex flow structure (two tasks instead of one)

---

## Efficiency Comparison

| | Nested Loops | ForEach (flat list) |
|---|---|---|
| Execution speed (sequential) | Same | Same |
| Kestra internal overhead | Higher (3 loop levels) | Lower (1 loop level) |
| Extra startup cost | None | ~1 sec Python script |
| Input variable syntax | `parents[X].taskrun.value` | `taskrun.value.key` |
| Ease of adding dimensions | Edit multiple `value` lists | Edit one Python list |
| Switching to parallel | Restructure all loops | Change one word |
| Concurrency control | Complex | `concurrencyLimit: N` |

---

## Which to Use

| Scenario | Recommended |
|---|---|
| Simple one-off backfill, no future changes expected | Nested loops |
| Production pipeline that may grow (more years, taxi types) | ForEach flat list |
| Need parallel execution with concurrency control | ForEach + EachParallel |
| Want to avoid Python dependency | Nested loops |
