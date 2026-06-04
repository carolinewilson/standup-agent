"""Integration tests for the CLI (T011).

These tests FAIL before T016 — the real classify command is not yet implemented.
Uses Typer's CliRunner to invoke the app in-process.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from pr_classifier._cli.main import app
from pr_classifier._exceptions import AuthenticationError, PartialResultError
from pr_classifier._models import (
    ClassificationReport,
    ClassificationState,
    RepositoryResult,
)

runner = CliRunner(mix_stderr=False)

UTC = timezone.utc
NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC)


def _minimal_report(repos: list[str] | None = None) -> ClassificationReport:
    return ClassificationReport(
        repositories=[
            RepositoryResult(repo=r, prs=[], error=None)
            for r in (repos or ["owner/repo"])
        ],
        generated_at=NOW,
        staleness_threshold_hours=48,
        counts={s.value: 0 for s in ClassificationState},
    )


# ---------------------------------------------------------------------------
# Success path (exit 0)
# ---------------------------------------------------------------------------


def test_cli_exit_0_on_success(mocker):
    """Successful classification → exit code 0."""
    mocker.patch(
        "pr_classifier._cli.main.classify_repositories",
        return_value=_minimal_report(),
        create=True,
    )
    result = runner.invoke(app, ["owner/repo", "--token", "tok"])
    assert result.exit_code == 0


def test_cli_valid_output_shape(mocker):
    """stdout is valid JSON with required top-level keys on success."""
    mocker.patch(
        "pr_classifier._cli.main.classify_repositories",
        return_value=_minimal_report(),
        create=True,
    )
    result = runner.invoke(app, ["owner/repo", "--token", "tok"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "generated_at" in data
    assert "staleness_threshold_hours" in data
    assert "counts" in data
    assert "repositories" in data


# ---------------------------------------------------------------------------
# Authentication error (exit 1)
# ---------------------------------------------------------------------------


def test_cli_exit_1_on_auth_error(mocker):
    """AuthenticationError from library → exit 1, nothing on stdout."""
    mocker.patch(
        "pr_classifier._cli.main.classify_repositories",
        side_effect=AuthenticationError("bad token"),
        create=True,
    )
    result = runner.invoke(app, ["owner/repo", "--token", "bad"])
    assert result.exit_code == 1
    assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Validation error (exit 2)
# ---------------------------------------------------------------------------


def test_cli_exit_2_on_empty_repos():
    """No REPOS argument → exit 2."""
    result = runner.invoke(app, ["--token", "tok"])
    assert result.exit_code == 2


def test_cli_exit_2_on_missing_token(mocker):
    """No token (neither --token nor GITHUB_TOKEN env) → exit 2."""
    mocker.patch.dict("os.environ", {}, clear=True)
    result = runner.invoke(app, ["owner/repo"])
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Partial results (exit 3)
# ---------------------------------------------------------------------------


def test_cli_exit_3_on_partial(mocker):
    """PartialResultError from library → exit 3, JSON still on stdout."""
    partial_report = _minimal_report()
    mocker.patch(
        "pr_classifier._cli.main.classify_repositories",
        side_effect=PartialResultError(partial_report),
        create=True,
    )
    result = runner.invoke(app, ["owner/repo", "--token", "tok"])
    assert result.exit_code == 3
    data = json.loads(result.stdout)
    assert "repositories" in data
