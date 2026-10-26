"""Meterless — the investigation as a replayable mission.

Meterless (meterless.ai) is a local-first agentic platform, not a
metering/billing API. There is no Python SDK, no pip package and no
public REST API. So AddUp does not import Meterless — it RUNS through
it: each investigation is saved as a Meterless Nightshift mission, a
replayable workflow whose steps are vision-verified and whose replay
costs 0 new tokens. That is Meterless's value proposition (the workflow
is the asset), and it is exactly how the hackathon frames it: "run your
product through Meterless Nightshift on NVIDIA Nemotron."

This module writes the mission file (JSON) alongside the investigation
report. The file records the question, the data sources, the judge's
verdict and evidence, and the Nemotron explanation, so the whole
investigation can be replayed and audited step by step.
"""

from __future__ import annotations

import json
from pathlib import Path


def save_mission(
    *,
    path: str | Path,
    question: str,
    sources: list[str],
    verdict: bool,
    evidence: list[str],
    explanation: str,
    model: str,
) -> Path:
    """Save the investigation as a Meterless Nightshift mission file."""
    mission = {
        "product": "meterless-nightshift",
        "mission": "addup-investigation",
        "question": question,
        "sources": sources,
        "model": model,
        "steps": [
            {
                "step": 1,
                "name": "query",
                "detail": "Query the federated payments view (Zetaris) "
                "or load the local DUO episodes.",
            },
            {
                "step": 2,
                "name": "add-up",
                "detail": "Sum payments per payee across agents; flag team "
                "totals over the per-payee limit.",
            },
            {
                "step": 3,
                "name": "explain",
                "detail": "Nemotron explains the verdict with per-agent evidence.",
            },
        ],
        "verdict": {
            "coalition_overspend": verdict,
            "evidence": evidence,
            "explanation": explanation,
        },
        "replay": "Re-running this mission replays the same three steps "
        "against the same sources; the workflow is the asset.",
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(mission, indent=2))
    return out
