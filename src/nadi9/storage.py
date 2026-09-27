import json
import os
import tempfile
from pathlib import Path
from textwrap import wrap

from nadi9.models import State


def timestamp(milliseconds: int) -> str:
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def summary(state: State) -> dict:
    statuses = {
        kind: sum(item.decision == kind for item in state.decisions.values())
        for kind in ("APPROVED", "HUMAN_REVIEW", "ABSTAIN")
    }
    hold = (
        state.pack.synthetic or bool(state.plan) or statuses["APPROVED"] != len(state.pack.episode)
    )
    return {
        "pack": state.pack.id,
        "synthetic": state.pack.synthetic,
        "revision": state.revision,
        "recommendation": "HOLD" if hold else "READY_FOR_FINAL_EXPERT_SIGNOFF",
        "decisions": statuses,
        "pending": state.plan,
        "calls": state.limits.model_dump(),
    }


def atomic_write(path: Path, text: str):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def export(state: State, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    ordered = sorted(state.pack.episode, key=lambda line: (line.start_ms, line.id))
    decisions = [state.decisions[line.id] for line in ordered if line.id in state.decisions]
    blocks = []
    for index, line in enumerate(ordered, 1):
        decision = state.decisions.get(line.id)
        text = decision.nadi_9_text if decision else None
        rendered = "\n".join(wrap(text, width=42)) if text else f"[REVIEW REQUIRED: {line.id}]"
        blocks.append(
            f"{index}\n{timestamp(line.start_ms)} --> {timestamp(line.end_ms)}\n{rendered}\n"
        )
    report = summary(state)
    rows = [
        "# Release recommendation: " + report["recommendation"],
        "",
        "Synthetic demonstration only." if state.pack.synthetic else "Expert signoff required.",
        "",
        "The SRT is a review draft. Withheld lines contain explicit review markers.",
        "",
        "| Subtitle | Status | Supported proposal |",
        "| --- | --- | --- |",
    ]
    for item in decisions:
        text = (item.nadi_9_text or "withheld").replace("|", "\\|").replace("\n", " ")
        rows.append(f"| {item.subtitle_id} | {item.decision} | {text} |")
    rows.extend(
        [
            "",
            (
                f"Calls: {state.limits.model_calls}/{state.limits.max_model_calls} model; "
                f"{state.limits.tool_calls}/{state.limits.max_tool_calls} tool."
            ),
            "",
            "Confidence values are heuristic support scores, not calibrated probabilities.",
        ]
    )
    files = {
        "subtitles.srt": "\n".join(blocks),
        "subtitle_decisions.jsonl": "\n".join(item.model_dump_json() for item in decisions) + "\n",
        "learned_rules.json": json.dumps([item.model_dump() for item in state.claims]) + "\n",
        "evidence_records.jsonl": "\n".join(item.model_dump_json() for item in state.pack.evidence)
        + "\n",
        "review_queue.json": json.dumps(
            [item.model_dump() for item in decisions if item.decision != "APPROVED"]
        )
        + "\n",
        "audit.jsonl": "\n".join(json.dumps(event) for event in state.events) + "\n",
        "final_report.md": "\n".join(rows) + "\n",
        "state.json": state.model_dump_json() + "\n",
    }
    for name, content in files.items():
        atomic_write(output / name, content)
