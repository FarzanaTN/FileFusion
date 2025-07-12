import socket
import streamlit as st
import time
import os

HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 4096

# Allowed input → output mappings (must match server's)
ALLOWED_CONVERSIONS = {
    ".doc": ["pdf", "docx", "odt"],
    ".docx": ["pdf", "doc", "odt"],
    ".odt": ["pdf", "docx"],
    ".pptx": ["pdf"],
    ".xlsx": ["pdf"],
    ".xls": ["pdf"],
}

def send_with_progress(sock, file_bytes, progress_bar):
    total = len(file_bytes)
    sent = 0
    while sent < total:
        end = min(sent + BUFFER_SIZE, total)
        sock.sendall(file_bytes[sent:end])
        sent = end
        progress_bar.progress(sent / total)
    progress_bar.progress(1.0)

def receive_with_progress(sock, filesize, progress_bar):
    received = 0
    chunks = []
    while received < filesize:
        chunk = sock.recv(min(BUFFER_SIZE, filesize - received))
        if not chunk:
            break
        chunks.append(chunk)
        received += len(chunk)
        progress_bar.progress(received / filesize)
    progress_bar.progress(1.0)
    return b''.join(chunks)

def main():
    st.title("📄 Multi-Format File Converter")
    uploaded_file = st.file_uploader("Upload your file", type=list(ALLOWED_CONVERSIONS.keys()))

    output_format = None
    if uploaded_file:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_outputs = ALLOWED_CONVERSIONS.get(file_ext, [])

        if not allowed_outputs:
            st.error("Unsupported file type.")
            return
        else:
            output_format = st.selectbox("Select output format", allowed_outputs)

    if uploaded_file and output_format:
        filename = uploaded_file.name
        file_bytes = uploaded_file.read()

        if st.button("Upload and Convert"):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((HOST, PORT))

                # Send filename length and name
                sock.sendall(str(len(filename)).encode().ljust(4))
                sock.sendall(filename.encode())

                # Send output format (up to 8 bytes)
                sock.sendall(output_format.encode().ljust(8))

                # Send file size
                sock.sendall(str(len(file_bytes)).encode().ljust(16))

                st.info("Uploading...")
                upload_bar = st.progress(0)
                send_with_progress(sock, file_bytes, upload_bar)

                response = sock.recv(2)
                if response != b"OK":
                    st.error("Conversion failed. Server may not support this format.")
                    sock.close()
                    return

                # Receive filename
                name_len = int(sock.recv(4).decode().strip())
                converted_name = sock.recv(name_len).decode()

                # Receive file size
                converted_size = int(sock.recv(16).decode().strip())
                st.info(f"Downloading {converted_name}")
                download_bar = st.progress(0)
                converted_bytes = receive_with_progress(sock, converted_size, download_bar)

                upload_time_server = float(sock.recv(16).decode().strip())
                download_time_server = float(sock.recv(16).decode().strip())

                sock.close()

                st.success("Conversion successful!")
                st.write(f"Upload time: {upload_time_server:.2f} s")
                st.write(f"Download time: {download_time_server:.2f} s")

                st.download_button(
                    label="Download Converted File",
                    data=converted_bytes,
                    file_name=converted_name,
                    mime='application/octet-stream'
                )

            except Exception as e:
                st.error(f"Connection failed: {e}")

if __name__ == "__main__":
    main()