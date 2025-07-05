# Fixed server.py with proper Go-Back-N ACK implementation
import socket
import threading
import os
import time
import random
from converter import convert_with_libreoffice

HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 8192  # Smaller buffer for more reliable transfer
UPLOAD_DIR = 'uploads'
CONVERTED_DIR = 'converted'
WINDOW_SIZE = 4
DROP_PROBABILITY = 0.01  # Reduced drop probability

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

def receive_with_gobackn(conn, total_size):
    """Receive file using Go-Back-N protocol with ACK"""
    total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE
    received_packets = {}
    expected_seq = 0
    received_bytes = 0
    
    print(f"[SERVER] Expecting {total_size} bytes in {total_packets} packets")
    
    while received_bytes < total_size:
        try:
            conn.settimeout(10.0)
            
            # Receive sequence number
            seq_data = conn.recv(4)
            if not seq_data:
                continue
                
            seq_num = int.from_bytes(seq_data, 'big')
            
            # Receive data
            remaining = total_size - received_bytes
            chunk_size = min(BUFFER_SIZE, remaining)
            chunk = conn.recv(chunk_size)
            
            if not chunk:
                continue
                
            print(f"[SERVER] Received packet {seq_num} ({len(chunk)} bytes)")
            
            if seq_num == expected_seq:
                # Correct packet received
                received_packets[seq_num] = chunk
                received_bytes += len(chunk)
                expected_seq += 1
                
                # Send ACK for this packet
                ack = seq_num.to_bytes(4, 'big')
                conn.sendall(ack)
                print(f"[SERVER] Sent ACK {seq_num}")
                
            else:
                # Wrong packet, send ACK for last correct packet
                ack = (expected_seq - 1).to_bytes(4, 'big')
                conn.sendall(ack)
                print(f"[SERVER] Wrong packet {seq_num}, sent ACK {expected_seq - 1}")
                
        except socket.timeout:
            print("[SERVER] Timeout waiting for packet")
            continue
        except Exception as e:
            print(f"[SERVER] Error receiving packet: {e}")
            break
    
    # Reconstruct file
    file_data = b""
    for i in range(total_packets):
        if i in received_packets:
            file_data += received_packets[i]
    
    print(f"[SERVER] Received {len(file_data)} bytes total")
    return file_data

def send_with_gobackn(conn, file_path):
    """Send file using Go-Back-N protocol with ACK"""
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
    except Exception as e:
        print(f"[SERVER] Cannot read file {file_path}: {e}")
        return False

    total_packets = (len(file_bytes) + BUFFER_SIZE - 1) // BUFFER_SIZE
    seq_num = 0
    base = 0
    
    print(f"[SERVER] Sending {len(file_bytes)} bytes in {total_packets} packets")
    
    # Send file size first
    conn.sendall(str(len(file_bytes)).encode().ljust(16))
    time.sleep(0.1)
    
    while base < total_packets:
        # Send packets in current window
        while seq_num < base + WINDOW_SIZE and seq_num < total_packets:
            start = seq_num * BUFFER_SIZE
            end = min(start + BUFFER_SIZE, len(file_bytes))
            chunk = file_bytes[start:end]
            
            # Simulate packet drop
            if random.random() > DROP_PROBABILITY:
                try:
                    # Send sequence number + data
                    packet = seq_num.to_bytes(4, 'big') + chunk
                    conn.sendall(packet)
                    print(f"[SERVER] Sent packet {seq_num} ({len(chunk)} bytes)")
                except Exception as e:
                    print(f"[SERVER] Error sending packet {seq_num}: {e}")
                    return False
            else:
                print(f"[SERVER] Simulated drop of packet {seq_num}")
            
            seq_num += 1
        
        # Wait for ACK
        try:
            conn.settimeout(5.0)
            ack_data = conn.recv(4)
            if ack_data:
                ack_num = int.from_bytes(ack_data, 'big')
                print(f"[SERVER] Received ACK {ack_num}")
                
                if ack_num >= base:
                    base = ack_num + 1
                
        except socket.timeout:
            print(f"[SERVER] Timeout waiting for ACK, resending from {base}")
            seq_num = base
        except Exception as e:
            print(f"[SERVER] Error receiving ACK: {e}")
            return False
    
    print(f"[SERVER] File transfer completed successfully")
    return True

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    try:
        # Receive file metadata
        name_len = int(conn.recv(4).decode())
        filename = conn.recv(name_len).decode()
        output_format = conn.recv(8).decode().strip().lower()
        print(f"[INFO] File: {filename}, Format: {output_format}")

        # Validate file extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pptx", ".doc", ".docx", ".odt", ".xls", ".xlsx"]:
            print(f"[ERROR] Unsupported file type: {ext}")
            conn.sendall(b"ER")
            return

        # Set up file paths
        input_path = os.path.join(UPLOAD_DIR, filename)
        output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
        output_path = os.path.join(CONVERTED_DIR, output_filename)

        # Receive file size
        filesize = int(conn.recv(16).decode().strip())
        print(f"[INFO] Receiving file ({filesize:,} bytes)")
        
        # Receive file using Go-Back-N
        upload_start = time.time()
        file_data = receive_with_gobackn(conn, filesize)
        upload_end = time.time()
        
        if len(file_data) == 0:
            print(f"[ERROR] No data received")
            conn.sendall(b"ER")
            return

        # Save uploaded file
        with open(input_path, 'wb') as f:
            f.write(file_data)
        print(f"[INFO] File saved to {input_path}")
        print(f"[INFO] Upload time: {upload_end - upload_start:.2f}s")

        # Convert file
        print(f"[INFO] Starting conversion...")
        conversion_start = time.time()
        success = convert_with_libreoffice(input_path, output_path, output_format)
        conversion_end = time.time()
        
        if not success or not os.path.exists(output_path):
            print(f"[ERROR] Conversion failed")
            conn.sendall(b"ER")
            return

        print(f"[INFO] Conversion successful. Output: {output_path}")
        print(f"[INFO] Conversion time: {conversion_end - conversion_start:.2f}s")

        # Send success response
        conn.sendall(b"OK")
        
        # Send converted file info
        conn.sendall(str(len(output_filename)).encode().ljust(4))
        conn.sendall(output_filename.encode())
        
        # Send converted file using Go-Back-N
        print(f"[INFO] Starting file download...")
        download_start = time.time()
        send_success = send_with_gobackn(conn, output_path)
        download_end = time.time()
        
        if send_success:
            # Send timing information
            conn.sendall(f"{upload_end - upload_start:.4f}".encode().ljust(16))
            conn.sendall(f"{download_end - download_start:.4f}".encode().ljust(16))
            print(f"[INFO] Download time: {download_end - download_start:.2f}s")
            print(f"[INFO] Total processing time: {download_end - upload_start:.2f}s")
        else:
            print("[ERROR] Failed to send converted file")

    except Exception as e:
        print(f"[ERROR] Error handling client {addr}: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.sendall(b"ER")
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass
        print(f"[DISCONNECTED] {addr} disconnected.")

def start_server():
    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("\n[SHUTTING DOWN] Server shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()