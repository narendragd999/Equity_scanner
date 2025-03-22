# api.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Path to the merged_output.csv file
MERGED_FILE_PATH = "output/merged_output.csv"

@app.get("/")
async def root():
    return {"message": "FastAPI server is running. Access the merged CSV at /api/merged-output"}

@app.get("/api/merged-output")
async def get_merged_output():
    # Check if the file exists
    if not os.path.exists(MERGED_FILE_PATH):
        raise HTTPException(status_code=404, detail="Merged output file not found")
    
    # Return the file as a downloadable response
    return FileResponse(
        path=MERGED_FILE_PATH,
        media_type="text/csv",
        filename="merged_output.csv"
    )