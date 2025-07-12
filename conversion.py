import os
import io
import subprocess
import tempfile
from pdf2docx import Converter
from PIL import Image
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
        with Converter(input_path) as cv:
            cv.convert(output_path)
        return output_path

    return _convert_with_temp_file(uploaded_file, logic)


def image_convert(uploaded_file, output_format, **kwargs):
    with Image.open(uploaded_file) as img:
        if output_format.lower() in ['jpg', 'jpeg'] and img.mode == 'RGBA':
            img = img.convert('RGB')

        # Pillow expects 'JPEG' for .jpg files, so we normalize the format name.
        save_format = 'JPEG' if output_format.lower() == 'jpg' else output_format.upper()

        output_buffer = io.BytesIO()
        img.save(output_buffer, format=save_format)
        image_data = output_buffer.getvalue()

    return image_data, f"converted.{output_format.lower()}"


def docx_to_pdf(uploaded_file, **kwargs):
    """Converts a DOCX file to PDF using LibreOffice in headless mode."""
    def logic(input_path, temp_dir):
        # LibreOffice will create a PDF with the same name as the input file
        # in the specified output directory.
        # e.g., /tmp/xyz/document.docx -> /tmp/xyz/document.pdf
        
        # We must set a HOME env var for LibreOffice in headless mode to prevent
        # it from trying to write to the real home directory, which may not be
        # writable in a containerized environment.
        env = os.environ.copy()
        env["HOME"] = temp_dir

        command = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            temp_dir,
            input_path,
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=90,  # Generous timeout for large or complex files
                env=env,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "LibreOffice not found. Ensure 'libreoffice' is in your packages.txt."
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            stderr = e.stderr.decode("utf-8", "ignore") if hasattr(e, 'stderr') else "Timeout expired."
            raise RuntimeError(f"LibreOffice conversion failed. Error: {stderr}")

        # The output file will have the same name as the input, but with a .pdf extension.
        pdf_filename = os.path.splitext(os.path.basename(input_path))[0] + ".pdf"
        generated_pdf_path = os.path.join(temp_dir, pdf_filename)

        if not os.path.exists(generated_pdf_path):
            stderr_info = result.stderr.decode("utf-8", "ignore")
            raise FileNotFoundError(
                f"LibreOffice did not produce a PDF file. STDERR: {stderr_info}"
            )
        
        return generated_pdf_path

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
