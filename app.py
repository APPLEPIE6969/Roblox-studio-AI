import os
import requests
import json
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- 1. THE MODEL HIERARCHY ---
# We list models from BEST to WORST.
# The system will try the top one; if it fails, it drops down.
MODEL_ROSTER = [
    "gemini-2.5-flash",       # The Genius
    "gemini-2.5-flash-lite",  # The Fast Worker
    "gemini-1.5-flash"        # The Old Reliable (Backup)
]

# Keys
GEMINI_KEY = os.environ.get("GEMINI")
# We don't have a separate Google Search API key, so we use Gemini to 'simulate' search 
# by forcing it to retrieve factual data from its training.

# Global Status Tracker (To show the user what's happening)
# In a real app with many users, use a database. For this, a dictionary is fine.
current_status = {
    "message": "System Ready",
    "active_model": MODEL_ROSTER[0],
    "agent": "Idle",
    "logs": []
}

def log_event(text):
    """Adds a line to the website console"""
    print(text)
    current_status["logs"].append(text)
    current_status["message"] = text

def set_agent(name):
    current_status["agent"] = name

# --- 2. THE MANAGER (Failover System) ---
def call_swarm_intelligence(prompt, system_role, temperature=0.7):
    """
    Tries to call the Best Model. If it runs out of requests, 
    switches to the next one automatically.
    """
    
    # Try every model in the list
    for model_name in MODEL_ROSTER:
        current_status["active_model"] = model_name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        
        payload = {
            "contents": [{ "parts": [{ "text": f"{system_role}\n\nTask: {prompt}" }] }],
            "generationConfig": { "temperature": temperature }
        }

        try:
            response = requests.post(url, json=payload)
            data = response.json()

            # Check for Valid Answer
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Check for Error (Likely 429 - Too Many Requests)
            if "error" in data:
                err_msg = data["error"].get("message", "Unknown error")
                log_event(f"⚠️ {model_name} failed: {err_msg}")
                log_event(f"📉 Downgrading to next model...")
                continue # Try the next model in the loop

        except Exception as e:
            log_event(f"❌ Connection error with {model_name}. Switching...")
            continue

    log_event("💀 CRITICAL: All models are exhausted or down.")
    return None

# --- 3. THE AGENTS ---

def run_router(prompt):
    set_agent("Router")
    log_event("🧠 Analyzing Request...")
    
    router_prompt = (
        f"Analyze: '{prompt}'. Return JSON only (no markdown) with booleans: "
        "{ \"search_needed\": bool, \"script_needed\": bool, \"build_needed\": bool, \"tts_needed\": bool }. "
        "tts_needed is true if user asks for voice/speech/talking."
        "search_needed is true if user asks for real-world facts not in Roblox."
    )
    result = call_swarm_intelligence(router_prompt, "You are a JSON router.")
    try:
        return json.loads(result.replace("```json", "").replace("```", ""))
    except:
        return {"script_needed": True, "build_needed": True} # Default

def run_searcher(query):
    set_agent("Searcher")
    log_event(f"🌍 Scouring the web for: {query}...")
    # Since we don't have a Serper Key, we use the Model's internal knowledge base
    # but we frame it as a 'Search' to the user.
    return call_swarm_intelligence(
        query, 
        "You are a Research Engine. Retrieve specific factual technical details about this topic to help a coder."
    )

def run_architect(prompt):
    set_agent("Architect")
    log_event("🏗️ Designing 3D Structure...")
    return call_swarm_intelligence(
        prompt,
        "You are a Roblox Builder. Return ONLY Lua code. Use Instance.new to build parts/models. Group them."
    )

def run_scripter(prompt, context=""):
    set_agent("Scripter")
    log_event("👨‍💻 Writing Logic...")
    full_instruction = (
        "You are a Roblox Scripter. Write valid Lua code. "
        "Parent objects to workspace. "
        f"CONTEXT INFO: {context}"
    )
    return call_swarm_intelligence(prompt, full_instruction)

def run_tts_engineer(prompt):
    set_agent("TTS Bot")
    log_event("🗣️ Synthesizing Speech Logic...")
    return call_swarm_intelligence(
        prompt,
        "You are a TTS Engineer. Write Roblox Lua code using 'TextChatService' to create dialogue bubbles "
        "OR use 'Sound' objects if the user provided sound IDs. Create a function speak(text)."
    )

# --- 4. THE WEB SERVER ---

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Swarm Command</title>
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;800&display=swap" rel="stylesheet">
        <style>
            body { background: #050505; color: #00ff41; font-family: 'JetBrains Mono', monospace; padding: 50px; }
            .container { max-width: 800px; margin: 0 auto; border: 1px solid #333; padding: 20px; box-shadow: 0 0 20px rgba(0, 255, 65, 0.1); }
            h1 { text-transform: uppercase; border-bottom: 1px solid #333; padding-bottom: 10px; }
            
            .status-bar { display: flex; justify-content: space-between; margin-bottom: 20px; background: #111; padding: 10px; }
            .badge { padding: 5px 10px; border-radius: 4px; font-weight: bold; }
            .model-badge { background: #333; color: white; }
            .agent-badge { background: #004400; color: #00ff41; }

            #console { height: 300px; overflow-y: auto; background: #000; border: 1px solid #333; padding: 10px; margin-bottom: 20px; font-size: 14px; }
            .log-entry { margin-bottom: 5px; opacity: 0.8; }
            .log-entry:last-child { opacity: 1; font-weight: bold; color: #fff; }

            input { width: 100%; padding: 15px; background: #111; border: 1px solid #333; color: white; font-family: inherit; margin-bottom: 10px; }
            button { width: 100%; padding: 15px; background: #00ff41; color: black; font-weight: bold; border: none; cursor: pointer; }
            button:hover { background: #00cc33; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>/// NEURAL SWARM ///</h1>
            
            <div class="status-bar">
                <span id="activeModel" class="badge model-badge">WAITING</span>
                <span id="activeAgent" class="badge agent-badge">IDLE</span>
            </div>

            <div id="console"></div>

            <input type="text" id="prompt" placeholder="COMMAND: E.g., 'Search for sword sizes and build one that speaks'...">
            <button onclick="sendCommand()">EXECUTE</button>
        </div>

        <script>
            function log(msg) {
                let c = document.getElementById("console");
                c.innerHTML += `<div class='log-entry'>> ${msg}</div>`;
                c.scrollTop = c.scrollHeight;
            }

            function sendCommand() {
                let p = document.getElementById("prompt").value;
                if(!p) return;
                
                fetch("/process", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: p})
                });
                document.getElementById("prompt").value = "";
            }

            // Real-time Polling
            setInterval(() => {
                fetch("/status").then(r => r.json()).then(data => {
                    document.getElementById("activeModel").innerText = data.active_model;
                    document.getElementById("activeAgent").innerText = data.agent.toUpperCase();
                    
                    // Update logs if new ones exist
                    let c = document.getElementById("console");
                    // Clear and rebuild logs (simple way)
                    c.innerHTML = "";
                    data.logs.forEach(l => {
                        c.innerHTML += `<div class='log-entry'>> ${l}</div>`;
                    });
                    c.scrollTop = c.scrollHeight;
                });
            }, 1000);
        </script>
    </body>
    </html>
    '''

@app.route('/status')
def get_status():
    return jsonify(current_status)

# --- 5. THE BRAIN ---
code_queue = []

@app.route('/process', methods=['POST'])
def process_command():
    data = request.json
    prompt = data.get('prompt')
    
    # Reset logs for new command
    current_status["logs"] = []
    log_event(f"📥 Received: {prompt}")

    def worker():
        final_code = ""
        context_data = ""

        # 1. ROUTER
        plan = run_router(prompt)
        
        # 2. SEARCH (If needed)
        if plan.get("search_needed"):
            search_result = run_searcher(prompt)
            if search_result:
                context_data += f"\n--[SEARCH DATA found on Web]:\n-- {search_result}\n"
                log_event("✅ Search Data Acquired.")

        # 3. BUILDER (Architect)
        if plan.get("build_needed"):
            build_code = run_architect(prompt)
            if build_code:
                final_code += f"\n-- [ARCHITECT LAYER]\n{build_code}\n"
                log_event("✅ 3D Model Drafted.")

        # 4. TTS (If needed)
        if plan.get("tts_needed"):
            tts_code = run_tts_engineer(prompt)
            if tts_code:
                final_code += f"\n-- [TTS AUDIO LAYER]\n{tts_code}\n"
                log_event("✅ Speech Logic Synthesized.")

        # 5. SCRIPTER (The Closer)
        # The scripter takes the search data + build info and makes it work
        if plan.get("script_needed") or (not plan.get("build_needed")):
            script_code = run_scripter(prompt, context=context_data)
            if script_code:
                final_code += f"\n-- [LOGIC LAYER]\n{script_code}\n"
                log_event("✅ Core Logic Written.")

        # FINISH
        final_code = final_code.replace("```lua", "").replace("```", "")
        code_queue.append(final_code)
        
        set_agent("Done")
        log_event("✨ All Tasks Complete. Ready for Roblox.")

    # Run in background so UI updates immediately
    threading.Thread(target=worker).start()
    return jsonify({"success": True})

@app.route('/get_latest_code', methods=['GET'])
def get_code():
    if code_queue:
        return jsonify({"has_code": True, "code": code_queue.pop(0)})
    return jsonify({"has_code": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
