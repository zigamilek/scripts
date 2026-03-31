# Structured Takeaways Plan

This file describes the stronger follow-up approach for maximizing takeaway recall in long videos without padding the output with fluff.

## Goal

Capture all materially useful takeaways from a video, especially long or dense ones, while staying source-grounded, deduplicated, and concise.

The key difference from the current prompt-only approach is that the pipeline would extract takeaways as structured units first, then audit for missing items before rendering the final Markdown.

## Why Change

The current implementation is good at producing readable summaries, but it still compresses intermediate notes into prose-like blocks. On long videos, lower-salience but still useful takeaways can be lost during reduction.

The stronger approach reduces that risk by:
- extracting takeaways explicitly instead of hoping they survive summarization
- preserving timestamps and evidence earlier in the pipeline
- adding a dedicated coverage check before the final report is rendered

## Proposed Pipeline

1. Transcript chunk extraction
   Extract structured candidate takeaways from each chunk, not just chunk summaries.

2. Structured merge and dedupe
   Merge overlapping takeaways across chunks while preserving distinct ones.

3. Coverage audit
   Compare the merged takeaway set against the reduced notes and ask the model what materially useful takeaways are still missing.

4. Final render
   Render the Markdown report from the audited takeaway set plus timeline and supporting notes.

## Suggested Chunk Output Shape

Each chunk should produce a machine-readable or strongly structured block with one entry per candidate takeaway.

Suggested fields per takeaway:
- `timestamp`
- `title`
- `type`
- `takeaway`
- `why_it_matters`
- `evidence`
- `confidence`

Suggested `type` values:
- `action`
- `idea`
- `warning`
- `constraint`
- `definition`
- `decision`

## Suggested Merge Rules

- Merge items that make the same point with different wording.
- Fold examples into the parent takeaway instead of keeping them as standalone items unless the example adds a distinct lesson.
- Preserve the strongest timestamp and the clearest wording when merging.
- Keep separate items when they change what the reader understands, decides, or does in different ways.

## Coverage Audit Step

After merge/dedupe, run one additional model pass with this objective:

- compare the merged takeaway list against the reduced notes and timeline
- identify any materially useful takeaways that are still missing
- return only missing items, or `NONE` if coverage is complete

This pass should be strict:
- do not add restatements
- do not add intro/setup fluff
- do not promote small examples into takeaways unless they add a distinct principle or warning

## Rendering Strategy

The final Markdown report should be rendered from the audited takeaway inventory rather than directly from prose summaries.

Suggested sections:
- `## Executive Brief`
- `## Important Takeaways`
- `## Key Moments`
- `## Research Notes`

Rendering rules:
- `Important Takeaways` should come from the audited takeaway set
- `Key Moments` should come from merged timeline entries
- `Research Notes` should capture nuance, caveats, and supporting detail not already covered by takeaways

## Implementation Todo

- [ ] Add a structured intermediate schema for chunk outputs.
- [ ] Replace `Practical/Important Takeaways` prose extraction with structured candidate takeaway extraction.
- [ ] Add a merge/dedupe step that preserves timestamps and takeaway type.
- [ ] Add a coverage-audit pass that compares merged takeaways against consolidated notes.
- [ ] Render the final Markdown from the audited takeaway inventory.
- [ ] Add regression tests with one short video and one long/dense video transcript fixture.
- [ ] Measure whether the stronger approach materially increases token usage and latency.

## Acceptance Criteria

- Long videos produce more takeaways only when the source genuinely contains more distinct useful ideas.
- Repetition and setup do not inflate the takeaway count.
- Distinct actionable advice, warnings, and constraints are not dropped during reduction.
- Every final takeaway can be traced back to source-grounded intermediate output.
- The audit pass returns `NONE` on videos where the merged takeaways already have full coverage.
