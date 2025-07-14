import streamlit as st
import os
from streamlit_autorefresh import st_autorefresh

# CONFIG
st.set_page_config(page_title="Client & Server Logs Dashboard", layout="wide")
st.title("📜 Secure File Transfer Logs Dashboard")

# Paths
LOG_DIR = "../logs"
server_log_file = os.path.join(LOG_DIR, "server.log")

# Refresh
refresh_interval = st.slider("🔄 Refresh interval (seconds)", 1, 10, 3)
st_autorefresh(interval=refresh_interval * 1000, key="refresh_counter")

# Columns layout: Left (Server logs), Right (Client logs)
cols = st.columns([1, 2])

############################
# LEFT COLUMN: Server Logs
############################
with cols[0]:
    st.subheader("🖥️ Server Logs")

    try:
        with open(server_log_file, "r") as f:
            server_logs = f.read()
        st.text_area(
            label="Server Log Output",
            value=server_logs,
            height=400,
            key="server_log_area"
        )
    except FileNotFoundError:
        st.warning("⚠️ Server log not found yet.")

############################
# RIGHT COLUMN: Client Logs
############################
with cols[1]:
    st.subheader("💻 Client Logs")

    # Discover all client logs
    client_logs_files = sorted(
        [f for f in os.listdir(LOG_DIR) if f.startswith("client_") and f.endswith(".log")]
    )

    if not client_logs_files:
        st.info("ℹ️ No client logs found yet.")
    else:
        st.caption("🗂️ Displaying all available client logs (2 per row):")

        # Render 2 columns at a time
        for i in range(0, len(client_logs_files), 2):
            row_files = client_logs_files[i:i+2]
            row_cols = st.columns(2)
            for col, filename in zip(row_cols, row_files):
                with col:
                    st.markdown(f"**🗎 {filename}**")
                    try:
                        with open(os.path.join(LOG_DIR, filename), "r") as f:
                            client_logs = f.read()
                        st.text_area(
                            label="",         # No extra label inside box
                            value=client_logs,
                            height=200,       # Compact height with scroll
                            key=f"client_log_{filename}"
                        )
                    except Exception as e:
                        st.error(f"❌ Error loading {filename}: {e}")
