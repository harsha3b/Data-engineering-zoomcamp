import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    import dlt

    return alt, dlt, mo


@app.cell
def _(dlt):
    pipeline = dlt.attach("football_data_pipeline")
    dataset = pipeline.dataset()
    return (dataset,)


@app.cell
def _(mo):
    mo.md("""
    # Manchester United — Season Dashboard

    Built from the `football_data_pipeline` dataset (`team_matches` table),
    loaded from the football-data.org API. All match records are for team id
    `66` (Manchester United), home or away, restricted to finished matches.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Match Record per Season

    Matches played, wins, draws, and losses per season, computed with an
    ibis expression over `team_matches` (win/draw/loss determined from
    `score__winner` relative to whether Man Utd played home or away).
    """)
    return


@app.cell
def _(dataset):
    import ibis as _ibis

    _t = dataset["team_matches"].to_ibis()
    _finished = _t.filter(_t.status == "FINISHED")
    _is_home = _finished.home_team__id == 66

    _matches = _finished.mutate(
        season=_finished.season__start_date.cast("date").year(),
        is_win=((_is_home) & (_finished.score__winner == "HOME_TEAM"))
        | ((~_is_home) & (_finished.score__winner == "AWAY_TEAM")),
        is_draw=_finished.score__winner == "DRAW",
        is_loss=((_is_home) & (_finished.score__winner == "AWAY_TEAM"))
        | ((~_is_home) & (_finished.score__winner == "HOME_TEAM")),
    )

    _season_record_expr = (
        _matches.group_by("season")
        .aggregate(
            matches_played=_matches.id.count(),
            wins=_matches.is_win.sum(),
            draws=_matches.is_draw.sum(),
            losses=_matches.is_loss.sum(),
        )
        .order_by("season")
    )
    df_chart1 = dataset(_season_record_expr).df()
    return (df_chart1,)


@app.cell
def _(df_chart1, mo):
    _table = mo.ui.table(df_chart1)
    _table
    return


@app.cell
def _(mo):
    mo.md("""
    ## Running Points Total per Season

    Cumulative points per match (3 for a win, 1 for a draw, 0 for a loss),
    computed with an ibis window function partitioned by season and
    ordered by `utc_date`. One line per season.
    """)
    return


@app.cell
def _(dataset):
    import ibis as _ibis

    _t = dataset["team_matches"].to_ibis()
    _finished = _t.filter(_t.status == "FINISHED")
    _is_home = _finished.home_team__id == 66

    _matches = _finished.mutate(
        season=_finished.season__start_date.cast("date").year(),
        is_win=((_is_home) & (_finished.score__winner == "HOME_TEAM"))
        | ((~_is_home) & (_finished.score__winner == "AWAY_TEAM")),
        is_draw=_finished.score__winner == "DRAW",
    )
    _matches = _matches.mutate(
        points=_ibis.ifelse(_matches.is_win, 3, _ibis.ifelse(_matches.is_draw, 1, 0))
    )

    _season_window = _ibis.window(group_by="season", order_by="utc_date")
    _running_points_expr = (
        _matches.mutate(running_points=_matches.points.sum().over(_season_window))
        .select("season", "utc_date", "points", "running_points")
        .order_by(["season", "utc_date"])
    )
    df_chart2 = dataset(_running_points_expr).df()
    return (df_chart2,)


@app.cell
def _(alt, df_chart2):
    _chart = (
        alt.Chart(df_chart2)
        .mark_line()
        .encode(
            x="utc_date:T",
            y="running_points:Q",
            color="season:O",
            tooltip=["season:O", "utc_date:T", "running_points:Q"],
        )
        .properties(title="Manchester United — Running Points Total per Season")
    )
    _chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Goals Scored vs Conceded per Season

    Total goals scored and conceded per season (from `score__full_time__home`
    / `score__full_time__away`, flipped depending on home/away), computed
    with ibis and reshaped to long form for a grouped bar chart.
    """)
    return


@app.cell
def _(dataset):
    import ibis as _ibis

    _t = dataset["team_matches"].to_ibis()
    _finished = _t.filter(_t.status == "FINISHED")
    _is_home = _finished.home_team__id == 66

    _goals = _finished.mutate(
        season=_finished.season__start_date.cast("date").year(),
        goals_scored=_ibis.ifelse(
            _is_home, _finished.score__full_time__home, _finished.score__full_time__away
        ),
        goals_conceded=_ibis.ifelse(
            _is_home, _finished.score__full_time__away, _finished.score__full_time__home
        ),
    )

    _season_goals_expr = (
        _goals.group_by("season")
        .aggregate(
            goals_scored=_goals.goals_scored.sum(),
            goals_conceded=_goals.goals_conceded.sum(),
        )
        .order_by("season")
    )
    _df_season_goals = dataset(_season_goals_expr).df()
    df_chart3 = _df_season_goals.melt(
        id_vars="season",
        value_vars=["goals_scored", "goals_conceded"],
        var_name="metric",
        value_name="goals",
    )
    return (df_chart3,)


@app.cell
def _(alt, df_chart3):
    _chart = (
        alt.Chart(df_chart3)
        .mark_bar()
        .encode(
            x="season:O",
            y="goals:Q",
            color="metric:N",
            xOffset="metric:N",
            tooltip=["season:O", "metric:N", "goals:Q"],
        )
        .properties(title="Manchester United — Goals Scored vs Conceded per Season")
    )
    _chart
    return


if __name__ == "__main__":
    app.run()
