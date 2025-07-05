# Fixed client.py with proper Go-Back-N ACK implementation
import socket
import streamlit as st
import time
import os
import random

HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 1024  # Smaller buffer for more reliable transfer
WINDOW_SIZE = 4
DROP_PROBABILITY = 0.01  # Reduced drop probability

ALLOWED_CONVERSIONS = {
    ".doc": ["pdf", "docx", "odt"],
    ".docx": ["pdf", "doc", "odt"],
    ".odt": ["pdf", "docx"],
    ".pptx": ["pdf"],
    ".xlsx": ["pdf"],
    ".xls": ["pdf"],
}

def send_with_gobackn(sock, file_bytes, progress_bar):
    """Send file using Go-Back-N protocol with ACK"""
    total_packets = (len(file_bytes) + BUFFER_SIZE - 1) // BUFFER_SIZE
    seq_num = 0
    base = 0
    
    print(f"[CLIENT] Sending {len(file_bytes)} bytes in {total_packets} packets")
    
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
                    sock.sendall(packet)
                    print(f"[CLIENT] Sent packet {seq_num} ({len(chunk)} bytes)")
                except Exception as e:
                    print(f"[CLIENT] Error sending packet {seq_num}: {e}")
                    return False
            else:
                print(f"[CLIENT] Simulated drop of packet {seq_num}")
            
            seq_num += 1
        
        # Wait for ACK
        try:
            sock.settimeout(5.0)
            ack_data = sock.recv(4)
            if ack_data:
                ack_num = int.from_bytes(ack_data, 'big')
                print(f"[CLIENT] Received ACK {ack_num}")
                
                if ack_num >= base:
                    base = ack_num + 1
                    progress_bar.progress(min(base / total_packets, 1.0))
                
        except socket.timeout:
            print(f"[CLIENT] Timeout waiting for ACK, resending from {base}")
            seq_num = base
        except Exception as e:
            print(f"[CLIENT] Error receiving ACK: {e}")
            return False
    
    print(f"[CLIENT] File transfer completed successfully")
    return True

def receive_with_gobackn(sock, total_size, progress_bar):
    """Receive file using Go-Back-N protocol with ACK"""
    total_packets = (total_size + BUFFER_SIZE - 1) // BUFFER_SIZE
    received_packets = {}
    expected_seq = 0
    received_bytes = 0
    
    print(f"[CLIENT] Expecting {total_size} bytes in {total_packets} packets")
    
    while received_bytes < total_size:
        try:
            sock.settimeout(10.0)
            
            # Receive sequence number
            seq_data = sock.recv(4)
            if not seq_data:
                continue
                
            seq_num = int.from_bytes(seq_data, 'big')
            
            # Receive data
            remaining = total_size - received_bytes
            chunk_size = min(BUFFER_SIZE, remaining)
            chunk = sock.recv(chunk_size)
            
            if not chunk:
                continue
                
            print(f"[CLIENT] Received packet {seq_num} ({len(chunk)} bytes)")
            
            if seq_num == expected_seq:
                # Correct packet received
                received_packets[seq_num] = chunk
                received_bytes += len(chunk)
                expected_seq += 1
                
                # Send ACK for this packet
                ack = seq_num.to_bytes(4, 'big')
                sock.sendall(ack)
                print(f"[CLIENT] Sent ACK {seq_num}")
                
                progress_bar.progress(min(received_bytes / total_size, 1.0))
                
            else:
                # Wrong packet, send ACK for last correct packet
                ack = (expected_seq - 1).to_bytes(4, 'big')
                sock.sendall(ack)
                print(f"[CLIENT] Wrong packet {seq_num}, sent ACK {expected_seq - 1}")
                
        except socket.timeout:
            print("[CLIENT] Timeout waiting for packet")
            continue
        except Exception as e:
            print(f"[CLIENT] Error receiving packet: {e}")
            break
    
    # Reconstruct file
    file_data = b""
    for i in range(total_packets):
        if i in received_packets:
            file_data += received_packets[i]
    
    print(f"[CLIENT] Received {len(file_data)} bytes total")
    return file_data

def main():
    st.title("📄 Multi-Format File Converter (Go-Back-N)")
    
    # Initialize session state
    if 'converted_file' not in st.session_state:
        st.session_state.converted_file = None
    if 'conversion_complete' not in st.session_state:
        st.session_state.conversion_complete = False
    
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
            # Reset session state for new conversion
            st.session_state.converted_file = None
            st.session_state.conversion_complete = False
            
            try:
                with st.spinner("Connecting to server..."):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(30.0)
                    sock.connect((HOST, PORT))

                # Send file metadata
                sock.sendall(str(len(filename)).encode().ljust(4))
                sock.sendall(filename.encode())
                sock.sendall(output_format.encode().ljust(8))
                sock.sendall(str(len(file_bytes)).encode().ljust(16))

                # Upload file using Go-Back-N
                st.info("Uploading file using Go-Back-N protocol...")
                upload_bar = st.progress(0)
                upload_start = time.time()
                
                success = send_with_gobackn(sock, file_bytes, upload_bar)
                upload_end = time.time()
                
                if not success:
                    st.error("Upload failed!")
                    sock.close()
                    return

                st.info(f"Upload completed in {upload_end - upload_start:.2f}s")
                st.info("Converting file... Please wait.")

                # Check conversion status
                sock.settimeout(60.0)  # Give server time to convert
                response = sock.recv(2)
                if response != b"OK":
                    st.error("Conversion failed. Server may not support this format.")
                    sock.close()
                    return

                # Get converted file info
                name_len = int(sock.recv(4).decode().strip())
                converted_name = sock.recv(name_len).decode()
                converted_size = int(sock.recv(16).decode().strip())

                st.info(f"Downloading {converted_name} ({converted_size:,} bytes)")
                download_bar = st.progress(0)
                download_start = time.time()
                
                # Download converted file using Go-Back-N
                converted_bytes = receive_with_gobackn(sock, converted_size, download_bar)
                download_end = time.time()

                if len(converted_bytes) == 0:
                    st.error("Download failed - no data received")
                    sock.close()
                    return

                # Get timing info
                try:
                    upload_time_server = float(sock.recv(16).decode().strip())
                    download_time_server = float(sock.recv(16).decode().strip())
                except:
                    upload_time_server = upload_end - upload_start
                    download_time_server = download_end - download_start
                
                # Close connection
                sock.close()

                # Store result in session state
                st.session_state.converted_file = {
                    'data': converted_bytes,
                    'name': converted_name
                }
                st.session_state.conversion_complete = True
                
                st.success("🎉 Conversion successful!")
                st.write(f"📤 Upload time: {upload_time_server:.2f}s")
                st.write(f"📥 Download time: {download_time_server:.2f}s")
                st.write(f"📄 File size: {len(converted_bytes):,} bytes")
                
                # Force UI refresh to show download button
                st.rerun()

            except socket.timeout:
                st.error("Connection timeout. Please try again.")
            except Exception as e:
                st.error(f"Connection failed: {e}")
                print(f"Error details: {e}")

    # Show download button if conversion is complete
    if st.session_state.conversion_complete and st.session_state.converted_file:
        st.success("✅ Your file is ready for download!")
        st.download_button(
            label="📥 Download Converted File",
            data=st.session_state.converted_file['data'],
            file_name=st.session_state.converted_file['name'],
            mime='application/octet-stream',
            key="download_converted_file"
        )

if __name__ == "__main__":
    main()