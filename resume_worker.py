import gspread
import requests
import time
import datetime
import os
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# --- CONFIGURATION ---
SPREADSHEET_FILE_NAME = os.getenv("GOOGLE_SHEET_NAME", "Daily SMPM Jobs Aggregator")
RESUME_API_URL = "http://localhost:5000/generate" # Ab dono ek hi container mein hain (main.py)
SERVER_PUBLIC_IP = "http://localhost:5000"
COL_JOB_DESCRIPTION = "job_description"
COL_RESUME_LINK = "resume" 

def get_todays_tab_name():
    today = datetime.date.today()
    return f"Jobs_{today.strftime('%Y-%m-%d')}"

def connect_to_drive():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client

# Note: Humne 'is_active_check' argument add kiya hai
def run_worker_cycle(is_active_check=None):
    yield "data: 🚀 Initializing Automation Protocol...\n\n"
    time.sleep(1)

    try:
        # Stop Check 1
        if is_active_check and not is_active_check():
            yield "data: 🛑 Process Stopped by User.\n\n"
            yield "data: DONE\n\n"
            return

        gc = connect_to_drive()
        yield "data: 📡 Connecting to Google Drive API...\n\n"
        
        try:
            main_sheet = gc.open(SPREADSHEET_FILE_NAME)
            yield f"data: ✅ Found File: {SPREADSHEET_FILE_NAME}\n\n"
        except Exception:
            yield f"data: ❌ Error: File '{SPREADSHEET_FILE_NAME}' not found.\n\n"
            yield "data: DONE\n\n"
            return

        # Stop Check 2
        if is_active_check and not is_active_check(): yield "data: DONE\n\n"; return

        target_tab_name = get_todays_tab_name()
        yield f"data: 🔍 Searching for Tab: {target_tab_name}\n\n"

        try:
            worksheet = main_sheet.worksheet(target_tab_name)
            yield f"data: ✅ Target Tab Connected.\n\n"
        except Exception:
            yield f"data: ⚠️ Tab '{target_tab_name}' not found yet.\n\n"
            yield "data: DONE\n\n"
            return

        headers = worksheet.row_values(1)
        headers_lower = [h.lower().strip() for h in headers]
        
        if COL_RESUME_LINK.lower() not in headers_lower:
            yield f"data: ⚠️ Column '{COL_RESUME_LINK}' not found.\n\n"
            yield "data: DONE\n\n"
            return
        
        link_col_index = headers_lower.index(COL_RESUME_LINK.lower()) + 1
        records = worksheet.get_all_records()
        processed_count = 0

        for i, row in enumerate(records):
            # --- CRITICAL STOP CHECK (Har row par check karega) ---
            if is_active_check and not is_active_check():
                yield "data: 🛑 Automation Stopped Immediately.\n\n"
                yield "data: DONE\n\n"
                return
            # -----------------------------------------------------

            row_number = i + 2
            jd_text = row.get(COL_JOB_DESCRIPTION, "")
            actual_header_name = headers[link_col_index-1]
            current_link = row.get(actual_header_name, "")
            job_title = row.get("job_title", "Unknown Role")

            if jd_text and not current_link:
                yield f"data: ⚡ Processing Row {row_number}: {job_title}\n\n"
                
                try:
                    # Direct function calls are better but keeping API for consistency
                    response = requests.post(RESUME_API_URL, json={"jd": jd_text})
                    
                    if response.status_code == 200:
                        data = response.json()
                        full_link = f"{SERVER_PUBLIC_IP}{data.get('pdf_url')}"
                        worksheet.update_cell(row_number, link_col_index, full_link)
                        yield f"data: ✅ Resume Generated: {full_link}\n\n"
                        processed_count += 1
                    else:
                        yield f"data: ❌ Generation Failed: {response.text}\n\n"
                except Exception as e:
                    yield f"data: ❌ Error on Row {row_number}: {str(e)}\n\n"
        
        if processed_count == 0:
            yield "data: ✨ No new jobs pending processing.\n\n"
        else:
            yield f"data: 🎉 Batch Complete! {processed_count} resumes created.\n\n"

    except Exception as e:
        yield f"data: ❌ Critical Error: {str(e)}\n\n"

    yield "data: DONE\n\n"