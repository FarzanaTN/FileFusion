import socket
import ssl
import streamlit as st
import time
import os
from collections import defaultdict
import qrcode
from io import BytesIO
from urllib.parse import quote
import random

timestamp = int(time.time())
LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"client_{timestamp}.log")

HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 4096
PACKET_HEADER_SIZE = 8
TIMEOUT = 50.0
WINDOW_SIZE = 5
STATIC_DIR = "static_downloads"

os.makedirs(STATIC_DIR, exist_ok=True)




def log_message(message):
    print(message)
    with open(LOG_FILE, "a") as f:
        f.write(f"{message}\n")


def send_ack(sock, ack_num):
    sock.sendall(ack_num.to_bytes(4, 'big'))
    log_message(f"[CLIENT] Sent ACK {ack_num}")

def receive_ack(sock):
    ack_data = b''
    while len(ack_data) < 4:
        chunk = sock.recv(4 - len(ack_data))
        if not chunk:
            raise ConnectionResetError("Connection closed while waiting for ACK")
        ack_data += chunk
    return int.from_bytes(ack_data, 'big')

# def send_with_ack(sock, file_bytes, progress_bar, status_text):
#     total_size = len(file_bytes)
#     total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE

#     sock.sendall(str(total_size).encode().ljust(16))
#     status_text.text(f"Sent file size: {total_size}")

#     # LOSS_PACKETS = {10, 50}
#     # dropped_once = set()

#     packets = []
#     for seq_num in range(total_packets):
#         start = seq_num * BUFFER_SIZE
#         end = min(start + BUFFER_SIZE, total_size)
#         data = file_bytes[start:end]
#         header = seq_num.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
#         packets.append((seq_num, header + data))

#     base = 0
#     next_seq = 0
#     timers = {}
#     dup_acks = defaultdict(int)
#     sock.settimeout(TIMEOUT)

#       # TCP Reno congestion control variables
#     cwnd = 1
#     ssthresh = 16
#     reno_state = "Slow Start"

#     LOSS_PACKETS = {10, 50}
#     dropped_once = set()

#     log_message(f"[CLIENT][CC] cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#     # while base < total_packets:
#     #     while next_seq < base + WINDOW_SIZE and next_seq < total_packets:
#     #         seq, pkt_data = packets[next_seq]
#     #         if seq in LOSS_PACKETS and seq not in dropped_once:
#     #             log_message(f"[CLIENT] Intentionally dropping Packet {seq}")
#     #             dropped_once.add(seq)
#     #             timers[seq] = time.time()
#     #             next_seq += 1
#     #             continue
#     #         sock.sendall(pkt_data)
#     #         log_message(f"[CLIENT] Sent Packet {seq}")
#     #         timers[seq] = time.time()
#     #         next_seq += 1

#     #     try:
#     #         ack_num = receive_ack(sock)
#     #         log_message(f"[CLIENT] Received ACK {ack_num}")
#     #         if ack_num >= base:
#     #             base = ack_num + 1
#     #             for i in list(timers):
#     #                 if i <= ack_num:
#     #                     timers.pop(i, None)
#     #             dup_acks.clear()
#     #             progress_bar.progress(min(base / total_packets, 1.0))
#     #         else:
#     #             dup_acks[ack_num] += 1
#     #             if dup_acks[ack_num] >= 3:
#     #                 resend_seq = ack_num + 1
#     #                 if resend_seq < total_packets:
#     #                     log_message(f"[CLIENT] Fast retransmit of Packet {resend_seq}")
#     #                     sock.sendall(packets[resend_seq][1])
#     #                     timers[resend_seq] = time.time()
#     #                 dup_acks[ack_num] = 0

#     #     except socket.timeout:
#     #         now = time.time()
#     #         for seq in range(base, next_seq):
#     #             if seq in timers and now - timers[seq] >= TIMEOUT:
#     #                 log_message(f"[CLIENT] Timeout retransmit of Packet {seq}")
#     #                 sock.sendall(packets[seq][1])
#     #                 timers[seq] = time.time()
#     #                 status_text.text(f"Timeout! Resending from Packet {seq}")

#     while base < total_packets:
#         while next_seq < base + int(cwnd) and next_seq < total_packets:
#             seq, pkt_data = packets[next_seq]
#             if seq in LOSS_PACKETS and seq not in dropped_once:
#                 log_message(f"[CLIENT] Intentionally dropping Packet {seq}")
#                 dropped_once.add(seq)
#                 timers[seq] = time.time()
#                 next_seq += 1
#                 continue
#             sock.sendall(pkt_data)
#             log_message(f"[CLIENT] Sent Packet {seq}")
#             timers[seq] = time.time()
#             next_seq += 1

#         try:
#             ack_num = receive_ack(sock)
#             log_message(f"[CLIENT] Received ACK {ack_num}")

#             if ack_num >= base:
#                 base = ack_num + 1
#                 for i in list(timers):
#                     if i <= ack_num:
#                         timers.pop(i, None)
#                 dup_acks.clear()

#                 # Congestion control state update
#                 if reno_state == "Slow Start":
#                     cwnd += 1
#                     if cwnd >= ssthresh:
#                         reno_state = "Congestion Avoidance"
#                 elif reno_state == "Congestion Avoidance":
#                     cwnd += 1 / cwnd

#                 log_message(f"[CLIENT][CC] cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")
#                 progress_bar.progress(min(base / total_packets, 1.0))

#             else:
#                 dup_acks[ack_num] += 1
#                 if dup_acks[ack_num] >= 3:
#                     ssthresh = max(cwnd / 2, 2)
#                     cwnd = ssthresh + 3
#                     reno_state = "Fast Recovery"
#                     log_message(f"[CLIENT][CC] DUPACK threshold: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#                     resend_seq = ack_num + 1
#                     if resend_seq < total_packets:
#                         log_message(f"[CLIENT] Fast retransmit of Packet {resend_seq}")
#                         sock.sendall(packets[resend_seq][1])
#                         timers[resend_seq] = time.time()
#                     dup_acks[ack_num] = 0

#         except socket.timeout:
#             now = time.time()
#             for seq in range(base, next_seq):
#                 if seq in timers and now - timers[seq] >= TIMEOUT:
#                     ssthresh = max(cwnd / 2, 2)
#                     cwnd = 1
#                     reno_state = "Slow Start"
#                     log_message(f"[CLIENT][CC] TIMEOUT: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#                     log_message(f"[CLIENT] Timeout retransmit of Packet {seq}")
#                     sock.sendall(packets[seq][1])
#                     timers[seq] = time.time()
#                     status_text.text(f"Timeout! Resending from Packet {seq}")

#     sock.sendall((0xFFFFFFFF).to_bytes(4, 'big') + (0).to_bytes(4, 'big'))
#     time.sleep(0.1)  # let the server process the end marker
#     status_text.text("Upload complete!")
#     progress_bar.progress(1.0)
#     return True

# def send_with_ack(sock, file_bytes, progress_bar, status_text):
#     total_size = len(file_bytes)
#     total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE

#     sock.sendall(str(total_size).encode().ljust(16))
#     status_text.text(f"Sent file size: {total_size}")

#     packets = []
#     for seq_num in range(total_packets):
#         start = seq_num * BUFFER_SIZE
#         end = min(start + BUFFER_SIZE, total_size)
#         data = file_bytes[start:end]
#         header = seq_num.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
#         packets.append((seq_num, header + data))

#     base = 0
#     next_seq = 0
#     timers = {}
#     dup_acks = defaultdict(int)
#     sock.settimeout(TIMEOUT)

#     # TCP Reno variables
#     cwnd = 1
#     ssthresh = 16
#     reno_state = "Slow Start"
#     recover_point = None

#     LOSS_PACKETS = {10, 50}
#     dropped_once = set()

#     log_message(f"[CLIENT][CC] cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#     while base < total_packets:
#         while next_seq < base + int(cwnd) and next_seq < total_packets:
#             seq, pkt_data = packets[next_seq]
#             if seq in LOSS_PACKETS and seq not in dropped_once:
#                 log_message(f"[CLIENT] Intentionally dropping Packet {seq}")
#                 dropped_once.add(seq)
#                 timers[seq] = time.time()
#                 next_seq += 1
#                 continue
#             sock.sendall(pkt_data)
#             log_message(f"[CLIENT] Sent Packet {seq}")
#             timers[seq] = time.time()
#             next_seq += 1

#         try:
#             ack_num = receive_ack(sock)
#             log_message(f"[CLIENT] Received ACK {ack_num}")

#             if ack_num >= base:
#                 base = ack_num + 1
#                 for i in list(timers):
#                     if i <= ack_num:
#                         timers.pop(i, None)
#                 dup_acks.clear()

#                 # ✅ Fast Recovery exit condition
#                 if reno_state == "Fast Recovery" and ack_num >= recover_point:
#                     cwnd = ssthresh
#                     reno_state = "Congestion Avoidance"
#                     log_message(f"[CLIENT][CC] Exit FR: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#                 # Regular cwnd increase
#                 if reno_state == "Slow Start":
#                     cwnd += 1
#                     if cwnd >= ssthresh:
#                         reno_state = "Congestion Avoidance"
#                 elif reno_state == "Congestion Avoidance":
#                     cwnd += 1 / cwnd
#                 elif reno_state == "Fast Recovery":
#                     cwnd = cwnd  # Stay fixed in FR unless we exit

#                 log_message(f"[CLIENT][CC] cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")
#                 progress_bar.progress(min(base / total_packets, 1.0))

#             else:
#                 dup_acks[ack_num] += 1
#                 if dup_acks[ack_num] >= 3 and reno_state != "Fast Recovery":
#                     ssthresh = max(cwnd / 2, 2)
#                     cwnd = ssthresh + 3
#                     reno_state = "Fast Recovery"
#                     recover_point = next_seq - 1
#                     log_message(f"[CLIENT][CC] DUPACK threshold: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#                     resend_seq = ack_num + 1
#                     if resend_seq < total_packets:
#                         log_message(f"[CLIENT] Fast retransmit of Packet {resend_seq}")
#                         sock.sendall(packets[resend_seq][1])
#                         timers[resend_seq] = time.time()
#                     dup_acks[ack_num] = 0

#         except socket.timeout:
#             now = time.time()
#             for seq in range(base, next_seq):
#                 if seq in timers and now - timers[seq] >= TIMEOUT:
#                     ssthresh = max(cwnd / 2, 2)
#                     cwnd = 1
#                     reno_state = "Slow Start"
#                     log_message(f"[CLIENT][CC] TIMEOUT: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

#                     log_message(f"[CLIENT] Timeout retransmit of Packet {seq}")
#                     sock.sendall(packets[seq][1])
#                     timers[seq] = time.time()
#                     status_text.text(f"Timeout! Resending from Packet {seq}")

#     sock.sendall((0xFFFFFFFF).to_bytes(4, 'big') + (0).to_bytes(4, 'big'))
#     time.sleep(0.1)
#     status_text.text("Upload complete!")
#     progress_bar.progress(1.0)

#     # # ✅ Send the client log to server
#     # with open(LOG_FILE, "r") as f:
#     #     log_data = f.read()

#     # log_bytes = log_data.encode()
#     # sock.sendall(str(len(log_bytes)).encode().ljust(16))
#     # sock.sendall(log_bytes)
    
#     return True

def send_with_ack(sock, file_bytes, progress_bar, status_text):
    total_size = len(file_bytes)
    total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE

    sock.sendall(str(total_size).encode().ljust(16))
    status_text.text(f"Sent file size: {total_size}")

    packets = []
    for seq_num in range(total_packets):
        start = seq_num * BUFFER_SIZE
        end = min(start + BUFFER_SIZE, total_size)
        data = file_bytes[start:end]
        header = seq_num.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
        packets.append((seq_num, header + data))

    # ✅ Randomly choose 6 unique packets to drop once (no repeats)
    LOSS_PACKETS = set(random.sample(range(total_packets), min(6, total_packets)))
    dropped_once = set()
    log_message(f"[CLIENT] Random LOSS_PACKETS selected: {sorted(LOSS_PACKETS)}")

    base = 0
    next_seq = 0
    timers = {}
    dup_acks = defaultdict(int)
    sock.settimeout(TIMEOUT)

    # TCP Reno variables
    cwnd = 1
    ssthresh = 16
    reno_state = "Slow Start"
    recover_point = None

    log_message(f"[CLIENT][CC] cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

    while base < total_packets:
        while next_seq < base + int(cwnd) and next_seq < total_packets:
            seq, pkt_data = packets[next_seq]
            if seq in LOSS_PACKETS and seq not in dropped_once:
                log_message(f"[CLIENT] Intentionally dropping Packet {seq}")
                dropped_once.add(seq)
                timers[seq] = time.time()
                next_seq += 1
                continue
            sock.sendall(pkt_data)
            log_message(f"[CLIENT] Sent Packet {seq}")
            timers[seq] = time.time()
            next_seq += 1

        try:
            ack_num = receive_ack(sock)
            log_message(f"[CLIENT] Received ACK {ack_num}")

            if ack_num >= base:
                base = ack_num + 1
                for i in list(timers):
                    if i <= ack_num:
                        timers.pop(i, None)
                dup_acks.clear()

                # ✅ Fast Recovery exit condition
                if reno_state == "Fast Recovery" and ack_num >= recover_point:
                    cwnd = ssthresh
                    reno_state = "Congestion Avoidance"
                    log_message(f"[CLIENT][CC] Exit FR: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

                # Regular cwnd increase
                if reno_state == "Slow Start":
                    cwnd += 1
                    if cwnd >= ssthresh:
                        reno_state = "Congestion Avoidance"
                elif reno_state == "Congestion Avoidance":
                    cwnd += 1 / cwnd
                elif reno_state == "Fast Recovery":
                    cwnd = cwnd  # Stay fixed in FR unless we exit

                log_message(f"[CLIENT][CC] cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")
                progress_bar.progress(min(base / total_packets, 1.0))

            else:
                dup_acks[ack_num] += 1
                if dup_acks[ack_num] >= 3 and reno_state != "Fast Recovery":
                    ssthresh = max(cwnd / 2, 2)
                    cwnd = ssthresh + 3
                    reno_state = "Fast Recovery"
                    recover_point = next_seq - 1
                    log_message(f"[CLIENT][CC] DUPACK threshold: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

                    resend_seq = ack_num + 1
                    if resend_seq < total_packets:
                        log_message(f"[CLIENT] Fast retransmit of Packet {resend_seq}")
                        sock.sendall(packets[resend_seq][1])
                        timers[resend_seq] = time.time()
                    dup_acks[ack_num] = 0

        except socket.timeout:
            now = time.time()
            for seq in range(base, next_seq):
                if seq in timers and now - timers[seq] >= TIMEOUT:
                    ssthresh = max(cwnd / 2, 2)
                    cwnd = ssthresh
                    reno_state = "Slow Start"
                    log_message(f"[CLIENT][CC] TIMEOUT: cwnd={cwnd:.2f} ssthresh={ssthresh:.2f} state={reno_state}")

                    log_message(f"[CLIENT] Timeout retransmit of Packet {seq}")
                    sock.sendall(packets[seq][1])
                    timers[seq] = time.time()
                    status_text.text(f"Timeout! Resending from Packet {seq}")

    sock.sendall((0xFFFFFFFF).to_bytes(4, 'big') + (0).to_bytes(4, 'big'))
    time.sleep(0.1)
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
        if not header:
            raise ConnectionResetError("Connection closed while receiving header")
        seq_num = int.from_bytes(header[:4], 'big')
        data_len = int.from_bytes(header[4:], 'big')

        if seq_num == 0xFFFFFFFF and data_len == 0:
            break

        data = b''
        while len(data) < data_len:
            chunk = sock.recv(data_len - len(data))
            if not chunk:
                raise ConnectionResetError("Connection closed during data reception")
            data += chunk

        buffer[seq_num] = data

        if seq_num == expected_seq:
            while expected_seq in buffer:
                expected_seq += 1
        send_ack(sock, expected_seq - 1)
        received_bytes += len(data)
        progress_bar.progress(min(received_bytes / filesize, 1.0))

    return b''.join(buffer[seq] for seq in sorted(buffer))

def generate_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# def main():
#     st.title("📄 FileFusion (Secure File Converter)")

#     with st.expander("📊 Protocol Information"):
#         st.write(f"**Packet Size:** {BUFFER_SIZE} bytes")
#         st.write(f"**Window Size:** {WINDOW_SIZE}")
#         st.write(f"**Timeout:** {TIMEOUT} seconds")
#         st.write(f"**Server:** {HOST}:{PORT}")

#     uploaded_file = st.file_uploader("Upload your file", type=[".doc", ".docx", ".odt", ".pptx"])

#     output_format = None
#     if uploaded_file:
#         file_ext = os.path.splitext(uploaded_file.name)[1].lower()
#         allowed_outputs = ["pdf", "docx", "odt"]
#         output_format = st.selectbox("Select output format", allowed_outputs)

#     if uploaded_file and output_format:
#         filename = uploaded_file.name
#         file_bytes = uploaded_file.read()

#         st.info(f"📄  **File:** {filename}")
#         st.info(f"📏  **Size:** {len(file_bytes):,} bytes")
#         st.info(f"🔄 **Converting to:** {output_format.upper()}")

#         expected_packets = (len(file_bytes) + BUFFER_SIZE - 1) // BUFFER_SIZE
#         st.info(f"📦 **Expected packets:** {expected_packets}")

#         if st.button("Upload and Convert"):
#             sock = None
#             try:
#                 with st.spinner("Connecting to secure server..."):
#                     raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                     context = ssl._create_unverified_context()
#                     sock = context.wrap_socket(raw_sock, server_hostname=HOST)
#                     sock.settimeout(30.0)
#                     sock.connect((HOST, PORT))
#                     sock.settimeout(None)

#                     sock.sendall(str(len(filename)).encode().ljust(4))
#                     sock.sendall(filename.encode())
#                     sock.sendall(output_format.encode().ljust(8))

#                 st.subheader("📤 Upload Progress")
#                 upload_progress = st.progress(0)
#                 upload_status = st.empty()

#                 upload_start = time.time()
#                 success = send_with_ack(sock, file_bytes, upload_progress, upload_status)
#                 upload_end = time.time()

#                 if not success:
#                     st.error("❌ Upload failed")
#                     return

#                 st.subheader("⚙️ Conversion Progress")
#                 conversion_status = st.empty()
#                 conversion_status.text("Waiting for server response...")

#                 sock.settimeout(600.0)
#                 response = sock.recv(2)
#                 sock.settimeout(None)

#                 if response != b"OK":
#                     st.error("❌ Conversion failed on server")
#                     return

#                 conversion_status.text("Conversion completed successfully!")

#                 st.subheader("📥 Download Progress")
#                 name_len = int(sock.recv(4).decode().strip())
#                 converted_name = sock.recv(name_len).decode()

#                 download_progress = st.progress(0)
#                 download_status = st.empty()
#                 download_start = time.time()
#                 converted_data = receive_with_ack(sock, download_progress, download_status)
#                 download_end = time.time()

#                 if not converted_data:
#                     st.error("❌ Failed to receive converted file")
#                     return

#                 st.success("🎉 Conversion completed successfully!")

#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.metric("📤 Upload Time (Client)", f"{upload_end - upload_start:.2f}s")
#                     st.metric("📥 Download Time (Client)", f"{download_end - download_start:.2f}s")
#                     st.metric("📦 Total Packets", expected_packets)

#                 # with col2:
#                 #     st.metric("⚙️ Conversion Time (Server)", "N/A")
#                 #     st.metric("📤 Upload Time (Server)", "N/A")
#                 #     st.metric("📥 Download Time (Server)", "N/A")

#                 st.download_button(
#                     label="💾 Download Converted File",
#                     data=converted_data,
#                     file_name=converted_name,
#                     mime='application/octet-stream'
#                 )

#                 with st.expander("📲 Share via QR code on local network"):
#                     # st.markdown(
#                     #     "✅ To share over LAN, run this in terminal (in static_downloads folder):\n"
#                     #     "```\n"
#                     #     "cd static_downloads\n"
#                     #     "python -m http.server 8000\n"
#                     #     "```\n"
#                     #     "Then enter your computer's LAN IP below (same network)."
#                     # )

#                     os.makedirs("static_downloads", exist_ok=True)
#                     shared_path = os.path.join("static_downloads", converted_name)
#                     with open(shared_path, "wb") as f:
#                         f.write(converted_data)

#                    # lan_ip = st.text_input("Enter your computer's LAN IP:", "192.168.1.102")
#                     if "lan_ip" not in st.session_state:
#                          st.session_state.lan_ip = "192.168.1.101"

#                     lan_ip = st.text_input(
#                      "Enter your computer's LAN IP:",
#                      value=st.session_state.lan_ip,
#                         key="lan_ip"
#                     )
                   
#                     encoded_name = quote(converted_name)
#                     share_url = f"http://{lan_ip}:8000/{encoded_name}"
#                     st.markdown(f"🔗 **Direct Link:** [{share_url}]({share_url})")
#                     qr_buf = generate_qr_code(share_url)
#                     st.image(qr_buf, caption="Scan this QR on your phone to download", use_container_width=False)

#             except Exception as e:
#                 st.error(f"❌ Connection failed: {e}")
#                 import traceback
#                 st.text(traceback.format_exc())
#             finally:
#                 if sock:
#                     try:
#                         sock.close()
#                     except:
#                         pass


def main():
    st.title("📄 FileFusion (Secure File Converter)")

    with st.expander("📊 Protocol Information"):
        st.write(f"**Packet Size:** {BUFFER_SIZE} bytes")
        st.write(f"**Window Size:** {WINDOW_SIZE}")
        st.write(f"**Timeout:** {TIMEOUT} seconds")
        st.write(f"**Server:** {HOST}:{PORT}")

    uploaded_file = st.file_uploader("Upload your file", type=[".doc", ".docx", ".odt", ".pptx"])

    output_format = None
    if uploaded_file:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_outputs = ["pdf", "docx", "odt"]
        output_format = st.selectbox("Select output format", allowed_outputs)

    if uploaded_file and output_format:
        filename = uploaded_file.name
        file_bytes = uploaded_file.read()

        st.info(f"📄  **File:** {filename}")
        st.info(f"📏  **Size:** {len(file_bytes):,} bytes")
        st.info(f"🔄 **Converting to:** {output_format.upper()}")

        expected_packets = (len(file_bytes) + BUFFER_SIZE - 1) // BUFFER_SIZE
        st.info(f"📦 **Expected packets:** {expected_packets}")

        if st.button("Upload and Convert"):
            sock = None
            try:
                with st.spinner("Connecting to secure server..."):
                    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    context = ssl._create_unverified_context()
                    sock = context.wrap_socket(raw_sock, server_hostname=HOST)
                    sock.settimeout(30.0)
                    sock.connect((HOST, PORT))
                    sock.settimeout(None)

                    sock.sendall(str(len(filename)).encode().ljust(4))
                    sock.sendall(filename.encode())
                    sock.sendall(output_format.encode().ljust(8))

                st.subheader("📤 Upload Progress")
                upload_progress = st.progress(0)
                upload_status = st.empty()

                upload_start = time.time()
                success = send_with_ack(sock, file_bytes, upload_progress, upload_status)
                upload_end = time.time()

                if not success:
                    st.error("❌ Upload failed")
                    return

                st.subheader("⚙️ Conversion Progress")
                conversion_status = st.empty()
                conversion_status.text("Waiting for server response...")

                sock.settimeout(600.0)
                response = sock.recv(2)
                sock.settimeout(None)

                if response != b"OK":
                    st.error("❌ Conversion failed on server")
                    return

                conversion_status.text("Conversion completed successfully!")

                st.subheader("📥 Download Progress")
                name_len = int(sock.recv(4).decode().strip())
                converted_name = sock.recv(name_len).decode()

                download_progress = st.progress(0)
                download_status = st.empty()
                download_start = time.time()
                converted_data = receive_with_ack(sock, download_progress, download_status)
                download_end = time.time()

                if not converted_data:
                    st.error("❌ Failed to receive converted file")
                    return

                st.success("🎉 Conversion completed successfully!")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📤 Upload Time (Client)", f"{upload_end - upload_start:.2f}s")
                    st.metric("📥 Download Time (Client)", f"{download_end - download_start:.2f}s")
                    st.metric("📦 Total Packets", expected_packets)

                st.download_button(
                    label="💾 Download Converted File",
                    data=converted_data,
                    file_name=converted_name,
                    mime='application/octet-stream'
                )

                # ✅ Save conversion result to session_state for later sharing
                st.session_state['converted_name'] = converted_name
                st.session_state['converted_data'] = converted_data

                # ✅ Also save a local copy in static_downloads
                os.makedirs("static_downloads", exist_ok=True)
                shared_path = os.path.join("static_downloads", converted_name)
                with open(shared_path, "wb") as f:
                    f.write(converted_data)

            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
                import traceback
                st.text(traceback.format_exc())
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass

    # ✅ Always show share section if we have a converted file
    if 'converted_name' in st.session_state and 'converted_data' in st.session_state:
        st.subheader("📲 Share via QR code on local network")
        with st.expander("Share your file"):
            if "lan_ip" not in st.session_state:
                st.session_state['lan_ip'] = "192.168.1.100"

            lan_ip = st.text_input(
                "Enter your computer's LAN IP:",
                value=st.session_state['lan_ip'],
                key="lan_ip"
            )

            converted_name = st.session_state['converted_name']
            encoded_name = quote(converted_name)
            share_url = f"http://{lan_ip}:8000/{encoded_name}"

            st.markdown(f"🔗 **Direct Link:** [{share_url}]({share_url})")
            qr_buf = generate_qr_code(share_url)
            st.image(qr_buf, caption="Scan this QR on your phone to download", use_container_width=False)


if __name__ == "__main__":
    main()
