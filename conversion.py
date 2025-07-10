import os
import io
import tempfile
from pdf2docx import Converter
from PIL import Image
import pypandoc
# from pydub import AudioSegment


def pdf_to_docx(uploaded_file, **kwargs):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        output_path = os.path.join(temp_dir, "converted.docx")
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()

        with open(output_path, "rb") as f:
            docx_data = f.read()

    return docx_data, "converted.docx"


def image_convert(uploaded_file, output_format, **kwargs):
    with Image.open(uploaded_file) as img:
        if output_format.lower() in ['jpg', 'jpeg'] and img.mode == 'RGBA':
            img = img.convert('RGB')

        # Pillow expects 'JPEG' for .jpg files.
        save_format = output_format.upper()
        if save_format == 'JPG':
            save_format = 'JPEG'

        output_buffer = io.BytesIO()
        img.save(output_buffer, format=save_format)
        image_data = output_buffer.getvalue()

    return image_data, f"converted.{output_format.lower()}"


def docx_to_pdf(uploaded_file, **kwargs):
    # Requires pandoc to be installed on the system
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        output_path = os.path.join(temp_dir, "converted.pdf")
        pypandoc.convert_file(input_path, 'pdf', outputfile=output_path)

        with open(output_path, "rb") as f:
            pdf_data = f.read()

    return pdf_data, "converted.pdf"


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
