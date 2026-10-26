"""Zetaris data layer.

Zetaris is a data fabric: it federates queries across sources so the
agent queries ONE view instead of reading files directly. For AddUp the
two sources are the agents' tool logs and their chat logs. The federated
view ``payments_by_agent`` sums payments per payee across agents — the
same add-up the judge performs, pushed down into the fabric.

Setup (free 60-day trial at zetaris.com, or Zetaris Cloud free tier):
  1. Upload the two log datasets (CSV/Parquet) via the Data Fabric
     File System.
  2. Create the view, e.g.:
         CREATE DATASOURCE VIEW payments_by_agent AS (
           SELECT agent, payee, SUM(amount) AS total_paid
           FROM tool_logs WHERE tool = 'pay' AND status = 'paid'
           GROUP BY agent, payee
         )
  3. Set these environment variables from the trial account:
         ZETARIS_API_URL   e.g. https://apiservice.trial.enterprise.zetaris.com
         ZETARIS_ORG_ID    your organisation id
         ZETARIS_API_KEY   your decrypt / API key
         ZETARIS_VIEW      view name, default "payments_by_agent"

The exact REST path is confirmed from inside a trial account (the public
knowledge-base article links to example scripts that 404). ``query_view``
uses the documented v5+ advanced-API pattern (POST a SQL statement,
rows back as JSON) and raises a clear error if the endpoint shape
differs, instead of silently returning wrong data.

When Zetaris is not configured, the agent runs in LOCAL mode on the
bundled DUO episodes (``addup.data``). Local mode is for development
and the demo only — it is NOT presented as a Zetaris integration.
"""

from __future__ import annotations

import os

import requests


class ZetarisNotConfigured(RuntimeError):
    """Raised when the agent is asked to query Zetaris without credentials."""


class ZetarisClient:
    """Minimal client for the Zetaris advanced REST API (v5+)."""

    def __init__(
        self,
        api_url: str | None = None,
        org_id: str | None = None,
        api_key: str | None = None,
        view: str = "payments_by_agent",
        timeout: int = 60,
    ):
        self.api_url = (api_url or os.environ.get("ZETARIS_API_URL") or "").rstrip("/")
        self.org_id = org_id or os.environ.get("ZETARIS_ORG_ID") or ""
        self.api_key = api_key or os.environ.get("ZETARIS_API_KEY") or ""
        self.view = view or os.environ.get("ZETARIS_VIEW", "payments_by_agent")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.org_id and self.api_key)

    def require_configured(self) -> None:
        if not self.configured:
            raise ZetarisNotConfigured(
                "Zetaris is not configured. Set ZETARIS_API_URL, "
                "ZETARIS_ORG_ID and ZETARIS_API_KEY from a trial account "
                "(free 60-day trial at zetaris.com), or run in local mode."
            )

    def query_view(self, sql: str | None = None) -> list[dict]:
        """Query the federated payments view and return rows as dicts.

        Default SQL sums payments per payee across agents — the add-up.
        """
        self.require_configured()
        statement = sql or (
            f"SELECT agent, payee, SUM(amount) AS total_paid "
            f"FROM {self.view} GROUP BY agent, payee"
        )
        resp = requests.post(
            f"{self.api_url}/api/v5/query",
            json={
                "orgId": self.org_id,
                "statement": statement,
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        if resp.status_code == 404:
            raise RuntimeError(
                "Zetaris query endpoint returned 404. The v5+ path "
                "(/api/v5/query) did not match this account's API. Confirm "
                "the exact advanced-API path from the trial console or the "
                "knowledge-base advanced-API docs before retrying."
            )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("rows") or data.get("data") or data
        if not isinstance(rows, list):
            raise RuntimeError(f"Unexpected Zetaris response shape: {type(rows)}")
        return rows
