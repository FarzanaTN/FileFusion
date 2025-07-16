import os
import subprocess

def convert_with_libreoffice(input_path: str, output_path: str, output_format: str) -> bool:
    try:
        # Check if soffice is available
        result = subprocess.run(['soffice', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] LibreOffice not found: {result.stderr}")
            return False

        print(f"[INFO] Converting: {input_path} -> {output_path} as {output_format}")
        subprocess.run([
            'soffice',
            '--headless',
            '--convert-to', output_format,
            '--outdir', os.path.dirname(output_path),
            input_path
        ], check=True, capture_output=True, text=True)

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        generated_file = os.path.join(os.path.dirname(output_path), f"{base_name}.{output_format}")

        if not os.path.exists(generated_file):
            print(f"[ERROR] Conversion failed: Output file {generated_file} not created")
            return False

        if generated_file != output_path:
            os.rename(generated_file, output_path)

        print(f"[INFO] Conversion successful: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] LibreOffice conversion failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"[ERROR] Conversion error: {e}")
        return False