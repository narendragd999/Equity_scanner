import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ✅ Load merged CSV file
merged_file_path = "output/merged_output.csv"

st.title("📊 Options Data Analyzer Tool")

# ✅ Check if the merged CSV exists
if not os.path.exists(merged_file_path):
    st.error("❌ Merged CSV not found. Please run the ZIP merger tool first.")
else:
    df = pd.read_csv(merged_file_path)

    # ✅ Clean and Prepare Data
    df = df.dropna(subset=['LOW_PRICE', 'HIGH_PRICE', 'CLOSE_PRICE', 'OPEN_PRICE', 'DATE'])
    df['CLOSE_PRICE'] = pd.to_numeric(df['CLOSE_PRICE'], errors='coerce')
    df['OPEN_PRICE'] = pd.to_numeric(df['OPEN_PRICE'], errors='coerce')
    df['LOW_PRICE'] = pd.to_numeric(df['LOW_PRICE'], errors='coerce')
    df['HIGH_PRICE'] = pd.to_numeric(df['HIGH_PRICE'], errors='coerce')
    df['DATE'] = pd.to_datetime(df['DATE'], format='%d-%b-%Y', errors='coerce')

    # ✅ Streamlit UI for Analysis
    #st.title("📈 Options Price Gain Tracker")

    # ✅ Sidebar Filters
    security = st.sidebar.selectbox("Select Security", ["All"] + list(df['SECURITY'].unique()))
    gain_threshold = st.sidebar.slider("Gain % Threshold", min_value=1, max_value=100, value=1, step=1)

    # ✅ Day Range Selection
    day_range = st.sidebar.selectbox("Select Day Range", ["1 Day", "2 Days", "3 Days", "Custom"])

    if day_range == "Custom":
        custom_days = st.sidebar.number_input("Enter Custom Days", min_value=1, max_value=30, value=5)
        days = custom_days
    else:
        days = int(day_range.split()[0])

    # ✅ Apply Filters
    df_filtered = df.copy()

    if security != "All":
        df_filtered = df_filtered[df_filtered['SECURITY'] == security]

    # ✅ Function to calculate day-wise gain
    def calculate_daywise_gain(df, days):
        """Calculate gain % with single row per security for N-day range"""
        df_sorted = df.sort_values(['SECURITY', 'DATE'])

        gain_data = []

        # Group by Security
        for sec, group in df_sorted.groupby(['SECURITY']):
            group = group.reset_index(drop=True)

            # ✅ Use overall low price if no day filter is applied
            if len(group) >= days:
                low_price = group.iloc[-days]['LOW_PRICE']
            else:
                low_price = group['LOW_PRICE'].iloc[0]  # Fallback to first row if N days not available

            close_price = group['CLOSE_PRICE'].iloc[-1]  # Latest close price

            # ✅ Calculate gain percent
            gain_percent = ((close_price - low_price) / low_price) * 100 if low_price != 0 else 0

            gain_data.append({
                'SECURITY': sec,
                'LOW_PRICE': low_price,
                'CLOSE_PRICE': close_price,
                'GAIN_PERCENT': gain_percent
            })

        return pd.DataFrame(gain_data)

    # ✅ Apply Day-wise Gain Calculation
    df_daywise = calculate_daywise_gain(df_filtered, days)

    # ✅ Filter by Gain Threshold
    df_final_filtered = df_daywise[df_daywise['GAIN_PERCENT'] >= gain_threshold]

    # ✅ Display Table
    st.dataframe(df_final_filtered[['SECURITY', 'LOW_PRICE', 'CLOSE_PRICE', 'GAIN_PERCENT']])

    # ✅ Plot Bar Chart
    fig = px.bar(
        df_final_filtered,
        x='SECURITY',
        y='GAIN_PERCENT',
        title=f"Options with High Gains over {days} Days",
        hover_data=['LOW_PRICE', 'CLOSE_PRICE']
    )
    st.plotly_chart(fig)

    # ✅ Candlestick Chart
    if not df_filtered.empty and security != "All":
        df_strike = df_filtered[df_filtered['SECURITY'] == security]

        if not df_strike.empty:
            fig_candlestick = go.Figure(data=[go.Candlestick(
                x=df_strike['DATE'],
                open=df_strike['OPEN_PRICE'],
                high=df_strike['HIGH_PRICE'],
                low=df_strike['LOW_PRICE'],
                close=df_strike['CLOSE_PRICE']
            )])
            st.plotly_chart(fig_candlestick)
        else:
            st.warning("No data available for the selected security.")
    else:
        st.warning("Please select a specific security to view the candlestick chart.")
