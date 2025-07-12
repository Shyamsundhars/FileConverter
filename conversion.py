import os
import io
import subprocess
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
    """Converts a DOCX file to PDF using pandoc with the xelatex engine."""
    def logic(input_path, temp_dir):
        output_path = os.path.join(temp_dir, "converted.pdf")

        # Using --pdf-engine=xelatex provides much better support for Unicode
        # and custom fonts, which is key to solving the symbol issue.
        extra_args = [
            '--pdf-engine=xelatex',
            '-V', 'geometry:margin=1in',      # Set 1-inch margins
            # Use a single, robust font for all text types to ensure
            # maximum character compatibility and prevent font lookup errors.
            '-V', 'mainfont="Noto Sans"',
            '-V', 'sansfont="Noto Sans"',
            '-V', 'monofont="Noto Sans"',
        ]

        # By setting the working directory to temp_dir, pandoc will correctly
        # find any media (like images) that it extracts from the .docx file,
        # as it places them in a 'media' subdirectory within the CWD.
        try:
            pypandoc.convert_file(
                source_file=input_path,
                to='pdf',
                outputfile=output_path,
                extra_args=extra_args,
                cworkdir=temp_dir
            )
        except OSError as e:
            raise RuntimeError(
                "Pandoc/xelatex conversion failed. Ensure 'pandoc' and 'texlive-*' "
                "packages are in packages.txt, especially 'texlive-xetex'."
            ) from e
        except RuntimeError as e:
            # pypandoc raises RuntimeError on pandoc errors
            error_message = str(e)
            if "Error producing PDF" in error_message:
                err_hint = (
                    "This can happen with complex formatting, missing LaTeX packages, "
                    "or fonts that don't support all characters in the document."
                )
                if "longtable" in error_message:
                    err_hint = (
                        "This often happens with complex tables. "
                        "Ensuring 'texlive-latex-extra' is in packages.txt can help."
                    )
                elif "Missing character" in error_message:
                    err_hint = (
                        "The font is missing characters from your document. "
                        "Ensure 'fonts-noto-core' is in packages.txt and set as the 'mainfont'."
                    )
                elif "kpathsea: Running mktextfm" in error_message:
                    err_hint = (
                        "The TeX engine failed to find or load the specified font. "
                        "This can be a font name or quoting issue."
                    )
                raise RuntimeError(
                    f"Pandoc failed to create PDF. {err_hint} "
                    f"Original error: {error_message}"
                )
            if "xelatex not found" in error_message:
                raise RuntimeError(
                    "The 'xelatex' PDF engine was not found. "
                    "Ensure 'texlive-xetex' is in packages.txt. "
                    f"Original error: {error_message}"
                )
            raise e
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
