# Nadi-9 subtitle agent

An offline subtitle decision pipeline that learns supported claims from aligned evidence,
keeps disagreements visible, withholds unsupported text, and revises only affected decisions.

**The included language, speakers, examples, and episode are synthetic test fixtures.**
No verified Nadi-9 evidence pack is included.
The demo illustrates pipeline behavior and does not establish facts about Nadi-9.

## Run in two minutes

Requires Python 3.11 or newer. No API key, account, or network access is needed after installation.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -c requirements.lock -e '.[dev]'
nadi9 validate fixtures/demo.json
nadi9 run fixtures/demo.json --out work/initial
nadi9 correct work/initial/state.json fixtures/correction.json --out work/corrected
pytest -q
```

The initial run approves 3 lines, sends 1 to review, and abstains on 2. Withdrawing a poisoned
vendor entry reprocesses only `S002`, whose proposal changes from withheld to `sa mi vo`.
The revised run has 4 approved lines, 1 review, and 1 abstention. Both releases remain `HOLD`.
These are synthetic outcomes, not translation accuracy measurements.

## What is implemented

- Strict input validation, source provenance, revisioned evidence, and inspectable hypotheses.
- Lexical and word-order hypotheses tested against multiple reviewed, aligned observations.
- Relationship-specific meanings, conflicting dictionaries, and retractable approved examples.
- Risk-prioritized planning, offline proposal provider, independent deterministic verification.
- Exact lexical realization, source-unit coverage, names/numbers, order, timing, overlap, and speed checks.
- Structured confidence explanations, review questions, explicit abstention, and a release gate.
- Resumable run state, bounded provider retry, cumulative budgets, and selective correction invalidation.
- Non-executable retrieval text and a complete decision history with original evidence snapshots.

## Outputs

Every run writes these files to `--out`:

| File | Purpose |
| --- | --- |
| `subtitles.srt` | Timed review draft; withheld lines contain explicit review markers |
| `subtitle_decisions.jsonl` | Text, evidence, assumptions, conflicts, checks, confidence and review status |
| `learned_rules.json` | Supported, contested and unsupported lexical/word-order claims |
| `evidence_records.jsonl` | Current source records with locators and revision numbers |
| `review_queue.json` | All decisions requiring expert attention |
| `state.json` | Full resumable state, source metadata and cumulative call budgets |
| `audit.jsonl` | Plans, original evidence, failures, corrections and historical decisions |
| `final_report.md` | Release recommendation and per-line results |

A checked-in corrected example is in [sample_run](sample_run). The audit also contains the initial
run. `APPROVED` means supported within this constrained pipeline, not ready for unattended release.
`HOLD` is mandatory for synthetic, incomplete, unsupported, or unresolved runs.

## Pausing, corrections and failures

```sh
nadi9 run fixtures/demo.json --max-lines 2 --out work/partial
nadi9 correct work/partial/state.json fixtures/correction.json --out work/resumed
nadi9 resume work/partial/state.json --out work/finished
nadi9 run fixtures/demo.json --simulate-failures 2 --out work/failure-demo
nadi9 run fixtures/demo.json --max-model-calls 1 --max-tool-calls 3 --out work/budget-demo
```

Corrections replace existing evidence IDs and increment their revisions by exactly one. They can
withdraw entries or repair observations. Correction IDs are unique. The original evidence remains
in the audit. A correction does not replenish call budgets. Use a new output directory for each
milestone to preserve convenient snapshots. An exhausted budget creates review items, not a crash.

## Load the real evidence pack

```sh
nadi9 schema pack > work/pack.schema.json
nadi9 schema correction > work/correction.schema.json
nadi9 validate /path/to/pack.json
nadi9 run /path/to/pack.json --out work/real-run
```

Use `fixtures/demo.json` as a structural example, never as dialect evidence. Each source needs an
author, date, scope, reliability classification, and rationale. Each evidence record needs a stable
ID, source ID, locator, kind, raw text, and typed annotation. Episode units must account for the
source text in order. Each observed example includes a checked source/target alignment.

The current importer accepts curated structured JSON. A reviewer must transcribe and annotate raw
PDFs, interviews and dictionaries before import. Dates and author names are provenance, not automatic
proof of reliability. Mark uncertain speaker relationships and humour as `risks` so they require review.
Only deliberately preserved names, numbers or reviewed code-switches should use `literal: true`.

The built-in provider is deterministic replay/composition. The Python `ProposalProvider` protocol
allows another provider to be supplied to `Engine`; every returned candidate still passes the same
verifier. There is no hidden hosted provider or automatic upload path.

## Development

```sh
pytest -q
ruff check src tests
ruff format --check src tests
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for decisions and trust boundaries, and
[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for the intentionally narrow language coverage.
