import os
import io
import tempfile
from pdf2docx import Converter
from PIL import Image
import pypandoc
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
        cv.convert(output_path)
        cv.close()
        return output_path

    return _convert_with_temp_file(uploaded_file, logic)


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
    def logic(input_path, temp_dir):
        output_path = os.path.join(temp_dir, "converted.pdf")
        pypandoc.convert_file(input_path, 'pdf', outputfile=output_path,
                              extra_args=['--pdf-engine=wkhtmltopdf', # Use wkhtmltopdf engine
                                          # Pass the --enable-local-file-access flag TO the engine
                                          '--pdf-engine-opt=--enable-local-file-access'])
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
