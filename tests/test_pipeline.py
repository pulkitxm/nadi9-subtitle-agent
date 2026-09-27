import json


from pathlib import Path


import pytest


from nadi9.engine import Engine


from nadi9.models import Candidate, Correction, Limits, Pack, State


from nadi9.providers import ReplayProvider


from nadi9.storage import export, summary


@pytest.fixture
def pack():
    return Pack.model_validate_json(Path("fixtures/demo.json").read_text())


@pytest.fixture
def correction():
    return Correction.model_validate_json(Path("fixtures/correction.json").read_text())


def test_conflict_unsupported_term_and_context_are_not_silently_released(pack):
    state = Engine.start(pack).run()
    assert state.decisions["S001"].nadi_9_text == "mi ti vo"
    assert state.decisions["S002"].decision == "ABSTAIN"
    assert "poison-you@1" in state.decisions["S002"].evidence
    assert state.decisions["S002"].conflicts
    assert state.decisions["S003"].decision == "ABSTAIN"
    assert "dance" in state.decisions["S003"].review_question
    assert state.decisions["S004"].nadi_9_text == "Mira 7 vo"
    assert state.decisions["S005"].decision == "HUMAN_REVIEW"
    assert summary(state)["recommendation"] == "HOLD"


def test_timing_and_preserved_literals_are_verified(pack):
    pack.episode[3].end_ms = pack.episode[3].start_ms + 100
    state = Engine.start(pack).run()
    assert "reading_speed_exceeds_20_cps" in state.decisions["S004"].checks
    assert "duration_outside_1_to_7_seconds" in state.decisions["S004"].checks


def test_reproducible_offline_run(pack):
    assert Engine.start(pack).run().model_dump() == Engine.start(pack).run().model_dump()
