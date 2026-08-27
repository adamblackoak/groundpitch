# GroundPitch

**Marketing copy that cannot outrun its receipts.**

GroundPitch turns product, technical and compliance documents into an evidence boundary for marketing claims.

A source document goes through **Nutrient DWS** first. GroundPitch then tests candidate claims against the extracted evidence, attaches page-level receipts, and gives every claim one of three dispositions:

- **ADMIT** — evidence is strong enough to release the claim.
- **REVIEW** — some support exists, but a human must decide.
- **REJECT** — the claim outruns the evidence, including unsupported numbers or absolute qualifiers.

For claims whose truth can change with time or public market state, GroundPitch can add a second boundary using **SerpApi**. Live search results are attached as current public context and require explicit human clearance before release. SerpApi can hold or downgrade a claim; it can never turn an unsupported source claim into authority.

The output is a downloadable audit ledger containing the source hash, Nutrient extraction hash, request configuration, evidence spans, SerpApi search receipts where applicable, gate reasons, human decisions and final release state.

## Why Nutrient DWS is core

GroundPitch does not treat DWS as a decorative API call. DWS performs the core document operation that creates the primary evidence surface used by every downstream decision.

The live app sends the uploaded document to `POST https://api.nutrient.io/build` with `output.type = json-content`, extracting plain text, structured text, key-value pairs and tables.

If DWS extraction fails, GroundPitch has no source-evidence boundary and releases nothing.

## Why SerpApi is structural

Some marketing assertions are not purely documentary facts. Claims such as "currently available in...", "the fastest...", market position, pricing, coverage and availability can go stale even when the internal source document is genuine.

GroundPitch therefore uses SerpApi as a **live-context boundary** for claims whose truth depends on current public state:

1. Nutrient-derived source evidence must support the claim first.
2. Relevant live/public claims are searched through SerpApi's structured Google Search API.
3. The search query, timestamp, response hash and result snippets/links are recorded.
4. A human explicitly clears or rejects the live-context check.
5. Search results never upgrade a source-unsupported claim.

This preserves a simple control principle: **internal evidence establishes authority; live web data tests whether that authority may have become stale or externally contestable.**

## Architecture

```text
Source document
      |
      v
Nutrient DWS /build
json-content extraction
      |
      v
Page-indexed source evidence
      |
      v
Candidate marketing claims
      |
      v
Deterministic source-evidence gate
  ADMIT / REVIEW / REJECT
      |
      +------ rejected claims stop here
      |
      v
Claims needing current/public context
      |
      v
SerpApi structured live search
      |
      v
Human live-context clearance
      |
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
$env:SERPAPI_API_KEY="your-live-key"
streamlit run app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
export NUTRIENT_API_KEY="your-live-key"
export SERPAPI_API_KEY="your-live-key"
streamlit run app.py
```

You can also paste either key into the app sidebar.

## Fast local proof without API keys

```bash
python demo_cli.py
python -m unittest discover -s tests -v
```

The offline Nutrient fixture exists only to make development and tests reproducible. The submission demo should use live Nutrient DWS and SerpApi requests.

## Live DWS smoke test

```powershell
$env:NUTRIENT_API_KEY="your-live-key"
.\.venv\Scripts\python.exe scripts\live_nutrient_smoke.py
```

## Demo path

1. Upload `sample/product_brief.pdf`.
2. Enable the SerpApi live-context boundary.
3. Use the default candidate claims.
4. Click **Ground the claims**.
5. Show Nutrient DWS extracting the source and an admitted claim with its page-level receipt.
6. Show an unsupported claim being rejected before web context can rescue it.
7. Show a current/public claim with its SerpApi search receipts and human live-context clearance.
8. Download the audit ledger and show the source hash, DWS-response hash and recorded live-search evidence.

## Deliberate boundary

GroundPitch does **not** claim that lexical evidence matching or search-engine results prove regulatory compliance or factual truth. It demonstrates a narrower control: generated or proposed marketing claims cannot silently become releasable copy without traceable source support, and claims dependent on current public state cannot bypass a live-context review.

## Where the sponsor APIs do the heavy lifting

**Nutrient DWS** performs the core deterministic extraction that turns uploaded product and technical documents into page-indexed source evidence; GroundPitch will not admit a marketing claim unless that DWS-derived evidence warrants it.

**SerpApi** provides structured, live web evidence for claims whose validity depends on current or public market state; that evidence creates an additional human-review boundary before release rather than acting as an automatic truth oracle.

## Security

- API keys are read from environment variables or password fields.
- Keys are never written to the audit ledger.
- Source, DWS and SerpApi responses are represented in the audit trail by SHA-256 hashes.

## License

MIT.
