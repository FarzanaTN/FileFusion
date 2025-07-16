# ==================== SECURE client3.py ====================
import socket
import ssl
import streamlit as st
import time
import os
from collections import defaultdict
import qrcode
from io import BytesIO
from urllib.parse import quote

# Configuration
HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 4096
PACKET_HEADER_SIZE = 8
TIMEOUT = 50.0
WINDOW_SIZE = 5
STATIC_DIR = "static_downloads"

os.makedirs(STATIC_DIR, exist_ok=True)

def send_ack(sock, ack_num):
    sock.sendall(ack_num.to_bytes(4, 'big'))
    print(f"[CLIENT] Sent ACK {ack_num}")

def receive_ack(sock):
    ack_data = b''
    while len(ack_data) < 4:
        ack_data += sock.recv(4 - len(ack_data))
    return int.from_bytes(ack_data, 'big')

def send_with_ack(sock, file_bytes, progress_bar, status_text):
    total_size = len(file_bytes)
    total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE

    sock.sendall(str(total_size).encode().ljust(16))
    status_text.text(f"Sent file size: {total_size}")

    LOSS_PACKETS = {10, 50}
    dropped_once = set()

    packets = []
    for seq_num in range(total_packets):
        start = seq_num * BUFFER_SIZE
        end = min(start + BUFFER_SIZE, total_size)
        data = file_bytes[start:end]
        header = seq_num.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
        packets.append((seq_num, header + data))

    base = 0
    next_seq = 0
    timers = {}
    dup_acks = defaultdict(int)
    sock.settimeout(TIMEOUT)

    while base < total_packets:
        while next_seq < base + WINDOW_SIZE and next_seq < total_packets:
            seq, pkt_data = packets[next_seq]
            if seq in LOSS_PACKETS and seq not in dropped_once:
                print(f"[CLIENT] Intentionally dropping Packet {seq}")
                dropped_once.add(seq)
                timers[seq] = time.time()
                next_seq += 1
                continue
            sock.sendall(pkt_data)
            print(f"[CLIENT] Sent Packet {seq}")
            timers[seq] = time.time()
            next_seq += 1

        try:
            ack_num = receive_ack(sock)
            print(f"[CLIENT] Received ACK {ack_num}")
            if ack_num >= base:
                base = ack_num + 1
                for i in list(timers):
                    if i <= ack_num:
                        timers.pop(i, None)
                dup_acks.clear()
                progress_bar.progress(min(base / total_packets, 1.0))
            else:
                dup_acks[ack_num] += 1
                if dup_acks[ack_num] >= 3:
                    resend_seq = ack_num + 1
                    if resend_seq < total_packets:
                        print(f"[CLIENT] Fast retransmit of Packet {resend_seq}")
                        sock.sendall(packets[resend_seq][1])
                        timers[resend_seq] = time.time()
                    dup_acks[ack_num] = 0

        except socket.timeout:
            now = time.time()
            for seq in range(base, next_seq):
                if seq in timers and now - timers[seq] >= TIMEOUT:
                    print(f"[CLIENT] Timeout retransmit of Packet {seq}")
                    sock.sendall(packets[seq][1])
                    timers[seq] = time.time()
                    status_text.text(f"Timeout! Resending from Packet {seq}")

    sock.sendall((0xFFFFFFFF).to_bytes(4, 'big') + (0).to_bytes(4, 'big'))
    status_text.text("Upload complete!")
    progress_bar.progress(1.0)
    return True

def receive_with_ack(sock, progress_bar, status_text):
    filesize = int(sock.recv(16).decode().strip())
    buffer = {}
    expected_seq = 0
    received_bytes = 0

    while received_bytes < filesize:
        header = sock.recv(PACKET_HEADER_SIZE)
        seq_num = int.from_bytes(header[:4], 'big')
        data_len = int.from_bytes(header[4:], 'big')

        if seq_num == 0xFFFFFFFF and data_len == 0:
            break

        data = b''
        while len(data) < data_len:
            data += sock.recv(data_len - len(data))

        buffer[seq_num] = data

        if seq_num == expected_seq:
            while expected_seq in buffer:
                expected_seq += 1
        send_ack(sock, expected_seq - 1)
        received_bytes += len(data)
        progress_bar.progress(min(received_bytes / filesize, 1.0))

    return b''.join(buffer[seq] for seq in sorted(buffer))

def main():
    st.title("📄 Secure File Converter (TLS + Selective Repeat)")

    with st.expander("📊 Protocol Info"):
        st.write(f"**Server:** {HOST}:{PORT}")
        st.write(f"**Packet Size:** {BUFFER_SIZE} bytes")

    uploaded_file = st.file_uploader("Upload file", type=[".doc", ".docx", ".odt", ".pptx", ".xls", ".xlsx"])

    if uploaded_file:
        output_format = st.selectbox("Output format", ["pdf", "docx", "odt"])
        if output_format and st.button("Upload and Convert"):
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name

            try:
                # === Secure SSL connection (no verification for self-signed certs) ===
                raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                context = ssl._create_unverified_context()
                sock = context.wrap_socket(raw_sock, server_hostname=HOST)
                sock.connect((HOST, PORT))

                sock.sendall(str(len(filename)).encode().ljust(4))
                sock.sendall(filename.encode())
                sock.sendall(output_format.encode().ljust(8))

                upload_progress = st.progress(0)
                status = st.empty()
                send_with_ack(sock, file_bytes, upload_progress, status)

                st.success("✅ Upload complete")
                st.info("Waiting for server...")

                response = sock.recv(2)
                if response != b"OK":
                    st.error("Server error during conversion")
                    return

                name_len = int(sock.recv(4).decode().strip())
                new_name = sock.recv(name_len).decode()

                download_progress = st.progress(0)
                status = st.empty()
                data = receive_with_ack(sock, download_progress, status)

                st.download_button("Download", data, new_name)

            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                try:
                    sock.close()
                except:
                    pass

if __name__ == "__main__":
    main()
