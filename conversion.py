import os
import io
import subprocess
import tempfile
from pdf2docx import Converter
from PIL import Image, ImageSequence
from PyPDF2 import PdfMerger
import zipfile
# from pydub import AudioSegment

def _convert_with_temp_file(uploaded_file, conversion_logic):
    """
    A helper to handle the boilerplate of writing an uploaded file to a
    temporary location, running a conversion function, and reading the output.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        output_path = conversion_logic(input_path, temp_dir)

        with open(output_path, "rb") as f:
            output_data = f.read()

    output_filename = os.path.basename(output_path)
    return output_data, output_filename

def pdf_to_docx(uploaded_file, **kwargs):
    def logic(input_path, temp_dir):
        output_path = os.path.join(temp_dir, "converted.docx")
        cv = Converter(input_path)
        try:
            cv.convert(output_path)
        finally:
            cv.close()
        return output_path

    return _convert_with_temp_file(uploaded_file, logic)


def image_convert(uploaded_file, output_format, **kwargs):
    with Image.open(uploaded_file) as img:
        if output_format.lower() in ['jpg', 'jpeg'] and img.mode == 'RGBA':
            img = img.convert('RGB')
        save_format = 'JPEG' if output_format.lower() == 'jpg' else output_format.upper()

        output_buffer = io.BytesIO()
        img.save(output_buffer, format=save_format)
        image_data = output_buffer.getvalue()

    return image_data, f"converted.{output_format.lower()}"


def merge_pdfs(uploaded_files, **kwargs):
    """
    Merges multiple PDF files into a single PDF document.

    Args:
        uploaded_files (list): A list of file-like objects (from Streamlit's
                               file_uploader) to be merged.
    """
    if not uploaded_files or len(uploaded_files) < 2:
        raise ValueError("Please upload at least two PDF files to merge.")

    merger = PdfMerger()

    for pdf_file in uploaded_files:
        merger.append(pdf_file)

    output_buffer = io.BytesIO()
    merger.write(output_buffer)
    merger.close()

    return output_buffer.getvalue(), "merged.pdf"

def image_to_pdf(uploaded_file, **kwargs):
    """
    Converts a single or multi-frame image file to a PDF document.

    This function handles various image formats like JPG, PNG, GIF, and TIFF,
    creating a multi-page PDF for animated or multi-frame images.
    """
    img = Image.open(uploaded_file)
    rgb_frames = []
    for frame in ImageSequence.Iterator(img):
        rgb_frames.append(frame.convert('RGB'))

    if not rgb_frames:
        raise ValueError("The provided image file contains no frames to convert.")
    output_buffer = io.BytesIO()
    rgb_frames[0].save(
        output_buffer,
        format="PDF",
        resolution=100.0,
        save_all=True,
        append_images=rgb_frames[1:]
    )
    base_filename = os.path.splitext(uploaded_file.name)[0]
    return output_buffer.getvalue(), f"{base_filename}.pdf"


def pdf_to_image(uploaded_file, image_format, **kwargs):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, page in enumerate(doc):
            pix = page.get_pixmap()
            img_bytes = pix.tobytes(output=image_format.lower())

            image_filename = f"page_{i + 1}.{image_format.lower()}"
            zip_file.writestr(image_filename, img_bytes)

    doc.close()
    base_filename = os.path.splitext(uploaded_file.name)[0]
    return zip_buffer.getvalue(), f"{base_filename}_images.zip"


def docx_to_pdf(uploaded_file, **kwargs):
    def logic(input_path, temp_dir):
        base_filename = os.path.basename(input_path)
        pdf_filename = os.path.splitext(base_filename)[0] + '.pdf'
        output_path = os.path.join(temp_dir, pdf_filename)

        try:
            subprocess.run(
                [
                    'soffice', 
                    '--headless',
                    '--convert-to', 'pdf:writer_pdf_Export',
                    '--outdir', temp_dir,
                    input_path
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120 
            )
        except FileNotFoundError:
            raise RuntimeError(
                "LibreOffice command not found. "
                "Ensure 'libreoffice-writer' is in packages.txt and in the system's PATH."
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LibreOffice conversion failed.\nStderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice conversion timed out after 120 seconds.")

        if not os.path.exists(output_path):
            raise FileNotFoundError(
                f"LibreOffice ran but failed to create the output PDF file at {output_path}. "
                "This may be due to a problem with the input file or a missing font."
            )

        return output_path

    return _convert_with_temp_file(uploaded_file, logic)


# def audio_convert(uploaded_file, output_format, **kwargs):
#     """Converts an audio file to a different format in-memory."""
#     # pydub can read directly from a file-like object
#     audio = AudioSegment.from_file(uploaded_file)
#
#     output_buffer = io.BytesIO()
#     audio.export(output_buffer, format=output_format)
#     audio_data = output_buffer.getvalue()
#
#     return audio_data, f"converted.{output_format.lower()}"
