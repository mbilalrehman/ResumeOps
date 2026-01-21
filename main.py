import json
import os
import re
import threading
import queue
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from dotenv import load_dotenv
from flask import Response, stream_with_context # Zaroori for streaming
from resume_worker import run_worker_cycle # <-- YEH IMPORT HAI (Logic yahan nahi, wahan hai)
from resume_worker import run_worker_cycle

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')

app = Flask(__name__)

# Yeh variable control karega ke automation chalni chahiye ya nahi
# --- GLOBAL VARIABLES FOR THREADING ---
log_queue = queue.Queue()
stop_event = threading.Event()
worker_thread = None
AUTOMATION_ACTIVE = False
# --- CONFIGURATION ---
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def load_data():
    try:
        with open('data/profile.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return None

# ---------------- FORCE FORMATTER (ZERO-FAIL VERSION) ----------------
def force_fix_casing(text):
    """
    Sabse aggressive replacement logic taake CI/CD aur IaC hamesha perfect hon.
    """
    if not isinstance(text, str):
        return text

    # 1. CI/CD Fix (Handles: ci/cd, cicd, ci-cd, ci cd with any casing)
    text = re.sub(r'ci[/ \-]?cd', 'CI/CD', text, flags=re.IGNORECASE)
    
    # 2. IaC Fix
    text = re.sub(r'\biac\b', 'IaC', text, flags=re.IGNORECASE)
    text = re.sub(r'Infrastructure As Code', 'Infrastructure as Code', text, flags=re.IGNORECASE)
    
    # 3. Common DevOps Terms
    text = re.sub(r'\baws\b', 'AWS', text, flags=re.IGNORECASE)
    text = re.sub(r'\bdevops\b', 'DevOps', text, flags=re.IGNORECASE)
    text = re.sub(r'\bkubernetes\b', 'Kubernetes', text, flags=re.IGNORECASE)
    text = re.sub(r'\bk8s\b', 'K8s', text, flags=re.IGNORECASE)
    text = re.sub(r'\bgithub actions\b', 'GitHub Actions', text, flags=re.IGNORECASE)
    text = re.sub(r'\bgitlab\b', 'GitLab', text, flags=re.IGNORECASE)

    return text

def smart_format_skills(ai_skills):
    """
    AI ke output ko scan karta hai aur har key aur value ko force-fix karta hai.
    """
    cleaned_skills = {}
    for category, tools in ai_skills.items():
        # Category (Key) ko fix karein
        clean_category = force_fix_casing(category.strip())
        
        # Tools (Value) ko fix karein
        clean_tools = force_fix_casing(tools.strip())
        
        cleaned_skills[clean_category] = clean_tools
    return cleaned_skills

def get_ai_content(master_data, job_description):
    system_prompt = """
    You are an expert Executive Resume Writer. 
    
    GOALS:
    1. **Job Title Extraction (CRITICAL):** Identify the EXACT Job Title from the JD (e.g., 'Site Reliability Engineer'). Use this for the 'job_title_extracted' field.
    2. **Content Richness (Target 2 Pages):** Write a **highly detailed, dense, and rich resume**. 
       - Do NOT be concise.
       - Expand every bullet point to 1-2 lines using the STAR method.
    3. **Keyword Optimization:** Extract EVERY technical keyword from the JD. Naturally integrate them into the Summary, Skills, and Experience.

    TASKS:
    - **Summary:** Start with the extracted Job Title. Make it impactful and keyword-heavy.
    - **Experience:** - Focus on "What, How, and Result". 
       - Add technical depth (tools, metrics, percentages) to every point.
       - Ensure the text fills the lines to maximize length while remaining professional.
    - **Skills:** Use professional categories (e.g., 'Observability', 'Cloud Platforms') and make sure projects skils also include.
    """

    user_prompt = f"""
    --- MASTER RESUME DATA ---
    {json.dumps(master_data.get('skills', {}))}
    {json.dumps(master_data.get('experience', []))}
    
    --- TARGET JOB DESCRIPTION ---
    {job_description}

    --- OUTPUT FORMAT (JSON) ---
    {{
        "job_title_extracted": "Extracted Job Title Here",
        "summary": "Detailed tailored summary...",
        "skills": {{
            "Cloud Platforms": "List...",
            "CI/CD": "List...",
            "Infrastructure as Code": "List...",
            "Category Name X": "Tool, Tool, Tool"
        }},
        "experience": [ 
            {{
                "company": "...", "role": "...", "location": "...", "date": "...", 
                "points": ["Long detailed point 1...", "Long detailed point 2...", "Long detailed point 3..."]
            }} 
        ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
            temperature=0.85 # Thora high rakha hai taake creative aur lamba likhe
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- WEB ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    jd_text = data.get('jd', '')
    
    if not jd_text:
        return jsonify({"status": "error", "message": "No JD provided"})

    master_data = load_data()
    
    # 1. Get AI Content
    ai_response = get_ai_content(master_data, jd_text)
    if not ai_response:
        return jsonify({"status": "error", "message": "AI Generation Failed"})

    # 2. Merge and Clean
    final_data = master_data.copy()
    final_data['summary'] = ai_response.get('summary', master_data['summary'])
    final_data['experience'] = ai_response.get('experience', master_data['experience'])
    
    # Force-fix the skills dictionary
    raw_skills = ai_response.get('skills', {})
    final_data['skills'] = smart_format_skills(raw_skills)

    # 3. PDF Generation & Filename Fix
    # AI se title lein. Agar AI ne title nahi diya to 'Tailored_Resume' use hoga.
    raw_title = ai_response.get('job_title_extracted', 'Tailored_Resume')
    
    # Filename ko safe banayein (Special chars remove karein)
    safe_filename = re.sub(r'[^a-zA-Z0-9_]', '_', raw_title)
    pdf_filename = f"{safe_filename}.pdf"

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('resume.html')
    rendered_html = template.render(**final_data)
    
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        
    # Save using Absolute Path
    pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)
    HTML(string=rendered_html, base_url='templates').write_pdf(pdf_path)
    # --- FIX ENDS HERE ---
    
    # Return JSON with dynamic filename
    return jsonify({
        "status": "success", 
        "pdf_url": f"/download/{pdf_filename}", 
        "job_title": raw_title
    })


# --- DEBUGGING DOWNLOAD FUNCTION ---
@app.route('/download/<path:filename>')
def download_pdf(filename):
    # 1. Force Hardcoded Path for Docker (Safety Net)
    # Docker mein path hamesha '/app/output' hi hota hai
    DOCKER_OUTPUT_PATH = '/app/output'
    
    print("\n" + "="*30)
    print(f"🔍 DEBUG REQUEST: {filename}")
    print(f"📂 Searching in: {DOCKER_OUTPUT_PATH}")
    
    # 2. Check: Kya folder exist karta hai?
    if not os.path.exists(DOCKER_OUTPUT_PATH):
        print("❌ ERROR: Output folder missing!")
        return jsonify({"error": "Output directory missing on server"}), 500
        
    # 3. List All Files (Sabse Important Step)
    files_in_folder = os.listdir(DOCKER_OUTPUT_PATH)
    print(f"📄 Files actually present: {files_in_folder}")
    
    # 4. Check: Kya hamari file wahan hai?
    if filename not in files_in_folder:
        print(f"❌ ERROR: File '{filename}' wahan nahi hai.")
        print("   (Shayad naam match nahi ho raha?)")
        return jsonify({
            "error": "File not found",
            "available_files": files_in_folder, # Browser mein dikhayega ke kya para hai
            "searched_for": filename
        }), 404

    print("✅ SUCCESS: File mil gayi! Sending...")
    return send_from_directory(DOCKER_OUTPUT_PATH, filename, as_attachment=True)

# --- AUTOMATION ROUTE ---
@app.route('/stream-worker')
def stream_worker():
    global worker_thread, stop_event

    # 1. Reset State
    while not log_queue.empty():
        log_queue.get()
    stop_event.clear()

    # 2. Start Background Thread (Only if not already running)
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=worker_wrapper)
        worker_thread.daemon = True # Ensures thread dies if main app dies
        worker_thread.start()

    # 3. Stream Logs from Queue (Non-blocking)
    def generate():
        while True:
            # Check if thread is dead and queue is empty
            if (worker_thread is None or not worker_thread.is_alive()) and log_queue.empty():
                yield "data: DONE\n\n"
                break
            
            try:
                # Wait for new log with timeout to keep connection alive
                message = log_queue.get(timeout=1.0)
                yield message
            except queue.Empty:
                # Send heartbeat or just continue check
                yield ": keep-alive\n\n"
                continue

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/stop-worker', methods=['POST'])
def stop_worker():
    global stop_event
    # Set the Stop Event flag
    stop_event.set()
    print("🛑 Stop Signal Sent to Background Thread.")
    return jsonify({"status": "stopping"})

def worker_wrapper():
    """
    Background thread function that runs the worker cycle.
    It captures logs and puts them into the queue for the frontend.
    """
    # Define a check function to pass to the worker
    def is_active():
        return not stop_event.is_set()

    # Run the worker and capture its generator output
    for log_message in run_worker_cycle(is_active_check=is_active):
        log_queue.put(log_message)
    
    # Signal that we are done
    log_queue.put("data: DONE\n\n")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)