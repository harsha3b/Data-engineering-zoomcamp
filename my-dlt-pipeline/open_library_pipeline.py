"""Pipeline to ingest book search results from the Open Library REST API."""

import dlt
from dlt.sources.rest_api import rest_api_resources
from dlt.sources.rest_api.typing import RESTAPIConfig


@dlt.source
def open_library_rest_api_source(query: str = "harry potter"):
    """Define dlt resources from Open Library REST API endpoints.

    Args:
        query: Search query passed to the Open Library search API (`q` param).
    """
    config: RESTAPIConfig = {
        "client": {
            # Open Library API requires no authentication
            "base_url": "https://openlibrary.org/",
        },
        "resources": [
            {
                "name": "books",
                "endpoint": {
                    "path": "search.json",
                    "params": {
                        "q": query,
                    },
                    "data_selector": "docs",
                },
                "primary_key": "key",
            },
        ],
    }

    yield from rest_api_resources(config)


pipeline = dlt.pipeline(
    pipeline_name='open_library_pipeline',
    destination='duckdb',
    # fresh dataset on every run while debugging
    dev_mode=True,
    # show basic progress of resources extracted, normalized files and load-jobs on stdout
    progress="log",
)


if __name__ == "__main__":
    load_info = pipeline.run(
        open_library_rest_api_source().add_limit(1),
        write_disposition="replace",
    )
    print(load_info)  # noqa: T201
