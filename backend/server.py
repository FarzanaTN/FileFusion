import socket
import threading
import os
import time
from converter import convert_pptx_to_pdf

HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 4096
UPLOAD_DIR = 'uploads'
CONVERTED_DIR = 'converted'

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

def send_with_progress(conn, file_path):
    filesize = os.path.getsize(file_path)
    conn.sendall(str(filesize).encode().ljust(16))  # Send file size fixed 16 bytes

    with open(file_path, 'rb') as f:
        sent = 0
        while sent < filesize:
            data = f.read(BUFFER_SIZE)
            conn.sendall(data)
            sent += len(data)

def receive_with_progress(conn, dest_path):
    filesize = int(conn.recv(16).decode().strip())
    received = 0
    with open(dest_path, 'wb') as f:
        while received < filesize:
            data = conn.recv(min(BUFFER_SIZE, filesize - received))
            if not data:
                break
            f.write(data)
            received += len(data)
    return filesize

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    try:
        # Receive original file name size and name
        name_len = int(conn.recv(4).decode())
        filename = conn.recv(name_len).decode()
        print(f"Receiving file: {filename}")
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pptx", ".docx"]:
            conn.sendall(b"ERROR")
            conn.close()
            return

        # Receive file with progress
        upload_start = time.time()
        uploaded_size = receive_with_progress(conn, os.path.join(UPLOAD_DIR, filename))
        upload_end = time.time()

        print(f"Upload completed in {upload_end - upload_start:.2f} seconds")

        # Convert the file
        input_file = os.path.join(UPLOAD_DIR, filename)
        output_file = os.path.join(CONVERTED_DIR, f"{os.path.splitext(filename)[0]}.pdf")

        success = convert_pptx_to_pdf(input_file, output_file)
        if not success:
            conn.sendall(b"ERROR")
            conn.close()
            return

        # Notify client conversion done and send converted file size and file
        conn.sendall(b"OK")

        # Send converted file name length and name
        converted_filename = os.path.basename(output_file)
        conn.sendall(str(len(converted_filename)).encode().ljust(4))
        conn.sendall(converted_filename.encode())

        # Send converted file with progress and timing
        download_start = time.time()
        send_with_progress(conn, output_file)
        download_end = time.time()
        
        

        # Send upload time and download time as float strings
        conn.sendall(f"{upload_end - upload_start:.4f}".encode().ljust(16))
        conn.sendall(f"{download_end - download_start:.4f}".encode().ljust(16))

        print(f"Download sent in {download_end - download_start:.2f} seconds")

    except Exception as e:
        print("Error handling client:", e)

    finally:
        conn.close()
        print(f"[DISCONNECTED] {addr} disconnected.")


def start_server():
    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


if __name__ == "__main__":
    start_server()
