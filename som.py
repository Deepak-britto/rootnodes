import paho.mqtt.client as mqtt
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import threading

import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_pydot import graphviz_layout
import streamlit as st

# ---------- Configuration ----------
BROKER = "ITAMR.readmeter.in"
PORT = 1883
TOPIC = "BroadcastTopic"
CSV_FILE = "meter_readings.csv"
EXCEL_FILE = "Nodes.xlsx"

# ---------- Initialize DataFrame ----------
columns = ["Date_time", "MeterID", "Value", "Energy_Units"]
df = pd.DataFrame(columns=columns)

# ---------- XML Parsing ----------
def parse_xml_message(xml_message):
    try:
        root = ET.fromstring(xml_message)
        date_time = datetime.strptime(root.find("Date_time").text, "%d %b %Y %I:%M %p")
        meter_id = int(root.find("MeterID").text)
        value = float(root.find("Value").text)
        return date_time, meter_id, value
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return None

# ---------- Update DataFrame ----------
def update_dataframe(xml_message):
    global df
    parsed_data = parse_xml_message(xml_message)
    if parsed_data:
        date_time, meter_id, value = parsed_data

        previous_record = df[df["MeterID"] == meter_id].sort_values(by="Date_time").tail(1)
        energy_units = value - previous_record["Value"].values[0] if not previous_record.empty else 0

        new_data = pd.DataFrame([[date_time, meter_id, value, energy_units]], columns=df.columns)
        df = pd.concat([df, new_data], ignore_index=True)

        time_threshold = datetime.now() - timedelta(minutes=5)
        df = df[df["Date_time"] >= time_threshold]

        df.to_csv(CSV_FILE, index=False, mode='w')
        print(f"Data saved to {CSV_FILE} at {datetime.now().strftime('%H:%M:%S')}")

# ---------- MQTT Callback ----------
def on_message(client, userdata, msg):
    try:
        message = msg.payload.decode("utf-8")
        print(f"Received MQTT Message:\n{message}")
        update_dataframe(message)
    except Exception as e:
        print(f"Error processing message: {e}")

# ---------- MQTT Thread ----------
def start_mqtt_client():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.subscribe(TOPIC)
    client.loop_forever()

# Start MQTT client in background
mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
mqtt_thread.start()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Energy Meter Dashboard", layout="wide")
st.title("📊 Energy Consumption Dashboard")

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(CSV_FILE, parse_dates=["Date_time"])
        df_nodes = pd.read_excel(EXCEL_FILE)
        df["Date_time"] = pd.to_datetime(df["Date_time"], errors="coerce")
        df = df.dropna(subset=["Date_time"])

        time_threshold = pd.Timestamp.now() - pd.Timedelta(minutes=5)
        df = df[df["Date_time"] >= time_threshold]

        if "Energy_Units" in df.columns:
            df_pt = df.pivot_table(index="MeterID", values="Energy_Units", aggfunc="sum").reset_index()
            df_pt["Energy_Units"].fillna(0, inplace=True)
        else:
            st.error("⚠️ Column 'Energy_Units' not found in CSV file!")
            return pd.DataFrame()

        merged_df = pd.merge(df_nodes, df_pt, on="MeterID", how="left")
        return merged_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    G = nx.DiGraph()

    for _, row in df.iterrows():
        label = f"{row['MCDescription']}\nValue: {round(row['Energy_Units'], 2)}"
        G.add_node(row["MeterID"], label=label, node_type=row["Child Node"])

    for _, row in df.iterrows():
        if row["Child Node"] != "Root Node":
            G.add_edge(row["Nodes"], row["MeterID"])

    node_colors = {
        "Root Node": "red",
        "Parent Node": "orange",
        "Child Node": "lightblue"
    }

    def plot_graph_for_root(root_node):
        subgraph_nodes = [node for node, data in G.nodes(data=True)
                          if data["node_type"] != "Root Node" and G.has_edge(root_node, node)]
        subgraph = G.subgraph(subgraph_nodes + [root_node])
        pos = graphviz_layout(subgraph, prog="dot")
        pos = {k: [v[0] * 0.2, v[1] * 0.5] for k, v in pos.items()}
        plt.figure(figsize=(5, 2.5))
        nx.draw_networkx_edges(subgraph, pos, edge_color="gray", width=1, alpha=0.2)

        for node, (x, y) in pos.items():
            node_data = df[df["MeterID"] == node].iloc[0]
            node_color = node_colors.get(node_data["Child Node"], "lightgray")
            label = G.nodes[node]["label"]
            font_size = 4 if node_data["Child Node"] == "Child Node" else 6
            padding = 0.2 if node_data["Child Node"] == "Child Node" else 0.5

            plt.text(
                x, y, label, fontsize=font_size, ha="center", va="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=" + str(padding), edgecolor="black", facecolor=node_color)
            )
        plt.axis("off")

    # Streamlit Layout
    row1_col1 = st.container()
    row2_col1, row2_col2 = st.columns([1, 1])

    with row1_col1:
        st.subheader("Root Node 74")
        plot_graph_for_root(74)
        st.pyplot(plt)

    with row2_col1:
        st.subheader("Root Node 122")
        plot_graph_for_root(122)
        st.pyplot(plt)

    with row2_col2:
        st.subheader("Root Node 129")
        plot_graph_for_root(129)
        st.pyplot(plt)
else:
    st.warning("⚠️ No recent data available for visualization!")
