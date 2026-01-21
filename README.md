# ResumeOps
AI-Powered Resume Optimization Engine (SaaS) Technologies: Python, Flask, Docker, OpenAI/Gemini API, AWS.
=== ResumeOps AI Automation Engine (Full Automation Version) ===

HOW TO INSTALL & RUN:

1. CONFIGURATION SETUP (API Keys):
   -----------------------------------
   A. OpenAI API Key:
      - Rename the file '.env.example' to '.env'
      - Open it and paste your OpenAI API Key inside.

   B. Google Cloud Credentials (For Automation):
      - Place your 'credentials.json' file in this main folder.
      - Open 'credentials.json' and copy the "client_email" address inside it.
      - Go to your Google Sheet -> Click 'Share' -> Paste the email -> Give 'Editor' access.

2. RUN THE APP (Docker Required):
   *Ensure 'Docker Desktop' is open and running on your computer.*

   [FOR WINDOWS USERS]:
   - Double-click 'start_app.bat'
     (This will automatically build and start the system containers).

   [FOR MAC / LINUX USERS]:
   - Open Terminal in this folder.
   - Run this command to give permission (first time only):
     chmod +x start_app.sh
   - Then run the app:
     ./start_app.sh

3. USE THE APP:
   - Open your browser and go to: http://localhost:5000

   [NEW FEATURE - SHEET AUTOMATION]:
   - On the dashboard, click the purple "Run Sheet Automation" button.
   - You can watch the Live Logs as the system scans your Google Sheet and generates resumes automatically.

OUTPUT:
- All generated PDFs will be saved in the 'output' folder automatically.
- Download links will be pasted directly into your Google Sheet.
