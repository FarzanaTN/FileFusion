import ssl
import socket
import threading
import os
import time
from collections import defaultdict
from converter import convert_with_libreoffice
import glob

HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 4096
PACKET_HEADER_SIZE = 8
TIMEOUT = 50.0
WINDOW_SIZE = 5
UPLOAD_DIR = 'uploads'
CONVERTED_DIR = 'converted'

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)


for file in glob.glob(os.path.join(LOG_DIR, "client_*.log")):
    os.remove(file)

# Reset server log with timestamp
LOG_FILE = os.path.join(LOG_DIR, "server.log")
with open(LOG_FILE, "w") as f:
    f.write(f"--- Server started at {time.ctime()} ---\n")


def log_message(message):
    print(message)
    with open(LOG_FILE, "a") as f:
        f.write(f"{message}\n")


def send_ack(conn, ack_num):
    conn.sendall(ack_num.to_bytes(4, 'big'))
    log_message(f"[SERVER] Sent ACK {ack_num}")

def receive_with_ack(conn, dest_path):
    filesize = int(conn.recv(16).decode().strip())
    log_message(f"[SERVER] Expecting {filesize} bytes")

    buffer = {}
    expected_seq = 0
    received_bytes = 0

    while received_bytes < filesize:
        header = conn.recv(PACKET_HEADER_SIZE)
        seq_num = int.from_bytes(header[:4], 'big')
        data_len = int.from_bytes(header[4:], 'big')

        if seq_num == 0xFFFFFFFF and data_len == 0:
            log_message("[SERVER] End of transmission")
            break

        data = b''
        while len(data) < data_len:
            data += conn.recv(data_len - len(data))

        buffer[seq_num] = data

        if seq_num == expected_seq:
            while expected_seq in buffer:
                expected_seq += 1
        send_ack(conn, expected_seq - 1)

    # reconstruct
    with open(dest_path, 'wb') as f:
        for seq in sorted(buffer):
            f.write(buffer[seq])
    log_message(f"[SERVER] File saved to {dest_path}")



def send_with_ack(conn, file_path):
    filesize = os.path.getsize(file_path)
    conn.sendall(str(filesize).encode().ljust(16))
    log_message(f"[SERVER] Sending file size: {filesize}")

    
    LOSS_PACKETS = {10, 20}
    dropped_once = set()

    
    packets = []
    with open(file_path, 'rb') as f:
        seq_num = 0
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            header = seq_num.to_bytes(4, 'big') + len(data).to_bytes(4, 'big')
            packets.append((seq_num, header + data))
            seq_num += 1
    total_packets = len(packets)

    base = 0
    next_seq = 0
    timers = {}
    dup_acks = defaultdict(int)
    conn.settimeout(TIMEOUT)

    while base < total_packets:
        while next_seq < base + WINDOW_SIZE and next_seq < total_packets:
            seq, pkt_data = packets[next_seq]

            if seq in LOSS_PACKETS and seq not in dropped_once:
                log_message(f"[SIMULATION] Intentionally dropping Packet {seq}")
                dropped_once.add(seq)
                timers[seq] = time.time()  # start timer even though dropped
                next_seq += 1
                continue

            conn.sendall(pkt_data)
            log_message(f"[SERVER] Sent Packet {seq}")
            timers[seq] = time.time()
            next_seq += 1

        try:
            ack_data = conn.recv(4)
            ack_num = int.from_bytes(ack_data, 'big')
            log_message(f"[SERVER] Received ACK {ack_num}")

            if ack_num >= base:
                base = ack_num + 1
                for i in list(timers):
                    if i <= ack_num:
                        timers.pop(i, None)
                dup_acks.clear()
            else:
                dup_acks[ack_num] += 1
                if dup_acks[ack_num] >= 3:
                    resend_seq = ack_num + 1
                    if resend_seq < total_packets:
                        log_message(f"[SERVER] Fast retransmit of Packet {resend_seq}")
                        conn.sendall(packets[resend_seq][1])
                        timers[resend_seq] = time.time()
                    dup_acks[ack_num] = 0

        except socket.timeout:
            now = time.time()
            for seq in range(base, next_seq):
                if now - timers.get(seq, 0) >= TIMEOUT:
                    log_message(f"[SERVER] Timeout retransmit of Packet {seq}")
                    conn.sendall(packets[seq][1])
                    timers[seq] = time.time()

    # End 
    conn.sendall((0xFFFFFFFF).to_bytes(4, 'big') + (0).to_bytes(4, 'big'))
    log_message("[SERVER] Finished sending")


def handle_client(conn, addr):
    try:
        log_message(f"[SERVER] Connected to {addr}")

        name_len = int(conn.recv(4).decode().strip())
        filename = conn.recv(name_len).decode()
        output_format = conn.recv(8).decode().strip().lower()

        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pptx", ".doc", ".docx", ".odt", ".xls", ".xlsx"]:
            conn.sendall(b"ER")
            return

        timestamp = int(time.time())
        input_path = os.path.join(UPLOAD_DIR, f"{timestamp}_{filename}")
        output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
        output_path = os.path.join(CONVERTED_DIR, f"{timestamp}_{output_filename}")

        receive_with_ack(conn, input_path)

        log_message("[SERVER] Converting...")
        success = convert_with_libreoffice(input_path, output_path, output_format)
        if not success:
            conn.sendall(b"ER")
            return

        conn.sendall(b"OK")
        conn.sendall(str(len(output_filename)).encode().ljust(4))
        conn.sendall(output_filename.encode())

        send_with_ack(conn, output_path)

    except Exception as e:
        log_message(f"[SERVER ERROR] {e}")
    finally:
        conn.close()
        log_message(f"[SERVER] Connection closed {addr}")

def start_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.bind((HOST, PORT))
    raw_sock.listen(5)
    log_message(f"[SERVER] Listening securely on {HOST}:{PORT}")
    while True:
        raw_conn, addr = raw_sock.accept()
        try:
            conn = context.wrap_socket(raw_conn, server_side=True)
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except ssl.SSLError as e:
            print(f"[SSL ERROR] {e}")
    return  
    

if __name__ == "__main__":
    start_server()