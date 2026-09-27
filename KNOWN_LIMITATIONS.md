# Known limitations

- The actual language pack was not supplied. The demo is synthetic and is never a release candidate.
- Input is curated structured JSON. Raw PDF extraction, audio transcription and automatic linguistic
  annotation are not implemented. Those steps need the actual pack and evaluation data.
- The replay provider handles supported lexical substitutions and observed role order. It does not infer
  morphology, tense, negation, irony or pragmatic meaning beyond supplied units and context. Representing
  those constructions requires reviewed annotations; unsupported constructions must remain withheld.
- Name, number and code-switch preservation relies on trusted literal annotations. Source coverage checks
  normalize case and punctuation; they do not prove semantic completeness or preserve punctuation intent.
- The verifier is independent of the proposal generator, but both rely on curated alignments. A bad alignment
  accepted by reviewers can pass both. Expert review and independently collected examples remain necessary.
- Two corroborating examples may be correlated. No provenance clustering, source authenticity checks or
  confidence calibration has been performed. Scores express support tiers, not measured correctness.
- Source reliability and correction acceptance are operator responsibilities. There is no reviewer login,
  cryptographic signature, authorization service, or approval workflow.
- Corrections replace existing evidence records. New evidence ingestion or source metadata revisions require
  a new pack/run. Claim retesting scans the whole pack, while subtitle regeneration is selective.
- Only the offline provider ships. The provider protocol permits integrations but there is no hosted model,
  live transcription service or command-line provider selection.
- Recovery occurs at saved run boundaries, not after every line. Concurrent writes and transactional
  multi-file export are not supported. Save to separate output directories for independent snapshots.
- The SRT is a draft with review markers. No editorial approval, quality certification or unattended
  publishing is performed, even when all supported lines pass their checks.
