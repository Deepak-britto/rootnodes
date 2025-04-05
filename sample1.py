import pandas as pd
import streamlit as st
import plotly.express as px

# File Paths
CSV_FILE = "meter_readings.csv"
EXCEL_FILE = "Nodes.xlsx"

st.set_page_config(page_title="Energy Meter Dashboard", layout="wide")
st.title("📊 Energy Consumption Dashboard")

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(CSV_FILE, parse_dates=["Date_time"])
        df_nodes = pd.read_excel(EXCEL_FILE)
        df["Date_time"] = pd.to_datetime(df["Date_time"], errors="coerce")
        df = df.dropna(subset=["Date_time"])

        # Filter last 5 minutes
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
    # Define meter ID groups
    group_1 = [74, 41, 88, 89, 106, 111, 112, 121, 14, 117, 120, 12, 92, 91, 45, 110, 98, 96, 43, 67, 129]
    group_2 = [60, 61, 47, 105, 36, 125, 58, 59]
    group_3 = [122, 118, 116, 115]

    # Filter data for each group
    df_1 = df[df["MeterID"].isin(group_1)]
    df_2 = df[df["MeterID"].isin(group_2)]
    df_3 = df[df["MeterID"].isin(group_3)]

    # Aggregate energy consumption for each chart
    df_1_summary = df_1.groupby("MCDescription")["Energy_Units"].sum().reset_index()
    df_2_summary = df_2.groupby("MCDescription")["Energy_Units"].sum().reset_index()
    df_3_summary = df_3.groupby("MCDescription")["Energy_Units"].sum().reset_index()

    # **Bar Chart (Full Width) - First Group**
    fig_1 = px.bar(
        df_1_summary,
        x="MCDescription",
        y="Energy_Units",
        title="🔋 Group 1 - Energy Consumption",
        labels={"MCDescription": "Machine", "Energy_Units": "Energy Consumption (kWh)"},
        color="Energy_Units",
        color_continuous_scale="Blues"
    )

    # **Line Chart - Second Group**
    fig_2 = px.line(
        df_2_summary,
        x="MCDescription",
        y="Energy_Units",
        title="📈 Group 2 - Energy Consumption Trend",
        labels={"MCDescription": "Machine", "Energy_Units": "Energy Consumption (kWh)"},
        markers=True
    )

    # **Scatter Chart - Third Group**
    fig_3 = px.scatter(
        df_3_summary,
        x="MCDescription",
        y="Energy_Units",
        title="⚡ Group 3 - Energy Consumption Distribution",
        labels={"MCDescription": "Machine", "Energy_Units": "Energy Consumption (kWh)"},
        color="Energy_Units",
        color_continuous_scale="Reds",
        size="Energy_Units"
    )

    # **Row 1: Full-width Bar Chart**
    st.plotly_chart(fig_1, use_container_width=True)

    # **Row 2: Two Charts Side by Side**
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_2, use_container_width=True)
    with col2:
        st.plotly_chart(fig_3, use_container_width=True)

else:
    st.warning("⚠️ No recent data available for visualization!")
