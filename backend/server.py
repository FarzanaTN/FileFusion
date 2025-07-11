# import socket
# import threading
# import os
# import time
# from converter import convert_with_libreoffice

# HOST = '0.0.0.0'
# PORT = 65432
# BUFFER_SIZE = 4096
# UPLOAD_DIR = 'uploads'
# CONVERTED_DIR = 'converted'

# os.makedirs(UPLOAD_DIR, exist_ok=True)
# os.makedirs(CONVERTED_DIR, exist_ok=True)

# def send_with_progress(conn, file_path):
#     filesize = os.path.getsize(file_path)
#     conn.sendall(str(filesize).encode().ljust(16))  # Send file size fixed 16 bytes

#     with open(file_path, 'rb') as f:
#         sent = 0
#         while sent < filesize:
#             data = f.read(BUFFER_SIZE)
#             conn.sendall(data)
#             sent += len(data)

# def receive_with_progress(conn, dest_path):
#     filesize = int(conn.recv(16).decode().strip())
#     received = 0
#     with open(dest_path, 'wb') as f:
#         while received < filesize:
#             data = conn.recv(min(BUFFER_SIZE, filesize - received))
#             if not data:
#                 break
#             f.write(data)
#             received += len(data)
#     return filesize

# def handle_client(conn, addr):
#     print(f"[NEW CONNECTION] {addr} connected.")
#     try:
#         name_len = int(conn.recv(4).decode())
#         filename = conn.recv(name_len).decode()

#         output_format = conn.recv(8).decode().strip().lower()

#         ext = os.path.splitext(filename)[1].lower()
#         if ext not in [".pptx", ".doc", ".docx", ".odt", ".xls", ".xlsx"]:
#             conn.sendall(b"ER")
#             conn.close()
#             return

#         input_path = os.path.join(UPLOAD_DIR, filename)
#         output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
#         output_path = os.path.join(CONVERTED_DIR, output_filename)

#         upload_start = time.time()
#         receive_with_progress(conn, input_path)
#         upload_end = time.time()

#         success = convert_with_libreoffice(input_path, output_path, output_format)
#         if not success:
#             conn.sendall(b"ER")
#             conn.close()
#             return

#         conn.sendall(b"OK")

#         conn.sendall(str(len(output_filename)).encode().ljust(4))
#         conn.sendall(output_filename.encode())
#         send_with_progress(conn, output_path)

#         download_end = time.time()

#         conn.sendall(f"{upload_end - upload_start:.4f}".encode().ljust(16))
#         conn.sendall(f"{download_end - upload_end:.4f}".encode().ljust(16))

#     except Exception as e:
#         print("Error handling client:", e)
#     finally:
#         conn.close()
#         print(f"[DISCONNECTED] {addr} disconnected.")


# def start_server():
#     print("[STARTING] Server is starting...")
#     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server.bind((HOST, PORT))
#     server.listen(5)
#     print(f"[LISTENING] Server listening on {HOST}:{PORT}")

#     while True:
#         conn, addr = server.accept()
#         thread = threading.Thread(target=handle_client, args=(conn, addr))
#         thread.start()
#         print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


# if __name__ == "__main__":
#     start_server()


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

# Packet protocol constants
PACKET_HEADER_SIZE = 8  # 4 bytes seq_num + 4 bytes data_len
ACK_SIZE = 4
MAX_RETRIES = 3
TIMEOUT = 10.0  # Increased timeout

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

def send_ack(conn, seq_num):
    """Send ACK for received packet"""
    try:
        ack_data = seq_num.to_bytes(4, byteorder='big')
        conn.sendall(ack_data)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send ACK for packet {seq_num}: {e}")
        return False

def receive_ack(conn, expected_seq):
    """Receive and validate ACK"""
    try:
        conn.settimeout(TIMEOUT)
        ack_data = b''
        while len(ack_data) < ACK_SIZE:
            chunk = conn.recv(ACK_SIZE - len(ack_data))
            if not chunk:
                return False
            ack_data += chunk
        
        received_seq = int.from_bytes(ack_data, byteorder='big')
        return received_seq == expected_seq
    except socket.timeout:
        print(f"[TIMEOUT] Waiting for ACK {expected_seq}")
        return False
    except Exception as e:
        print(f"[ERROR] Receiving ACK {expected_seq}: {e}")
        return False
    finally:
        conn.settimeout(None)

# def send_with_ack(conn, file_path):
#     """Send file with packet-by-packet ACK system"""
#     try:
#         filesize = os.path.getsize(file_path)
        
#         # Send file size first
#         conn.sendall(str(filesize).encode().ljust(16))
        
#         with open(file_path, 'rb') as f:
#             seq_num = 0
#             total_sent = 0
            
#             while total_sent < filesize:
#                 # Read data chunk
#                 remaining = filesize - total_sent
#                 chunk_size = min(BUFFER_SIZE, remaining)
#                 data = f.read(chunk_size)
                
#                 if not data:
#                     break
                
#                 # Prepare packet: seq_num (4 bytes) + data_len (4 bytes) + data
#                 packet_header = seq_num.to_bytes(4, byteorder='big') + len(data).to_bytes(4, byteorder='big')
                
#                 # Send packet with retries
#                 retry_count = 0
#                 ack_received = False
                
#                 while retry_count < MAX_RETRIES and not ack_received:
#                     try:
#                         # Send header first, then data
#                         conn.sendall(packet_header)
#                         conn.sendall(data)
#                         print(f"[SEND] Packet {seq_num}, Size: {len(data)} bytes")
                        
#                         # Wait for ACK
#                         ack_received = receive_ack(conn, seq_num)
#                         if ack_received:
#                             print(f"[ACK] Received ACK for packet {seq_num}")
#                             total_sent += len(data)
#                             seq_num += 1
#                             break
#                         else:
#                             retry_count += 1
#                             print(f"[RETRY] Packet {seq_num}, Attempt {retry_count}")
#                             # Reset file position for retry
#                             current_pos = f.tell()
#                             f.seek(current_pos - len(data))
                            
#                     except Exception as e:
#                         retry_count += 1
#                         print(f"[ERROR] Sending packet {seq_num}: {e}")
#                         # Reset file position for retry
#                         current_pos = f.tell()
#                         f.seek(current_pos - len(data))
                
#                 if not ack_received:
#                     print(f"[FAILED] Could not send packet {seq_num} after {MAX_RETRIES} attempts")
#                     return False
        
#         # Send end-of-transmission marker
#         end_packet = (0xFFFFFFFF).to_bytes(4, byteorder='big') + (0).to_bytes(4, byteorder='big')
#         conn.sendall(end_packet)
#         print("[SEND] End-of-transmission marker sent")
        
#         return True
#     except Exception as e:
#         print(f"[ERROR] send_with_ack: {e}")
#         return False


def send_with_ack(conn, file_path):
    """Send file with packet-by-packet ACK system"""
    try:
        filesize = os.path.getsize(file_path)
        
        # Send file size first
        conn.sendall(str(filesize).encode().ljust(16))
        
        with open(file_path, 'rb') as f:
            seq_num = 0
            total_sent = 0
            
            while total_sent < filesize:
                # Read data chunk
                remaining = filesize - total_sent
                chunk_size = min(BUFFER_SIZE, remaining)
                data = f.read(chunk_size)
                
                if not data:
                    break
                
                # Prepare packet: seq_num (4 bytes) + data_len (4 bytes) + data
                packet_header = seq_num.to_bytes(4, byteorder='big') + len(data).to_bytes(4, byteorder='big')
                
                # Send packet with retries
                retry_count = 0
                ack_received = False
                
                while retry_count < MAX_RETRIES and not ack_received:
                    try:
                        # Send header first, then data
                        conn.sendall(packet_header)
                        conn.sendall(data)
                        print(f"[SEND] Packet {seq_num}, Size: {len(data)} bytes")
                        
                        # Wait for ACK
                        ack_received = receive_ack(conn, seq_num)
                        if ack_received:
                            print(f"[ACK] Received ACK for packet {seq_num}")
                            total_sent += len(data)
                            seq_num += 1
                            break
                        else:
                            retry_count += 1
                            print(f"[RETRY] Packet {seq_num}, Attempt {retry_count}")
                            # No file seeking needed; just resend the same data
                    except Exception as e:
                        retry_count += 1
                        print(f"[ERROR] Sending packet {seq_num}: {e}")
                        # No file seeking needed; just resend the same data
                
                if not ack_received:
                    print(f"[FAILED] Could not send packet {seq_num} after {MAX_RETRIES} attempts")
                    return False
        
        # Send end-of-transmission marker
        end_packet = (0xFFFFFFFF).to_bytes(4, byteorder='big') + (0).to_bytes(4, byteorder='big')
        conn.sendall(end_packet)
        print("[SEND] End-of-transmission marker sent")
        
        return True
    except Exception as e:
        print(f"[ERROR] send_with_ack: {e}")
        return False
              



def receive_with_ack(conn, dest_path):
    """Receive file with packet-by-packet ACK system"""
    try:
        # Receive file size
        filesize_data = b''
        while len(filesize_data) < 16:
            chunk = conn.recv(16 - len(filesize_data))
            if not chunk:
                print("[ERROR] Connection closed while receiving file size")
                return 0
            filesize_data += chunk
        
        filesize = int(filesize_data.decode().strip())
        print(f"[RECEIVE] Expected file size: {filesize} bytes")
        
        received_bytes = 0
        expected_seq = 0
        
        with open(dest_path, 'wb') as f:
            while received_bytes < filesize:
                try:
                    # Receive packet header (ensure we get all 8 bytes)
                    header = b''
                    while len(header) < PACKET_HEADER_SIZE:
                        chunk = conn.recv(PACKET_HEADER_SIZE - len(header))
                        if not chunk:
                            print("[ERROR] Connection closed while receiving header")
                            return received_bytes
                        header += chunk
                    
                    seq_num = int.from_bytes(header[:4], byteorder='big')
                    data_len = int.from_bytes(header[4:8], byteorder='big')
                    
                    # Check for end-of-transmission marker
                    if seq_num == 0xFFFFFFFF and data_len == 0:
                        print("[RECEIVE] End-of-transmission marker received")
                        break
                    
                    # Receive data (ensure we get all bytes)
                    data = b''
                    while len(data) < data_len:
                        chunk = conn.recv(data_len - len(data))
                        if not chunk:
                            print("[ERROR] Connection closed while receiving data")
                            return received_bytes
                        data += chunk
                    
                    print(f"[RECEIVE] Packet {seq_num}, Size: {len(data)} bytes")
                    
                    # Check sequence number
                    if seq_num == expected_seq:
                        f.write(data)
                        received_bytes += len(data)
                        if not send_ack(conn, seq_num):
                            print(f"[ERROR] Failed to send ACK for packet {seq_num}")
                            return received_bytes
                        expected_seq += 1
                        print(f"[ACK] Sent ACK for packet {seq_num}")
                    else:
                        print(f"[ERROR] Expected seq {expected_seq}, got {seq_num}")
                        # Send ACK for last correctly received packet
                        if expected_seq > 0:
                            send_ack(conn, expected_seq - 1)
                
                except Exception as e:
                    print(f"[ERROR] Receiving packet: {e}")
                    break
        
        print(f"[RECEIVE] Total received: {received_bytes} bytes")
        return received_bytes
    except Exception as e:
        print(f"[ERROR] receive_with_ack: {e}")
        return 0

# def handle_client(conn, addr):
#     print(f"[NEW CONNECTION] {addr} connected.")
#     upload_start = 0
#     upload_end = 0
#     conversion_start = 0
#     conversion_end = 0
#     download_start = 0
#     download_end = 0
    
#     input_path = None
#     output_path = None

#     conn.settimeout(600)
    
#     try:
#         # Receive filename with better error handling
#         name_len_data = b''
#         while len(name_len_data) < 4:
#             chunk = conn.recv(4 - len(name_len_data))
#             if not chunk:
#                 print("[ERROR] Connection closed while receiving filename length")
#                 return
#             name_len_data += chunk
        
#         name_len = int(name_len_data.decode().strip())
#         print(f"[INFO] Expecting filename of length: {name_len}")
        
#         filename_data = b''
#         while len(filename_data) < name_len:
#             chunk = conn.recv(name_len - len(filename_data))
#             if not chunk:
#                 print("[ERROR] Connection closed while receiving filename")
#                 return
#             filename_data += chunk
        
#         filename = filename_data.decode()
#         print(f"[INFO] Filename: {filename}")

#         # Receive output format with better error handling
#         output_format_data = b''
#         while len(output_format_data) < 8:
#             chunk = conn.recv(8 - len(output_format_data))
#             if not chunk:
#                 print("[ERROR] Connection closed while receiving output format")
#                 return
#             output_format_data += chunk
        
#         output_format = output_format_data.decode().strip().lower()
#         print(f"[INFO] Output format: {output_format}")

#         # Validate file extension
#         ext = os.path.splitext(filename)[1].lower()
#         if ext not in [".pptx", ".doc", ".docx", ".odt", ".xls", ".xlsx"]:
#             print(f"[ERROR] Unsupported file extension: {ext}")
#             conn.sendall(b"ER")
#             return

#         # Prepare paths
#         input_path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{filename}")
#         output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
#         output_path = os.path.join(CONVERTED_DIR, f"{int(time.time())}_{output_filename}")

#         # Receive file with ACK system
#         print("[INFO] Starting file upload with ACK system...")
#         upload_start = time.time()
#         received_bytes = receive_with_ack(conn, input_path)
#         upload_end = time.time()
        
#         if received_bytes == 0:
#             print("[ERROR] No bytes received during upload")
#             conn.sendall(b"ER")
#             return

#         print(f"[INFO] Upload completed: {received_bytes} bytes in {upload_end - upload_start:.2f} seconds")

#         # Convert file
#         print("[INFO] Starting conversion...")
#         conversion_start = time.time()
#         success = convert_with_libreoffice(input_path, output_path, output_format)
#         conversion_end = time.time()
        
#         if not success or not os.path.exists(output_path):
#             print("[ERROR] Conversion failed or output file not created")
#             conn.sendall(b"ER")
#             return

#         print(f"[INFO] Conversion completed in {conversion_end - conversion_start:.2f} seconds")

#         # Send success response
#         conn.sendall(b"OK")
#         print("[INFO] Sent OK response")

#         # Send converted filename
#         filename_len_data = str(len(output_filename)).encode().ljust(4)
#         conn.sendall(filename_len_data)
#         conn.sendall(output_filename.encode())
#         print(f"[INFO] Sent filename: {output_filename}")

#         # Send converted file with ACK system
#         print("[INFO] Starting file download with ACK system...")
#         download_start = time.time()
#         success = send_with_ack(conn, output_path)
#         download_end = time.time()
        
#         if not success:
#             print("[ERROR] Failed to send converted file")
#             return

#         print(f"[INFO] Download completed in {download_end - download_start:.2f} seconds")

#         # Send timing information with better error handling
#         try:
#             upload_time = f"{upload_end - upload_start:.4f}".encode().ljust(16)
#             download_time = f"{download_end - download_start:.4f}".encode().ljust(16)
#             conversion_time = f"{conversion_end - conversion_start:.4f}".encode().ljust(16)
            
#             conn.sendall(upload_time)
#             conn.sendall(download_time)
#             conn.sendall(conversion_time)
            
#             print(f"[INFO] Sent timing data: upload={upload_end - upload_start:.2f}s, download={download_end - download_start:.2f}s, conversion={conversion_end - conversion_start:.2f}s")
#         except Exception as e:
#             print(f"[ERROR] Failed to send timing data: {e}")

#         print(f"[SUCCESS] Client {addr} served successfully")

#     except Exception as e:
#         print(f"[ERROR] Handling client {addr}: {e}")
#         import traceback
#         traceback.print_exc()
#         try:
#             conn.sendall(b"ER")
#         except:
#             pass
#     finally:
#         # Clean up files
#         try:
#             if input_path and os.path.exists(input_path):
#                 os.remove(input_path)
#                 print(f"[CLEANUP] Removed input file: {input_path}")
#         except Exception as e:
#             print(f"[CLEANUP ERROR] Failed to remove input file: {e}")
        
#         try:
#             if output_path and os.path.exists(output_path):
#                 os.remove(output_path)
#                 print(f"[CLEANUP] Removed output file: {output_path}")
#         except Exception as e:
#             print(f"[CLEANUP ERROR] Failed to remove output file: {e}")
        
#         try:
#             conn.close()
#         except:
#             pass
#         print(f"[DISCONNECTED] {addr} disconnected.")

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    upload_start = upload_end = conversion_start = conversion_end = download_start = download_end = 0
    input_path = output_path = None

    conn.settimeout(600)
    
    try:
        # Receive filename
        name_len_data = b''
        start_time = time.time()
        while len(name_len_data) < 4:
            if time.time() - start_time > TIMEOUT:
                print("[TIMEOUT] Receiving filename length")
                return
            chunk = conn.recv(4 - len(name_len_data))
            if not chunk:
                print("[ERROR] Connection closed while receiving filename length")
                return
            name_len_data += chunk
        
        name_len = int(name_len_data.decode().strip())
        filename_data = b''
        start_time = time.time()
        while len(filename_data) < name_len:
            if time.time() - start_time > TIMEOUT:
                print("[TIMEOUT] Receiving filename")
                return
            chunk = conn.recv(name_len - len(filename_data))
            if not chunk:
                print("[ERROR] Connection closed while receiving filename")
                return
            filename_data += chunk
        
        filename = filename_data.decode()
        print(f"[INFO] Filename: {filename}")

        # Receive output format
        output_format_data = b''
        start_time = time.time()
        while len(output_format_data) < 8:
            if time.time() - start_time > TIMEOUT:
                print("[TIMEOUT] Receiving output format")
                return
            chunk = conn.recv(8 - len(output_format_data))
            if not chunk:
                print("[ERROR] Connection closed while receiving output format")
                return
            output_format_data += chunk
        
        output_format = output_format_data.decode().strip().lower()
        print(f"[INFO] Output format: {output_format}")

        # Validate file extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pptx", ".doc", ".docx", ".odt", ".xls", ".xlsx"]:
            print(f"[ERROR] Unsupported file extension: {ext}")
            conn.sendall(b"ER")
            return

        # Prepare paths with unique filenames
        timestamp = int(time.time())
        input_path = os.path.join(UPLOAD_DIR, f"{timestamp}_{filename}")
        output_filename = f"{os.path.splitext(filename)[0]}.{output_format}"
        output_path = os.path.join(CONVERTED_DIR, f"{timestamp}_{output_filename}")

        # Receive file
        upload_start = time.time()
        received_bytes = receive_with_ack(conn, input_path)
        upload_end = time.time()
        
        if received_bytes == 0:
            print("[ERROR] No bytes received during upload")
            conn.sendall(b"ER")
            return

        print(f"[INFO] Upload completed: {received_bytes} bytes in {upload_end - upload_start:.2f} seconds")

        # Convert file
        conversion_start = time.time()
        success = convert_with_libreoffice(input_path, output_path, output_format)
        conversion_end = time.time()
        
        if not success or not os.path.exists(output_path):
            print("[ERROR] Conversion failed or output file not created")
            conn.sendall(b"ER")
            return

        print(f"[INFO] Conversion completed in {conversion_end - conversion_start:.2f} seconds")

        # Send success response
        conn.sendall(b"OK")
        print("[INFO] Sent OK response")

        # Send converted filename
        filename_len_data = str(len(output_filename)).encode().ljust(4)
        conn.sendall(filename_len_data)
        conn.sendall(output_filename.encode())
        print(f"[INFO] Sent filename: {output_filename}")

        # Send converted file
        download_start = time.time()
        success = send_with_ack(conn, output_path)
        download_end = time.time()
        
        if not success:
            print("[ERROR] Failed to send converted file")
            return

        print(f"[INFO] Download completed in {download_end - download_start:.2f} seconds")

        # Send timing information
        upload_time = f"{upload_end - upload_start:.4f}".encode().ljust(16)
        download_time = f"{download_end - download_start:.4f}".encode().ljust(16)
        conversion_time = f"{conversion_end - conversion_start:.4f}".encode().ljust(16)
        
        conn.sendall(upload_time)
        conn.sendall(download_time)
        conn.sendall(conversion_time)
        
        print(f"[INFO] Sent timing data: upload={upload_end - upload_start:.2f}s, download={download_end - download_start:.2f}s, conversion={conversion_end - conversion_start:.2f}s")

        print(f"[SUCCESS] Client {addr} served successfully")

    except Exception as e:
        print(f"[ERROR] Handling client {addr}: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.sendall(b"ER")
        except:
            pass
    # finally:
    #     if input_path and os.path.exists(input_path):
    #         try:
    #             os.remove(input_path)
    #             print(f"[CLEANUP] Removed input file: {input_path}")
    #         except Exception as e:
    #             print(f"[CLEANUP ERROR] Failed to remove input file: {e}")
        
    #     if output_path and os.path.exists(output_path):
    #         try:
    #             os.remove(output_path)
    #             print(f"[CLEANUP] Removed output file: {output_path}")
    #         except Exception as e:
    #             print(f"[CLEANUP ERROR] Failed to remove output file: {e}")
        
    #     try:
    #         conn.close()
    #     except:
    #         pass
    #     print(f"[DISCONNECTED] {addr} disconnected.")

def start_server():
    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[LISTENING] Server listening on {HOST}:{PORT}")
        print(f"[CONFIG] Packet size: {BUFFER_SIZE} bytes, Max retries: {MAX_RETRIES}, Timeout: {TIMEOUT}s")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server shutting down...")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()