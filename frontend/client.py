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

<<<<<<< HEAD
def send_with_progress(sock, file_bytes, progress_bar):
    total = len(file_bytes)
    sent = 0
    while sent < total:
        end = min(sent + BUFFER_SIZE, total)
        sock.sendall(file_bytes[sent:end])
        sent = end
        progress_bar.progress(sent / total)
    progress_bar.progress(1.0)
=======
# def send_ack(sock, seq_num):
#     """Send ACK for received packet"""
#     try:
#         ack_data = seq_num.to_bytes(4, byteorder='big')
#         sock.sendall(ack_data)
#         return True
#     except Exception as e:
#         print(f"Failed to send ACK for packet {seq_num}: {e}")
#         return False

# def receive_ack(sock, expected_seq):
#     """Receive and validate ACK"""
#     try:
#         sock.settimeout(TIMEOUT)
#         ack_data = b''
#         while len(ack_data) < ACK_SIZE:
#             chunk = sock.recv(ACK_SIZE - len(ack_data))
#             if not chunk:
#                 return False
#             ack_data += chunk
        
#         received_seq = int.from_bytes(ack_data, byteorder='big')
#         return received_seq == expected_seq
#     except socket.timeout:
#         return False
#     except Exception as e:
#         print(f"Error receiving ACK for {expected_seq}: {e}")
#         return False
#     finally:
#         sock.settimeout(None)

# def send_with_ack(sock, file_bytes, progress_bar, status_text):
#     """Send file with packet-by-packet ACK system"""
#     try:
#         total_size = len(file_bytes)
        
#         # Send file size first
#         sock.sendall(str(total_size).encode().ljust(16))
        
#         seq_num = 0
#         offset = 0
#         total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE
        
#         while offset < total_size:
#             # Prepare data chunk
#             remaining = total_size - offset
#             chunk_size = min(BUFFER_SIZE, remaining)
#             data = file_bytes[offset:offset + chunk_size]
            
#             # Prepare packet header
#             packet_header = seq_num.to_bytes(4, byteorder='big') + len(data).to_bytes(4, byteorder='big')
            
#             # Send packet with retries
#             retry_count = 0
#             ack_received = False
            
#             while retry_count < MAX_RETRIES and not ack_received:
#                 try:
#                     # Send header first, then data
#                     sock.sendall(packet_header)
#                     sock.sendall(data)
#                     status_text.text(f"Sending packet {seq_num + 1}/{total_packets} (Attempt {retry_count + 1})")
                    
#                     # Wait for ACK
#                     ack_received = receive_ack(sock, seq_num)
#                     if ack_received:
#                         offset += len(data)
#                         seq_num += 1
#                         progress_bar.progress(offset / total_size)
#                         break
#                     else:
#                         retry_count += 1
#                         if retry_count < MAX_RETRIES:
#                             status_text.text(f"Retry packet {seq_num + 1}, attempt {retry_count + 1}")
                        
#                 except Exception as e:
#                     retry_count += 1
#                     status_text.text(f"Error sending packet {seq_num}: {e}")
            
#             if not ack_received:
#                 status_text.text(f"Failed to send packet {seq_num} after {MAX_RETRIES} attempts")
#                 return False
        
#         # Send end-of-transmission marker
#         end_packet = (0xFFFFFFFF).to_bytes(4, byteorder='big') + (0).to_bytes(4, byteorder='big')
#         sock.sendall(end_packet)
#         status_text.text("Upload completed successfully!")
#         progress_bar.progress(1.0)
        
#         return True
#     except Exception as e:
#         status_text.text(f"Upload failed: {e}")
#         return False

# def receive_with_ack(sock, progress_bar, status_text):
#     """Receive file with packet-by-packet ACK system"""
#     try:
#         # Receive file size with better error handling
#         filesize_data = b''
#         while len(filesize_data) < 16:
#             chunk = sock.recv(16 - len(filesize_data))
#             if not chunk:
#                 status_text.text("Connection closed while receiving file size")
#                 return b''
#             filesize_data += chunk
        
#         try:
#             filesize = int(filesize_data.decode().strip())
#         except ValueError as e:
#             status_text.text(f"Invalid file size data: {filesize_data}")
#             return b''
        
#         status_text.text(f"Expecting {filesize} bytes")
        
#         received_bytes = 0
#         expected_seq = 0
#         data_chunks = []
#         total_packets = (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE if filesize > 0 else 0
        
#         while received_bytes < filesize:
#             try:
#                 # Receive packet header (ensure we get all 8 bytes)
#                 header = b''
#                 while len(header) < PACKET_HEADER_SIZE:
#                     chunk = sock.recv(PACKET_HEADER_SIZE - len(header))
#                     if not chunk:
#                         status_text.text("Connection closed while receiving header")
#                         break
#                     header += chunk
                
#                 if len(header) != PACKET_HEADER_SIZE:
#                     break
                
#                 seq_num = int.from_bytes(header[:4], byteorder='big')
#                 data_len = int.from_bytes(header[4:8], byteorder='big')
                
#                 # Check for end-of-transmission marker
#                 if seq_num == 0xFFFFFFFF and data_len == 0:
#                     status_text.text("Download completed successfully!")
#                     break
                
#                 # Receive data (ensure we get all bytes)
#                 data = b''
#                 while len(data) < data_len:
#                     chunk = sock.recv(data_len - len(data))
#                     if not chunk:
#                         status_text.text("Connection closed while receiving data")
#                         break
#                     data += chunk
                
#                 if len(data) != data_len:
#                     status_text.text(f"Data length mismatch: expected {data_len}, got {len(data)}")
#                     continue
                
#                 status_text.text(f"Receiving packet {seq_num + 1}/{total_packets}")
                
#                 # Check sequence number
#                 if seq_num == expected_seq:
#                     data_chunks.append(data)
#                     received_bytes += len(data)
#                     if not send_ack(sock, seq_num):
#                         status_text.text(f"Failed to send ACK for packet {seq_num}")
#                         break
#                     expected_seq += 1
#                     if filesize > 0:
#                         progress_bar.progress(received_bytes / filesize)
#                 else:
#                     status_text.text(f"Sequence error: expected {expected_seq}, got {seq_num}")
#                     # Send ACK for last correctly received packet
#                     if expected_seq > 0:
#                         send_ack(sock, expected_seq - 1)
                
#             except Exception as e:
#                 status_text.text(f"Error receiving packet: {e}")
#                 break
        
#         progress_bar.progress(1.0)
#         return b''.join(data_chunks)
#     except Exception as e:
#         status_text.text(f"Download failed: {e}")
#         return b''

def send_ack(sock, seq_num):
    """Send ACK for received packet"""
    try:
        ack_data = seq_num.to_bytes(4, byteorder='big')
        sock.sendall(ack_data)
        print(f"[ACK] Sent ACK for packet {seq_num}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send ACK for packet {seq_num}: {e}")
        return False

def receive_ack(sock, expected_seq):
    """Receive and validate ACK"""
    try:
        sock.settimeout(TIMEOUT)
        ack_data = b''
        start_time = time.time()
        while len(ack_data) < ACK_SIZE:
            if time.time() - start_time > TIMEOUT:
                print(f"[TIMEOUT] Waiting for ACK {expected_seq}")
                return False
            chunk = sock.recv(ACK_SIZE - len(ack_data))
            if not chunk:
                print(f"[ERROR] Connection closed while waiting for ACK {expected_seq}")
                return False
            ack_data += chunk
        
        received_seq = int.from_bytes(ack_data, byteorder='big')
        if received_seq != expected_seq:
            print(f"[ERROR] Expected ACK {expected_seq}, got {received_seq}")
            return False
        print(f"[ACK] Received ACK for packet {expected_seq}")
        return True
    except Exception as e:
        print(f"[ERROR] Receiving ACK {expected_seq}: {e}")
        return False
    finally:
        sock.settimeout(None)

def send_with_ack(sock, file_bytes, progress_bar, status_text):
    """Send file with packet-by-packet ACK system"""
    try:
        total_size = len(file_bytes)
        sock.sendall(str(total_size).encode().ljust(16))
        status_text.text(f"Sending file size: {total_size} bytes")
        
        seq_num = 0
        offset = 0
        total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE
        
        while offset < total_size:
            remaining = total_size - offset
            chunk_size = min(BUFFER_SIZE, remaining)
            data = file_bytes[offset:offset + chunk_size]
            
            packet_header = seq_num.to_bytes(4, byteorder='big') + len(data).to_bytes(4, byteorder='big')
            
            retry_count = 0
            ack_received = False
            
            while retry_count < MAX_RETRIES and not ack_received:
                try:
                    sock.sendall(packet_header)
                    sock.sendall(data)
                    print(f"[CLIENT] Sent Packet {seq_num} | Size: {len(data)} bytes | Attempt {retry_count + 1}")
                    status_text.text(f"Sending packet {seq_num + 1}/{total_packets} (Attempt {retry_count + 1})")
                    
                    ack_received = receive_ack(sock, seq_num)
                    if ack_received:
                        print(f"[CLIENT] Received ACK for Packet {seq_num}")
                        offset += len(data)
                        seq_num += 1
                        progress_bar.progress(offset / total_size)
                        break
                    else:
                        retry_count += 1
                        print(f"[CLIENT] Retrying Packet {seq_num} | Attempt {retry_count + 1}")
                        if retry_count < MAX_RETRIES:
                            status_text.text(f"Retrying packet {seq_num + 1}, attempt {retry_count + 1}")
                except Exception as e:
                    retry_count += 1
                    print(f"[CLIENT] Error sending Packet {seq_num}: {e}")
                    status_text.text(f"Error sending packet {seq_num}: {e}")
            
            if not ack_received:
                print(f"[CLIENT] Failed to send Packet {seq_num} after {MAX_RETRIES} attempts")
                status_text.text(f"Failed to send packet {seq_num} after {MAX_RETRIES} attempts")
                return False
        
        end_packet = (0xFFFFFFFF).to_bytes(4, byteorder='big') + (0).to_bytes(4, byteorder='big')
        sock.sendall(end_packet)
        status_text.text("Upload completed successfully!")
        print("[CLIENT] Upload completed successfully!")
        progress_bar.progress(1.0)
        return True
    except Exception as e:
        status_text.text(f"Upload failed: {e}")
        print(f"[CLIENT] Upload failed: {e}")
        return False


#before pkt loss
def receive_with_ack(sock, progress_bar, status_text):
    """Receive file with packet-by-packet ACK system"""
    try:
        filesize_data = b''
        start_time = time.time()
        while len(filesize_data) < 16:
            if time.time() - start_time > TIMEOUT:
                status_text.text("Timeout receiving file size")
                print(f"[CLIENT] Timeout receiving file size")
                return b''
            chunk = sock.recv(16 - len(filesize_data))
            if not chunk:
                status_text.text("Connection closed while receiving file size")
                print(f"[CLIENT] Connection closed while receiving file size")
                return b''
            filesize_data += chunk
        
        filesize = int(filesize_data.decode().strip())
        status_text.text(f"Expecting {filesize} bytes")
        
        received_bytes = 0
        expected_seq = 0
        data_chunks = []
        total_packets = (filesize + BUFFER_SIZE - 1) // BUFFER_SIZE if filesize > 0 else 0
        
        while received_bytes < filesize:
            header = b''
            start_time = time.time()
            while len(header) < PACKET_HEADER_SIZE:
                if time.time() - start_time > TIMEOUT:
                    status_text.text("Timeout receiving packet header")
                    print(f"[CLIENT] Timeout receiving packet header")
                    break
                chunk = sock.recv(PACKET_HEADER_SIZE - len(header))
                if not chunk:
                    status_text.text("Connection closed while receiving header")
                    print(f"[CLIENT] Connection closed while receiving header")
                    return b''.join(data_chunks)
                header += chunk
            
            if len(header) != PACKET_HEADER_SIZE:
                break
            
            seq_num = int.from_bytes(header[:4], byteorder='big')
            data_len = int.from_bytes(header[4:8], byteorder='big')
            
            if seq_num == 0xFFFFFFFF and data_len == 0:
                status_text.text("Download completed successfully!")
                print("[CLIENT] Download completed successfully!")
                break
            
            data = b''
            start_time = time.time()
            while len(data) < data_len:
                if time.time() - start_time > TIMEOUT:
                    status_text.text(f"Timeout receiving data for packet {seq_num}")
                    print(f"[CLIENT] Timeout receiving data for packet {seq_num}")
                    break
                chunk = sock.recv(data_len - len(data))
                if not chunk:
                    status_text.text(f"Connection closed while receiving data for packet {seq_num}")
                    print(f"[CLIENT] Connection closed while receiving data for packet {seq_num}")
                    break
                data += chunk
            
            if len(data) != data_len:
                status_text.text(f"Data length mismatch: expected {data_len}, got {len(data)}")
                print(f"[CLIENT] Data length mismatch: expected {data_len}, got {len(data)}")
                send_ack(sock, expected_seq - 1 if expected_seq > 0 else 0)
                continue
            
            status_text.text(f"Receiving packet {seq_num + 1}/{total_packets}")
            print(f"[CLIENT] Receiving Packet {seq_num} | Size: {len(data)} bytes")
            
            if seq_num == expected_seq:
                data_chunks.append(data)
                received_bytes += len(data)
                if not send_ack(sock, seq_num):
                    status_text.text(f"Failed to send ACK for packet {seq_num}")
                    print(f"[CLIENT] Failed to send ACK for packet {seq_num}")
                    break
                expected_seq += 1
                if filesize > 0:
                    progress_bar.progress(received_bytes / filesize)
            else:
                status_text.text(f"Sequence error: expected {expected_seq}, got {seq_num}")
                print(f"[CLIENT] Sequence error: expected {expected_seq}, got {seq_num}")
                send_ack(sock, expected_seq - 1 if expected_seq > 0 else 0)
        
        progress_bar.progress(1.0)
        return b''.join(data_chunks)
    except Exception as e:
        status_text.text(f"Download failed: {e}")
        print(f"[CLIENT] Download failed: {e}")
        return b''
>>>>>>> amina

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

#after pkt loss


# def main():


#     st.title("📄 Multi-Format File Converter (Enhanced with Packet ACK)")
    
#     # Display protocol information
#     with st.expander("📊 Protocol Information"):
#         st.write(f"**Packet Size:** {BUFFER_SIZE} bytes")
#         st.write(f"**Max Retries:** {MAX_RETRIES}")
#         st.write(f"**Timeout:** {TIMEOUT} seconds")
#         st.write(f"**Server:** {HOST}:{PORT}")
    
#     uploaded_file = st.file_uploader("Upload your file", type=list(ALLOWED_CONVERSIONS.keys()))

#     output_format = None
#     if uploaded_file:
#         file_ext = os.path.splitext(uploaded_file.name)[1].lower()
#         allowed_outputs = ALLOWED_CONVERSIONS.get(file_ext, [])

#         if not allowed_outputs:
#             st.error("Unsupported file type.")
#             return
#         else:
#             output_format = st.selectbox("Select output format", allowed_outputs)

#     if uploaded_file and output_format:
#         filename = uploaded_file.name
#         file_bytes = uploaded_file.read()
        
#         st.info(f"📄  **File:** {filename}")
#         st.info(f"📏  **Size:** {len(file_bytes):,} bytes")
#         st.info(f"🔄 **Converting to:** {output_format.upper()}")
        
#         # Calculate expected packets
#         expected_packets = (len(file_bytes) + BUFFER_SIZE - 1) // BUFFER_SIZE
#         st.info(f"📦 **Expected packets:** {expected_packets}")

#         if st.button("Upload and Convert"):
#             sock = None
#             try:
#                 sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 sock.settimeout(30.0)  # Set overall connection timeout
#                 sock.connect((HOST, PORT))
#                 sock.settimeout(None)  # Remove timeout for normal operations
                
#                 # Send filename length and name
#                 filename_len_data = str(len(filename)).encode().ljust(4)
#                 sock.sendall(filename_len_data)
#                 sock.sendall(filename.encode())

#                 # Send output format (up to 8 bytes)
#                 output_format_data = output_format.encode().ljust(8)
#                 sock.sendall(output_format_data)

#                 # Upload phase
#                 st.subheader("📤 Upload Progress")
#                 upload_progress = st.progress(0)
#                 upload_status = st.empty()
                
#                 upload_start = time.time()
#                 upload_success = send_with_ack(sock, file_bytes, upload_progress, upload_status)
#                 upload_end = time.time()
                
#                 if not upload_success:
#                     st.error("Upload failed!")
#                     return

#                 # Wait for conversion response
#                 st.subheader("⚙️ Conversion Progress")
#                 conversion_status = st.empty()
#                 conversion_status.text("Waiting for server response...")
                
#                 # Set timeout for server response
#                 sock.settimeout(600.0)
#                 response_data = b''
#                 while len(response_data) < 2:
#                     chunk = sock.recv(2 - len(response_data))
#                     if not chunk:
#                         st.error("Connection closed while waiting for server response")
#                         return
#                     response_data += chunk
#                 sock.settimeout(None)
                
#                 if response_data != b"OK":
#                     st.error(f"Conversion failed. Server response: {response_data}")
#                     return

#                 conversion_status.text("Conversion completed successfully!")

#                 # Download phase
#                 st.subheader("📥 Download Progress")
                
#                 # Receive filename with better error handling
#                 name_len_data = b''
#                 while len(name_len_data) < 4:
#                     chunk = sock.recv(4 - len(name_len_data))
#                     if not chunk:
#                         st.error("Connection closed while receiving filename length")
#                         return
#                     name_len_data += chunk
                
#                 name_len = int(name_len_data.decode().strip())
                
#                 converted_name_data = b''
#                 while len(converted_name_data) < name_len:
#                     chunk = sock.recv(name_len - len(converted_name_data))
#                     if not chunk:
#                         st.error("Connection closed while receiving filename")
#                         return
#                     converted_name_data += chunk
                
#                 converted_name = converted_name_data.decode()

#                 download_progress = st.progress(0)
#                 download_status = st.empty()
                
#                 download_start = time.time()
#                 converted_bytes = receive_with_ack(sock, download_progress, download_status)
#                 download_end = time.time()
                
#                 if not converted_bytes:
#                     st.error("Failed to receive converted file")
#                     return

#                 # Receive timing information with better error handling
#                 timing_data = {}
#                 timing_labels = ['upload', 'download', 'conversion']
                
#                 for label in timing_labels:
#                     try:
#                         data = b''
#                         while len(data) < 16:
#                             chunk = sock.recv(16 - len(data))
#                             if not chunk:
#                                 st.warning(f"Connection closed while receiving {label} timing")
#                                 break
#                             data += chunk
                        
#                         if len(data) == 16:
#                             timing_data[label] = float(data.decode().strip())
#                         else:
#                             timing_data[label] = 0.0
#                     except Exception as e:
#                         st.warning(f"Failed to parse {label} timing: {e}")
#                         timing_data[label] = 0.0

#                 # Display results
#                 st.success("ðŸŽ‰ Conversion completed successfully!")
                
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.metric("📤 Upload Time (Client)", f"{upload_end - upload_start:.2f}s")
#                     st.metric("📤  Download Time (Client)", f"{download_end - download_start:.2f}s")
#                     st.metric("📦 Total Packets", expected_packets)
                
#                 with col2:
#                     st.metric("📤Upload Time (Server)", f"{timing_data.get('upload', 0):.2f}s")
#                     st.metric("📤Download Time (Server)", f"{timing_data.get('download', 0):.2f}s")
#                     st.metric("⚙️ Conversion Time", f"{timing_data.get('conversion', 0):.2f}s")

#                 st.download_button(
#                     label="💾 Download Converted File",
#                     data=converted_bytes,
#                     file_name=converted_name,
#                     mime='application/octet-stream'
#                 )

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
<<<<<<< HEAD
    st.title("📄 Multi-Format File Converter")
=======
    st.title("📄 Multi-Format File Converter (Enhanced with Packet ACK)")

    # Display protocol information
    with st.expander("📊 Protocol Information"):
        st.write(f"**Packet Size:** {BUFFER_SIZE} bytes")
        st.write(f"**Max Retries:** {MAX_RETRIES}")
        st.write(f"**Timeout:** {TIMEOUT} seconds")
        st.write(f"**Server:** {HOST}:{PORT}")

>>>>>>> amina
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
<<<<<<< HEAD
=======

        st.info(f"📄  **File:** {filename}")
        st.info(f"📏  **Size:** {len(file_bytes):,} bytes")
        st.info(f"🔄 **Converting to:** {output_format.upper()}")

        expected_packets = (len(file_bytes) + BUFFER_SIZE - 1) // BUFFER_SIZE
        st.info(f"📦 **Expected packets:** {expected_packets}")
>>>>>>> amina

        if st.button("Upload and Convert"):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
<<<<<<< HEAD
                sock.connect((HOST, PORT))
=======
                sock.settimeout(30.0)
                sock.connect((HOST, PORT))
                sock.settimeout(None)
>>>>>>> amina

                # Send filename length and name
                sock.sendall(str(len(filename)).encode().ljust(4))
                sock.sendall(filename.encode())

<<<<<<< HEAD
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
=======
                # Send output format
                sock.sendall(output_format.encode().ljust(8))

                # Upload
                st.subheader("📤 Upload Progress")
                upload_progress = st.progress(0)
                upload_status = st.empty()

                upload_success = send_with_ack(sock, file_bytes, upload_progress, upload_status)
                # upload_success = send_with_ack(sock, file_bytes)
                if not upload_success:
                    st.error("Upload failed!")
                    return

                # Wait for server response
                st.subheader("⚙️ Conversion Progress")
                conversion_status = st.empty()
                conversion_status.text("Waiting for server response...")

                sock.settimeout(600.0)
                response_data = b''
                while len(response_data) < 2:
                    chunk = sock.recv(2 - len(response_data))
                    if not chunk:
                        st.error("Connection closed while waiting for server response")
                        return
                    response_data += chunk
                sock.settimeout(None)

                if response_data != b"OK":
                    st.error(f"Conversion failed. Server response: {response_data}")
                    return
>>>>>>> amina

                # Receive file size
                converted_size = int(sock.recv(16).decode().strip())
                st.info(f"Downloading {converted_name}")
                download_bar = st.progress(0)
                converted_bytes = receive_with_progress(sock, converted_size, download_bar)

<<<<<<< HEAD
                upload_time_server = float(sock.recv(16).decode().strip())
                download_time_server = float(sock.recv(16).decode().strip())

                sock.close()

                st.success("Conversion successful!")
                st.write(f"Upload time: {upload_time_server:.2f} s")
                st.write(f"Download time: {download_time_server:.2f} s")
=======
                # Download
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
                converted_bytes = receive_with_ack(sock, download_progress, download_status)

                if not converted_bytes:
                    st.error("Failed to receive converted file")
                    return

                # Success message only
                st.success("🎉 Conversion completed successfully!")
>>>>>>> amina

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