import io
import html
import time
import fitz  # PyMuPDF
import streamlit as st
from datetime import datetime
from deep_translator import GoogleTranslator

# -------------- UI CONFIG --------------
st.set_page_config(page_title="PDF Translator", page_icon="🌐", layout="centered")

st.title("🌐 Translate PDF ALL Language")
st.caption("Translate text blocks inside a PDF, overlay with white background and **black** translated text.")

with st.sidebar:
    st.header("Settings")
    target_lang = st.text_input("Target language code", value="id", help="e.g., 'id' for Indonesian, 'en' for English, 'es' for Spanish")
    source_lang = st.text_input("Source language code (auto if blank)", value="auto")
    min_font_size = st.number_input("Minimum font size (pt)", min_value=6.0, value=9.5, step=0.5, help="Adjust if text overflows or is too small")
    line_height = st.number_input("Line height (em)", min_value=1.0, value=1.25, step=0.05)
    use_textbox = st.toggle("Use insert_textbox fallback (no HTML)", value=False, help="If insert_htmlbox misbehaves, use plain text mode")

uploaded = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)

colA, colB = st.columns(2)
with colA:
    start_page = st.number_input("From page (1-based)", min_value=1, value=1, step=1)
with colB:
    end_page = st.number_input("To page (0 = auto to last)", min_value=0, value=0, step=1)

run = st.button("🚀 Translate PDF")

# -------------- HELPERS --------------
WHITE = fitz.pdfcolor["white"]
BLACK = fitz.pdfcolor["black"]
TEXTFLAGS = fitz.TEXT_DEHYPHENATE

@st.cache_data(show_spinner=False)
def _translate(text: str, src: str, tgt: str) -> str:
    translator = GoogleTranslator(source=src if src.strip() else "auto", target=tgt)
    return translator.translate(text)

def text_to_html(s: str) -> str:
    safe = html.escape(s or "")
    safe = safe.replace("\n", "<br>")
    return f"<div class='id-text'>{safe}</div>"

# -------------- MAIN ACTION --------------
if run:
    if not uploaded:
        st.error("Please upload a PDF first.")
        st.stop()

    # Load PDF into memory for PyMuPDF
    data = uploaded.read()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        st.exception(e)
        st.stop()

    total_pages = doc.page_count

    # Compute page range (convert to 0-based indices)
    first_idx = max(0, int(start_page) - 1)
    last_idx = total_pages - 1 if int(end_page) == 0 else min(total_pages - 1, int(end_page) - 1)
    if first_idx > last_idx:
        st.error("Invalid page range.")
        st.stop()

    # Create translation layer
    ocg = doc.add_ocg(f"Translated({target_lang})", on=True)

    progress = st.progress(0)
    status = st.empty()

    # Iterate pages
    for pno in range(first_idx, last_idx + 1):
        page = doc[pno]
        status.info(f"Translating page {pno + 1}/{last_idx + 1}…")

        try:
            blocks = page.get_text("blocks", flags=TEXTFLAGS)
        except Exception:
            blocks = []

        for block in blocks:
            bbox = block[:4]
            text = block[4] if len(block) > 4 else ""

            if not isinstance(text, str) or not text.strip():
                continue

            # Translate (cached)
            try:
                translated = _translate(text, source_lang, target_lang)
            except Exception:
                translated = text  # fallback keeps process moving

            if not isinstance(translated, str):
                continue

            # Paint white rectangle to cover original
            try:
                page.draw_rect(bbox, color=None, fill=WHITE, oc=ocg)
            except Exception:
                continue

            # Place translated text
            try:
                if use_textbox:
                    page.insert_textbox(
                        bbox,
                        translated,
                        fontsize=min_font_size,
                        color=BLACK,
                        align=0,  # left
                        render_mode=0,
                        overlay=True,
                        oc=ocg,
                    )
                else:
                    html_text = text_to_html(translated)
                    css = f"""
                    * {{ font-family: sans-serif; }}
                    .id-text {{
                        font-size: {min_font_size}pt;
                        line-height: {line_height};
                        color: black;
                        white-space: normal;
                        word-wrap: break-word;
                    }}
                    """
                    page.insert_htmlbox(bbox, html_text, css=css, oc=ocg)
            except Exception:
                try:
                    page.insert_textbox(
                        bbox,
                        translated,
                        fontsize=min_font_size,
                        color=BLACK,
                        align=0,
                        render_mode=0,
                        overlay=True,
                        oc=ocg,
                    )
                except Exception:
                    pass

        progress.progress(int(((pno - first_idx + 1) / (last_idx - first_idx + 1)) * 100))
        time.sleep(0.02)

    # Optimize fonts and export into memory
    try:
        doc.subset_fonts()
    except Exception:
        pass

    out_stream = io.BytesIO()
    doc.ez_save(out_stream)
    doc.close()

    out_stream.seek(0)

    # Dynamic file name: [original]_translated_[HHMMSS].pdf
    base_name = uploaded.name.rsplit('.', 1)[0]
    timestamp = datetime.now().strftime("%H%M%S")
    output_filename = f"{base_name}_translated_{timestamp}.pdf"

    st.success("Translation complete! Download your PDF below.")
    st.download_button(
        label=f"⬇️ Download {output_filename}",
        data=out_stream,
        file_name=output_filename,
        mime="application/pdf",
    )

    with st.expander("Troubleshooting & Tips"):
        st.markdown(
            """
            - If text overflows or looks cramped, increase **Minimum font size** or **Line height**.
            - If `insert_htmlbox` causes issues on certain PDFs, enable **Use insert_textbox fallback**.
            - Some PDFs contain scanned images; this tool doesn't run OCR.
            - Rate limits from GoogleTranslator can cause occasional fallbacks to original text.
            - For large PDFs, translate a page range first to test layout.
            """
        )