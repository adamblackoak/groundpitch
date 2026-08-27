from __future__ import annotations

import json
import os
import re
from pathlib import Path

import streamlit as st

from groundpitch.audit import build_audit_ledger
from groundpitch.gate import gate_claims
from groundpitch.nutrient import NutrientError, extract_document, extract_page_texts
from groundpitch.serpapi import (
    SerpApiError,
    claim_requires_live_context,
    search_claim_context,
)


def _infer_subject(pages: list[dict], filename: str) -> str:
    if pages:
        text = str(pages[0].get("text", "")).strip()
        if text:
            first = re.split(r"[.\n]", text, maxsplit=1)[0].strip()
            first = re.sub(
                r"\b(product|technical|compliance)\s+brief\b",
                "",
                first,
                flags=re.I,
            )
            first = re.sub(r"\s+", " ", first).strip(" -:")
            if 2 <= len(first) <= 100:
                return first

    return Path(filename).stem.replace("_", " ").replace("-", " ")


st.set_page_config(page_title="GroundPitch", page_icon="🧾", layout="wide")
st.title("GroundPitch")
st.caption("Marketing copy that cannot outrun its receipts.")
st.markdown(
    "**Two evidence boundaries:** Nutrient DWS establishes source support first; "
    "SerpApi checks current public context only for claims that survive that gate."
)

with st.sidebar:
    st.header("Evidence boundaries")
    offline = st.checkbox(
        "Offline DWS fixture mode",
        value=False,
        help="Useful for UI development only. The submission demo should use live Nutrient DWS.",
    )
    nutrient_key = st.text_input(
        "Nutrient API key",
        value=os.getenv("NUTRIENT_API_KEY", ""),
        type="password",
        disabled=offline,
    )

    st.divider()
    use_serpapi = st.checkbox(
        "SerpApi live-context boundary",
        value=bool(os.getenv("SERPAPI_API_KEY", "")),
        help=(
            "Searches live public web context for claims whose truth can change "
            "with time or market state."
        ),
    )
    serpapi_key = st.text_input(
        "SerpApi API key",
        value=os.getenv("SERPAPI_API_KEY", ""),
        type="password",
        disabled=not use_serpapi,
    )
    search_subject = st.text_input(
        "Web-search subject/entity (optional)",
        value="",
        disabled=not use_serpapi,
        help="For example a product or company name. If blank, GroundPitch infers one from the source.",
    )
    force_all_web = st.checkbox(
        "Web-check every eligible claim",
        value=False,
        disabled=not use_serpapi,
        help=(
            "Even in this mode, source-rejected claims stop before SerpApi. "
            "Search cannot rescue unsupported copy."
        ),
    )

    st.markdown(
        "**Boundary rule:** Nutrient establishes source support. SerpApi adds live "
        "public context where freshness matters. Web search may hold or downgrade "
        "a claim for human review, but can never turn unsupported source copy into authority."
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
    "2. Candidate marketing claims (for example from an AI copywriter), one per line",
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
                    api_key=nutrient_key,
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

    live_scans = {}
    live_skips = {}
    if use_serpapi:
        if not serpapi_key.strip():
            st.error("SerpApi live-context mode is enabled but SERPAPI_API_KEY is missing.")
            st.stop()

        subject = search_subject.strip() or _infer_subject(pages, filename)
        claims_to_scan = []
        for decision in decisions:
            if decision.disposition == "REJECT":
                live_skips[decision.claim] = "STOPPED_AT_SOURCE_EVIDENCE_GATE"
                continue
            if force_all_web or claim_requires_live_context(decision.claim):
                claims_to_scan.append(decision.claim)
            else:
                live_skips[decision.claim] = "LIVE_CONTEXT_NOT_REQUIRED"

        if claims_to_scan:
            try:
                with st.spinner(
                    f"SerpApi is checking live context for {len(claims_to_scan)} eligible claim(s)..."
                ):
                    for claim in claims_to_scan:
                        live_scans[claim] = search_claim_context(
                            claim=claim,
                            api_key=serpapi_key,
                            subject=subject,
                        ).to_dict()
            except SerpApiError as exc:
                st.error(str(exc))
                st.stop()

    st.session_state["gp_run"] = {
        "file_bytes": file_bytes,
        "filename": filename,
        "response_sha": response_sha,
        "instructions": instructions,
        "pages": pages,
        "decisions": [d.to_dict() for d in decisions],
        "live_scans": live_scans,
        "live_skips": live_skips,
    }

run_state = st.session_state.get("gp_run")
if run_state:
    decisions = run_state["decisions"]
    live_scans = run_state.get("live_scans", {})
    live_skips = run_state.get("live_skips", {})
    counts = {
        "ADMIT": sum(d["disposition"] == "ADMIT" for d in decisions),
        "REVIEW": sum(d["disposition"] == "REVIEW" for d in decisions),
        "REJECT": sum(d["disposition"] == "REJECT" for d in decisions),
    }

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("DWS pages", len(run_state["pages"]))
    c2.metric("Admit", counts["ADMIT"])
    c3.metric("Review", counts["REVIEW"])
    c4.metric("Reject", counts["REJECT"])
    c5.metric("Live web checks", len(live_scans))

    st.subheader("Claim ledger")
    human_reviews = {}
    live_context_reviews = {}

    for i, decision in enumerate(decisions):
        disposition = decision["disposition"]
        icon = {"ADMIT": "✅", "REVIEW": "🟠", "REJECT": "⛔"}[disposition]

        with st.expander(
            f"{icon} {disposition}: {decision['claim']}",
            expanded=(disposition != "ADMIT" or decision["claim"] in live_scans),
        ):
            st.write(decision["reason"])
            st.caption(
                f"Source-evidence support score: {decision['confidence']:.2f} "
                "(heuristic, not calibrated probability)"
            )

            if decision["unsupported_numbers"]:
                st.write("Unsupported numbers:", ", ".join(decision["unsupported_numbers"]))
            if decision["unsupported_risky_terms"]:
                st.write(
                    "Unsupported qualifiers:",
                    ", ".join(decision["unsupported_risky_terms"]),
                )

            st.markdown("**Source receipts — Nutrient DWS**")
            for evidence in decision["evidence"]:
                st.markdown(
                    f"- Page {int(evidence['page_index']) + 1}, support "
                    f"{evidence['score']:.2f}: {evidence['text']}"
                )

            if disposition == "REVIEW":
                human_reviews[decision["claim"]] = st.selectbox(
                    "Source-evidence human decision",
                    ["PENDING", "APPROVE", "REJECT"],
                    key=f"review-{i}",
                )

            scan = live_scans.get(decision["claim"])
            if scan:
                st.markdown("**Live public context — SerpApi**")
                st.caption(
                    f"Query: {scan['query']} · status: {scan['search_status']} · "
                    f"checked: {scan['checked_at_utc']}"
                )

                if scan["results"]:
                    for result in scan["results"][:5]:
                        title = result["title"] or result["domain"] or result["link"]
                        link = result["link"]
                        snippet = result["snippet"]
                        if link:
                            st.markdown(f"- [{title}]({link}) — {snippet}")
                        else:
                            st.markdown(f"- **{title}** — {snippet}")
                else:
                    st.warning(
                        "SerpApi returned no organic results. Absence of search evidence "
                        "is not evidence that the claim is false."
                    )

                live_context_reviews[decision["claim"]] = st.selectbox(
                    "Live-context human decision",
                    ["PENDING", "APPROVE", "REJECT"],
                    key=f"web-review-{i}",
                    help=(
                        "Search results are context, not authority. Explicit human "
                        "clearance is required before a live-context claim can release."
                    ),
                )
            elif decision["claim"] in live_skips:
                reason = live_skips[decision["claim"]]
                if reason == "STOPPED_AT_SOURCE_EVIDENCE_GATE":
                    st.info(
                        "SerpApi not called: this claim failed the Nutrient-derived "
                        "source-evidence boundary and cannot be rescued by web search."
                    )

    ledger = build_audit_ledger(
        filename=run_state["filename"],
        file_bytes=run_state["file_bytes"],
        nutrient_response_sha256=run_state["response_sha"],
        nutrient_instructions=run_state["instructions"],
        decisions=decisions,
        human_reviews=human_reviews,
        live_context_scans=live_scans,
        live_context_reviews=live_context_reviews,
        live_context_skips=live_skips,
    )

    released = [
        item["claim"]
        for item in ledger["claims"]
        if item["final_disposition"] in {"ADMIT", "ADMIT_BY_HUMAN_REVIEW"}
    ]

    held = [
        item
        for item in ledger["claims"]
        if item["final_disposition"] in {"HOLD", "HOLD_LIVE_CONTEXT"}
    ]

    left, right = st.columns(2)
    with left:
        st.subheader("Released copy")
        if released:
            for claim in released:
                st.success(claim)
        else:
            st.info("No claim is currently releasable.")

        if held:
            st.markdown("**Held pending review**")
            for item in held:
                st.warning(f"{item['claim']} — {item['final_disposition']}")

    with right:
        st.subheader("Audit artifact")
        st.code(
            f"Source SHA-256: {ledger['source']['sha256']}\n"
            f"DWS response SHA-256: {ledger['nutrient_dws']['response_sha256']}\n"
            f"SerpApi live scans: {ledger['serpapi']['scan_count']}\n"
            f"SerpApi skipped: {ledger['serpapi']['skip_count']}",
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
