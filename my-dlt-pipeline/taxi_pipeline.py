from typing import Any

import dlt
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources


@dlt.source(name="taxi")
def taxi_source() -> Any:
    config: RESTAPIConfig = {
        "client": {
            "base_url": "https://us-central1-dlthub-analytics.cloudfunctions.net/",
        },
        "resource_defaults": {
            "write_disposition": "replace",
        },
        "resources": [
            {
                "name": "ny_taxi",
                "endpoint": {
                    "path": "data_engineering_zoomcamp_api",
                    # API returns a raw JSON array (no wrapper object)
                    "data_selector": "$",
                    "paginator": {
                        "type": "page_number",
                        "page_param": "page",
                        "base_page": 1,
                        # total_path defaults to "total" (a response key) - this API
                        # doesn't report a total, so disable it. stop_after_empty_page
                        # defaults to True: pagination stops once a page is empty.
                        "total_path": None,
                    },
                },
            },
        ],
    }

    yield from rest_api_resources(config)


def load_taxi() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="taxi_pipeline",
        destination="duckdb",
        dataset_name="taxi_data",
        dev_mode=True,
    )

    load_info = pipeline.run(taxi_source())
    print(load_info)  # noqa: T201


if __name__ == "__main__":
    load_taxi()