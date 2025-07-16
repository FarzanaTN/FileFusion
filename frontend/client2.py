# import socket
# import streamlit as st
# import time
# import os

# HOST = '127.0.0.1'
# PORT = 65432
# BUFFER_SIZE = 4096
# PACKET_HEADER_SIZE = 8
# TIMEOUT = 5.0
# WINDOW_SIZE = 5

# def send_ack(sock, ack_num):
#     sock.sendall(ack_num.to_bytes(4, 'big'))
#     print(f"[CLIENT] Sent ACK {ack_num}")

# def receive_ack(sock):
#     ack_data = b''
#     while len(ack_data) < 4:
#         ack_data += sock.recv(4 - len(ack_data))
#     return int.from_bytes(ack_data, 'big')

# def send_with_ack(sock, file_bytes, progress_bar, status_text):
#     total_size = len(file_bytes)
#     total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE

#     sock.sendall(str(total_size).encode().ljust(16))
#     status_text.text(f"Sent file size: {total_size}")

#     base = 0
#     next_seq = 0
#     buffer = {}
#     sock.settimeout(TIMEOUT)

#     while base < total_packets:
#         while next_seq < base + WINDOW_SIZE and next_seq < total_packets:
#             start = next_seq * BUFFER_SIZE
#             end = min(start + BUFFER_SIZE, total_size)
#             data = file_bytes[start:end]
#             header = next_seq.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
#             packet = header + data
#             buffer[next_seq] = packet
#             sock.sendall(packet)
#             print(f"[CLIENT] Sent Packet {next_seq}")
#             next_seq += 1

#         try:
#             ack_num = receive_ack(sock)
#             print(f"[CLIENT] Got cumulative ACK {ack_num}")
#             if ack_num >= base:
#                 base = ack_num + 1
#                 progress_bar.progress(min(base / total_packets, 1.0))
#         except socket.timeout:
#             status_text.text(f"Timeout! Resending from {base}")
#             print(f"[CLIENT] Timeout. Resending from {base}")
#             for seq in range(base, next_seq):
#                 sock.sendall(buffer[seq])

#     sock.sendall((0xFFFFFFFF).to_bytes(4, 'big') + (0).to_bytes(4, 'big'))
#     status_text.text("Upload complete!")
#     progress_bar.progress(1.0)
#     return True

# def receive_with_ack(sock, progress_bar, status_text):
#     filesize = int(sock.recv(16).decode().strip())
#     buffer = {}
#     expected_seq = 0
#     received_bytes = 0

#     while received_bytes < filesize:
#         header = sock.recv(PACKET_HEADER_SIZE)
#         seq_num = int.from_bytes(header[:4], 'big')
#         data_len = int.from_bytes(header[4:], 'big')

#         if seq_num == 0xFFFFFFFF and data_len == 0:
#             break

#         data = b''
#         while len(data) < data_len:
#             data += sock.recv(data_len - len(data))

#         buffer[seq_num] = data

#         if seq_num == expected_seq:
#             while expected_seq in buffer:
#                 expected_seq += 1
#         send_ack(sock, expected_seq - 1)
#         received_bytes += len(data)
#         progress_bar.progress(min(received_bytes / filesize, 1.0))

#     data_bytes = b''.join(buffer[seq] for seq in sorted(buffer))
#     return data_bytes

# def main():
#     st.title("📄 Selective Repeat File Converter")

#     uploaded_file = st.file_uploader("Upload your file", type=[".doc", ".docx", ".odt", ".pptx", ".xls", ".xlsx"])
#     if uploaded_file:
#         output_format = st.selectbox("Select output format", ["pdf", "docx", "odt"])

#         if st.button("Upload and Convert"):
#             filename = uploaded_file.name
#             file_bytes = uploaded_file.read()

#             with st.spinner("Connecting to server..."):
#                 sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 sock.connect((HOST, PORT))

#                 sock.sendall(str(len(filename)).encode().ljust(4))
#                 sock.sendall(filename.encode())
#                 sock.sendall(output_format.encode().ljust(8))

#             st.subheader("📤 Upload Progress")
#             upload_bar = st.progress(0)
#             upload_status = st.empty()
#             success = send_with_ack(sock, file_bytes, upload_bar, upload_status)
#             if not success:
#                 st.error("Upload failed")
#                 return

#             st.subheader("⚙️ Waiting for Conversion")
#             sock.settimeout(600.0)
#             response = sock.recv(2)
#             if response != b"OK":
#                 st.error("Conversion failed on server")
#                 return

#             st.subheader("📥 Download Progress")
#             name_len = int(sock.recv(4).decode().strip())
#             converted_name = sock.recv(name_len).decode()

#             download_bar = st.progress(0)
#             download_status = st.empty()
#             converted_data = receive_with_ack(sock, download_bar, download_status)

#             st.success("🎉 Conversion Complete!")
#             st.download_button("💾 Download", data=converted_data, file_name=converted_name)
#             sock.close()

# if __name__ == "__main__":
#     main()



import socket
import streamlit as st
import time
import os
from collections import defaultdict

HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 4096
PACKET_HEADER_SIZE = 8
TIMEOUT = 50.0
WINDOW_SIZE = 5

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

    # Define which packets to "drop" on first try
    LOSS_PACKETS = {10, 50}
    dropped_once = set()

    # Prepare packets
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
        # Send packets within window
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

    # Send end marker
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

    data_bytes = b''.join(buffer[seq] for seq in sorted(buffer))
    return data_bytes

def main():
    st.title("📄 Multi-Format File Converter (Selective Repeat with Packet ACK)")

    # Display protocol information
    with st.expander("📊 Protocol Information"):
        st.write(f"**Packet Size:** {BUFFER_SIZE} bytes")
        st.write(f"**Window Size:** {WINDOW_SIZE}")
        st.write(f"**Timeout:** {TIMEOUT} seconds")
        st.write(f"**Server:** {HOST}:{PORT}")

    uploaded_file = st.file_uploader("Upload your file", type=[".doc", ".docx", ".odt", ".pptx", ".xls", ".xlsx"])

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
                with st.spinner("Connecting to server..."):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
                name_len_data = b''
                while len(name_len_data) < 4:
                    chunk = sock.recv(4 - len(name_len_data))
                    if not chunk:
                        st.error("Connection closed while receiving filename length")
                        return
                    name_len_data += chunk

                name_len = int(name_len_data.decode().strip())

                converted_name_data = b''
                while len(converted_name_data) < name_len:
                    chunk = sock.recv(name_len - len(converted_name_data))
                    if not chunk:
                        st.error("Connection closed while receiving filename")
                        return
                    converted_name_data += chunk

                converted_name = converted_name_data.decode()

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

                with col2:
                    st.metric("⚙️ Conversion Time (Server)", "N/A")
                    st.metric("📤 Upload Time (Server)", "N/A")
                    st.metric("📥 Download Time (Server)", "N/A")

                st.download_button(
                    label="💾 Download Converted File",
                    data=converted_data,
                    file_name=converted_name,
                    mime='application/octet-stream'
                )

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

if __name__ == "__main__":
    main()
