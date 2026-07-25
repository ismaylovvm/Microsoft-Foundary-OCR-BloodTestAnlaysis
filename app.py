import tempfile
from pathlib import Path

import streamlit as st

from llm_analysis import (
    INITIAL_PROMPT,
    analyze_blood_test,
    build_api_messages,
    create_initial_messages,
    initialize_manager,
    load_model_and_client,
    stream_chat_response,
)

st.set_page_config(
    page_title="Blood Test Analysis",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

    :root {
        /* Text Colors */
        --ink: #0f172a; /* Daha koyu, daha net metin */
        --ink-soft: #475569;
        --ink-faint: #94a3b8;
        
        /* Primary Theme (Modern Crimson/Rose for Blood Theme) */
        --primary-900: #881337;
        --primary-800: #9f1239;
        --primary-700: #be123c;
        --primary-600: #e11d48;
        --primary-100: #ffe4e6;
        --primary-50: #fff1f2;
        
        /* Status Colors (Medical Standard) */
        --status-normal: #10b981; /* Emerald Green */
        --status-low: #0ea5e9;    /* Sky Blue */
        --status-high: #ef4444;   /* Rose Red */
        --status-unknown: #94a3b8;/* Slate */

        /* Layout Colors */
        --border: #e2e8f0;
        --bg: #f8fafc; /* Uygulama arkapanı için çok hafif cool-gray */
        --surface: #ffffff; /* Kartlar ve inputlar için beyaz */
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--ink) !important;
    }

    .stApp { background-color: var(--bg); color: var(--ink); }

    /* --- Force readable text everywhere --- */
    p, span, label, li, div, h1, h2, h3, h4, h5, h6,
    .stMarkdown, .stMarkdown p, .stMarkdown li,
    .stCaption, .stText, .stAlert, .stAlert p,
    .stTextInput label, .stTextInput input,
    .stTextArea label, .stTextArea textarea,
    .stSelectbox label, .stSelectbox div,
    .stFileUploader label, .stFileUploader small,
    .stFileUploader div[data-testid="stFileUploaderDropzone"],
    .stFileUploader div[data-testid="stFileUploaderDropzone"] *,
    .stChatInput textarea, .stChatInput input,
    .stExpander, .stExpander p, .stExpander summary,
    .stTooltipIcon, .stTooltipContent,
    .stCodeBlock, .stCodeBlock code {
        color: var(--ink) !important;
    }

    /* Placeholders and helper/small text */
    ::placeholder { color: var(--ink-faint) !important; opacity: 1; }
    small, .stCaption p, [data-testid="stCaptionContainer"] * {
        color: var(--ink-soft) !important;
    }

    /* Inputs and dropzone */
    .stTextInput input, .stTextArea textarea, .stChatInput textarea,
    div[data-testid="stFileUploaderDropzone"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        transition: all 0.2s ease;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stChatInput textarea:focus {
        border-color: var(--primary-600) !important;
        box-shadow: 0 0 0 3px var(--primary-100) !important;
    }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, var(--primary-800) 0%, var(--primary-600) 100%);
        padding: 2.25rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: #ffffff;
        box-shadow: 0 10px 30px -5px rgba(225, 29, 72, 0.3);
    }
    .main-header h1, .main-header p { color: #ffffff !important; }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .main-header p { margin: 0.75rem 0 0; opacity: 0.9; font-size: 1.1rem; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--surface);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] code {
        background-color: var(--bg) !important;
        border: 1px solid var(--border);
        color: var(--primary-700) !important;
        border-radius: 6px;
        padding: 0.2rem 0.4rem;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: var(--surface);
        padding: 1.25rem 1.5rem;
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
    }
    div[data-testid="stMetricValue"] { color: var(--ink) !important; font-weight: 700; font-size: 2rem !important; }
    div[data-testid="stMetricLabel"] { color: var(--ink-soft) !important; font-weight: 500; font-size: 1rem !important; }

    /* Status labels */
    .status-normal { color: var(--status-normal) !important; font-weight: 700; background: #ecfdf5; padding: 4px 10px; border-radius: 20px; display: inline-block; font-size: 0.9em; }
    .status-low    { color: var(--status-low) !important; font-weight: 700; background: #f0f9ff; padding: 4px 10px; border-radius: 20px; display: inline-block; font-size: 0.9em; }
    .status-high   { color: var(--status-high) !important; font-weight: 700; background: #fef2f2; padding: 4px 10px; border-radius: 20px; display: inline-block; font-size: 0.9em; }
    .status-unknown{ color: var(--status-unknown) !important; font-weight: 600; background: #f1f5f9; padding: 4px 10px; border-radius: 20px; display: inline-block; font-size: 0.9em; }

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        background: var(--surface);
        border-radius: 16px;
        border: 1px solid var(--border);
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    /* AI Assistant bubble differentiation */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background: var(--primary-50);
        border: 1px solid var(--primary-100);
    }

    /* Buttons */
    button[kind="primary"] {
        background-color: var(--primary-600) !important;
        border-color: var(--primary-600) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px -1px rgba(225, 29, 72, 0.2);
    }
    button[kind="primary"]:hover, button[kind="primary"]:focus {
        background-color: var(--primary-700) !important;
        border-color: var(--primary-700) !important;
        box-shadow: 0 6px 10px -1px rgba(225, 29, 72, 0.3);
        transform: translateY(-1px);
    }
    button[kind="secondary"], .stButton button, .stDownloadButton button {
        color: var(--ink) !important;
        border-color: var(--border) !important;
        background-color: var(--surface) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    button[kind="secondary"]:hover, .stButton button:hover, .stDownloadButton button:hover {
        color: var(--primary-600) !important;
        border-color: var(--primary-600) !important;
        background-color: var(--primary-50) !important;
    }

    /* Links */
    a, a:visited { color: var(--primary-600) !important; text-decoration: none; font-weight: 500; }
    a:hover { color: var(--primary-800) !important; text-decoration: underline; }

    /* Tabs */
    div[data-testid="stTabs"] { gap: 1rem; }
    div[data-testid="stTabs"] button { color: var(--ink-soft) !important; font-weight: 500; font-size: 1.05rem; padding-bottom: 0.75rem; }
    div[data-testid="stTabs"] button:hover { color: var(--primary-600) !important; }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--primary-700) !important;
        font-weight: 700;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: var(--primary-600) !important;
        height: 3px;
        border-radius: 3px 3px 0 0;
    }

    /* Alerts */
    div[data-testid="stAlert"] { border-radius: 12px !important; border: none !important; }
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] div { color: var(--ink) !important; }

    /* Dividers */
    hr { border-color: var(--border) !important; margin: 2rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

STATUS_LABELS = {
    "normal": ("Normal", "status-normal"),
    "low": ("Low", "status-low"),
    "high": ("High", "status-high"),
    "unknown": ("Unknown", "status-unknown"),
}


@st.cache_resource(show_spinner="Preparing the local AI model…")
def get_cached_llm_client():
    manager = initialize_manager()
    model, client = load_model_and_client(manager)
    return client


def ensure_llm_client():
    return get_cached_llm_client()


def run_ocr_from_upload(uploaded_file) -> list[dict]:
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    return analyze_blood_test(tmp_path)


def render_results_table(rows: list[dict]):
    if not rows:
        st.warning("No readable test rows were found in the table. Try a different image.")
        return

    header = st.columns([3, 1.2, 1, 2, 1.2])
    headers = ["Test", "Result", "Unit", "Reference", "Status"]
    for col, label in zip(header, headers):
        col.markdown(f"**{label}**")

    for row in rows:
        label, css = STATUS_LABELS.get(row["status"], STATUS_LABELS["unknown"])
        c1, c2, c3, c4, c5 = st.columns([3, 1.2, 1, 2, 1.2])
        c1.write(row["test_name"])
        c2.write(row["value"])
        c3.write(row.get("unit") or "—")
        c4.write(row.get("reference_range") or "—")
        c5.markdown(f'<span class="{css}">{label}</span>', unsafe_allow_html=True)
        st.divider()


with st.sidebar:
    st.markdown("## 🩸")
    st.title("Settings")
    st.caption("The OCR + local Phi-4-mini pipeline matches `llm_analysis.py`.")
    st.divider()
    st.markdown("**Required environment variables**")
    st.code("ocr_endpoint\nocr_key", language="text")
    st.markdown("**CLI alternative**")
    st.code("python llm_analysis.py", language="bash")
    st.info(
        "This application does not provide a medical diagnosis; it is for "
        "informational purposes only. Always consult a doctor about your results."
    )

st.markdown(
    """
<div class="main-header">
    <h1>🩸 Blood Test OCR & AI Interpretation</h1>
    <p>Upload a photo of your lab report; view the results in a table and get a plain-language explanation from AI.</p>
</div>
""",
    unsafe_allow_html=True,
)

if "parsed_results" not in st.session_state:
    st.session_state.parsed_results = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "interpretation_done" not in st.session_state:
    st.session_state.interpretation_done = False

tab_ocr, tab_ai = st.tabs(["📄 OCR Results", "💬 AI Interpretation & Q&A"])

# ------------------------------------------------------------------
# TAB 1 — Upload + OCR results only
# ------------------------------------------------------------------
with tab_ocr:
    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        st.subheader("1. Upload report")
        uploaded = st.file_uploader(
            "PNG or JPG",
            type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
            help="A clear, flat photo of the lab printout gives the best results.",
        )

        if uploaded and st.button("Analyze", type="primary", use_container_width=True):
            with st.spinner("Reading the table with Azure OCR…"):
                try:
                    st.session_state.parsed_results = run_ocr_from_upload(uploaded)
                    st.session_state.chat_messages = []
                    st.session_state.interpretation_done = False
                    st.success(f"{len(st.session_state.parsed_results)} tests read.")
                except Exception as e:
                    st.error(f"OCR error: {e}")
                    st.session_state.parsed_results = None

        if uploaded:
            st.image(uploaded, caption="Uploaded report", use_container_width=True)

    with col_right:
        st.subheader("2. Extracted values")
        rows = st.session_state.parsed_results
        if rows:
            normal = sum(1 for r in rows if r["status"] == "normal")
            abnormal = len(rows) - normal - sum(1 for r in rows if r["status"] == "unknown")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total tests", len(rows))
            m2.metric("Normal", normal)
            m3.metric("Abnormal", abnormal)
            st.write("") # Spacer
            render_results_table(rows)
            st.info("Switch to the **💬 AI Interpretation & Q&A** tab to see the AI interpretation and ask questions.")
        else:
            st.markdown(
                "_No analysis yet. Upload a report on the left and click **Analyze**._"
            )

# ------------------------------------------------------------------
# TAB 2 — LLM interpretation + Q&A chat together
# ------------------------------------------------------------------
with tab_ai:
    if not st.session_state.parsed_results:
        st.info("First analyze a report in the **📄 OCR Results** tab.")
    else:
        rows = st.session_state.parsed_results

        st.subheader("AI Interpretation")
        if not st.session_state.interpretation_done:
            if st.button("Generate Interpretation", type="primary", use_container_width=True):
                try:
                    client = ensure_llm_client()
                    messages = create_initial_messages(rows)
                    st.session_state.chat_messages = [{"role": "user", "content": INITIAL_PROMPT}]
                    full = ""
                    with st.chat_message("assistant"):
                        stream_box = st.empty()
                        for part in stream_chat_response(client, messages):
                            full += part
                            stream_box.markdown(full)
                    st.session_state.chat_messages.append({"role": "assistant", "content": full})
                    st.session_state.interpretation_done = True
                    st.rerun()
                except ImportError:
                    st.error("foundry_local_sdk is not installed. Install it via requirements.txt.")
                except Exception as e:
                    st.error(f"Model error: {e}")
        else:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            st.divider()
            st.subheader("Ask a question about your results")

            if prompt := st.chat_input("e.g. What should I do about low hemoglobin?"):
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                try:
                    client = ensure_llm_client()
                    api_messages = build_api_messages(
                        st.session_state.parsed_results,
                        st.session_state.chat_messages,
                    )

                    full = ""
                    with st.chat_message("assistant"):
                        box = st.empty()
                        for part in stream_chat_response(client, api_messages):
                            full += part
                            box.markdown(full)
                    st.session_state.chat_messages.append({"role": "assistant", "content": full})
                except Exception as e:
                    st.error(f"Chat error: {e}")