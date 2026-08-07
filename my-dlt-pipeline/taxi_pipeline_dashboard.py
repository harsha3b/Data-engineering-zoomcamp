import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    import dlt
    return alt, dlt, mo


@app.cell
def _(dlt):
    pipeline = dlt.attach("taxi_pipeline")
    dataset = pipeline.dataset()
    return dataset, pipeline


@app.cell
def _(mo):
    mo.md("## NYC Taxi Dashboard — June 2009")
    return


@app.cell
def _(mo):
    mo.md("### Daily Revenue Trend")
    return


@app.cell
def _(dataset):
    df_chart1 = dataset("""
        SELECT
            DATE_TRUNC('day', trip_pickup_date_time) AS trip_date,
            SUM(total_amt) AS daily_revenue
        FROM ny_taxi
        GROUP BY 1
        ORDER BY 1
    """).df()
    return (df_chart1,)


@app.cell
def _(alt, df_chart1, mo):
    _chart = alt.Chart(df_chart1).mark_line(point=True).encode(
        x="trip_date:T",
        y="daily_revenue:Q",
        tooltip=["trip_date:T", "daily_revenue:Q"]
    ).properties(title="Daily Revenue Trend (June 2009)")
    _chart
    return


@app.cell
def _(mo):
    mo.md("### Daily Trip Volume Trend")
    return


@app.cell
def _(dataset):
    df_chart2 = dataset("""
        SELECT
            DATE_TRUNC('day', trip_pickup_date_time) AS trip_date,
            COUNT(*) AS trip_count
        FROM ny_taxi
        GROUP BY 1
        ORDER BY 1
    """).df()
    return (df_chart2,)


@app.cell
def _(alt, df_chart2, mo):
    _chart = alt.Chart(df_chart2).mark_line(point=True).encode(
        x="trip_date:T",
        y="trip_count:Q",
        tooltip=["trip_date:T", "trip_count:Q"]
    ).properties(title="Daily Trip Volume (June 2009)")
    _chart
    return


@app.cell
def _(mo):
    mo.md("### Fare vs Trip Distance")
    return


@app.cell
def _(dataset):
    df_chart3 = dataset("""
        SELECT
            FLOOR(trip_distance) AS distance_mile_bucket,
            AVG(fare_amt) AS avg_fare,
            COUNT(*) AS trip_count
        FROM ny_taxi
        WHERE trip_distance > 0 AND fare_amt > 0
        GROUP BY 1
        ORDER BY 1
    """).df()
    return (df_chart3,)


@app.cell
def _(alt, df_chart3, mo):
    _chart = alt.Chart(df_chart3).mark_circle().encode(
        x=alt.X("distance_mile_bucket:Q", title="Trip Distance (miles, binned)"),
        y=alt.Y("avg_fare:Q", title="Average Fare ($)"),
        size=alt.Size("trip_count:Q", title="Trip Count"),
        tooltip=["distance_mile_bucket:Q", "avg_fare:Q", "trip_count:Q"]
    ).properties(title="Average Fare by Trip Distance")
    _chart
    return


if __name__ == "__main__":
    app.run()
