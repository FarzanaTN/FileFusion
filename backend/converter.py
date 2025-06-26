import os
import subprocess

def convert_with_libreoffice(input_path: str, output_path: str, output_format: str) -> bool:
    try:
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', output_format,
            '--outdir', os.path.dirname(output_path),
            input_path
        ], check=True)

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        generated_file = os.path.join(os.path.dirname(output_path), f"{base_name}.{output_format}")

        if generated_file != output_path:
            os.rename(generated_file, output_path)

        return True
    except Exception as e:
        print("Conversion error:", e)
        return False
