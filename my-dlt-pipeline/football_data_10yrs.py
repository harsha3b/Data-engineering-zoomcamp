"""
Pulls Manchester United's match history for the past 10 years from football-data.org.
Splits the range into <750-day chunks (API limit) and loads them all into one table.
"""

from datetime import date, timedelta

import dlt
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources


def date_chunks(years_back: int = 10, chunk_days: int = 700):
    """Yield (dateFrom, dateTo) ISO date string tuples covering the past N years,
    each chunk no longer than chunk_days (API cap is 750 days)."""
    end = date.today()
    start_boundary = end.replace(year=end.year - years_back)
    chunks = []
    current_end = end
    while current_end > start_boundary:
        current_start = max(current_end - timedelta(days=chunk_days), start_boundary)
        chunks.append((current_start.isoformat(), current_end.isoformat()))
        current_end = current_start - timedelta(days=1)
    return chunks


@dlt.source
def football_data_10yr_source(api_key: str = dlt.secrets.value):
    match_resources = [
        {
            "name": f"team_matches_{i}",
            "endpoint": {
                "path": "teams/66/matches",
                "params": {"dateFrom": start, "dateTo": end},
                "data_selector": "matches",
            },
            "table_name": "team_matches",  # all chunks land in the same table
        }
        for i, (start, end) in enumerate(date_chunks())
    ]

    config: RESTAPIConfig = {
        "client": {
            "base_url": "https://api.football-data.org/v4/",
            "headers": {
                "X-Auth-Token": api_key,
            },
        },
        "resource_defaults": {
            "primary_key": "id",
        },
        "resources": match_resources,
    }
    yield from rest_api_resources(config)


def run_pipeline():
    pipeline = dlt.pipeline(
        pipeline_name="football_data_10yr_pipeline",
        destination="duckdb",
        dataset_name="football_data_10yr",
    )
    load_info = pipeline.run(football_data_10yr_source())
    print(load_info)
    return load_info


if __name__ == "__main__":
    run_pipeline()