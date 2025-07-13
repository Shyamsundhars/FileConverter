import os
import io
import subprocess
import tempfile
from pdf2docx import Converter
from PIL import Image, ImageSequence
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
        # The version of pdf2docx used in the environment does not support
        # the context manager protocol (the 'with' statement).
        # We must manually create the converter, use it, and then close it
        # in a `finally` block to ensure it always runs.
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

        # Pillow expects 'JPEG' for .jpg files, so we normalize the format name.
        save_format = 'JPEG' if output_format.lower() == 'jpg' else output_format.upper()

        output_buffer = io.BytesIO()
        img.save(output_buffer, format=save_format)
        image_data = output_buffer.getvalue()

    return image_data, f"converted.{output_format.lower()}"


def image_to_pdf(uploaded_file, **kwargs):
    """
    Converts a single or multi-frame image file to a PDF document.

    This function handles various image formats like JPG, PNG, GIF, and TIFF,
    creating a multi-page PDF for animated or multi-frame images.
    """
    img = Image.open(uploaded_file)

    # Convert all frames to RGB and store them in a list.
    # This handles single-frame images as well as multi-frame ones (GIFs, TIFFs).
    # Conversion to 'RGB' is a safe choice for PDF compatibility, as it
    # correctly handles transparency (RGBA) and palette-based (P) images.
    rgb_frames = []
    for frame in ImageSequence.Iterator(img):
        rgb_frames.append(frame.convert('RGB'))

    if not rgb_frames:
        raise ValueError("The provided image file contains no frames to convert.")

    # Use a BytesIO buffer to save the PDF in memory.
    output_buffer = io.BytesIO()

    # The first image is used to create the PDF, and subsequent images are appended.
    rgb_frames[0].save(
        output_buffer,
        format="PDF",
        resolution=100.0,
        save_all=True,
        append_images=rgb_frames[1:]
    )

    # Generate a descriptive output filename.
    base_filename = os.path.splitext(uploaded_file.name)[0]
    return output_buffer.getvalue(), f"{base_filename}.pdf"


def docx_to_pdf(uploaded_file, **kwargs):
    """
    Converts a DOCX file to PDF using LibreOffice for high-fidelity layout
    and formatting preservation.
    """
    def logic(input_path, temp_dir):
        # LibreOffice will create a PDF with the same basename as the input file
        # in the specified output directory.
        # e.g., my_document.docx -> my_document.pdf
        base_filename = os.path.basename(input_path)
        pdf_filename = os.path.splitext(base_filename)[0] + '.pdf'
        output_path = os.path.join(temp_dir, pdf_filename)

        try:
            # Use LibreOffice (soffice) to perform a high-fidelity conversion that
            # preserves complex layouts like multi-column pages. This is more
            # reliable than pandoc for visual fidelity. The environment should
            # have `ttf-mscorefonts-installer` in packages.txt to provide
            # common Microsoft fonts, which prevents rendering artifacts.
            subprocess.run(
                [
                    'soffice',  # Use 'soffice' for better stability in some environments
                    '--headless',
                    '--convert-to', 'pdf:writer_pdf_Export',
                    '--outdir', temp_dir,
                    input_path
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120  # Add a timeout for large files
            )
        except FileNotFoundError:
            raise RuntimeError(
                "LibreOffice command not found. "
                "Ensure 'libreoffice-writer' is in packages.txt and in the system's PATH."
            )
        except subprocess.CalledProcessError as e:
            # This happens if LibreOffice fails. The stderr often contains useful diagnostic info.
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
