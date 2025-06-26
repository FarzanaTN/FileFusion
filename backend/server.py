import socket
import threading
import os
import time
from converter import convert_with_libreoffice

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
        name_len = int(conn.recv(4).decode())
        filename = conn.recv(name_len).decode()

        output_format = conn.recv(8).decode().strip().lower()

        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pptx", ".doc", ".docx", ".odt", ".xls", ".xlsx"]:
            conn.sendall(b"ER")
            conn.close()
            return

        input_path = os.path.join(UPLOAD_DIR, filename)
        output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
        output_path = os.path.join(CONVERTED_DIR, output_filename)

        upload_start = time.time()
        receive_with_progress(conn, input_path)
        upload_end = time.time()

        success = convert_with_libreoffice(input_path, output_path, output_format)
        if not success:
            conn.sendall(b"ER")
            conn.close()
            return

        conn.sendall(b"OK")

        conn.sendall(str(len(output_filename)).encode().ljust(4))
        conn.sendall(output_filename.encode())
        send_with_progress(conn, output_path)

        download_end = time.time()

        conn.sendall(f"{upload_end - upload_start:.4f}".encode().ljust(16))
        conn.sendall(f"{download_end - upload_end:.4f}".encode().ljust(16))

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