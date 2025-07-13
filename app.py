import os
import streamlit as st
from streamlit_sortables import sort_items
from conversion import pdf_to_docx, image_convert, docx_to_pdf, image_to_pdf, pdf_to_image, merge_pdfs, split_pdf #, audio_convert

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
    "Merge PDFs": {
        "uploader_label": "Upload PDFs to Merge",
        "file_types": ["pdf"],
        "conversion_func": merge_pdfs,
        "output_name": "Merged PDF",
        "multiple_files": True,
        "failure_tip": "Merging can fail if one of the PDFs is corrupted or password-protected.",
    },
    "Split PDF": {
        "uploader_label": "Upload PDF to Split",
        "file_types": ["pdf"],
        "conversion_func": split_pdf,
        "extra_ui": lambda: st.text_input(
            "Page ranges to split (e.g., 1-3, 4, 5-7)",
            placeholder="1-3, 5, 7-9"
        ),
        "extra_arg_name": "page_ranges",
        "output_name": "Split PDFs (zip)",
        "failure_tip": "Splitting can fail if the page range format is incorrect or the PDF is corrupted/empty.",
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

uploaded_content = st.file_uploader(
    label=config["uploader_label"],
    type=config["file_types"],
    accept_multiple_files=config.get("multiple_files", False)
)

files_to_process = uploaded_content

# Add UI for reordering files if the selected conversion is "Merge PDFs"
if conversion_choice == "Merge PDFs" and uploaded_content:
    if len(uploaded_content) > 1:
        # Create a dictionary to map names back to file objects
        file_map = {f.name: f for f in uploaded_content}

        # Get a list of original filenames to pass to the sortable list
        original_filenames = [f.name for f in uploaded_content]

        # Use the sort_items component to allow drag-and-drop reordering
        sorted_filenames = sort_items(
            original_filenames,
            header="Set Merge Order",
            direction="vertical"
        )

        # Re-create the list of file objects in the desired order
        files_to_process = [file_map[name] for name in sorted_filenames]


extra_args = {}
if extra_ui_func := config.get("extra_ui"):
    extra_args[config["extra_arg_name"]] = extra_ui_func()

if files_to_process and st.button(f"Convert to {config['output_name']}"):
    with st.spinner("Converting..."):
        try:
            output, filename = config["conversion_func"](files_to_process, **extra_args)
            if not output:
                st.error("Conversion failed and produced an empty file.")
                if tip := config.get("failure_tip"):
                    st.info(tip)
            else:
                st.download_button("Download Converted File", output, file_name=filename)
        except Exception as e:
            st.error("An error occurred during conversion.")
            st.error(f"Details: {e}")
            st.info("This can happen with corrupted, encrypted, or unusually complex files (e.g., complex tables).")
            st.exception(e)
