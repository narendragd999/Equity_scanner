import os
import pandas as pd
import re
import zipfile
import shutil
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Define directories
source_folder = "zip"
output_folder = "output"
merged_file_path = os.path.join(output_folder, "merged_output.csv")
fno_file_path = "data/FO_SECURITY.xlsx"  # F&O securities file
tickers_file_path = "data/tickers.csv"  # New tickers file for SYMBOL matching

# Ensure directories exist
os.makedirs(source_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Function to extract date (from bhav.py)
def extract_date(folder_name):
    match = re.search(r"(\d{2})(\d{2})(\d{2})$", folder_name.split(".")[0])
    if match:
        day, month, year = match.groups()
        year = "20" + year if int(year) <= 50 else "19" + year
        month_names = {
            "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR", "05": "MAY", "06": "JUN",
            "07": "JUL", "08": "AUG", "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"
        }
        month = month_names.get(month, month)
        return f"{day}-{month}-{year}"
    return ""

# Function to process ZIP files (bhav.py logic)
def process_zip_files():
    merged_data = []
    for zip_file in os.listdir(source_folder):
        if zip_file.endswith(".zip"):
            zip_path = os.path.join(source_folder, zip_file)
            extract_folder = os.path.join(output_folder, zip_file.replace(".zip", ""))
            os.makedirs(extract_folder, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            
            formatted_date = extract_date(zip_file)
            
            for root, _, files in os.walk(extract_folder):
                for file in files:
                    if file.startswith("Pd") and file.endswith(".csv"):
                        file_path = os.path.join(root, file)
                        df = pd.read_csv(file_path)
                        
                        # Apply logic: Remove columns A, B, C and J to P
                        df.drop(df.columns[[0, 1] + list(range(9, 16))], axis=1, inplace=True)
                        
                        # Add DATE column
                        df["DATE"] = formatted_date
                        
                        merged_data.append(df)
            
            shutil.rmtree(extract_folder)

    if merged_data:
        final_df = pd.concat(merged_data, ignore_index=True)
        final_df.to_csv(merged_file_path, index=False)
        return True, f"✅ Merged CSV saved at: {merged_file_path}", final_df
    return False, "No valid CSV files found for processing.", None

# Streamlit App (app.py + bhav.py combined)
def run_app():
    st.title("📊 Equity Data Analyzer Tool")

    # ZIP File Uploader
    st.sidebar.header("Upload ZIP Files")
    uploaded_files = st.sidebar.file_uploader("Upload ZIP files", type=["zip"], accept_multiple_files=True)
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            zip_path = os.path.join(source_folder, uploaded_file.name)
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.success(f"Saved {uploaded_file.name} to {source_folder}")

    # Process Data Button
    if st.sidebar.button("Process ZIP Files"):
        with st.spinner("Processing ZIP files..."):
            success, message, final_df = process_zip_files()
            if success:
                st.success(message)
                st.download_button(
                    label="Download Merged CSV",
                    data=final_df.to_csv(index=False).encode('utf-8'),
                    file_name="merged_output.csv"
                )
            else:
                st.error(message)

    # Check if merged CSV exists
    if not os.path.exists(merged_file_path):
        st.error("❌ Merged CSV not found. Please upload ZIP files and process them first.")
        return

    # Load the main data
    df = pd.read_csv(merged_file_path)

    # Load F&O Securities
    if os.path.exists(fno_file_path):
        df_fno = pd.read_excel(fno_file_path)
        df_fno['FIRST_WORD'] = df_fno['SECURITY'].str.split().str[0].str.upper().str.strip()
        fno_list = df_fno['FIRST_WORD'].tolist()
    else:
        st.error("❌ F&O securities file not found.")
        fno_list = []

    # Load tickers.csv for SYMBOL matching
    ticker_symbols = []
    if os.path.exists(tickers_file_path):
        df_tickers = pd.read_csv(tickers_file_path)
        if 'SYMBOL' in df_tickers.columns:
            ticker_symbols = df_tickers['SYMBOL'].str.upper().str.strip().tolist()
        else:
            st.warning("⚠️ 'SYMBOL' column not found in tickers.csv")
    else:
        st.warning("⚠️ tickers.csv file not found at data/tickers.csv")

    # Clean and Prepare Data
    df = df.dropna(subset=['LOW_PRICE', 'HIGH_PRICE', 'CLOSE_PRICE', 'OPEN_PRICE', 'DATE', 'SYMBOL'])
    df['CLOSE_PRICE'] = pd.to_numeric(df['CLOSE_PRICE'], errors='coerce')
    df['OPEN_PRICE'] = pd.to_numeric(df['OPEN_PRICE'], errors='coerce')
    df['LOW_PRICE'] = pd.to_numeric(df['LOW_PRICE'], errors='coerce')
    df['HIGH_PRICE'] = pd.to_numeric(df['HIGH_PRICE'], errors='coerce')
    df['DATE'] = pd.to_datetime(df['DATE'], format='%d-%b-%Y', errors='coerce')
    df['FIRST_WORD'] = df['SECURITY'].str.split().str[0].str.upper().str.strip().fillna('')
    df['SYMBOL'] = df['SYMBOL'].astype(str).str.upper().str.strip()

    # Filter by first-word with partial matching
    def filter_first_word_partial(df, fno_list):
        if not fno_list:
            return df
        mask = df['FIRST_WORD'].apply(lambda x: any(fno in x for fno in fno_list))
        return df[mask]

    df = filter_first_word_partial(df, fno_list)

    # Calculate the most recent OPEN_PRICE for each SYMBOL
    df_sorted_by_date = df.sort_values('DATE')
    yesterday_open_price = df_sorted_by_date.groupby('SYMBOL')['OPEN_PRICE'].last().reset_index()
    yesterday_open_price.rename(columns={'OPEN_PRICE': 'YESTERDAY_OPEN_PRICE'}, inplace=True)

    # Sidebar Filters
    st.sidebar.header("Filters")
    security = st.sidebar.selectbox("Select Security", ["All"] + list(df['SECURITY'].unique()))
    symbol_filter = st.sidebar.selectbox("Select SYMBOL", ["All"] + list(df['SYMBOL'].unique()))
    gain_threshold = st.sidebar.slider("Gain % Threshold", min_value=1, max_value=100, value=15, step=1)
    security_type = st.sidebar.selectbox("Select Security Type", ["Nifty", "2.5%", "Others", "NONE"], index=3)
    day_range = st.sidebar.selectbox("Select Day Range", ["1 Day", "2 Days", "3 Days", "Custom"], index=3)
    show_fno_only = st.sidebar.checkbox("Show only F&O Securities (match SYMBOL with tickers.csv)", value=True)
    
    if day_range == "Custom":
        custom_days = st.sidebar.number_input("Enter Custom Days", min_value=1, max_value=30, value=5)
        days = custom_days
    else:
        days = int(day_range.split()[0])

    close_price_filter = st.sidebar.text_input("Filter by CLOSE_PRICE (>=)", "90")

    # Apply Filters
    df_filtered = df.copy()

    if security_type != "NONE":
        if security_type == "Nifty":
            df_filtered = df_filtered[df_filtered['SECURITY'].str.startswith("Nifty", na=False)]
        elif security_type == "2.5%":
            df_filtered = df_filtered[df_filtered['SECURITY'].str.startswith("2.5", na=False)]
        elif security_type == "Others":
            df_filtered = df_filtered[~df_filtered['SECURITY'].str.startswith(("Nifty", "2.5"), na=False)]

    if security != "All":
        df_filtered = df_filtered[df_filtered['SECURITY'] == security]

    if symbol_filter != "All":
        df_filtered = df_filtered[df_filtered['SYMBOL'] == symbol_filter]

    if show_fno_only and ticker_symbols:
        df_filtered = df_filtered[df_filtered['SYMBOL'].isin(ticker_symbols)]

    if close_price_filter:
        try:
            close_price_value = float(close_price_filter)
            df_filtered = df_filtered[df_filtered['CLOSE_PRICE'] >= close_price_value]
        except ValueError:
            st.warning("Please enter a valid numeric value for CLOSE_PRICE filter")

    # Function to calculate day-wise gain
    def calculate_daywise_gain(df, days):
        df_sorted = df.sort_values(['SECURITY', 'DATE'])
        gain_data = []
        for sec, group in df_sorted.groupby(['SECURITY']):
            group = group.reset_index(drop=True)
            if len(group) >= days:
                low_price = group.iloc[-days]['LOW_PRICE']
            else:
                low_price = group['LOW_PRICE'].iloc[0]
            close_price = group['CLOSE_PRICE'].iloc[-1]
            gain_percent = ((close_price - low_price) / low_price) * 100 if low_price != 0 else 0
            symbol = group['SYMBOL'].iloc[-1]
            gain_data.append({
                'SECURITY': sec,
                'SYMBOL': symbol,
                'LOW_PRICE': low_price,
                'CLOSE_PRICE': close_price,
                'GAIN_PERCENT': gain_percent
            })
        return pd.DataFrame(gain_data)

    # Calculate gains based on filtered data
    df_daywise = calculate_daywise_gain(df_filtered, days)
    df_final_filtered = df_daywise[df_daywise['GAIN_PERCENT'] >= gain_threshold]

    # Merge with yesterday_open_price to add YESTERDAY_OPEN_PRICE column
    df_final_filtered = df_final_filtered.merge(yesterday_open_price, on='SYMBOL', how='left')

    # Add Serial Number column after all filters are applied
    df_final_filtered = df_final_filtered.reset_index(drop=True)
    df_final_filtered.insert(0, 'S.No', range(1, len(df_final_filtered) + 1))

    # Display Table with YESTERDAY_OPEN_PRICE included
    st.dataframe(df_final_filtered[['S.No', 'SECURITY', 'SYMBOL', 'LOW_PRICE', 'CLOSE_PRICE', 'YESTERDAY_OPEN_PRICE', 'GAIN_PERCENT']])

    # Plot Bar Chart
    fig = px.bar(
        df_final_filtered,
        x='SECURITY',
        y='GAIN_PERCENT',
        title=f"Equities with High Gains over {days} Days",
        hover_data=['SYMBOL', 'LOW_PRICE', 'CLOSE_PRICE', 'YESTERDAY_OPEN_PRICE']
    )
    st.plotly_chart(fig)

    # Candlestick Chart
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

# Run the app
if __name__ == "__main__":
    run_app()