from nadi9.evidence import learn
from nadi9.models import Evidence, Example, Pack, Source, Unit


def small_pack():
    source = Source(
        id="s",
        author="fixture linguist",
        date="2026-01-01",
        scope="demo",
        reliability="reviewed",
        rationale="Synthetic reviewed examples",
    )
    unit = Unit(text="hello", role="greeting")
    examples = [
        Evidence(
            id=f"E{i}",
            source_id="s",
            locator=f"row {i}",
            kind="example",
            text="hello = zeni",
            example=Example(
                units=[unit], target_by_unit=["zeni"], target_order=[0], target_text="zeni"
            ),
        )
        for i in range(2)
    ]
    from nadi9.models import Line

    return Pack(
        id="fixture",
        synthetic=True,
        sources=[source],
        evidence=examples,
        episode=[
            Line(
                id="S1",
                source_text="hello",
                speaker="A",
                scene="demo",
                start_ms=0,
                end_ms=2000,
                units=[unit],
            )
        ],
    )


def test_rule_requires_two_observations_and_preserves_counterexamples():
    pack = small_pack()
    pack.evidence.append(
        Evidence(
            id="word",
            source_id="s",
            locator="entry 1",
            kind="lexical",
            text="hello = zeni",
            key="hello",
            value="zeni",
        )
    )
    assert learn(pack)[0].status == "SUPPORTED"
    pack.evidence[1].example.target_by_unit = ["wrong"]
    pack.evidence[1].example.target_text = "wrong"
    claim = learn(pack)[0]
    assert claim.status == "CONTESTED"
    assert claim.counterexamples == ["E1@1"]


def test_model_proposed_rule_without_examples_is_unsupported():
    pack = small_pack()
    pack.evidence.append(
        Evidence(
            id="rule",
            source_id="s",
            locator="hypothesis",
            kind="grammar",
            text="unverified",
            key="word_order",
            value=["verb", "subject"],
        )
    )
    claim = learn(pack)[0]
    assert claim.status == "UNSUPPORTED"
    assert not claim.supporting
