import os
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
# We load both keys from the Render Environment Variables
GEMINI_KEY = os.environ.get("GEMINI")
MODEL_3D_KEY = os.environ.get("MODEL_3D")

# API URLs
# Note: We assume MODEL_3D uses an OpenAI-compatible structure (common for many AIs).
# If your 3D model AI uses a specific URL (like Meshy or Tripo), change the URL below.
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
MODEL_URL = "https://api.openai.com/v1/chat/completions" # REPLACE if your 3D AI has a different URL

# --- STORAGE ---
code_queue = []

# --- HELPER FUNCTIONS ---

def call_gemini(prompt, system_instruction=""):
    """Calls Gemini for Scripting/Logic"""
    full_prompt = f"{system_instruction}\n\nRequest: {prompt}"
    payload = { "contents": [{ "parts": [{ "text": full_prompt }] }] }
    try:
        response = requests.post(GEMINI_URL, json=payload)
        data = response.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini Error: {e}")
    return None

def call_model_ai(prompt):
    """Calls the 3D Model AI to generate Build Code"""
    # We ask the 3D AI to generate Lua code that 'draws' the object using Parts/Wedges.
    # This allows it to work instantly in Roblox without file uploads.
    system_prompt = (
        "You are a 3D Architect for Roblox. "
        "Do not write logic/scripts. "
        "Write ONLY Lua code to create a detailed 3D model using Instance.new('Part') or 'WedgePart'. "
        "Use mostly Unions or detailed Part positioning. "
        "Group the model into a Model folder. "
        "Return ONLY code."
    )
    
    # If your MODEL_3D key is for a specific service (like OpenAI), use this:
    headers = {
        "Authorization": f"Bearer {MODEL_3D_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-4o", # Or your specific 3D model name
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        # If your 3D AI uses a different format, change this request logic!
        response = requests.post(MODEL_URL, json=body, headers=headers)
        data = response.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Model AI Error: {e}")
        # Fallback: If 3D AI fails, ask Gemini to do the build
        return call_gemini(prompt, system_prompt)
    return None

def router(prompt):
    """Decides if we need a Script, a Model, or Both"""
    router_prompt = (
        f"Analyze this request: '{prompt}'. "
        "Return valid JSON with boolean keys: "
        "{ \"needs_script\": true/false, \"needs_model\": true/false }. "
        "Example: 'Make a car' -> needs_model: true, needs_script: true. "
        "'Kill player' -> needs_model: false, needs_script: true."
    )
    result = call_gemini(router_prompt)
    try:
        # Clean up JSON if the AI added markdown
        clean_json = result.replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except:
        # Default to both if unsure
        return {"needs_script": True, "needs_model": True}

# --- THE WEBSITE ---
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dual-Core AI Commander</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root { --primary: #7000ff; --secondary: #00f2ea; --bg: #050505; }
            body { font-family: 'Inter', sans-serif; background: var(--bg); color: white; display: flex; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }
            .glow { position: absolute; width: 600px; height: 600px; background: radial-gradient(circle, var(--primary) 0%, transparent 60%); opacity: 0.2; filter: blur(50px); animation: move 10s infinite alternate; }
            @keyframes move { from { transform: translate(-50px, -50px); } to { transform: translate(50px, 50px); } }
            .card { background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(20px); width: 400px; text-align: center; z-index: 2; box-shadow: 0 0 50px rgba(112, 0, 255, 0.2); }
            input { width: 100%; padding: 15px; background: rgba(0,0,0,0.4); border: 1px solid #333; color: white; border-radius: 10px; margin: 20px 0; font-size: 16px; }
            input:focus { border-color: var(--secondary); outline: none; box-shadow: 0 0 15px rgba(0, 242, 234, 0.3); }
            button { width: 100%; padding: 15px; background: linear-gradient(45deg, var(--primary), #a200ff); border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer; transition: 0.3s; }
            button:hover { transform: scale(1.02); box-shadow: 0 0 20px var(--primary); }
            #status { margin-top: 15px; font-size: 14px; color: #888; min-height: 20px; }
        </style>
    </head>
    <body>
        <div class="glow"></div>
        <div class="card">
            <h1>AI Architect</h1>
            <p style="color: #666; font-size: 14px;">Gemini (Logic) + Model_3D (Build)</p>
            <input type="text" id="prompt" placeholder="E.g., Make a spinning neon tower..." onkeypress="if(event.key==='Enter') send()">
            <button onclick="send()" id="btn">Generate</button>
            <p id="status"></p>
        </div>
        <script>
            function send() {
                let p = document.getElementById("prompt").value;
                let s = document.getElementById("status");
                let b = document.getElementById("btn");
                if(!p) return;
                
                b.disabled = true;
                b.innerText = "Analyzing...";
                s.innerText = "Routing Request...";
                
                fetch("/process", {
                    method: "POST", 
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: p})
                }).then(r=>r.json()).then(d=>{
                    if(d.success) {
                        s.innerText = "✓ Sent to Roblox!";
                        s.style.color = "#00f2ea";
                    } else {
                        s.innerText = "Error: " + d.error;
                        s.style.color = "red";
                    }
                    b.disabled = false;
                    b.innerText = "Generate";
                    document.getElementById("prompt").value = "";
                });
            }
        </script>
    </body>
    </html>
    '''

# --- BACKEND LOGIC ---
@app.route('/process', methods=['POST'])
def process():
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt: return jsonify({"success": False, "error": "Empty prompt"})

    # 1. ASK THE ROUTER: What do we need?
    plan = router(prompt)
    
    final_code = ""
    
    # 2. GENERATE MODEL (If needed)
    if plan.get("needs_model"):
        build_code = call_model_ai(prompt)
        if build_code:
            final_code += f"\n-- [AI GENERATED 3D MODEL]\n{build_code}\n"
        
    # 3. GENERATE SCRIPT (If needed)
    if plan.get("needs_script"):
        # We tell Gemini the model might already exist, so attach script to it
        context_prompt = prompt
        if plan.get("needs_model"):
            context_prompt += " (The 3D model is already built by another AI. Write a script that finds this model in workspace and applies the logic to it.)"
            
        script_code = call_gemini(context_prompt, "You are a Roblox Scripter. Write ONLY Lua code.")
        if script_code:
            final_code += f"\n-- [AI GENERATED LOGIC]\n{script_code}\n"

    # 4. CLEANUP
    if final_code:
        final_code = final_code.replace("```lua", "").replace("```", "")
        code_queue.append(final_code)
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "AI produced no code"})

@app.route('/get_latest_code', methods=['GET'])
def get_code():
    if code_queue:
        return jsonify({"has_code": True, "code": code_queue.pop(0)})
    return jsonify({"has_code": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
