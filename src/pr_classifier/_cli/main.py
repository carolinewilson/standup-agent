"""CLI entry point — thin wrapper over the pr_classifier library (FR-010)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import List, Optional

import typer

from pr_classifier import classify_repositories
from pr_classifier._exceptions import AuthenticationError, PartialResultError
from pr_classifier._models import ClassificationReport

app = typer.Typer(help="Classify GitHub pull requests by review state.")


def _serialise_report(report: ClassificationReport) -> dict:
    """Convert ClassificationReport to a JSON-serialisable dict per output-schema.md."""
    return {
        "generated_at": report.generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "staleness_threshold_hours": report.staleness_threshold_hours,
        "counts": report.counts,
        "repositories": [
            {
                "repo": rr.repo,
                "error": rr.error,
                "prs": [
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "author": pr.author,
                        "url": pr.url,
                        "last_activity_at": pr.last_activity_at.strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        "state": pr.state.value,
                    }
                    for pr in rr.prs
                ],
            }
            for rr in report.repositories
        ],
    }


@app.command()
def classify(
    repos: List[str] = typer.Argument(..., help="Repositories in owner/repo format."),
    token: Optional[str] = typer.Option(None, "--token", help="GitHub personal access token."),
    staleness_hours: int = typer.Option(48, "--staleness-hours", help="Inactivity threshold in hours."),
) -> None:
    """Classify open GitHub pull requests by review state."""
    # Resolve token from --token or GITHUB_TOKEN env var
    resolved_token = token or os.environ.get("GITHUB_TOKEN", "")

    try:
        report = classify_repositories(
            repos=repos,
            token=resolved_token,
            staleness_hours=staleness_hours,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)
    except AuthenticationError as exc:
        raise typer.Exit(1)
    except PartialResultError as exc:
        typer.echo(json.dumps(_serialise_report(exc.report), indent=2))
        raise typer.Exit(3)

    typer.echo(json.dumps(_serialise_report(report), indent=2))


if __name__ == "__main__":  # pragma: no cover
    app()

