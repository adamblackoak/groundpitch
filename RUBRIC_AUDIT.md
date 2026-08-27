# GroundPitch rubric audit

## Overall judging

### Progress

Visible working flow:
- document upload
- live Nutrient DWS extraction
- page-indexed evidence
- claim admission gate
- human review lane
- downloadable audit ledger
- tests and Docker packaging

### Concept

Real problem:
- fluent generated marketing can exceed the evidence behind it
- the control is especially relevant where claims have regulatory, financial or reputational consequences

### Feasibility

Plausible product path:
- evidence-bound marketing review for regulated organisations
- policy packs and richer entailment can be added without changing the release boundary
- the architecture can sit in front of CMS, campaign or document publishing systems

## Nutrient sponsor fit

- DWS is a core document operation, not a throwaway call.
- GroundPitch depends on DWS extraction to build its evidence surface.
- Outputs are replayable and auditable through source and response hashes.
- Uncertain claims go to a human rather than being silently released.
