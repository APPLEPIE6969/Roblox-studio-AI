import os
import requests
import json
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI")

# --- THE COMPLETE "OMNI-SWARM" ROSTER (Backend Logic) ---
MODELS = {
    "DIRECTOR": "gemini-3-flash",              # Logic & Review
    "SEARCH": "gemini-1.5-pro",                # Research/Facts
    "ROBOTICS": "gemini-robotics-er-1.5-preview", # Physics/Constraints
    "DIALOG": "gemini-2.5-flash-native-audio-dialog", # Natural Speech Patterns
    "AUDIO": "gemini-2.5-flash-tts",           # Sound Service Logic
    "CREATIVE": "gemma-3-27b-it",              # Lore/Story
    "WORKER": "gemini-2.5-flash",              # Building/General
    "SCOUT": "gemini-2.5-flash-lite"           # Routing
}

# Status Tracking
current_status = {
    "message": "System Ready",
    "active_model": "None",
    "agent": "Idle",
    "logs": []
}

def log_event(text, highlight=False):
    # We add a prefix so the UI knows it's a server message
    prefix = "✨ " if highlight else ""
    print(f"{prefix}{text}")
    current_status["logs"].append(text)
    current_status["message"] = text

# --- UNIVERSAL CALLER ---
def call_ai(model_key, prompt, system_role):
    model_name = MODELS.get(model_key, MODELS["WORKER"])
    current_status["active_model"] = model_name.upper()
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{ "parts": [{ "text": f"{system_role}\n\nSpecific Task: {prompt}" }] }]
    }

    try:
        r = requests.post(url, json=payload)
        data = r.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            log_event(f"⚠️ {model_name} Busy/Error: {data['error']['message']}. Switching to Worker...")
            return call_ai("WORKER", prompt, system_role)
    except Exception as e:
        log_event(f"❌ Connection Error on {model_name}: {str(e)}")
        return None

# --- SPECIALIST AGENTS (The Logic) ---

def run_router(prompt):
    log_event(f"🔍 [SCOUT] Analyzing request: '{prompt}'...")
    instruction = (
        "Analyze request. Return JSON with booleans:\n"
        "{ \"needs_search\": bool (true if asking for real world facts/specific items),\n"
        "\"needs_physics\": bool (true if moving parts/motors),\n"
        "\"needs_lore\": bool (true if story),\n"
        "\"needs_dialog\": bool (true if NPCs talking),\n"
        "\"needs_sound\": bool (true if sfx/music),\n"
        "\"needs_build\": bool }"
    )
    res = call_ai("SCOUT", instruction + f"\nRequest: {prompt}", "You are a JSON Router.")
    try:
        clean = res.replace("```json", "").replace("```", "")
        return json.loads(clean)
    except:
        return {"needs_build": True, "needs_search": True} 

def run_searcher(query):
    log_event(f"🌍 [SEARCHER] Retrieving data on: {query}...")
    instruction = "You are a Research Engine. Provide technical details (Color RGB, Size, Key Parts) for a Roblox Builder."
    return call_ai("SEARCH", query, instruction)

def run_robotics_engineer(prompt, context):
    log_event("⚙️ [ROBOTICS] Calculating constraints...")
    instruction = (
        f"You are a Robotics Engineer. Context: {context}. "
        "Write Roblox Lua for mechanical parts using HingeConstraint/Motor6D. Return ONLY Lua."
    )
    return call_ai("ROBOTICS", prompt, instruction)

def run_creative_writer(prompt):
    log_event("📖 [GEMMA] Drafting lore...")
    instruction = "You are a Creative Writer. Write a Lua script that creates Lore StringValues. Return ONLY Lua."
    return call_ai("CREATIVE", prompt, instruction)

def run_dialogue_coach(prompt):
    log_event("🗣️ [NATIVE-DIALOG] Formatting speech patterns...")
    instruction = (
        "You are a Dialogue Coach. Use your training in natural audio patterns to write a Lua Table of dialogue. "
        "Include fields for 'Text', 'Delay', and 'Emotion'. "
        "Make the text feel natural and conversational. Return ONLY Lua."
    )
    return call_ai("DIALOG", prompt, instruction)

def run_audio_engineer(prompt):
    log_event("🔊 [TTS-AUDIO] Designing soundscape...")
    instruction = "You are an Audio Director. Write Lua using TextChatService and SoundService. Return ONLY Lua."
    return call_ai("AUDIO", prompt, instruction)

def run_architect(prompt, context):
    log_event("🏗️ [WORKER] Building structure...")
    instruction = (
        f"You are a Builder. Context: {context}. "
        "Build using Instance.new('Part'). Group into a Model. Return ONLY Lua."
    )
    return call_ai("WORKER", prompt, instruction)

# --- BOSS REVIEW ---
def run_boss_review(code, prompt):
    log_event("🧐 [DIRECTOR] Reviewing code...")
    critique = call_ai("DIRECTOR", 
        f"Review this code:\n{code}\nRequest: {prompt}", 
        "Strict Code Reviewer. Reply 'PERFECT' or list errors."
    )
    
    if "PERFECT" not in critique.upper():
        log_event("🔧 [DIRECTOR] Fixing issues...")
        return call_ai("DIRECTOR", f"Fix these errors:\n{critique}\n\nCode:\n{code}", "Fix the code. Return ONLY Lua.")
    
    log_event("✅ [DIRECTOR] Approved.")
    return code

# --- WEB SERVER (The User's UI) ---
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
        final_code = ""
        context_data = ""
        
        # 1. SCOUT
        plan = run_router(prompt)
        
        # 2. SEARCH
        if plan.get("needs_search"):
            context_data = run_searcher(prompt)

        # 3. SPECIALISTS
        if plan.get("needs_physics"):
            final_code += f"\n-- [PHYSICS]\n{run_robotics_engineer(prompt, context_data)}\n"
        elif plan.get("needs_build"):
            final_code += f"\n-- [BUILD]\n{run_architect(prompt, context_data)}\n"

        if plan.get("needs_lore"):
            final_code += f"\n-- [LORE]\n{run_creative_writer(prompt)}\n"
        
        if plan.get("needs_dialog"):
            final_code += f"\n-- [DIALOGUE]\n{run_dialogue_coach(prompt)}\n"

        if plan.get("needs_sound"):
            final_code += f"\n-- [AUDIO]\n{run_audio_engineer(prompt)}\n"

        # 4. GENERAL LOGIC
        final_code += f"\n-- [LOGIC]\n{call_ai('WORKER', prompt, f'Main Script. Context: {context_data}. Object built.')}\n"

        # 5. BOSS REVIEW
        if deep_think:
            final_code = run_boss_review(final_code, prompt)
        
        clean = final_code.replace("```lua", "").replace("```", "")
        code_queue.append(clean)
        log_event("✨ Sequence Complete.")

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
