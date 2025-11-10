Streamlit PDF Translator (English ➜ Indonesian) using PyMuPDF + deep_translator

How to run:
1) pip install -U streamlit pymupdf deep-translator
2) streamlit run main.py

Notes:
- Uses insert_htmlbox() to render translated text as HTML with black text over a white rectangle.
- Handles empty blocks safely, escapes HTML, and shows a progress bar.
- Optionally lets you choose page range and target language.
- Produces a downloadable translated PDF with dynamic filename: [originalname]_translated_[HHMMSS].pdf