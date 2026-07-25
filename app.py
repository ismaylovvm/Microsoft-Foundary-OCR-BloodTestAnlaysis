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


def ensure_llm_client():
    if st.session_state.get("llm_client") is not None:
        return st.session_state.llm_client

    with st.status("Yerel AI modeli hazırlanıyor…", expanded=True) as status:
        ep_label = st.empty()

        def ep_progress(ep_name: str, percent: float):
            ep_label.write(f"{ep_name}: {percent:.1f}%")

        st.write("Execution provider kayıtları indiriliyor…")
        manager = initialize_manager(progress_callback=ep_progress)

        dl_label = st.empty()

        def download_progress(progress: float):
            dl_label.write(f"Phi-4-mini indiriliyor: {progress:.1f}%")

        st.write("Model yükleniyor…")
        model, client = load_model_and_client(manager, download_progress=download_progress)
        st.session_state.llm_model = model
        st.session_state.llm_client = client
        status.update(label="Model hazır", state="complete")

    return client


def run_ocr_from_upload(uploaded_file) -> list[dict]:
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    return analyze_blood_test(tmp_path)


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


with st.sidebar:
    st.markdown("## 🩸")
    st.title("Ayarlar")
    st.caption("OCR + yerel Phi-4-mini akışı `llm_analysis.py` ile aynıdır.")
    st.divider()
    st.markdown("**Gerekli ortam değişkenleri**")
    st.code("ocr_endpoint\nocr_key", language="text")
    st.markdown("**CLI alternatifi**")
    st.code("python llm_analysis.py", language="bash")
    st.info(
        "Bu uygulama tıbbi teşhis koymaz; bilgilendirme amaçlıdır. "
        "Sonuçlar için mutlaka bir hekime danışın."
    )

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
                    st.session_state.parsed_results = run_ocr_from_upload(uploaded)
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

        if prompt := st.chat_input("Örn: What should I do about low hemoglobin?"):
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
                st.error(f"Sohbet hatası: {e}")
