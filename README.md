# GroundPitch

**Marketing copy that cannot outrun its receipts.**

GroundPitch turns product, technical and compliance documents into an evidence boundary for marketing claims.

A source document goes through **Nutrient DWS** first. GroundPitch then tests candidate claims against the extracted evidence, attaches page-level receipts, and gives every claim one of three dispositions:

- **ADMIT** — evidence is strong enough to release the claim.
- **REVIEW** — some support exists, but a human must decide.
- **REJECT** — the claim outruns the evidence, including unsupported numbers or absolute qualifiers.

The output is a downloadable audit ledger containing the source hash, Nutrient extraction hash, request configuration, evidence spans, gate reasons, human decisions and final release state.

## Why Nutrient DWS is core

GroundPitch does not treat DWS as a decorative API call. DWS performs the core document operation that creates the evidence surface used by every downstream decision.

The live app sends the uploaded document to `POST https://api.nutrient.io/build` with `output.type = json-content`, extracting plain text, structured text, key-value pairs and tables.

If DWS extraction fails, GroundPitch has no evidence boundary and releases nothing.

## Architecture

```text
Source document
      |
      v
Nutrient DWS /build
json-content extraction
      |
      v
Page-indexed evidence
      |
      v
Candidate marketing claims
      |
      v
Deterministic claim gate
  ADMIT / REVIEW / REJECT
      |        |
      |        +--> human review
      v
Released copy + audit ledger
```

## Run

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:NUTRIENT_API_KEY="your-live-key"
streamlit run app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
export NUTRIENT_API_KEY="your-live-key"
streamlit run app.py
```

You can also paste the key into the app sidebar.

## Fast local proof without an API key

```bash
python demo_cli.py
python -m unittest discover -s tests -v
```

The offline fixture exists only to make development and tests reproducible. The submission demo should use a live Nutrient DWS request.

## Live DWS smoke test

```powershell
$env:NUTRIENT_API_KEY="your-live-key"
.\.venv\Scripts\python.exe scripts\live_nutrient_smoke.py
```

## Demo path

1. Upload `sample/product_brief.pdf`.
2. Use the default five candidate claims.
3. Click **Ground the claims**.
4. Show the DWS page count and extracted evidence.
5. Open an admitted claim and show its page-level receipt.
6. Open the unsupported “fastest” or “guaranteed zero” claim and show rejection.
7. If a claim enters REVIEW, make a human decision.
8. Download the audit ledger and show the source and DWS-response hashes.

## Deliberate boundary

GroundPitch does **not** claim that lexical evidence matching proves regulatory compliance or factual truth. It demonstrates a narrower control: generated or proposed marketing claims cannot silently become releasable copy without traceable support from submitted source evidence.

## Where DWS does the heavy lifting

**Nutrient DWS performs the core deterministic extraction that turns uploaded product and technical documents into page-indexed evidence; GroundPitch will not admit a marketing claim unless that DWS-derived evidence warrants it.**

## Security

- The Nutrient API key is read from an environment variable or password field.
- The key is never written to the audit ledger.
- Source and DWS responses are represented in the audit trail by SHA-256 hashes.

## License

MIT.
