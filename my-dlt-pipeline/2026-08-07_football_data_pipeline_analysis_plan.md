# Analysis Plan: football_data_pipeline

## Connection
pipeline: football_data_pipeline
dataset: football_data
destination: duckdb

## Profile Summary
| table | rows | key columns | notes |
|-------|------|-------------|-------|
| team_matches | (not profiled — high-intent path) | id, utc_date, status, score__winner, score__full_time__home, score__full_time__away, home_team__id, away_team__id, season__id, season__start_date | temporal: utc_date; status filters finished vs scheduled matches; team id 66 = Manchester United (home or away) |

Query style note: all three charts use **ibis expressions** (`dataset[...].to_ibis()`), not raw SQL strings — explicit user requirement, overrides this toolkit's SQL-first default. All aggregations filter `status == "FINISHED"` since `score__winner` / scores are null for unplayed matches.

Season labeling note: `season__id` is football-data.org's internal season identifier (e.g. `2287`, `2403`) — not a human-readable year. All charts derive `season` as the year extracted from `season__start_date` (`.cast("date").year()`), which reads as `2024`, `2025`, etc. Group-by, window partitioning, and altair encodings all use `season`, not `season__id`.

## Questions
1. [x] How many matches has Man Utd played/won/drawn/lost per season? → Chart 1 (table, no chart)
2. [x] What's the running points total per season? → Chart 2
3. [x] Goals scored vs conceded per season? → Chart 3

## Data Gaps
(none)

## Chart 1: Match Record per Season (table, no chart)
question: How many matches has Man Utd (id 66) played/won/drawn/lost per season?
type: table
x: season (year, derived from season__start_date)
y: matches_played, wins, draws, losses
source: team_matches

```ibis
t = dataset["team_matches"].to_ibis()
finished = t.filter(t.status == "FINISHED")
is_home = finished.home_team__id == 66

matches = finished.mutate(
    season=finished.season__start_date.cast("date").year(),
    is_win=((is_home) & (finished.score__winner == "HOME_TEAM"))
        | ((~is_home) & (finished.score__winner == "AWAY_TEAM")),
    is_draw=finished.score__winner == "DRAW",
    is_loss=((is_home) & (finished.score__winner == "AWAY_TEAM"))
        | ((~is_home) & (finished.score__winner == "HOME_TEAM")),
)

season_record = (
    matches.group_by("season")
    .aggregate(
        matches_played=matches.id.count(),
        wins=matches.is_win.sum(),
        draws=matches.is_draw.sum(),
        losses=matches.is_loss.sum(),
    )
    .order_by("season")
)
```

No altair chart — rendered as a `mo.ui.table` of the ibis result.

## Chart 2: Running Points Total per Season
question: How do Man Utd's season points accumulate over time (3 win / 1 draw / 0 loss)?
type: line
x: utc_date (per match, within season)
y: running_points (cumulative sum via ibis window function)
color: season (one line per season year)
source: team_matches

```ibis
t = dataset["team_matches"].to_ibis()
finished = t.filter(t.status == "FINISHED")
is_home = finished.home_team__id == 66

matches = finished.mutate(
    season=finished.season__start_date.cast("date").year(),
    is_win=((is_home) & (finished.score__winner == "HOME_TEAM"))
        | ((~is_home) & (finished.score__winner == "AWAY_TEAM")),
    is_draw=finished.score__winner == "DRAW",
)
matches = matches.mutate(
    points=ibis.ifelse(matches.is_win, 3, ibis.ifelse(matches.is_draw, 1, 0))
)

season_window = ibis.window(group_by="season", order_by="utc_date")
running_points = (
    matches.mutate(running_points=matches.points.sum().over(season_window))
    .select("season", "utc_date", "points", "running_points")
    .order_by(["season", "utc_date"])
)
```

```altair
alt.Chart(df_chart2).mark_line().encode(
    x="utc_date:T",
    y="running_points:Q",
    color="season:O",
    tooltip=["season:O", "utc_date:T", "running_points:Q"]
).properties(title="Manchester United — Running Points Total per Season")
```

## Chart 3: Goals Scored vs Conceded per Season
question: How do Man Utd's goals scored and conceded compare per season?
type: bar (grouped)
x: season (year, derived from season__start_date)
y: goals
color: metric (scored / conceded)
source: team_matches

```ibis
t = dataset["team_matches"].to_ibis()
finished = t.filter(t.status == "FINISHED")
is_home = finished.home_team__id == 66

goals = finished.mutate(
    season=finished.season__start_date.cast("date").year(),
    goals_scored=ibis.ifelse(is_home, finished.score__full_time__home, finished.score__full_time__away),
    goals_conceded=ibis.ifelse(is_home, finished.score__full_time__away, finished.score__full_time__home),
)

season_goals = (
    goals.group_by("season")
    .aggregate(
        goals_scored=goals.goals_scored.sum(),
        goals_conceded=goals.goals_conceded.sum(),
    )
    .order_by("season")
)
```

Chart-prep note: melt `season_goals` result from wide (goals_scored, goals_conceded columns) to long (metric, goals) with `pandas.melt` before charting, so altair can group bars by metric.

```altair
alt.Chart(df_chart3_long).mark_bar().encode(
    x="season:O",
    y="goals:Q",
    color="metric:N",
    xOffset="metric:N",
    tooltip=["season:O", "metric:N", "goals:Q"]
).properties(title="Manchester United — Goals Scored vs Conceded per Season")
```

## Notes
- Output notebook filename is a hard user requirement: `football_dashboard.py` (not the toolkit default `<pipeline_name>_dashboard.py`).
- Do not modify football_data.py or football_data_10yrs.py — only create football_dashboard.py.
- "Marimo's native charting support" = marimo's built-in rendering of altair chart objects (a cell returning an `alt.Chart` renders inline); wrapped in `mo.ui.altair_chart()` per this toolkit's interactivity convention.
- `season__id` (football-data.org's internal id, e.g. `2287`/`2403`) is not human-readable — all charts use `season` (year derived from `season__start_date`) instead. See Profile Summary note.
