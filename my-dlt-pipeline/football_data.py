import dlt
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources
from tomlkit import date
from datetime import date as dt, timedelta


def date_chunks(years_back=10, chunk_days=700):
    """Yield (dateFrom, dateTo) tuples covering the past N years in <750-day chunks."""
    end = dt.today()
    start_boundary = end.replace(year=end.year - years_back)
    chunks = []
    current_end = end
    while current_end > start_boundary:
        current_start = max(current_end - timedelta(days=chunk_days), start_boundary)
        chunks.append((current_start.isoformat(), current_end.isoformat()))
        current_end = current_start - timedelta(days=1)
    return chunks

@dlt.source
def football_data_source(api_key: str = dlt.secrets.value):
    config: RESTAPIConfig = {
        "client": {
            "base_url": "https://api.football-data.org/v4/",
            "headers": {
                "X-Auth-Token": api_key,
            },
        "paginator": {
            "type": "single_page",  # or "offset", "page_number", "cursor", "json_link", etc.
            },
        },
        "resource_defaults": {
            "primary_key": "id",
        },
        "resources": [
            {
                "name": "team",
                "endpoint": {
                    "path": "teams/66",
                    "data_selector": "$", # single object response, not a list -> select the whole body
                },
            },
            {
                "name": "team_matches",
                "endpoint": {
                    "path": "teams/66/matches",
                    "params": {
                        "dateFrom": (dt.today().replace(year=dt.today().year - 2)).isoformat(),
                        "dateTo": dt.today().isoformat(),
                    },
                    # block for paginator can be added here if needed, but football-data.org API does not provide pagination for this endpoint
                # "paginator": {
                #      "type": "offset",
                #     "limit": 100,
                #     "offset_param": "offset",
                #      "limit_param": "limit",
                #     },
                },
            },
        ],
    }
    yield from rest_api_resources(config)

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="football_data_pipeline",
        destination="duckdb",
        dataset_name="football_data",
    )
    load_info = pipeline.run(football_data_source())
    print(load_info)
    