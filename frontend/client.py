import socket
import streamlit as st
import time
import os

HOST = '127.0.0.1'  # Change if server on different machine
PORT = 65432
BUFFER_SIZE = 4096

def send_with_progress(sock, file_bytes, progress_bar):
    total = len(file_bytes)
    sent = 0
    chunk_size = 4096

    while sent < total:
        end = min(sent + chunk_size, total)
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
    st.title("PPTX to PDF File Converter")

    # uploaded_file = st.file_uploader("Drag and drop PPTX file here", type=["pptx"])
    
    uploaded_file = st.file_uploader("Drag and drop PPTX or DOCX file here", type=["pptx", "docx"])


    if uploaded_file is not None:
        filename = uploaded_file.name
        file_bytes = uploaded_file.read()

        if st.button("Upload and Convert"):

            # Connect to server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))

            # Send filename length and filename
            sock.sendall(str(len(filename)).encode().ljust(4))
            sock.sendall(filename.encode())

            # Send file size first
            sock.sendall(str(len(file_bytes)).encode().ljust(16))

            # Upload file with progress bar
            st.info("Uploading file...")
            upload_bar = st.progress(0)
            upload_start = time.time()
            send_with_progress(sock, file_bytes, upload_bar)
            upload_end = time.time()

            # Wait for server response if conversion is ok
            response = sock.recv(2)
            if response != b"OK":
                st.error("Server failed to convert the file.")
                sock.close()
                return

            # Receive converted filename length and name
            converted_name_len = int(sock.recv(4).decode().strip())
            converted_name = sock.recv(converted_name_len).decode()

            # Receive converted file size
            converted_filesize = int(sock.recv(16).decode().strip())

            st.info(f"Downloading converted file: {converted_name}")
            download_bar = st.progress(0)
            download_start = time.time()
            converted_bytes = receive_with_progress(sock, converted_filesize, download_bar)
            download_end = time.time()

            # Receive upload and download times from server
            upload_time_server = float(sock.recv(16).decode().strip())
            download_time_server = float(sock.recv(16).decode().strip())

            sock.close()

            st.success(f"File converted successfully!")
            st.write(f"Upload time: {upload_time_server:.2f} seconds")
            st.write(f"Download time: {download_time_server:.2f} seconds")

            st.download_button(
                label="Download Converted PDF",
                data=converted_bytes,
                file_name=converted_name,
                mime='application/pdf'
            )

if __name__ == "__main__":
    main()
