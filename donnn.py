import paho.mqtt.client as mqtt
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# MQTT Broker Configuration
BROKER = "ITAMR.readmeter.in"
PORT = 1883
TOPIC = "BroadcastTopic"

# CSV file to store data
CSV_FILE = "meter_readings.csv"

# Initialize an empty DataFrame
columns = ["Date_time", "MeterID", "Value", "Energy_Units"]
df = pd.DataFrame(columns=columns)

def parse_xml_message(xml_message):
    """Parses an XML message and extracts Date_time, MeterID, and Value."""
    try:
        root = ET.fromstring(xml_message)
        date_time = datetime.strptime(root.find("Date_time").text, "%d %b %Y %I:%M %p")
        meter_id = int(root.find("MeterID").text)
        value = float(root.find("Value").text)
        return date_time, meter_id, value
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return None

def update_dataframe(xml_message):
    """Updates DataFrame with Energy_Units calculation and retains last 5 minutes of data."""
    global df

    parsed_data = parse_xml_message(xml_message)
    if parsed_data:
        date_time, meter_id, value = parsed_data

        # Get previous value for this MeterID
        previous_record = df[df["MeterID"] == meter_id].sort_values(by="Date_time").tail(1)

        # Calculate Energy_Units as the difference
        if not previous_record.empty:
            prev_value = previous_record["Value"].values[0]
            energy_units = value - prev_value
        else:
            energy_units = 0  # First record, no previous value

        # Append new record
        new_data = pd.DataFrame([[date_time, meter_id, value, energy_units]], columns=df.columns)
        df = pd.concat([df, new_data], ignore_index=True)

        # Keep only last 5 minutes of data
        time_threshold = datetime.now() - timedelta(minutes=5)
        df = df[df["Date_time"] >= time_threshold]

        print(f"\nUpdated DataFrame (Last 20 Rows):\n{df.tail(20)}")

def save_to_csv():
    """Saves the latest DataFrame to CSV every 5 minutes."""
    global df
    df.to_csv(CSV_FILE, index=False, mode='w')
    print(f"\nData saved to {CSV_FILE} at {datetime.now().strftime('%H:%M:%S')}")

# MQTT Callback when a message is received
def on_message(client, userdata, msg):
    try:
        message = msg.payload.decode("utf-8")
        print(f"\nReceived MQTT Message:\n{message}")

        update_dataframe(message)

    except Exception as e:
        print(f"Error processing message: {e}")

# MQTT Client Setup
client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC)

print(f"\nListening for messages on topic '{TOPIC}'...\n")

# Start MQTT in a separate thread
client.loop_start()

# Periodically save data every 5 minutes
while True:
    save_to_csv()
    time.sleep(300)  # 300 seconds = 5 minutes