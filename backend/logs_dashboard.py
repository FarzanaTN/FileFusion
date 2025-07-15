import streamlit as st
import os
import time
import pandas as pd
import altair as alt
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
                            label="",
                            value=client_logs,
                            height=200,
                            key=f"client_log_{filename}"
                        )
                    except Exception as e:
                        st.error(f"❌ Error loading {filename}: {e}")

############################
# SECTION: Per-Client CWND Graphs
############################
st.subheader("📈 TCP Reno CWND Graphs (One per Client)")

if not client_logs_files:
    st.info("No client logs found for graphs yet.")
else:
    for filename in client_logs_files:
        st.markdown(f"### 📌 Graph for {filename}")

        round_numbers = []
        cwnd_values = []
        ssthresh_values = []
        states = []

        try:
            with open(os.path.join(LOG_DIR, filename), "r") as f:
                round_counter = 1
                for line in f:
                    if "[CC]" in line:
                        # Remove timestamp if present
                        if "," in line and line[0].isdigit():
                            _, text = line.strip().split(",", 1)
                        else:
                            text = line.strip()

                        tokens = text.split()
                        cwnd_token = [t for t in tokens if t.startswith("cwnd=")]
                        ssthresh_token = [t for t in tokens if t.startswith("ssthresh=")]
                        state_token = [t for t in tokens if t.startswith("state=")]

                        if cwnd_token and ssthresh_token and state_token:
                            cwnd = float(cwnd_token[0].split("=")[1])
                            ssthresh = float(ssthresh_token[0].split("=")[1])
                            state = state_token[0].split("=")[1]
                            round_numbers.append(round_counter)
                            cwnd_values.append(cwnd)
                            ssthresh_values.append(ssthresh)
                            states.append(state)
                            round_counter += 1

        except Exception as e:
            st.warning(f"Error reading {filename}: {e}")
            continue

        if not cwnd_values:
            st.info(f"No congestion control logs in {filename}.")
            continue

        # Build DataFrame
        df = pd.DataFrame({
            "Round": round_numbers,
            "CWND": cwnd_values,
            "SSTHRESH": ssthresh_values,
            "State": states
        })

        # ✅ Limit to first 150 rounds
        df = df[df["Round"] <= 150]

        if df.empty:
            st.info(f"No data in first 150 rounds for {filename}.")
            continue

        # Build background shading intervals
        bands = []
        if not df.empty:
            prev_state = df.iloc[0]["State"]
            start_round = df.iloc[0]["Round"]
            for i in range(1, len(df)):
                this_state = df.iloc[i]["State"]
                if this_state != prev_state:
                    bands.append({
                        "Start": start_round,
                        "End": df.iloc[i]["Round"],
                        "State": prev_state
                    })
                    start_round = df.iloc[i]["Round"]
                    prev_state = this_state
            bands.append({
                "Start": start_round,
                "End": df.iloc[-1]["Round"] + 1,
                "State": prev_state
            })

        bands_df = pd.DataFrame(bands)

        # Show data
        st.dataframe(df)

        # Build chart
        background = (
            alt.Chart(bands_df)
            .mark_rect(opacity=0.2)
            .encode(
                x='Start:Q',
                x2='End:Q',
                color=alt.Color('State:N', legend=alt.Legend(title="TCP Reno State"))
            )
        )

        line = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "Round:Q",
                    title="Transmission Round",
                    scale=alt.Scale(domain=[0, 150]),
                    axis=alt.Axis(
                        values=list(range(0, 151, 5)),
                        title='Transmission Round',
                        tickMinStep=5
                    )
                ),
                y=alt.Y("CWND:Q", title="Congestion Window Size (packets)"),
                tooltip=["Round", "CWND", "SSTHRESH", "State"]
            )
        )

        chart = alt.layer(background, line).resolve_scale(color='independent').properties(
            title=f"TCP Reno CWND vs Transmission Round with State Shading - {filename}",
            width='container'
        )

        st.altair_chart(chart, use_container_width=True)
