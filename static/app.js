// DOM Elements
const jdInput = document.getElementById("jdInput");
const generateBtn = document.getElementById("generateBtn");
const consoleLogs = document.getElementById("consoleLogs");
const resultCard = document.getElementById("resultCard");
const downloadLink = document.getElementById("downloadLink");
const wordCountElement = document.getElementById("wordCount");
const jobTitleElement = document.getElementById("jobTitle");

// --- Helper Functions ---

// 1. Word Count & Job Title Detection
jdInput.addEventListener("input", function () {
  const text = jdInput.value.trim();
  const words = text.length > 0 ? text.split(/\s+/).length : 0;
  wordCountElement.textContent = words;

  if (words > 5) detectJobTitle(text);
});

function detectJobTitle(text) {
  const commonTitles = [
    "DevOps Engineer",
    "Software Engineer",
    "Frontend Dev",
    "Backend Dev",
    "Full Stack",
    "Cloud Architect",
  ];
  for (let title of commonTitles) {
    if (text.toLowerCase().includes(title.toLowerCase())) {
      jobTitleElement.textContent = title;
      break;
    }
  }
}

// 2. Logging Function (Visuals)
function log(message, type = "") {
  const now = new Date();
  const timestamp = `[${now.getHours().toString().padStart(2, "0")}:${now
    .getMinutes()
    .toString()
    .padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}]`;

  const logLine = document.createElement("div");
  logLine.className = `log-line ${type}`;
  logLine.innerHTML = `
        <div class="timestamp">${timestamp}</div>
        <i class="fa-solid fa-circle-${
          type.includes("success")
            ? "check"
            : type.includes("warning")
            ? "exclamation"
            : type.includes("error")
            ? "xmark"
            : "info"
        }"></i>
        <div>${message}</div>
    `;
  consoleLogs.appendChild(logLine);
  consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

function clearConsole() {
  consoleLogs.innerHTML = "";
}

// --- MAIN GENERATION LOGIC ---

async function startGeneration() {
  const jdText = jdInput.value.trim();

  if (!jdText) {
    alert("Please paste a Job Description first!");
    jdInput.focus();
    return;
  }

  // 1. UI Reset
  generateBtn.disabled = true;
  generateBtn.innerHTML =
    '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
  resultCard.classList.remove("visible");
  consoleLogs.innerHTML = "";

  // 2. Visual Logs (Start Fake Animation)
  log("Initializing ResumeOps Engine...", "text-info");
  setTimeout(() => log("Analyzing JD structure...", "text-warning"), 500);
  setTimeout(
    () => log(`Detected ${jdText.length} characters input`, "text-muted"),
    800
  );
  setTimeout(
    () => log("Extracting keywords (AWS, Kubernetes, CI/CD)...", "text-info"),
    1500
  );
  setTimeout(
    () => log("Connecting to OpenAI (gpt-4o)...", "text-warning"),
    2200
  );

  // 3. REAL API CALL
  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jd: jdText }),
    });

    const data = await response.json();

    if (data.status === "success") {
      // Success Logs
      setTimeout(() => {
        log("Content generated successfully!", "text-success");
        log("Rendering PDF with WeasyPrint...", "text-info");
      }, 2500);

      setTimeout(() => {
        log("Optimization Complete.", "text-success");

        // Update UI with REAL Download Link
        generateBtn.innerHTML =
          '<i class="fa-solid fa-check"></i> Process Complete';
        generateBtn.disabled = false;
        downloadLink.href = data.pdf_url; // Backend se URL aaya
        resultCard.classList.add("visible");
      }, 3500);
    } else {
      // Backend Error
      setTimeout(
        () => log(`Server Error: ${data.message}`, "text-error"),
        2500
      );
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Try Again';
    }
  } catch (error) {
    // Network Error
    setTimeout(
      () => log(`Network Error: ${error.message}`, "text-error"),
      2500
    );
    console.error(error);
    generateBtn.disabled = false;
    generateBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Try Again';
  }
}

// --- Reset / Clear Function ---
function resetApp() {
    jdInput.value = '';
    wordCountElement.textContent = '0';
    consoleLogs.innerHTML = '<div class="log-line text-info"><div class="timestamp">[System]</div><i class="fa-solid fa-circle-info"></i><div>Ready. Waiting for input...</div></div>';
    resultCard.classList.remove('visible');
    generateBtn.disabled = false;
    generateBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Initialize Tailoring Engine';
}

// --- AUTOMATION FEATURE ---

// --- UPDATED AUTOMATION LOGIC (WITH START/STOP) ---

let eventSource = null; // Global variable to control connection

function startAutomation() {
    const consoleLogs = document.getElementById('consoleLogs');
    const startBtn = document.getElementById('autoBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    // UI Updates
    startBtn.style.display = 'none'; // Hide Start
    stopBtn.style.display = 'inline-block'; // Show Stop
    
    consoleLogs.innerHTML = '';
    const startDiv = document.createElement('div');
    startDiv.className = 'log-line text-info';
    startDiv.innerHTML = `<div class="timestamp">[System]</div><i class="fa-solid fa-terminal"></i><div>Starting Automation Sequence...</div>`;
    consoleLogs.appendChild(startDiv);

    // Connect to Backend
    eventSource = new EventSource("/stream-worker");

    eventSource.onmessage = function(event) {
        const data = event.data;

        if (data === "DONE") {
            stopAutomation(); // Auto stop when done
            return;
        }

        const div = document.createElement('div');
        div.className = 'log-line text-warning';
        div.innerHTML = `<div class="timestamp">[Worker]</div><i class="fa-solid fa-gears"></i><div>${data}</div>`;
        consoleLogs.appendChild(div);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    };

    eventSource.onerror = function() {
        // Connection Error handling
        const div = document.createElement('div');
        div.className = 'log-line text-danger';
        div.innerHTML = `<div class="timestamp">[Error]</div><i class="fa-solid fa-triangle-exclamation"></i><div>Connection lost or stopped.</div>`;
        consoleLogs.appendChild(div);
        stopAutomation();
    };
}

function stopAutomation() {
    const startBtn = document.getElementById('autoBtn');
    const stopBtn = document.getElementById('stopBtn');

    // 1. Tell Server to Stop (New Step)
    fetch('/stop-worker', { method: 'POST' })
        .then(response => console.log("Stop signal sent to server"));

    // 2. Close Connection
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }

    // 3. UI Reset
    startBtn.style.display = 'inline-block';
    stopBtn.style.display = 'none';
    
    const consoleLogs = document.getElementById('consoleLogs');
    const div = document.createElement('div');
    div.className = 'log-line text-success';
    div.innerHTML = `<div class="timestamp">[System]</div><i class="fa-solid fa-check"></i><div>Process Stopped / Completed.</div>`;
    consoleLogs.appendChild(div);
}

// Helper function to ensure logs look consistent
function addToLog(source, message, cssClass) {
    const consoleLogs = document.getElementById('consoleLogs');
    const div = document.createElement('div');
    div.className = `log-line ${cssClass}`;
    div.innerHTML = `
        <div class="timestamp">${source}</div>
        <i class="fa-solid fa-terminal"></i>
        <div>${message}</div>
    `;
    consoleLogs.appendChild(div);
}
