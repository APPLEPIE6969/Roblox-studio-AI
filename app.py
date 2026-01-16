import os
import requests
import json
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI")

# WE ASSIGN JOBS TO YOUR SPECIFIC MODELS
# 1. Lite = Fast Router
MODEL_ROUTER = "gemini-2.5-flash-lite" 
# 2. Flash = The Hard Worker (Drafter)
MODEL_WORKER = "gemini-2.5-flash"
# 3. 3-Flash = The Smart Boss (Reviewer)
MODEL_BOSS = "gemini-3-flash" 

# Fallback list in case the Boss is busy (Error 429)
FALLBACK_CHAIN = [MODEL_BOSS, MODEL_WORKER, MODEL_ROUTER]

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

# --- THE CORE AI ENGINE ---
def call_specific_model(model_name, prompt, system_role):
    """
    Calls a specific model from your list. 
    If it fails, it tries the next best one in the chain.
    """
    # Create a priority list starting with the requested model
    priority_list = [model_name] + [m for m in FALLBACK_CHAIN if m != model_name]
    
    for model in priority_list:
        current_status["active_model"] = model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        payload = { "contents": [{ "parts": [{ "text": f"{system_role}\n\nTask: {prompt}" }] }] }
        
        try:
            r = requests.post(url, json=payload)
            data = r.json()
            
            # Success?
            if "candidates" in data: 
                return data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Error? (Rate limit / overload)
            if "error" in data:
                log_event(f"⚠️ {model} Busy/Error. Switching to backup...")
                continue # Try next in list
                
        except Exception as e:
            continue
            
    return None

# --- THE SELF-REFLECTION LOOP (The "Brain") ---
def generate_with_reflection(prompt, role, deep_think=False):
    
    # 1. First Draft -> Uses 2.5 Flash (The Worker)
    log_event(f"📝 Drafting with {MODEL_WORKER}...")
    draft_code = call_specific_model(MODEL_WORKER, prompt, role)
    
    if not deep_think or not draft_code:
        return draft_code

    # 2. The Critique -> Uses 3.0 Flash (The Boss)
    log_event(f"🤔 Deep Think: {MODEL_BOSS} is reviewing the code...")
    critique_prompt = (
        f"You are a Senior Roblox Code Reviewer. Look at this Lua code:\n\n{draft_code}\n\n"
        f"The user asked for: '{prompt}'.\n"
        "Identify logic errors, physics issues, or deprecated methods. "
        "If it is perfect, reply ONLY: 'PERFECT'. "
        "Otherwise, list the specific fixes needed."
    )
    critique = call_specific_model(MODEL_BOSS, critique_prompt, "You are a critical expert reviewer.")

    if critique and "PERFECT" in critique.upper():
        log_event("✅ Deep Think: Code approved by Boss.")
        return draft_code
    
    # 3. The Refinement -> Uses 3.0 Flash (The Boss fixes it)
    log_event(f"🔧 Deep Think: Optimizing logic based on review...")
    fix_prompt = (
        f"Original Request: {prompt}\n"
        f"Draft Code: {draft_code}\n"
        f"Reviewer Feedback: {critique}\n\n"
        "Rewrite the Lua code completely to fix these issues. Return ONLY the code."
    )
    final_code = call_specific_model(MODEL_BOSS, fix_prompt, role)
    return final_code

# --- THE AGENTS ---
def run_architect(prompt, deep_think):
    current_status["agent"] = "Architect"
    instruction = (
        "You are a Roblox Builder. You cannot upload meshes. "
        "Build the requested object using ONLY Instance.new('Part'). "
        "Set Size, Position, Color, Anchored = true. Group into a Model. "
        "Do NOT use 'smoothplastic' as a material enum (use Enum.Material.Plastic). "
        "Return ONLY Lua."
    )
    return generate_with_reflection(prompt, instruction, deep_think)

def run_scripter(prompt, context, deep_think):
    current_status["agent"] = "Scripter"
    instruction = (
        f"You are a Roblox Scripter. Write valid Lua code. Context: {context}. "
        "Ensure all variables are defined. Return ONLY Lua."
    )
    return generate_with_reflection(prompt, instruction, deep_think)

def run_router(prompt):
    # Uses 2.5 Flash Lite (The Scout) for speed
    instruction = "Decide if this request needs a Build, a Script, or Both. JSON format."
    # (Simplified for this version to just return true/false context)
    return True # We default to doing both for robustness

# --- WEB SERVER (Polished UI) ---
code_queue = []

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Neural Architect 3.0</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #050508;
                --card-bg: rgba(20, 20, 30, 0.6);
                --glass-border: rgba(255, 255, 255, 0.08);
                --primary: #00f2ea;
                --primary-glow: rgba(0, 242, 234, 0.4);
                --secondary: #7000ff;
                --secondary-glow: rgba(112, 0, 255, 0.4);
                --text: #ffffff;
                --text-dim: #8888aa;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; outline: none; }

            body {
                background: var(--bg);
                color: var(--text);
                font-family: 'Outfit', sans-serif;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
                position: relative;
            }

            /* --- ANIMATED BACKGROUND --- */
            .orb { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.4; z-index: -1; animation: float 10s infinite alternate ease-in-out; }
            .orb-1 { width: 500px; height: 500px; background: var(--secondary); top: -10%; left: -10%; }
            .orb-2 { width: 400px; height: 400px; background: var(--primary); bottom: -10%; right: -10%; animation-delay: 2s; }
            @keyframes float { 0% { transform: translate(0,0); } 100% { transform: translate(30px, 30px); } }

            /* --- MAIN CARD --- */
            .interface {
                width: 90%;
                max-width: 480px;
                background: var(--card-bg);
                backdrop-filter: blur(24px);
                -webkit-backdrop-filter: blur(24px);
                border: 1px solid var(--glass-border);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 20px 50px rgba(0,0,0,0.4);
                transform: translateY(20px);
                opacity: 0;
                animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            }

            @keyframes slideUp { to { transform: translateY(0); opacity: 1; } }

            /* --- HEADER --- */
            h1 {
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                letter-spacing: -0.5px;
                background: linear-gradient(135deg, #fff 0%, #aaa 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .status-indicator { width: 8px; height: 8px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 10px var(--primary); animation: pulse 2s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            
            p.subtitle { color: var(--text-dim); font-size: 14px; margin-bottom: 32px; font-weight: 300; }

            /* --- INPUT --- */
            .input-wrapper { position: relative; margin-bottom: 24px; }
            input[type="text"] {
                width: 100%;
                background: rgba(0,0,0,0.3);
                border: 2px solid var(--glass-border);
                padding: 18px;
                border-radius: 16px;
                color: #fff;
                font-size: 16px;
                font-family: 'Outfit', sans-serif;
                transition: all 0.3s ease;
            }
            input:focus { border-color: var(--primary); box-shadow: 0 0 20px var(--primary-glow); transform: translateY(-2px); }
            input::placeholder { color: rgba(255,255,255,0.2); }

            /* --- TOGGLE --- */
            .controls { display: flex; align-items: center; justify-content: space-between; margin-bottom: 30px; background: rgba(255,255,255,0.03); padding: 12px 16px; border-radius: 14px; border: 1px solid var(--glass-border); }
            .label-group { display: flex; flex-direction: column; }
            .label-title { font-size: 14px; font-weight: 500; color: #fff; }
            .label-desc { font-size: 12px; color: var(--text-dim); margin-top: 2px; }

            .switch { position: relative; width: 50px; height: 28px; }
            .switch input { opacity: 0; width: 0; height: 0; }
            .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #333; transition: .4s; border-radius: 34px; }
            .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
            
            input:checked + .slider { background-color: var(--secondary); }
            input:checked + .slider:before { transform: translateX(22px); }
            input:checked ~ .slider { box-shadow: 0 0 15px var(--secondary-glow); }

            /* --- BUTTON --- */
            button {
                width: 100%;
                padding: 18px;
                border: none;
                border-radius: 16px;
                background: linear-gradient(135deg, var(--primary) 0%, #00c2bb 100%);
                color: #000;
                font-size: 16px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                box-shadow: 0 10px 20px rgba(0, 242, 234, 0.2);
            }
            button:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 15px 30px rgba(0, 242, 234, 0.4); }
            button:active { transform: scale(0.95); }
            button.loading { background: #333; color: #666; cursor: not-allowed; pointer-events: none; box-shadow: none; }

            /* --- CONSOLE --- */
            .console-window {
                margin-top: 30px;
                background: #08080c;
                border-radius: 12px;
                padding: 15px;
                height: 160px;
                overflow-y: auto;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                border: 1px solid var(--glass-border);
                position: relative;
            }
            .console-window::-webkit-scrollbar { width: 5px; }
            .console-window::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
            
            .log-entry { 
                margin-bottom: 6px; 
                opacity: 0; 
                animation: fadeIn 0.3s forwards; 
                display: flex;
                gap: 8px;
            }
            .log-time { color: #555; }
            .log-msg { color: #aaa; }
            .log-highlight { color: var(--primary); font-weight: bold; }
            @keyframes fadeIn { to { opacity: 1; transform: translateY(0); } from { opacity: 0; transform: translateY(5px); } }

        </style>
    </head>
    <body>

        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>

        <div class="interface">
            <h1><div class="status-indicator"></div> Neural Architect 3.0</h1>
            <p class="subtitle">Powered by Gemini 3.0 & 2.5 Swarm</p>

            <div class="input-wrapper">
                <input type="text" id="prompt" placeholder="Describe your build..." autocomplete="off">
            </div>

            <div class="controls">
                <div class="label-group">
                    <span class="label-title">Deep Think Mode</span>
                    <span class="label-desc" id="modeDesc">Review by Gemini 3.0</span>
                </div>
                <label class="switch">
                    <input type="checkbox" id="deepThink" onchange="toggleGlow()">
                    <span class="slider"></span>
                </label>
            </div>

            <button id="genBtn" onclick="send()">Initialize Generation</button>

            <div class="console-window" id="console">
                <div class="log-entry"><span class="log-time">[SYS]</span> <span class="log-msg">Ready for input...</span></div>
            </div>
        </div>

        <script>
            function log(txt, highlight=false) { 
                let c = document.getElementById("console");
                let time = new Date().toLocaleTimeString([], {hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit'});
                let cls = highlight ? "log-highlight" : "log-msg";
                
                let html = `<div class="log-entry">
                    <span class="log-time">[${time}]</span> 
                    <span class="${cls}">${txt}</span>
                </div>`;
                
                c.innerHTML += html;
                c.scrollTop = c.scrollHeight;
            }

            function toggleGlow() {
                let check = document.getElementById("deepThink").checked;
                let card = document.querySelector(".interface");
                let desc = document.getElementById("modeDesc");
                
                if(check) {
                    card.style.boxShadow = "0 20px 60px rgba(112, 0, 255, 0.3)";
                    card.style.borderColor = "rgba(112, 0, 255, 0.3)";
                    desc.innerText = "Boss Mode (Gemini 3.0) Active";
                    desc.style.color = "#d4b3ff";
                } else {
                    card.style.boxShadow = "0 20px 50px rgba(0,0,0,0.4)";
                    card.style.borderColor = "rgba(255, 255, 255, 0.08)";
                    desc.innerText = "Standard Swarm Mode";
                    desc.style.color = "#8888aa";
                }
            }

            function send() {
                let p = document.getElementById("prompt");
                let dt = document.getElementById("deepThink").checked;
                let btn = document.getElementById("genBtn");
                
                if(!p.value) {
                    p.style.borderColor = "#ff0055";
                    setTimeout(() => p.style.borderColor = "rgba(255,255,255,0.08)", 500);
                    return;
                }

                btn.innerText = "Processing...";
                btn.classList.add("loading");
                log("Assigning Agents...", true);
                
                fetch("/process", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: p.value, deep_think: dt})
                }).then(r => {
                    log("Request Queued.");
                    p.value = "";
                    setTimeout(() => {
                        btn.innerText = "Initialize Generation";
                        btn.classList.remove("loading");
                    }, 2000);
                });
            }

            // Status Loop
            setInterval(() => {
                fetch("/status").then(r=>r.json()).then(d => {
                    if(d.logs.length > 0) d.logs.forEach(l => log(l, true));
                });
            }, 1000);
        </script>
    </body>
    </html>
    '''

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    prompt = data.get('prompt')
    deep_think = data.get('deep_think', False)
    current_status["logs"] = []

    def task():
        # 1. Build
        build_code = run_architect(prompt, deep_think)
        # 2. Script
        script_code = run_scripter(prompt, "Object is built.", deep_think)
        
        final = ""
        if build_code: final += f"\n{build_code}\n"
        if script_code: final += f"\n{script_code}\n"
        
        clean = final.replace("```lua", "").replace("```", "")
        code_queue.append(clean)
        log_event("✨ Sequence Complete. Executing in Studio.")

    threading.Thread(target=task).start()
    return jsonify({"success": True})

@app.route('/status')
def status():
    l = list(current_status["logs"])
    current_status["logs"] = []
    return jsonify({"logs": l})

@app.route('/get_latest_code', methods=['GET'])
def get_code():
    if code_queue: return jsonify({"has_code": True, "code": code_queue.pop(0)})
    return jsonify({"has_code": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
