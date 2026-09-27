from typing import Protocol

from nadi9.models import Candidate, Claim, Line


class ProviderUnavailable(RuntimeError):
    pass


class ProposalProvider(Protocol):
    def propose(self, line: Line, lexical: list[Claim | None], grammar: Claim) -> Candidate: ...


class ReplayProvider:
    def __init__(self, failures: int = 0):
        self.failures = failures

    def propose(self, line: Line, lexical: list[Claim | None], grammar: Claim) -> Candidate:
        if self.failures:
            self.failures -= 1
            raise ProviderUnavailable("Replay provider temporarily unavailable")
        pieces = []
        used = set()
        for role in grammar.value:
            index = next(
                i for i, unit in enumerate(line.units) if unit.role == role and i not in used
            )
            used.add(index)
            claim = lexical[index]
            pieces.append(line.units[index].text if claim is None else str(claim.value))
        claims = [grammar] + [claim for claim in lexical if claim is not None]
        refs = sorted({ref for claim in claims for ref in [claim.id, *claim.supporting]})
        return Candidate(text=" ".join(pieces), evidence=refs)
