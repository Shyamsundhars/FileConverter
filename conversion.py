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
    """
    Converts a DOCX file to PDF using a two-step process for high fidelity:
    1. Sanitize the DOCX with Pandoc to remove complex/problematic elements.
    2. Convert the sanitized DOCX to PDF with LibreOffice to preserve layout.
    """
    def logic(input_path, temp_dir):
        # --- Step 1: Sanitize the DOCX with Pandoc ---
        sanitized_docx_path = os.path.join(temp_dir, "sanitized.docx")
        try:
            # Converting docx to docx with pandoc cleans up a lot of
            # underlying XML, resolving issues with complex or corrupted files.
            # This can fix artifacts and layout issues in the final PDF.
            subprocess.run(
                [
                    'pandoc',
                    input_path,
                    '-o', sanitized_docx_path,
                    '--wrap=none' # Helps preserve line breaks
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60
            )
        except FileNotFoundError:
             raise RuntimeError(
                "Pandoc command not found. Ensure 'pandoc' is in packages.txt."
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            error_details = e.stderr if hasattr(e, 'stderr') else str(e)
            raise RuntimeError(
                "Pandoc sanitization step failed. This can happen with highly complex or "
                f"malformed DOCX files. Error: {error_details}"
            )

        # --- Step 2: Convert the sanitized DOCX to PDF with LibreOffice ---
        # LibreOffice creates a PDF with the same name as the input file.
        pdf_filename = "sanitized.pdf"
        output_path = os.path.join(temp_dir, pdf_filename)

        try:
            # Use LibreOffice for a high-fidelity conversion that
            # preserves complex layouts like multi-column pages.
            subprocess.run(
                [
                    'libreoffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', temp_dir,
                    sanitized_docx_path # Use the sanitized file
                ],
                check=True, capture_output=True, text=True,
                timeout=120  # Add a timeout for large files
            )
        except FileNotFoundError:
            raise RuntimeError("LibreOffice command not found. Ensure 'libreoffice-writer' is in packages.txt.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LibreOffice conversion failed.\nStderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice conversion timed out after 120 seconds.")

        if not os.path.exists(output_path):
            raise FileNotFoundError("LibreOffice ran but failed to create the output PDF file.")

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
