import os
import requests
import json
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
# ONLY ONE KEY NEEDED NOW (The Free One)
GEMINI_KEY = os.environ.get("GEMINI")

# Use the reliable 1.5 model to ensure it works
MODEL_ROSTER = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]

# Status Tracking
current_status = {
    "message": "System Ready",
    "active_model": "None",
    "agent": "Idle",
    "logs": []
}

def log_event(text):
    print(text)
    current_status["logs"].append(text)
    current_status["message"] = text

# --- THE MANAGER ---
def call_gemini_swarm(prompt, system_role):
    """
    Uses the free Gemini key for everything.
    """
    for model in MODEL_ROSTER:
        current_status["active_model"] = model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        
        payload = {
            "contents": [{ "parts": [{ "text": f"{system_role}\n\nUser Request: {prompt}" }] }]
        }

        try:
            response = requests.post(url, json=payload)
            data = response.json()
            
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            if "error" in data:
                log_event(f"⚠️ {model} Busy/Error. Switching...")
                continue
                
        except:
            continue
            
    return None

# --- THE AGENTS ---

def run_architect(prompt):
    # THIS IS THE FIX: We tell Gemini to build using PARTS, not meshes.
    current_status["agent"] = "Architect (Free Mode)"
    log_event(f"🏗️ Architect is coding the build for: {prompt}...")
    
    instruction = (
        "You are a Roblox Builder. You cannot upload meshes. "
        "You must build the requested object by writing Lua code that creates 'Part', 'WedgePart', or 'TrussPart'. "
        "Use Instance.new('Part'). "
        "Set the Size, CFrame (Position/Rotation), Color, and Material for every part. "
        "Group all parts into a Model folder. "
        "Example: Make a chair -> Create 4 legs and a seat using Parts."
        "Return ONLY Lua code."
    )
    return call_gemini_swarm(prompt, instruction)

def run_scripter(prompt, context):
    current_status["agent"] = "Scripter"
    log_event("👨‍💻 Scripter is writing logic...")
    instruction = (
        "You are a Roblox Scripter. Write valid Lua code. "
        "If an object was just built, write a script to make it interactive. "
        f"Context: {context}"
    )
    return call_gemini_swarm(prompt, instruction)

# --- WEB SERVER ---
code_queue = []

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Free AI Builder</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #1a1a1a; color: white; font-family: sans-serif; padding: 20px; text-align: center; }
            input { width: 80%; padding: 15px; border-radius: 5px; border: none; margin-top: 20px; }
            button { padding: 15px 30px; background: #007bff; color: white; border: none; border-radius: 5px; margin-top: 10px; cursor: pointer; }
            #console { background: black; padding: 15px; text-align: left; height: 200px; overflow-y: scroll; margin-top: 20px; font-family: monospace; color: #0f0; }
        </style>
    </head>
    <body>
        <h1>Roblox AI (Free Mode)</h1>
        <div id="console">System Ready...</div>
        <input type="text" id="prompt" placeholder="E.g., Build a glowing blue tree">
        <button onclick="send()">Build It</button>
        <script>
            function log(txt) { document.getElementById("console").innerHTML += "<div>> "+txt+"</div>"; }
            function send() {
                let p = document.getElementById("prompt").value;
                log("Sending: " + p);
                fetch("/process", {
                    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({prompt: p})
                });
                document.getElementById("prompt").value = "";
            }
            setInterval(() => {
                fetch("/status").then(r=>r.json()).then(d => {
                    if(d.logs.length > 0) {
                        d.logs.forEach(l => log(l));
                    }
                });
            }, 2000);
        </script>
    </body>
    </html>
    '''

@app.route('/process', methods=['POST'])
def process():
    prompt = request.json.get('prompt')
    current_status["logs"] = []
    
    def task():
        # 1. Build it (Using pure code)
        build_code = run_architect(prompt)
        
        # 2. Script it (Add logic)
        script_code = run_scripter(prompt, context="Object is built.")
        
        final = ""
        if build_code: final += f"\n-- BUILD --\n{build_code}\n"
        if script_code: final += f"\n-- SCRIPT --\n{script_code}\n"
        
        clean_final = final.replace("```lua", "").replace("```", "")
        code_queue.append(clean_final)
        log_event("✅ Done! Check Roblox.")

    threading.Thread(target=task).start()
    return jsonify({"status": "ok"})

@app.route('/status')
def status():
    logs = list(current_status["logs"])
    current_status["logs"] = [] # Clear sent logs
    return jsonify({"logs": logs})

@app.route('/get_latest_code', methods=['GET'])
def get_code():
    if code_queue: return jsonify({"has_code": True, "code": code_queue.pop(0)})
    return jsonify({"has_code": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
