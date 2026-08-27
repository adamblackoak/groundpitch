from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from groundpitch.audit import build_audit_ledger
from groundpitch.gate import gate_claims
from groundpitch.nutrient import NutrientError, extract_document, extract_page_texts

st.set_page_config(page_title="GroundPitch", page_icon="🧾", layout="wide")
st.title("GroundPitch")
st.caption("Marketing copy that cannot outrun its receipts.")

with st.sidebar:
    st.header("Run mode")
    offline = st.checkbox(
        "Offline fixture mode",
        value=False,
        help="Useful for UI development only. The submission demo should use live Nutrient DWS.",
    )
    api_key = st.text_input(
        "Nutrient API key",
        value=os.getenv("NUTRIENT_API_KEY", ""),
        type="password",
        disabled=offline,
    )
    st.markdown(
        "**DWS role:** the uploaded source is parsed by Nutrient DWS before any claim can be released."
    )

uploaded = st.file_uploader(
    "1. Upload product or technical evidence",
    type=["pdf", "png", "jpg", "jpeg", "docx", "pptx", "xlsx"],
)

default_claims = """Process up to 10,000 invoices per hour.
Cut manual review time by 37% in a controlled pilot.
The fastest invoice platform in Europe.
Guaranteed zero compliance errors.
Supports EU and UK deployments."""

claims_text = st.text_area(
    "2. Candidate marketing claims, one per line",
    value=default_claims,
    height=160,
)

run = st.button("3. Ground the claims", type="primary")

if run:
    if uploaded is None and not offline:
        st.error("Upload a source document first.")
        st.stop()

    if offline:
        fixture_path = Path(__file__).parent / "fixtures" / "nutrient_sample.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        file_bytes = (Path(__file__).parent / "sample" / "product_brief.pdf").read_bytes()
        filename = "product_brief.pdf"
        response_sha = "OFFLINE_FIXTURE_NOT_SUBMISSION_PROOF"
        instructions = {
            "parts": [{"file": "document"}],
            "output": {
                "type": "json-content",
                "plainText": True,
                "structuredText": True,
                "keyValuePairs": True,
                "tables": True,
                "language": "english",
            },
        }
    else:
        file_bytes = uploaded.getvalue()
        filename = uploaded.name
        try:
            with st.spinner("Nutrient DWS is extracting the source document..."):
                result = extract_document(
                    file_bytes=file_bytes,
                    filename=filename,
                    api_key=api_key,
                )
        except NutrientError as exc:
            st.error(str(exc))
            st.stop()

        payload = result.raw
        response_sha = result.response_sha256
        instructions = result.request_instructions

    pages = extract_page_texts(payload)
    claims = [line.strip() for line in claims_text.splitlines() if line.strip()]
    decisions = gate_claims(claims, pages)

    st.session_state["gp_run"] = {
        "file_bytes": file_bytes,
        "filename": filename,
        "response_sha": response_sha,
        "instructions": instructions,
        "pages": pages,
        "decisions": [d.to_dict() for d in decisions],
    }

run_state = st.session_state.get("gp_run")
if run_state:
    decisions = run_state["decisions"]
    counts = {
        "ADMIT": sum(d["disposition"] == "ADMIT" for d in decisions),
        "REVIEW": sum(d["disposition"] == "REVIEW" for d in decisions),
        "REJECT": sum(d["disposition"] == "REJECT" for d in decisions),
    }

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("DWS pages", len(run_state["pages"]))
    c2.metric("Admit", counts["ADMIT"])
    c3.metric("Review", counts["REVIEW"])
    c4.metric("Reject", counts["REJECT"])

    st.subheader("Claim ledger")
    human_reviews = {}

    for i, decision in enumerate(decisions):
        disposition = decision["disposition"]
        icon = {"ADMIT": "✅", "REVIEW": "🟠", "REJECT": "⛔"}[disposition]

        with st.expander(
            f"{icon} {disposition}: {decision['claim']}",
            expanded=(disposition != "ADMIT"),
        ):
            st.write(decision["reason"])
            st.caption(f"Gate confidence: {decision['confidence']:.2f}")

            if decision["unsupported_numbers"]:
                st.write("Unsupported numbers:", ", ".join(decision["unsupported_numbers"]))
            if decision["unsupported_risky_terms"]:
                st.write(
                    "Unsupported qualifiers:",
                    ", ".join(decision["unsupported_risky_terms"]),
                )

            st.markdown("**Receipts**")
            for evidence in decision["evidence"]:
                st.markdown(
                    f"- Page {int(evidence['page_index']) + 1}, support "
                    f"{evidence['score']:.2f}: {evidence['text']}"
                )

            if disposition == "REVIEW":
                human_reviews[decision["claim"]] = st.selectbox(
                    "Human decision",
                    ["PENDING", "APPROVE", "REJECT"],
                    key=f"review-{i}",
                )

    ledger = build_audit_ledger(
        filename=run_state["filename"],
        file_bytes=run_state["file_bytes"],
        nutrient_response_sha256=run_state["response_sha"],
        nutrient_instructions=run_state["instructions"],
        decisions=decisions,
        human_reviews=human_reviews,
    )

    released = [
        item["claim"]
        for item in ledger["claims"]
        if item["final_disposition"] in {"ADMIT", "ADMIT_BY_HUMAN_REVIEW"}
    ]

    left, right = st.columns(2)
    with left:
        st.subheader("Released copy")
        if released:
            for claim in released:
                st.success(claim)
        else:
            st.info("No claim is currently releasable.")

    with right:
        st.subheader("Audit artifact")
        st.code(
            f"Source SHA-256: {ledger['source']['sha256']}\n"
            f"DWS response SHA-256: {ledger['nutrient_dws']['response_sha256']}",
            language="text",
        )
        st.download_button(
            "Download audit ledger",
            data=json.dumps(ledger, indent=2),
            file_name="groundpitch_audit_ledger.json",
            mime="application/json",
        )

    with st.expander("Extracted source evidence"):
        for page in run_state["pages"]:
            st.markdown(f"**Page {int(page['page_index']) + 1}**")
            st.text(page["text"])
