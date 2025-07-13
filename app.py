import os
import streamlit as st
from conversion import pdf_to_docx, image_convert, docx_to_pdf, image_to_pdf, pdf_to_image #, audio_convert

os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-appuser")

st.title("File Converter")

# Configuration dictionary to make the app more scalable and less repetitive
CONVERSION_CONFIG = {
    "PDF to DOCX": {
        "uploader_label": "Upload PDF",
        "file_types": ["pdf"],
        "conversion_func": pdf_to_docx,
        "output_name": "DOCX",
        "failure_tip": "This can happen with scanned (image-based) PDFs or very complex layouts.",
    },
    "Image to Image": {
        "uploader_label": "Upload Image",
        "file_types": ["jpg", "png", "bmp", "tiff", "gif"],
        "conversion_func": image_convert,
        "extra_ui": lambda: st.selectbox("Output format", ["png", "jpg", "bmp", "tiff", "gif"]),
        "extra_arg_name": "output_format",
        "output_name": "Image",
    },
    "Image to PDF": {
        "uploader_label": "Upload Image",
        "file_types": ["jpg", "jpeg", "png", "bmp", "tiff", "gif"],
        "conversion_func": image_to_pdf,
        "output_name": "PDF",
        "failure_tip": "Conversion can fail for corrupted or unsupported image formats.",
    },
    "PDF to Image": {
        "uploader_label": "Upload PDF to Convert to Images",
        "file_types": ["pdf"],
        "conversion_func": pdf_to_image,
        "extra_ui": lambda: st.selectbox("Output image format", ["png", "jpg"]),
        "extra_arg_name": "image_format",
        "output_name": "Images (zip)",
        "failure_tip": "Conversion can fail for complex or corrupted PDFs.",
    },
    "DOCX to PDF": {
        "uploader_label": "Upload DOCX",
        "file_types": ["docx"],
        "conversion_func": docx_to_pdf,
        "output_name": "PDF",
        "failure_tip": "Conversion can fail for documents with very complex formatting or unsupported special characters/fonts.",
    },
    #Future Audio Component:
    # "Audio to Audio": {
    #     "uploader_label": "Upload Audio",
    #     "file_types": ["mp3", "wav", "ogg", "flac"],
    #     "conversion_func": audio_convert,
    #     "extra_ui": lambda: st.selectbox("Output format", ["mp3", "wav", "ogg", "flac"]),
    #     "extra_arg_name": "output_format",
    # },
}

conversion_choice = st.selectbox("Choose conversion", list(CONVERSION_CONFIG.keys()))

config = CONVERSION_CONFIG[conversion_choice]

uploaded_file = st.file_uploader(label=config["uploader_label"], type=config["file_types"])

# Handle optional UI elements for conversions like Image to Image
extra_args = {}
if extra_ui_func := config.get("extra_ui"):
    extra_args[config["extra_arg_name"]] = extra_ui_func()

if uploaded_file and st.button(f"Convert to {config['output_name']}"):
    with st.spinner("Converting..."):
        try:
            output, filename = config["conversion_func"](uploaded_file, **extra_args)
            if not output:
                st.error("Conversion failed and produced an empty file.")
                # Provide a context-specific tip from the config
                if tip := config.get("failure_tip"):
                    st.info(tip)
            else:
                st.download_button("Download Converted File", output, file_name=filename)
        except Exception as e:
            st.error("An error occurred during conversion.")
            st.error(f"Details: {e}")
            st.info("This can happen with corrupted, encrypted, or unusually complex files (e.g., complex tables).")
            st.exception(e)
