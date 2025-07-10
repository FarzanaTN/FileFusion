import socket
import threading
import os
import time
import traceback
import struct
from converter import convert_with_libreoffice

HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 4096
WINDOW_SIZE = 10
TIMEOUT = 1.0
UPLOAD_DIR = 'uploads'
CONVERTED_DIR = 'converted'
TIMEOUT = 10.0  # Align with client timeout


os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

def send_with_progress(conn, file_path):
    filesize = os.path.getsize(file_path)
    packet_count = min(100, (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE)
    adjusted_buffer = (filesize + packet_count - 1) // packet_count if filesize > BUFFER_SIZE * 100 else BUFFER_SIZE

    conn.sendall(str(filesize).encode().ljust(16))
    print(f"[SEND] Expecting {packet_count} ACKs for {file_path}")

    base = 0
    next_seq = 0
    packets = []
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(adjusted_buffer)
            if not data:
                break
            packets.append(data)

    while base < len(packets):
        while next_seq < min(base + WINDOW_SIZE, len(packets)):
            conn.sendall(struct.pack('!I', next_seq))  # Send seq as 4-byte unsigned int
            conn.sendall(packets[next_seq])
            print(f"[SEND] Sent packet {next_seq}")
            next_seq += 1

        conn.settimeout(TIMEOUT)
        try:
            ack_data = conn.recv(4)
            if len(ack_data) != 4:
                print(f"[SEND] Incomplete ACK received, len={len(ack_data)}")
                next_seq = base
                continue
            ack = struct.unpack('!I', ack_data)[0]
            print(f"[SEND] Received ACK {ack}")
            if ack >= base:
                base = ack + 1
        except socket.timeout:
            print(f"[SEND] Timeout, resending from {base}")
            next_seq = base
            continue
        except Exception as e:
            print(f"[SEND] Error receiving ACK: {e}")
            next_seq = base
            continue

# def receive_with_progress(conn, dest_path):
#     filesize_data = conn.recv(16)
#     if len(filesize_data) != 16:
#         raise ValueError(f"Invalid filesize data, received {len(filesize_data)} bytes")
#     filesize = int(filesize_data.decode().strip())
#     packet_count = min(100, (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE)
#     adjusted_buffer = (filesize + packet_count - 1) // packet_count if filesize > BUFFER_SIZE * 100 else BUFFER_SIZE
#     print(f"[RECV] Expecting {packet_count} ACKs for {dest_path}, filesize={filesize}")

#     expected_seq = 0
#     received = 0
#     with open(dest_path, 'wb') as f:
#         while received < filesize:
#             conn.settimeout(TIMEOUT)
#             try:
#                 seq_data = conn.recv(4)
#                 if len(seq_data) != 4:
#                     print(f"[RECV] Incomplete sequence number, len={len(seq_data)}")
#                     conn.sendall(struct.pack('!I', expected_seq - 1))
#                     continue
#                 seq = struct.unpack('!I', seq_data)[0]
#                 data = conn.recv(adjusted_buffer)
#                 if len(data) == 0:
#                     print(f"[RECV] No data received for packet {seq}")
#                     conn.sendall(struct.pack('!I', expected_seq - 1))
#                     continue
#                 if seq == expected_seq:
#                     f.write(data)
#                     received += len(data)
#                     conn.sendall(struct.pack('!I', expected_seq))
#                     print(f"[RECV] Received packet {seq}, sent ACK {expected_seq}, bytes={len(data)}")
#                     expected_seq += 1
#                 else:
#                     conn.sendall(struct.pack('!I', expected_seq - 1))
#                     print(f"[RECV] Out-of-order packet {seq}, sent ACK {expected_seq - 1}")
#             except socket.timeout:
#                 conn.sendall(struct.pack('!I', expected_seq - 1))
#                 print(f"[RECV] Timeout, sent ACK {expected_seq - 1}")
#                 continue
#             except Exception as e:
#                 print(f"[RECV] Error: {e}")
#                 conn.sendall(struct.pack('!I', expected_seq - 1))
#                 continue
#     return filesize

# def receive_with_progress(conn, dest_path):
#     filesize_data = conn.recv(16)
#     if len(filesize_data) != 16:
#         raise ValueError(f"Invalid filesize data, received {len(filesize_data)} bytes")
#     filesize = int(filesize_data.decode().strip())
#     packet_count = min(100, (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE)
#     adjusted_buffer = (filesize + packet_count - 1) // packet_count if filesize > BUFFER_SIZE * 100 else BUFFER_SIZE
#     print(f"[RECV] Expecting {packet_count} ACKs for {dest_path}, filesize={filesize}")

#     expected_seq = 0
#     received = 0
#     buffer = {}

#     with open(dest_path, 'wb') as f:
#         while received < filesize:
#             conn.settimeout(TIMEOUT)
#             try:
#                 seq_data = conn.recv(4)
#                 if len(seq_data) != 4:
#                     print(f"[RECV] Incomplete sequence number, len={len(seq_data)}")
#                     conn.sendall(struct.pack('!I', expected_seq - 1))
#                     continue
#                 seq = struct.unpack('!I', seq_data)[0]
#                 data = conn.recv(adjusted_buffer)
#                 if len(data) == 0:
#                     print(f"[RECV] No data received for packet {seq}")
#                     conn.sendall(struct.pack('!I', expected_seq - 1))
#                     continue

#                 if seq == expected_seq:
#                     buffer[seq] = data
#                     # Simulate lost ACKs for seq 10 and 50
#                     if seq in [10, 50]:
#                         print(f"[RECV] Simulated ACK loss for {seq}")
#                         # Do not send ACK
#                     else:
#                         conn.sendall(struct.pack('!I', expected_seq))
#                         print(f"[RECV] Received packet {seq}, sent ACK {expected_seq}, bytes={len(data)}")
#                         # Write in-order confirmed packets
#                         while expected_seq in buffer:
#                             f.write(buffer[expected_seq])
#                             received += len(buffer[expected_seq])
#                             del buffer[expected_seq]
#                             expected_seq += 1
#                 else:
#                     # Out-of-order or duplicate
#                     conn.sendall(struct.pack('!I', expected_seq - 1))
#                     print(f"[RECV] Out-of-order packet {seq}, sent ACK {expected_seq - 1}")
#             except socket.timeout:
#                 conn.sendall(struct.pack('!I', expected_seq - 1))
#                 print(f"[RECV] Timeout, sent ACK {expected_seq - 1}")
#                 continue
#             except Exception as e:
#                 print(f"[RECV] Error: {e}")
#                 conn.sendall(struct.pack('!I', expected_seq - 1))
#                 continue
#     return filesize

def receive_with_progress(conn, dest_path):
    filesize_data = conn.recv(16)
    if len(filesize_data) != 16:
        raise ValueError(f"Invalid filesize data, received {len(filesize_data)} bytes")
    filesize = int(filesize_data.decode().strip())
    packet_count = min(100, (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE)
    adjusted_buffer = (filesize + packet_count - 1) // packet_count if filesize > BUFFER_SIZE * 100 else BUFFER_SIZE
    print(f"[RECV] Expecting {packet_count} ACKs for {dest_path}, filesize={filesize}")

    expected_seq = 0
    received = 0
    buffer = {}
    ack10_lost_once = False
    ack50_lost_once = False

    with open(dest_path, 'wb') as f:
        while received < filesize:
            conn.settimeout(TIMEOUT)
            try:
                seq_data = conn.recv(4)
                if len(seq_data) != 4:
                    print(f"[RECV] Incomplete sequence number, len={len(seq_data)}")
                    conn.sendall(struct.pack('!I', expected_seq - 1))
                    continue

                seq = struct.unpack('!I', seq_data)[0]
                data = conn.recv(adjusted_buffer)
                if len(data) == 0:
                    print(f"[RECV] No data received for packet {seq}")
                    conn.sendall(struct.pack('!I', expected_seq - 1))
                    continue

                if seq == expected_seq:
                    buffer[seq] = data

                    # Simulate ACK loss for 10 and 50 only once
                    if seq == 10 and not ack10_lost_once:
                        print(f"[RECV] Simulated ACK loss for {seq}")
                        ack10_lost_once = True
                        continue  # skip ACK
                    elif seq == 50 and not ack50_lost_once:
                        print(f"[RECV] Simulated ACK loss for {seq}")
                        ack50_lost_once = True
                        continue  # skip ACK
                    else:
                        conn.sendall(struct.pack('!I', expected_seq))
                        print(f"[RECV] Received packet {seq}, sent ACK {expected_seq}, bytes={len(data)}")

                        # Write confirmed, in-order packets
                        while expected_seq in buffer:
                            f.write(buffer[expected_seq])
                            received += len(buffer[expected_seq])
                            del buffer[expected_seq]
                            expected_seq += 1

                else:
                    # Out-of-order or early packet, re-ACK last confirmed
                    conn.sendall(struct.pack('!I', expected_seq - 1))
                    print(f"[RECV] Out-of-order packet {seq}, sent ACK {expected_seq - 1}")

            except socket.timeout:
                conn.sendall(struct.pack('!I', expected_seq - 1))
                print(f"[RECV] Timeout, sent ACK {expected_seq - 1}")
                continue
            except Exception as e:
                print(f"[RECV] Error: {e}")
                conn.sendall(struct.pack('!I', expected_seq - 1))
                continue

    return filesize


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    try:
        name_len_data = conn.recv(4)
        if len(name_len_data) != 4:
            raise ValueError(f"Invalid name length data, received {len(name_len_data)} bytes")
        name_len = int(name_len_data.decode())
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
        filesize = receive_with_progress(conn, input_path)
        upload_end = time.time()

        actual_size = os.path.getsize(input_path)
        if actual_size != filesize:
            print(f"[ERROR] File size mismatch: expected {filesize}, got {actual_size}")
            conn.sendall(b"ER")
            conn.close()
            return

        try:
            print(f"[CONVERSION] Starting conversion of {input_path} to {output_path}")
            success = convert_with_libreoffice(input_path, output_path, output_format)
            if not success:
                print(f"[ERROR] Conversion failed for {input_path}")
                conn.sendall(b"CV")
                conn.close()
                return
        except Exception as e:
            print(f"[ERROR] Conversion error: {str(e)}")
            print(traceback.format_exc())
            conn.sendall(b"CV")
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
        print(f"[ERROR] Error handling client: {str(e)}")
        print(traceback.format_exc())
        conn.sendall(b"ER")
    finally:
        # conn.close()
        # print(f"[DISCONNECTED] {addr} disconnected.")
        try:
            conn.close()
        except:
            pass
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