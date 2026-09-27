# Architecture

## Data flow

```text
Validated pack -> scoped hypotheses -> corroboration and counterexamples
                                            |
                                     risk-prioritized plan
                                            |
                          evidence resolution -> proposal provider
                                            |
                               independent deterministic verifier
                                            |
                         decision, review queue, draft SRT, release gate
```

`models.py` defines strict Pydantic schemas. Unknown fields, broken references, duplicate IDs,
invalid timings, incomplete source units and inconsistent observed alignments are rejected.
`evidence.py` learns claims. `engine.py` owns the plan, call budget, decisions and correction lifecycle.
`providers.py` supplies proposals. `verify.py` evaluates them without calling the proposal provider.
`storage.py` exports review artifacts and a resumable state snapshot.

## Planning and source precedence

Missing or conflicting vocabulary contributes ten risk points per unit; contextual risks contribute
five each and assumptions one each. Higher-risk lines run first, with time and ID as stable tie breakers.
The plan is saved before execution and revised after corrections.

Source classifications are explicit importer decisions with recorded rationales. Untrusted material
is retained for audit but cannot authorize a claim. Provisional material can propose hypotheses.
A lexical or word-order hypothesis requires two distinct reviewed examples in matching context.
One counterexample makes the claim contested. Conflicting values at the same scope block selection,
even when one source is larger, newer, or otherwise apparently more authoritative.

The most specific matching relationship/status scope applies. A specific unsupported claim blocks a
more general fallback. Grammar observations are compared only within the same set of semantic roles.
No new word or grammatical marker is invented. Unsupported roles or constructions lead to abstention.
Two examples are an engineering threshold, not statistical proof; copied examples and correlated
source errors remain limitations.

## Memory and correction handling

State contains the pack, source metadata, claims, pending plan, cumulative budgets, decisions and an
append-only sequence of audit events. Decision evidence uses `id@revision`. The initial pack snapshot
and every correction payload allow historical references to be resolved. Each decision includes
lexical and grammar dependency keys, including keys for currently missing words.

A correction is validated against a copy before state changes. It replaces known evidence records,
then locally retests hypotheses. Changed claims invalidate only dependent lines in matching contexts.
Removing an example can change multiple claims, so every affected line is queued. Unaffected decisions
retain their revision and content. Pending work is preserved when a correction arrives mid-run.
Local claim retesting scans the pack; only impacted subtitle proposals and verifications consume new
calls. This is not a claim that all local computation is incremental.

## Verification and confidence

The proposal provider receives resolved structured claims, not unrestricted retrieved text. The verifier
rechecks cited observations and context separately, then constructs the permitted realization for each
source unit. Exact comparison detects additions, omissions, unsupported vocabulary, altered literals and
incorrect role order. Timing checks cover overlap, one-to-seven-second durations, 20 characters per second,
and two lines of up to 42 characters. These are configurable-code defaults, not a broadcaster standard.

This verifier can reject the provider and uses no approval prompt. It shares input annotations and
observation interpretation with the learner, so it cannot independently prove those annotations correct.
Humour, ambiguous social intent and uncertain context explicitly require a language expert.

Scores are transparent heuristics: 0.85 for a fully checked supported proposal, 0.4 for an unapproved
proposal, and 0 for no proposal. They are not calibrated probabilities. Decision reasons, evidence,
conflicts and focused review questions carry the actionable information.

## Recovery, budgets and privacy

A run defaults to 25 proposal attempts and 50 tool calls. Each evidence-resolution operation and each
verification costs one tool call. Each provider attempt, including a failed retry, costs one model call,
even in replay mode. Pure in-memory planning, schema validation, claim testing and export are local
computation, not remote tool calls. Budgets persist across resume and correction operations.

Provider timeouts, connection errors and declared unavailability retry once. Repeated failure, malformed
proposals or exhausted budgets create reviewable abstentions. Individual export files are atomically
replaced, with `state.json` last. An interruption between files can leave mixed exports; state is the
canonical snapshot and can regenerate them. There is no concurrent-writer support.

The default runtime performs no network requests or shell execution. Retrieved instructions are inert
source text. Only a trusted importer assigns source reliability or accepts correction files; free-text
instructions cannot change either. Run state is local and contains the input material, so keep real packs
and outputs outside version control. A future hosted provider needs an explicitly approved data-retention
policy, bounded timeouts, and a request/response schema before use.

## Scaling direction

For many episodes, index claims and dependencies in a transactional database, address evidence by stable
content hashes, and use an idempotent job queue per episode revision. Share reviewed dialect knowledge
across episodes while keeping scene context and release decisions separate. Cache by evidence revision,
provider version, and normalized input. Transactional revisions and explicit review signoff should precede
parallel workers or automatic release. The current implementation intentionally stays local and inspectable.
