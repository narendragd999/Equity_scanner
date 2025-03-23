import os
import zipfile
import pandas as pd
import re
import shutil
import streamlit as st

def extract_date(folder_name):
    match = re.search(r"(\d{2})(\d{2})(\d{2})$", folder_name.split(".")[0])  # Extract last 6 digits
    if match:
        day, month, year = match.groups()
        year = "20" + year if int(year) <= 50 else "19" + year  # Ensure correct year
        month_names = {
            "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR", "05": "MAY", "06": "JUN",
            "07": "JUL", "08": "AUG", "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"
        }
        month = month_names.get(month, month)
        return f"{day}-{month}-{year}"
    return ""

# Streamlit UI
st.title("📊 Options Scanner ZIP Tool")

# Directory path
source_folder = "zip"
output_folder = "output"
merged_file_path = os.path.join(output_folder, "merged_output.csv")

os.makedirs(output_folder, exist_ok=True)
merged_data = []

# Extract and process all ZIP files in the folder
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
                    
                    # Apply script logic: Remove columns A, B, C and J to P
                    df.drop(df.columns[[0, 1] + list(range(9, 16))], axis=1, inplace=True)
                    
                    # Add DATE column
                    df["DATE"] = formatted_date
                    
                    merged_data.append(df)
        
        shutil.rmtree(extract_folder)

if merged_data:
    final_df = pd.concat(merged_data, ignore_index=True)
    final_df.to_csv(merged_file_path, index=False)
    st.success(f"✅ Merged CSV saved at: {merged_file_path}")
    st.download_button(label="Download Merged CSV", data=final_df.to_csv(index=False).encode('utf-8'), file_name="merged_output.csv")
else:
    st.warning("No valid CSV files found for processing.")
