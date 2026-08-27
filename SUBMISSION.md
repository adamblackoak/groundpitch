# Devpost submission copy

## Project name

GroundPitch

## One-line pitch

Marketing copy that cannot outrun its receipts.

## Whole story

Generative marketing has an awkward failure mode: fluent copy can quietly become more certain, more absolute or more impressive than the source material permits.

GroundPitch puts a warrant boundary between source documents and released claims.

Upload a product brief, technical PDF or compliance document. Nutrient DWS performs the core document extraction and returns page-indexed structured evidence. GroundPitch then tests candidate marketing claims against that evidence.

Every claim receives a disposition:

- ADMIT when the source materially supports it.
- REVIEW when a human needs to make the final call.
- REJECT when the claim introduces unsupported numbers, absolutes, superlatives or simply lacks sufficient evidence.

The useful output is not just accepted copy. It is the receipt. Each decision keeps its supporting page evidence, reason, source SHA-256, DWS response SHA-256, human decision where needed, and final release state in a downloadable audit ledger.

The control is intentionally narrow. GroundPitch does not pretend that a similarity score proves truth or compliance. It demonstrates a practical governance primitive: candidate copy is not release authority.

## Built with

- Nutrient DWS Processor API
- Python
- Streamlit
- deterministic claim-gating logic
- SHA-256 audit artifacts

## DWS heavy-lifting line

Nutrient DWS performs the core deterministic extraction that turns uploaded product and technical documents into page-indexed evidence; GroundPitch will not admit a marketing claim unless that DWS-derived evidence warrants it.

## What makes it useful

A regulated business can use the same pattern anywhere externally consequential wording must stay bounded by source evidence: product marketing, financial promotions, healthcare claims, procurement statements, investor materials and technical assertions.

## What I would build next

- DWS Viewer integration for in-document human review
- richer claim-to-source entailment models behind the same deterministic release boundary
- policy packs for sector-specific forbidden or qualified language
- signed release artifacts for downstream publishing systems
