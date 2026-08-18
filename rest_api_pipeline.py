"""Load GitHub REST API data for a single repository into MotherDuck."""

from typing import Any, Optional

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources

# pages (of 100 records) to pull per resource, overridable in config.toml
DEFAULT_PAGES_PER_RESOURCE = 5


@dlt.source(name="github")
def github_source(
    owner: str = "dlt-hub",
    repo: str = "dlt",
    access_token: Optional[str] = dlt.secrets.value,
) -> Any:
    """Load data from the GitHub REST API for one repository.

    Args:
        owner: repository owner or org, e.g. "dlt-hub".
        repo: repository name, e.g. "dlt".
        access_token: optional GitHub personal access token. Auto-loaded from
            secrets.toml when present. Public endpoints work without one, but
            unauthenticated requests are capped at 60/hour per IP (5,000/hour
            with a token).

    Resources: commits, issues, contributors.

    Note: GitHub treats every pull request as an issue, so the `issues`
    resource also returns PRs -- they are the rows where `pull_request__url`
    is not null.

    Examples:
        pipeline.run(github_source())
        pipeline.run(github_source(owner="duckdb", repo="duckdb"))
        pipeline.run(github_source().with_resources("contributors"))
    """
    config: RESTAPIConfig = {
        "client": {
            "base_url": f"https://api.github.com/repos/{owner}/{repo}/",
            # public repos need no auth -- attach it only when a token is configured
            "auth": ({"type": "bearer", "token": access_token} if access_token else None),
            "headers": {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            # GitHub returns next/prev/last URLs in the Link response header
            "paginator": {"type": "header_link"},
        },
        "resource_defaults": {
            "write_disposition": "replace",
            "endpoint": {
                "params": {
                    "per_page": 100,
                },
            },
        },
        "resources": [
            {
                "name": "commits",
                # commit objects carry no `id` field -- `sha` is the natural key
                "primary_key": "sha",
                "endpoint": {
                    "path": "commits",
                },
            },
            {
                "name": "issues",
                "primary_key": "id",
                "endpoint": {
                    "path": "issues",
                    "params": {
                        # the endpoint defaults to open issues only
                        "state": "all",
                        "sort": "updated",
                        "direction": "desc",
                    },
                },
            },
            {
                "name": "contributors",
                "primary_key": "id",
                "endpoint": {
                    "path": "contributors",
                    # 204 = empty repository, nothing to load
                    "response_actions": [{"status_code": 204, "action": "ignore"}],
                },
            },
        ],
    }

    yield from rest_api_resources(config)


@run.pipeline("github_api", trigger=trigger.schedule("0 3 * * *"))
def load_github() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="github_api",
        destination="motherduck",
        dataset_name="github_data",
    )

    # unauthenticated GitHub allows 60 requests/hour per IP, so cap the pages
    # per resource. Configure a token and raise this to load full history.
    pages = dlt.config.get("pages_per_resource", int) or DEFAULT_PAGES_PER_RESOURCE
    load_info = pipeline.run(github_source().add_limit(pages))
    print(load_info)  # noqa: T201


if __name__ == "__main__":
    load_github()
