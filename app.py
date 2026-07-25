import tempfile
from pathlib import Path

import streamlit as st

from data_process import parse_table
from ocr_analysis import analyze_table

st.set_page_config(
    page_title="Kan Tahlili Analizi",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #0f766e 0%, #134e4a 50%, #164e63 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 10px 40px rgba(15, 118, 110, 0.25);
    }
    .main-header h1 { margin: 0; font-size: 1.85rem; font-weight: 700; }
    .main-header p { margin: 0.5rem 0 0; opacity: 0.92; font-size: 1.05rem; }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    .status-normal { color: #059669; font-weight: 600; }
    .status-low { color: #2563eb; font-weight: 600; }
    .status-high { color: #dc2626; font-weight: 600; }
    .status-unknown { color: #64748b; font-weight: 600; }
    div[data-testid="stChatMessage"] {
        background: #f8faffc0;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
</style>
""",
    unsafe_allow_html=True,
)

STATUS_LABELS = {
    "normal": ("Normal", "status-normal"),
    "low": ("Düşük", "status-low"),
    "high": ("Yüksek", "status-high"),
    "unknown": ("Belirsiz", "status-unknown"),
}

SYSTEM_PROMPT = """
You are an experienced physician explaining blood test results to a patient.
Your goal is to provide a professional, clear, medically accurate, and very simple interpretation of the laboratory report.

Instructions:

1. Analyze the ENTIRE report before answering.
2. Analyze EVERY test exactly once in the order they appear. Never skip any test.
3. Use the provided "status" field as the correct classification. Do not recalculate.

4. For EACH test, keep your explanation strictly to these 3 simple steps:

   * **What it is:** Provide the [Test Name], [Result], and [Status]. Explain briefly and simply what this test measures in the body.
   * **Causes:** If the result is abnormal (High/Low), explain the most common reasons or causes for this specific result. (If normal, simply state it indicates good health).
   * **Solutions:** If the result is abnormal, provide clear, practical, and safe recommendations (diet, lifestyle, or medical next steps) to fix or manage it. (If normal, skip this part).

5. After explaining every individual test using the 3 steps above, provide a brief **Overall Assessment** summarizing the general health picture and how the abnormal results might be connected.

Respond in Turkish unless the user asks otherwise.
"""

INITIAL_PROMPT = (
    "Lütfen kan tahlili raporumu eksiksiz ve sade bir dille yorumla. "
    "Her testi sırayla 3 adımda (Ne ölçülür, Olası nedenler, Öneriler) açıkla, "
    "sonunda genel bir değerlendirme yap. Anormal sonuçlar için mutlaka öneri ver."
)


def build_context(parsed_result):
    lines = []
    for row in parsed_result:
        unit = row.get("unit") or "-"
        ref = row.get("reference_range") or "-"
        status = row.get("status") or "unknown"
        lines.append(
            f"- {row['test_name']}: {row['value']} {unit} "
            f"(referans: {ref}, durum: {status})"
        )
    return "patient's blood analysis results :\n" + "\n".join(lines)


def ensure_llm_client():
    if st.session_state.get("llm_client") is not None:
        return st.session_state.llm_client

    from foundry_local_sdk import Configuration, FoundryLocalManager

    config = Configuration(app_name="ocr_blood_analysis_ui")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    with st.status("Yerel AI modeli hazırlanıyor…", expanded=True) as status:
        st.write("Execution provider kayıtları indiriliyor…")
        manager.download_and_register_eps()
        st.write("Phi-4-mini indiriliyor ve yükleniyor…")
        model = manager.catalog.get_model("phi-4-mini")
        model.download(lambda p: None)
        model.load()
        client = model.get_chat_client()
        st.session_state.llm_model = model
        st.session_state.llm_client = client
        status.update(label="Model hazır", state="complete")

    return client


def run_ocr(uploaded_file) -> list[dict]:
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    result = analyze_table(tmp_path)
    return parse_table(result)


def render_results_table(rows: list[dict]):
    if not rows:
        st.warning("Tabloda okunabilir test satırı bulunamadı. Farklı bir görüntü deneyin.")
        return

    header = st.columns([3, 1.2, 1, 2, 1.2])
    headers = ["Test", "Sonuç", "Birim", "Referans", "Durum"]
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


# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🩸")
    st.title("Ayarlar")
    st.caption("Azure Document Intelligence ile OCR; yorum için yerel Phi-4-mini.")
    st.divider()
    st.markdown("**Gerekli ortam değişkenleri**")
    st.code("ocr_endpoint\nocr_key", language="text")
    st.info(
        "Bu uygulama tıbbi teşhis koymaz; bilgilendirme amaçlıdır. "
        "Sonuçlar için mutlaka bir hekime danışın."
    )

# --- Header ---
st.markdown(
    """
<div class="main-header">
    <h1>Kan Tahlili OCR & AI Yorum</h1>
    <p>Laboratuvar raporu fotoğrafını yükleyin; sonuçları tabloda görün, yapay zeka ile sade bir açıklama alın.</p>
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

tab_upload, tab_chat = st.tabs(["📄 Rapor & Sonuçlar", "💬 AI Asistan"])

with tab_upload:
    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        st.subheader("1. Rapor yükle")
        uploaded = st.file_uploader(
            "PNG veya JPG",
            type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
            help="Net, düz çekilmiş laboratuvar çıktısı en iyi sonucu verir.",
        )

        if uploaded and st.button("Analiz et", type="primary", use_container_width=True):
            with st.spinner("Azure OCR ile tablo okunuyor…"):
                try:
                    st.session_state.parsed_results = run_ocr(uploaded)
                    st.session_state.chat_messages = []
                    st.session_state.interpretation_done = False
                    st.success(f"{len(st.session_state.parsed_results)} test okundu.")
                except Exception as e:
                    st.error(f"OCR hatası: {e}")
                    st.session_state.parsed_results = None

        if uploaded:
            st.image(uploaded, caption="Yüklenen rapor", use_container_width=True)

    with col_right:
        st.subheader("2. Okunan değerler")
        rows = st.session_state.parsed_results
        if rows:
            normal = sum(1 for r in rows if r["status"] == "normal")
            abnormal = len(rows) - normal - sum(1 for r in rows if r["status"] == "unknown")
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam test", len(rows))
            m2.metric("Normal", normal)
            m3.metric("Anormal", abnormal)
            render_results_table(rows)

            st.subheader("3. AI yorumu")
            if st.button("Yorumu oluştur", use_container_width=True):
                try:
                    client = ensure_llm_client()
                    context = build_context(rows)
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
                        {"role": "user", "content": INITIAL_PROMPT},
                    ]
                    st.session_state.chat_messages = [{"role": "user", "content": INITIAL_PROMPT}]
                    full = ""
                    placeholder = st.empty()
                    with placeholder.container():
                        with st.chat_message("assistant"):
                            stream_box = st.empty()
                            for chunk in client.complete_streaming_chat(messages):
                                if not chunk.choices:
                                    continue
                                part = chunk.choices[0].delta.content
                                if part:
                                    full += part
                                    stream_box.markdown(full)
                    st.session_state.chat_messages.append({"role": "assistant", "content": full})
                    st.session_state.interpretation_done = True
                    st.success("Yorum hazır. «AI Asistan» sekmesinden soru sorabilirsiniz.")
                except ImportError:
                    st.error("foundry_local_sdk yüklü değil. requirements.txt ile kurun.")
                except Exception as e:
                    st.error(f"Model hatası: {e}")
        else:
            st.markdown(
                "_Henüz analiz yok. Sol taraftan bir rapor yükleyip **Analiz et**'e basın._"
            )

with tab_chat:
    st.subheader("Sonuçlar hakkında soru sor")
    if not st.session_state.parsed_results:
        st.info("Önce «Rapor & Sonuçlar» sekmesinde bir rapor analiz edin.")
    else:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Örn: Düşük hemoglobin için ne yapmalıyım?"):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            try:
                client = ensure_llm_client()
                context = build_context(st.session_state.parsed_results)
                api_messages = [
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
                ]
                for m in st.session_state.chat_messages:
                    api_messages.append({"role": m["role"], "content": m["content"]})

                full = ""
                with st.chat_message("assistant"):
                    box = st.empty()
                    for chunk in client.complete_streaming_chat(api_messages):
                        if not chunk.choices:
                            continue
                        part = chunk.choices[0].delta.content
                        if part:
                            full += part
                            box.markdown(full)
                st.session_state.chat_messages.append({"role": "assistant", "content": full})
            except Exception as e:
                st.error(f"Sohbet hatası: {e}")
