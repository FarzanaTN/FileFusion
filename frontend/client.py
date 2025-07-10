import socket
import streamlit as st
import time
import os
import struct

HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 4096
WINDOW_SIZE = 10
TIMEOUT = 10.0  # Increased timeout to handle network delays

ALLOWED_CONVERSIONS = {
    ".doc": ["pdf", "docx", "odt"],
    ".docx": ["pdf", "doc", "odt"],
    ".odt": ["pdf", "docx"],
    ".pptx": ["pdf"],
    ".xlsx": ["pdf"],
    ".xls": ["pdf"],
}

# def send_with_progress(sock, file_bytes, progress_bar):
#     total = len(file_bytes)
#     packet_count = min(100, (total + BUFFER_SIZE - 1) // BUFFER_SIZE)
#     adjusted_buffer = (total + packet_count - 1) // packet_count if total > BUFFER_SIZE * 100 else BUFFER_SIZE
#     sock.sendall(str(total).encode().ljust(16))

#     packets = [file_bytes[i:i + adjusted_buffer] for i in range(0, total, adjusted_buffer)]
#     base = 0
#     next_seq = 0
#     sent_bytes = 0

#     while base < len(packets):
#         while next_seq < min(base + WINDOW_SIZE, len(packets)):
#             sock.sendall(struct.pack('!I', next_seq))
#             sock.sendall(packets[next_seq])
#             print(f"[SEND] Sent packet {next_seq}")
#             sent_bytes = min((next_seq + 1) * adjusted_buffer, total)
#             progress_bar.progress(sent_bytes / total)
#             next_seq += 1

#         sock.settimeout(TIMEOUT)
#         try:
#             ack_data = sock.recv(4)
#             if len(ack_data) != 4:
#                 print(f"[SEND] Incomplete ACK received, len={len(ack_data)}")
#                 next_seq = base
#                 continue
#             ack = struct.unpack('!I', ack_data)[0]
#             print(f"[SEND] Received ACK {ack}")
#             if ack >= base:
#                 base = ack + 1
#                 progress_bar.progress(min((base * adjusted_buffer) / total, 1.0))
#         except socket.timeout:
#             print(f"[SEND] Timeout, resending from {base}")
#             next_seq = base
#             continue
#         except Exception as e:
#             print(f"[SEND] Error receiving ACK: {e}")
#             next_seq = base
#             continue
#     progress_bar.progress(1.0)

def send_with_progress(sock, file_bytes, progress_bar):
    total = len(file_bytes)
    packet_count = min(100, (total + BUFFER_SIZE - 1) // BUFFER_SIZE)
    adjusted_buffer = (total + packet_count - 1) // packet_count if total > BUFFER_SIZE * 100 else BUFFER_SIZE
    sock.sendall(str(total).encode().ljust(16))

    packets = [file_bytes[i:i + adjusted_buffer] for i in range(0, total, adjusted_buffer)]
    base = 0
    next_seq = 0
    sent_bytes = 0
    last_ack_time = time.time()

    while base < len(packets):
        # Send packets in the window
        while next_seq < min(base + WINDOW_SIZE, len(packets)):
            sock.sendall(struct.pack('!I', next_seq))
            sock.sendall(packets[next_seq])
            print(f"[SEND] Sent packet {next_seq}")
            next_seq += 1

        # Wait for ACK
        try:
            sock.settimeout(TIMEOUT)
            ack_data = sock.recv(4)
            if len(ack_data) != 4:
                print(f"[SEND] Incomplete ACK received, len={len(ack_data)}")
                next_seq = base
                continue

            ack = struct.unpack('!I', ack_data)[0]
            print(f"[SEND] Received ACK {ack}")

            if ack >= base:
                base = ack + 1
                progress_bar.progress(min((base * adjusted_buffer) / total, 1.0))
                last_ack_time = time.time()

        except socket.timeout:
            # Timeout → resend entire window
            print(f"[SEND] Timeout waiting for ACK. Resending from {base}")
            next_seq = base
            continue

        # Extra protection: detect stalled ACKs (simulate triple-duplicate ACKs if needed)
        if time.time() - last_ack_time > TIMEOUT:
            print(f"[SEND] ACK stalled. Resending from {base}")
            next_seq = base
            last_ack_time = time.time()



def receive_with_progress(sock, filesize, progress_bar):
    packet_count = min(100, (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE)
    adjusted_buffer = (filesize + packet_count - 1) // packet_count if filesize > BUFFER_SIZE * 100 else BUFFER_SIZE

    expected_seq = 0
    received = 0
    chunks = []
    while received < filesize:
        sock.settimeout(TIMEOUT)
        try:
            seq_data = sock.recv(4)
            if len(seq_data) != 4:
                print(f"[RECV] Incomplete sequence number, len={len(seq_data)}")
                sock.sendall(struct.pack('!I', expected_seq - 1))
                continue
            seq = struct.unpack('!I', seq_data)[0]
            data = sock.recv(adjusted_buffer)
            if len(data) == 0:
                print(f"[RECV] No data received for packet {seq}")
                sock.sendall(struct.pack('!I', expected_seq - 1))
                continue
            if seq == expected_seq:
                chunks.append(data)
                received += len(data)
                sock.sendall(struct.pack('!I', expected_seq))
                print(f"[RECV] Received packet {seq}, sent ACK {expected_seq}, bytes={len(data)}")
                expected_seq += 1
                progress_bar.progress(min(received / filesize, 1.0))
            else:
                sock.sendall(struct.pack('!I', expected_seq - 1))
                print(f"[RECV] Out-of-order packet {seq}, sent ACK {expected_seq - 1}")
        except socket.timeout:
            sock.sendall(struct.pack('!I', expected_seq - 1))
            print(f"[RECV] Timeout, sent ACK {expected_seq - 1}")
            continue
        except Exception as e:
            print(f"[RECV] Error: {e}")
            sock.sendall(struct.pack('!I', expected_seq - 1))
            continue
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
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((HOST, PORT))

                # Send filename length, filename, and output format
                sock.sendall(str(len(filename)).encode().ljust(4))
                sock.sendall(filename.encode())
                sock.sendall(output_format.encode().ljust(8))

                # Upload file with progress
                st.info("Uploading file...")
                upload_bar = st.progress(0)
                send_with_progress(sock, file_bytes, upload_bar)

                # Receive server response
                sock.settimeout(TIMEOUT)
                response = sock.recv(2)
                if response == b"CV":
                    st.error("Conversion failed on server. File may be corrupted or unsupported.")
                    return
                elif response == b"ER":
                    st.error("Transfer failed. Server may have encountered an error.")
                    return
                elif response != b"OK":
                    st.error("Conversion failed. Server may not support this format.")
                    return

                # Receive converted filename and size
                name_len_data = sock.recv(4)
                if len(name_len_data) != 4:
                    st.error("Failed to receive converted filename length.")
                    return
                name_len = int(name_len_data.decode().strip())
                converted_name = sock.recv(name_len).decode()

                size_data = sock.recv(16)
                if len(size_data) != 16:
                    st.error("Failed to receive converted file size.")
                    return
                converted_size = int(size_data.decode().strip())

                # Receive converted file with progress
                st.info("Downloading converted file...")
                download_bar = st.progress(0)
                converted_bytes = receive_with_progress(sock, converted_size, download_bar)

                # Verify received file size
                if len(converted_bytes) != converted_size:
                    st.error(f"File size mismatch: expected {converted_size}, received {len(converted_bytes)}")
                    return

                # Display download button
                st.success("File converted successfully!")
                mime_type = "application/pdf" if output_format == "pdf" else "application/octet-stream"
                st.download_button(
                    label="Download Converted File",
                    data=converted_bytes,
                    file_name=converted_name,
                    mime=mime_type
                )

                # Receive and display timing information
                upload_time_data = sock.recv(16)
                download_time_data = sock.recv(16)
                if len(upload_time_data) == 16 and len(download_time_data) == 16:
                    upload_time = float(upload_time_data.decode().strip())
                    download_time = float(download_time_data.decode().strip())
                    st.write(f"Upload time: {upload_time:.4f} seconds")
                    st.write(f"Download time: {download_time:.4f} seconds")
                else:
                    st.warning("Failed to receive timing information from server.")

            except socket.timeout:
                st.error("Connection timed out. Please try again.")
            except Exception as e:
                st.error(f"Connection failed: {e}")
            finally:
                if sock:
                    try:
                        # sock.close()
                        print("kireee")
                    except:
                        pass
                    print("[CLIENT] Socket closed.")

if __name__ == "__main__":
    main()