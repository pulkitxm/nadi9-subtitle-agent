from nadi9.models import Claim, Evidence, Line, Pack, words


def in_scope(scope: dict[str, str], context: dict[str, str]) -> bool:
    return all(context.get(key) == value for key, value in scope.items())


def reference(item: Evidence) -> str:
    return f"{item.id}@{item.revision}"


def observations(item: Evidence, hypothesis: Evidence) -> list[str | list[str]]:
    example = item.example
    if example is None or not in_scope(hypothesis.scope, example.context):
        return []
    if hypothesis.kind == "grammar":
        if sorted(unit.role for unit in example.units) != sorted(hypothesis.value):
            return []
        return [[example.units[i].role for i in example.target_order]]
    return [
        target
        for unit, target in zip(example.units, example.target_by_unit)
        if words(unit.text) == words(hypothesis.key) and not unit.literal
    ]


def learn(pack: Pack) -> list[Claim]:
    sources = {item.id: item for item in pack.sources}
    usable = [
        item
        for item in pack.evidence
        if item.active and sources[item.source_id].reliability != "untrusted"
    ]
    examples = [
        item
        for item in usable
        if item.kind == "example" and sources[item.source_id].reliability == "reviewed"
    ]
    claims = []
    for item in usable:
        if item.kind not in {"lexical", "grammar"}:
            continue
        supporting, counterexamples = [], []
        for example in examples:
            values = observations(example, item)
            if item.value in values:
                supporting.append(reference(example))
            if any(value != item.value for value in values):
                counterexamples.append(reference(example))
        status = "UNSUPPORTED"
        if counterexamples:
            status = "CONTESTED"
        elif len(supporting) >= 2:
            status = "SUPPORTED"
        claims.append(
            Claim(
                id=reference(item),
                kind=item.kind,
                key=item.key,
                value=item.value,
                scope=item.scope,
                supporting=supporting,
                counterexamples=counterexamples,
                status=status,
            )
        )
    return claims


def relevant(line: Line, claims: list[Claim], key: str, kind: str) -> list[Claim]:
    matches = [
        claim
        for claim in claims
        if claim.kind == kind
        and words(claim.key) == words(key)
        and in_scope(claim.scope, line.context)
    ]
    if not matches:
        return []
    specificity = max(len(claim.scope) for claim in matches)
    return [claim for claim in matches if len(claim.scope) == specificity]


def resolve(line: Line, claims: list[Claim], key: str, kind: str) -> tuple[Claim | None, list[str]]:
    matches = relevant(line, claims, key, kind)
    if kind == "grammar":
        matches = [
            claim
            for claim in matches
            if sorted(claim.value) == sorted(unit.role for unit in line.units)
        ]
    values = {str(claim.value) for claim in matches}
    conflicts = []
    if len(values) > 1:
        conflicts.append(f"Competing {key} claims: " + ", ".join(claim.id for claim in matches))
    if any(claim.counterexamples for claim in matches):
        conflicts.append(
            f"Counterexamples for {key}: "
            + ", ".join(sorted({ref for claim in matches for ref in claim.counterexamples}))
        )
    supported = [claim for claim in matches if claim.status == "SUPPORTED"]
    return (supported[0] if supported and not conflicts else None), conflicts


def dependency_keys(line: Line) -> list[str]:
    return sorted(
        {"grammar:word_order"}
        | {"lexical:" + " ".join(words(unit.text)) for unit in line.units if not unit.literal}
    )
