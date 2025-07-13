import os
import io
import subprocess
import tempfile
import re
from pdf2docx import Converter
from PIL import Image, ImageSequence
from PyPDF2 import PdfMerger
import zipfile
# from pydub import AudioSegment
import fitz  # PyMuPDF

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

def _parse_page_ranges(ranges_string: str, max_pages: int) -> list[list[int]]:
    """Parses a page range string like '1-3, 5, 7-9' into a list of page lists."""
    if not ranges_string.strip():
        raise ValueError("Page range cannot be empty.")

    final_page_groups = []
    parts = [part.strip() for part in ranges_string.split(',') if part.strip()]

    for part in parts:
        page_list = []
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if not (0 < start <= end <= max_pages):
                    raise ValueError(f"Invalid page range '{part}'. Pages must be between 1 and {max_pages}.")
                page_list.extend(range(start - 1, end))  # User input is 1-based
            except (ValueError, IndexError):
                raise ValueError(f"Invalid range format '{part}'. Use numbers like '1-4'.")
        else:
            try:
                page_num = int(part)
                if not (0 < page_num <= max_pages):
                    raise ValueError(f"Invalid page number '{page_num}'. Page must be between 1 and {max_pages}.")
                page_list.append(page_num - 1) # User input is 1-based
            except ValueError:
                raise ValueError(f"Invalid page number format '{part}'. Use numbers like '5'.")

        if page_list:
            # Use set to remove duplicates and then sort
            final_page_groups.append(sorted(list(set(page_list))))

    if not final_page_groups:
        raise ValueError("No valid pages found in the provided range string.")

    return final_page_groups

def split_pdf(uploaded_file, page_ranges: str, **kwargs):
    """Splits a PDF based on specified page ranges into separate PDF files."""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    parsed_page_groups = _parse_page_ranges(page_ranges, len(doc))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, page_list in enumerate(parsed_page_groups):
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page_list=page_list)
            pdf_bytes = new_doc.tobytes(garbage=4, deflate=True)
            part_name = f"split_part_{i+1}_pages_{page_list[0]+1}-{page_list[-1]+1}.pdf"
            zip_file.writestr(part_name, pdf_bytes)
            new_doc.close()

    doc.close()
    base_filename = os.path.splitext(uploaded_file.name)[0]
    return zip_buffer.getvalue(), f"{base_filename}_split.zip"

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
