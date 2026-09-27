from collections import Counter
from textwrap import wrap

from nadi9.evidence import in_scope, observations, reference
from nadi9.models import Candidate, Claim, Line, Pack, words


def verify(line: Line, proposal: Candidate, claims: list[Claim], pack: Pack) -> list[str]:
    failures = []
    records = {reference(item): item for item in pack.evidence if item.active}
    sources = {source.id: source for source in pack.sources}
    if any(ref not in records for ref in proposal.evidence):
        failures.append("unknown_or_stale_evidence")
    cited = [claim for claim in claims if claim.id in proposal.evidence]
    valid = []
    for claim in cited:
        original = records.get(claim.id)
        if original is None or not in_scope(claim.scope, line.context):
            failures.append("claim_scope_mismatch")
            continue
        corroboration = set()
        contrary = False
        for ref, item in records.items():
            if sources[item.source_id].reliability != "reviewed":
                continue
            observed = observations(item, original)
            if any(value != claim.value for value in observed):
                contrary = True
            if claim.value in observed and ref in proposal.evidence:
                corroboration.add(ref)
        if contrary or len(corroboration) < 2:
            failures.append(f"insufficient_corroboration:{claim.key}")
        else:
            valid.append(claim)
    grammars = [claim for claim in valid if claim.kind == "grammar"]
    if len(grammars) != 1:
        return sorted(set(failures + ["grammar_not_verified"]))
    grammar = grammars[0]
    if Counter(grammar.value) != Counter(unit.role for unit in line.units):
        return sorted(set(failures + ["grammar_roles_mismatch"]))
    translations = []
    for unit in line.units:
        choices = [
            claim
            for claim in valid
            if claim.kind == "lexical" and words(claim.key) == words(unit.text)
        ]
        if unit.literal:
            translations.append(unit.text)
        elif len(choices) == 1:
            translations.append(str(choices[0].value))
        else:
            failures.append(f"vocabulary_not_verified:{unit.text}")
            translations.append("")
    indexes = list(range(len(line.units)))
    expected = []
    for role in grammar.value:
        index = next(index for index in indexes if line.units[index].role == role)
        indexes.remove(index)
        expected.append(translations[index])
    if proposal.text != " ".join(expected):
        failures.append("unsupported_addition_omission_or_order")
    duration = (line.end_ms - line.start_ms) / 1000
    if len(proposal.text) / duration > 20:
        failures.append("reading_speed_exceeds_20_cps")
    if len(wrap(proposal.text, width=42)) > 2:
        failures.append("subtitle_exceeds_two_42_character_lines")
    if any(len(word) > 42 for word in proposal.text.split()):
        failures.append("unbreakable_word_exceeds_42_characters")
    if duration < 1 or duration > 7:
        failures.append("duration_outside_1_to_7_seconds")
    for other in pack.episode:
        if other.id != line.id and line.start_ms < other.end_ms and other.start_ms < line.end_ms:
            failures.append(f"overlapping_subtitle:{other.id}")
    return sorted(set(failures))
