import streamlit as st
from conversion import pdf_to_docx, image_convert, docx_to_pdf #, audio_convert

st.title("Free Universal File Converter")

# Configuration dictionary to make the app more scalable and less repetitive
CONVERSION_CONFIG = {
    "PDF to DOCX": {
        "uploader_label": "Upload PDF",
        "file_types": ["pdf"],
        "conversion_func": pdf_to_docx,
    },
    "Image to Image": {
        "uploader_label": "Upload Image",
        "file_types": ["jpg", "png", "bmp", "tiff", "gif"],
        "conversion_func": image_convert,
        "extra_ui": lambda: st.selectbox("Output format", ["png", "jpg", "bmp", "tiff", "gif"]),
        "extra_arg_name": "output_format",
    },
    "DOCX to PDF": {
        "uploader_label": "Upload DOCX",
        "file_types": ["docx"],
        "conversion_func": docx_to_pdf,
    },
    # "Audio to Audio": {
    #     "uploader_label": "Upload Audio",
    #     "file_types": ["mp3", "wav", "ogg", "flac"],
    #     "conversion_func": audio_convert,
    #     "extra_ui": lambda: st.selectbox("Output format", ["mp3", "wav", "ogg", "flac"]),
    #     "extra_arg_name": "output_format",
    # },
}

conversion_choice = st.selectbox("Choose conversion", list(CONVERSION_CONFIG.keys()))

# Get the configuration for the selected conversion
config = CONVERSION_CONFIG[conversion_choice]

uploaded_file = st.file_uploader(label=config["uploader_label"], type=config["file_types"])

extra_args = {}
if "extra_ui" in config:
    extra_arg_value = config["extra_ui"]()
    extra_args[config["extra_arg_name"]] = extra_arg_value

if uploaded_file and st.button(f"Convert to {conversion_choice.split(' to ')[-1]}"):
    with st.spinner("Converting..."):
        output, filename = config["conversion_func"](uploaded_file, **extra_args)
        st.download_button("Download Converted File", output, file_name=filename)
