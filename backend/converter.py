import os
import subprocess
import uuid

def convert_pptx_to_pdf(input_path: str, output_path: str) -> bool:
    """
    Convert pptx file to pdf using libreoffice CLI.
    Returns True if successful, else False.
    """

    # LibreOffice command to convert file
    # --headless = no UI, --convert-to pdf = convert to pdf
    # --outdir = output directory
    try:
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(output_path),
            input_path
        ], check=True)

        # LibreOffice will create a PDF with same basename in output directory
        # Rename/move it to desired output_path if needed
        base_pdf = os.path.splitext(os.path.basename(input_path))[0] + '.pdf'
        generated_pdf = os.path.join(os.path.dirname(output_path), base_pdf)

        if generated_pdf != output_path:
            os.rename(generated_pdf, output_path)

        return True

    except Exception as e:
        print("Conversion error:", e)
        return False
