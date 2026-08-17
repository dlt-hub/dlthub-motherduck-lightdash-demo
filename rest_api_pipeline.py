from typing import Any

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources


@dlt.source(name="jaffle_shop")
def jaffle_shop_source(
    base_url: str = "https://jaffle-shop.dlthub.com/api/v1/",
    page_size: int = 100,
) -> Any:
    """Load data from the dltHub Jaffle Shop API (public, no auth).

    Args:
        base_url: API base URL. Override via `[sources.jaffle_shop] base_url` in config.toml.
        page_size: Rows per page. The API paginates with a `Link: rel="next"` header.

    Example:
        pipeline.run(jaffle_shop_source())
        pipeline.run(jaffle_shop_source(page_size=500))
    """
    config: RESTAPIConfig = {
        "client": {
            "base_url": base_url,
            # The API signals the next page with a `Link` header (rel="next")
            "paginator": "header_link",
        },
        "resource_defaults": {
            "primary_key": "id",
            "write_disposition": "replace",
            "endpoint": {
                "params": {
                    "page_size": page_size,
                },
            },
        },
        "resources": [
            {
                "name": "customers",
                "endpoint": {
                    "path": "customers",
                },
            },
        ],
    }

    yield from rest_api_resources(config)


@run.pipeline("jaffle_shop", trigger=trigger.schedule("0 3 * * *"))  # daily at 03:00 UTC
def load_jaffle_shop() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="jaffle_shop",
        destination="motherduck",
        dataset_name="jaffle_shop_data",
    )

    load_info = pipeline.run(jaffle_shop_source())
    print(load_info)  # noqa: T201


if __name__ == "__main__":
    load_jaffle_shop()
