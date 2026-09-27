from nadi9.evidence import dependency_keys, in_scope, learn, relevant, resolve
from nadi9.models import (
    BudgetExhausted,
    Candidate,
    Correction,
    Decision,
    Limits,
    Line,
    Pack,
    State,
    words,
)
from nadi9.providers import ProposalProvider, ProviderUnavailable, ReplayProvider
from nadi9.verify import verify


class Engine:
    def __init__(self, state: State, provider: ProposalProvider | None = None):
        self.state = state
        self.provider = provider or ReplayProvider()

    @classmethod
    def start(cls, pack: Pack, limits: Limits | None = None, provider=None):
        state = State(pack=pack, limits=limits or Limits(), claims=learn(pack))
        engine = cls(state, provider)
        engine.replan()
        engine.event("initialized", pack=pack.model_dump(mode="json"))
        return engine

    def event(self, kind: str, **details):
        self.state.events.append(
            {
                "sequence": len(self.state.events) + 1,
                "revision": self.state.revision,
                "kind": kind,
                **details,
            }
        )

    def risk(self, line: Line) -> int:
        missing = sum(
            resolve(line, self.state.claims, unit.text, "lexical")[0] is None
            for unit in line.units
            if not unit.literal
        )
        return missing * 10 + len(line.risks) * 5 + len(line.assumptions)

    def replan(self, affected: set[str] | None = None):
        lines = [
            line for line in self.state.pack.episode if affected is None or line.id in affected
        ]
        lines.sort(key=lambda line: (-self.risk(line), line.start_ms, line.id))
        self.state.plan = [line.id for line in lines]
        self.event("plan", priority=[{"id": line.id, "risk": self.risk(line)} for line in lines])

    def run(self, max_lines: int | None = None):
        lines = {line.id: line for line in self.state.pack.episode}
        pending = self.state.plan[:] if max_lines is None else self.state.plan[:max_lines]
        for subtitle_id in pending:
            self.state.decisions[subtitle_id] = self.process(lines[subtitle_id])
            self.state.plan.remove(subtitle_id)
            self.event("decision", decision=self.state.decisions[subtitle_id].model_dump())
        return self.state

    def process(self, line: Line) -> Decision:
        claims = self.state.claims
        dependencies = dependency_keys(line)
        conflicts, missing, refs = [], [], set()
        lexical = []
        grammar = None
        candidate = None
        checks = []
        try:
            self.state.limits.charge("tool")
            for unit in line.units:
                claim, disagreements = (
                    (None, []) if unit.literal else resolve(line, claims, unit.text, "lexical")
                )
                lexical.append(claim)
                conflicts.extend(disagreements)
                if not unit.literal and claim is None:
                    missing.append(unit.text)
            grammar, disagreements = resolve(line, claims, "word_order", "grammar")
            conflicts.extend(disagreements)
            if grammar is None:
                missing.append("word_order")
            for key in dependencies:
                kind, term = key.split(":", 1)
                for claim in relevant(line, claims, term, kind):
                    refs.update([claim.id, *claim.supporting, *claim.counterexamples])
            if not missing:
                for attempt in range(2):
                    self.state.limits.charge("model")
                    try:
                        candidate = Candidate.model_validate(
                            self.provider.propose(line, lexical, grammar)
                        )
                        break
                    except (ProviderUnavailable, TimeoutError, ConnectionError) as error:
                        self.event(
                            "provider_failure",
                            subtitle_id=line.id,
                            attempt=attempt + 1,
                            error=type(error).__name__,
                        )
                        if attempt == 1:
                            checks.append("provider_unavailable_after_retry")
                if candidate is not None:
                    self.state.limits.charge("tool")
                    checks = verify(line, candidate, claims, self.state.pack)
                    refs.update(candidate.evidence)
        except BudgetExhausted as error:
            checks.append(str(error))
        except (ValueError, TypeError, AttributeError, StopIteration):
            checks.append("invalid_provider_response")
        issues = list(
            dict.fromkeys(conflicts + [f"Unsupported: {key}" for key in missing] + checks)
        )
        if line.risks:
            issues.extend(f"Context review: {risk}" for risk in line.risks)
        approved = candidate is not None and not issues
        status = "APPROVED" if approved else "HUMAN_REVIEW" if candidate else "ABSTAIN"
        return Decision(
            subtitle_id=line.id,
            source_text=line.source_text,
            nadi_9_text=candidate.text if approved else None,
            proposed_text=candidate.text if candidate else None,
            confidence=0.85 if approved else 0.4 if candidate else 0,
            confidence_reason=(
                "Heuristic support score, not a probability: every claim has two reviewed examples; "
                "independent vocabulary, order, literal and timing checks passed."
                if approved
                else "Heuristic support score: " + "; ".join(issues)
            ),
            decision=status,
            evidence=sorted(refs),
            assumptions=line.assumptions,
            conflicts=conflicts,
            checks=checks,
            dependencies=dependencies,
            review_question=None
            if approved
            else (
                f"For {line.id}, speaker {line.speaker} in {line.scene} ({line.context}), "
                "please resolve: "
                + "; ".join(issues)
                + ". Which cited evidence supports the answer?"
            ),
            revision=self.state.revision,
        )
