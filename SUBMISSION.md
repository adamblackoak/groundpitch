# Devpost submission copy

## Project name

GroundPitch

## One-line pitch

Marketing copy that cannot outrun its receipts.

## Whole story

Generative marketing has an awkward failure mode: fluent copy can quietly become more certain, more absolute or more impressive than the evidence permits.

GroundPitch puts two evidence boundaries between source material and released claims.

First, upload a product brief, technical PDF or compliance document. **Nutrient DWS** performs the core document extraction and returns page-indexed structured evidence. GroundPitch tests candidate marketing claims against that evidence.

Every claim receives a source-evidence disposition:

- ADMIT when the source materially supports it.
- REVIEW when a human needs to make the final call.
- REJECT when the claim introduces unsupported numbers, absolutes, superlatives or simply lacks sufficient evidence.

Second, claims whose validity depends on current or public market state can pass through a **SerpApi live-context boundary**. GroundPitch searches structured real-time web results, records the query, timestamp, response hash and supporting links/snippets, and requires explicit human clearance before release.

The asymmetry is deliberate: SerpApi may hold or downgrade a claim, but it can never rescue a claim that failed the source-evidence gate. Search results are context, not authority.

The useful output is not just accepted copy. It is the receipt. Each decision keeps its supporting document evidence, live-search evidence where applicable, gate reason, source SHA-256, DWS response SHA-256, human decisions and final release state in a downloadable audit ledger.

The control is intentionally narrow. GroundPitch does not pretend that a similarity score or search result proves truth or compliance. It demonstrates a practical governance primitive: candidate copy is not release authority.

## Built with

- Nutrient DWS Processor API
- SerpApi Google Search API
- Python
- Streamlit
- deterministic claim-gating logic
- human review boundaries
- SHA-256 audit artifacts

## Nutrient heavy-lifting line

Nutrient DWS performs the core deterministic extraction that turns uploaded product and technical documents into page-indexed source evidence; GroundPitch will not admit a marketing claim unless that DWS-derived evidence warrants it.

## SerpApi heavy-lifting line

SerpApi provides structured, live web evidence for claims whose validity depends on current or public market state; GroundPitch records that evidence and requires a human live-context clearance before release, while never allowing search results to upgrade a source-unsupported claim.

## What makes it useful

A regulated business can use the same pattern anywhere externally consequential wording must stay bounded by both internal evidence and changing public context: product marketing, financial promotions, healthcare claims, procurement statements, investor materials and technical assertions.

## What I would build next

- DWS Viewer integration for in-document human review
- richer claim-to-source entailment models behind the same deterministic release boundary
- policy packs for sector-specific forbidden or qualified language
- source-quality ranking for live web evidence
- signed release artifacts for downstream publishing systems
