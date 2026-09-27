import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def words(text: str) -> list[str]:
    return re.findall(r"\w+(?:['-]\w+)*", text.casefold())


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Record):
    id: str
    author: str
    date: date
    scope: str
    reliability: Literal["reviewed", "provisional", "untrusted"]
    rationale: str


class Unit(Record):
    text: str = Field(min_length=1)
    role: str
    literal: bool = False


class Example(Record):
    units: list[Unit]
    target_by_unit: list[str]
    target_order: list[int]
    target_text: str
    context: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent_alignment(self):
        if len(self.units) != len(self.target_by_unit):
            raise ValueError("Example alignment must cover every source unit")
        if any(not target.strip() for target in self.target_by_unit):
            raise ValueError("Example targets must be nonempty")
        if sorted(self.target_order) != list(range(len(self.units))):
            raise ValueError("Example order must use each unit exactly once")
        expected = " ".join(self.target_by_unit[i] for i in self.target_order)
        if words(expected) != words(self.target_text):
            raise ValueError("Example alignment must reproduce its observed target text")
        return self


class Evidence(Record):
    id: str
    source_id: str
    locator: str
    kind: Literal["lexical", "grammar", "example", "note"]
    text: str
    key: str = ""
    value: str | list[str] = ""
    scope: dict[str, str] = Field(default_factory=dict)
    example: Example | None = None
    active: bool = True
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def typed_payload(self):
        if self.kind == "example" and self.example is None:
            raise ValueError("Example evidence requires an observed alignment")
        if self.kind == "lexical" and (
            not self.key or not isinstance(self.value, str) or not self.value.strip()
        ):
            raise ValueError("Lexical claims require a key and string value")
        if self.kind == "grammar" and (
            self.key != "word_order" or not isinstance(self.value, list) or not self.value
        ):
            raise ValueError("Supported grammar claims require word_order and a role list")
        return self


class Line(Record):
    id: str
    source_text: str
    speaker: str
    scene: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    units: list[Unit] = Field(min_length=1)
    context: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_line(self):
        if self.end_ms <= self.start_ms:
            raise ValueError("Subtitle end must be after start")
        if words(" ".join(unit.text for unit in self.units)) != words(self.source_text):
            raise ValueError("Source units must cover the source in order without additions")
        return self


class Pack(Record):
    id: str
    synthetic: bool = False
    sources: list[Source]
    evidence: list[Evidence]
    episode: list[Line] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_references(self):
        for collection in (self.sources, self.evidence, self.episode):
            ids = [item.id for item in collection]
            if len(ids) != len(set(ids)):
                raise ValueError("Identifiers must be unique within each collection")
        source_ids = {source.id for source in self.sources}
        if any(item.source_id not in source_ids for item in self.evidence):
            raise ValueError("Every evidence record must refer to an existing source")
        return self


class Claim(Record):
    id: str
    kind: str
    key: str
    value: str | list[str]
    scope: dict[str, str]
    supporting: list[str]
    counterexamples: list[str]
    status: Literal["SUPPORTED", "CONTESTED", "UNSUPPORTED"]


class Candidate(Record):
    text: str
    evidence: list[str]


class Decision(Record):
    subtitle_id: str
    source_text: str
    nadi_9_text: str | None
    proposed_text: str | None = None
    confidence: float = Field(ge=0, le=1)
    confidence_reason: str
    decision: Literal["APPROVED", "HUMAN_REVIEW", "ABSTAIN"]
    evidence: list[str]
    assumptions: list[str]
    conflicts: list[str]
    checks: list[str]
    review_question: str | None
    dependencies: list[str]
    revision: int


class Limits(Record):
    max_model_calls: int = Field(default=25, ge=0, le=25)
    max_tool_calls: int = Field(default=50, ge=0, le=50)
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def usage_within_budget(self):
        if self.model_calls > self.max_model_calls or self.tool_calls > self.max_tool_calls:
            raise ValueError("Recorded usage exceeds the configured budget")
        return self

    def charge(self, kind: Literal["model", "tool"]):
        field = f"{kind}_calls"
        if getattr(self, field) >= getattr(self, f"max_{field}"):
            raise BudgetExhausted(f"{kind} call budget exhausted")
        setattr(self, field, getattr(self, field) + 1)


class BudgetExhausted(RuntimeError):
    pass


class Correction(Record):
    id: str
    reason: str
    replacements: list[Evidence] = Field(min_length=1)


class State(Record):
    schema_version: Literal[1] = 1
    pack: Pack
    limits: Limits
    revision: int = 1
    claims: list[Claim] = Field(default_factory=list)
    decisions: dict[str, Decision] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
