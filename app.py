import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
# We get the key from the Environment Variable you set in the image
GEMINI_KEY = os.environ.get("GEMINI") 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

# --- STORAGE ---
# We now store the generated CODE, not just the prompt
code_queue = []

# --- THE WEBSITE (Same UI) ---
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Command Center</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root { --primary: #00f2ea; --secondary: #ff0055; --bg-dark: #0a0a0a; --glass: rgba(255, 255, 255, 0.05); }
            * { box-sizing: border-box; margin: 0; padding: 0; outline: none; }
            body { font-family: 'Inter', sans-serif; background-color: var(--bg-dark); color: white; height: 100vh; display: flex; justify-content: center; align-items: center; overflow: hidden; background: radial-gradient(circle at 50% 50%, #1a1a2e 0%, #000000 100%); }
            .blob { position: absolute; filter: blur(80px); z-index: -1; opacity: 0.6; animation: float 10s infinite ease-in-out; }
            .blob-1 { top: -10%; left: -10%; width: 500px; height: 500px; background: var(--secondary); animation-delay: 0s; }
            .blob-2 { bottom: -10%; right: -10%; width: 600px; height: 600px; background: var(--primary); animation-delay: 5s; }
            @keyframes float { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(30px, -30px); } }
            .container { width: 90%; max-width: 450px; background: var(--glass); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; padding: 40px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); text-align: center; }
            h1 { font-size: 28px; font-weight: 800; margin-bottom: 10px; background: linear-gradient(to right, #fff, #aaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .subtitle { font-size: 14px; color: rgba(255, 255, 255, 0.5); margin-bottom: 30px; }
            input { width: 100%; padding: 16px 20px; background: rgba(0, 0, 0, 0.3); border: 2px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: white; font-size: 16px; transition: all 0.3s ease; margin-bottom: 20px; }
            input:focus { border-color: var(--primary); background: rgba(0, 0, 0, 0.5); }
            button { width: 100%; padding: 16px; background: linear-gradient(135deg, var(--primary), #00a8a2); color: #000; font-weight: 800; border: none; border-radius: 12px; cursor: pointer; font-size: 16px; transition: all 0.2s ease; }
            button:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0, 242, 234, 0.4); }
            button:disabled { opacity: 0.5; cursor: not-allowed; }
            #status { margin-top: 20px; font-size: 14px; font-weight: 600; min-height: 20px; }
            .success { color: var(--primary); }
            .error { color: var(--secondary); }
        </style>
    </head>
    <body>
        <div class="blob blob-1"></div><div class="blob blob-2"></div>
        <div class="container">
            <h1>Roblox Architect</h1>
            <p class="subtitle">Server-Side AI Processing</p>
            <input type="text" id="cmd" placeholder="Describe your build..." onkeypress="if(event.key==='Enter') send()">
            <button id="sendBtn" onclick="send()">Send Command</button>
            <p id="status"></p>
        </div>
        <script>
            function send() {
                const input = document.getElementById("cmd");
                const btn = document.getElementById("sendBtn");
                const status = document.getElementById("status");
                const txt = input.value.trim();
                if (!txt) return;

                input.disabled = true;
                btn.disabled = true;
                btn.innerText = "Thinking...";
                status.innerText = "";

                fetch("/process_command", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: txt})
                }).then(r => r.json()).then(data => {
                    if(data.success) {
                        status.innerText = "✓ Code Generated & Queued";
                        status.className = "success";
                    } else {
                        status.innerText = "Error: " + data.error;
                        status.className = "error";
                    }
                }).catch(err => {
                    status.innerText = "Server Error";
                    status.className = "error";
                }).finally(() => {
                    input.disabled = false;
                    btn.disabled = false;
                    btn.innerText = "Send Command";
                    input.value = "";
                    input.focus();
                });
            }
        </script>
    </body>
    </html>
    '''

# --- SERVER SIDE AI LOGIC ---
@app.route('/process_command', methods=['POST'])
def process_command():
    data = request.json
    prompt = data.get('prompt')
    
    if not prompt: 
        return jsonify({"success": False, "error": "No prompt"})

    # 1. Prepare the prompt for Gemini
    full_prompt = (
        "You are a Roblox Lua assistant. "
        "Return ONLY valid Lua code. Do not use markdown. "
        "Parent all new objects to workspace. "
        "Code request: " + prompt
    )
    
    payload = {
        "contents": [{ "parts": [{ "text": full_prompt }] }]
    }
    
    # 2. Call Google Gemini (Server to Server)
    try:
        response = requests.post(API_URL, json=payload)
        response_json = response.json()
        
        # 3. Extract Code
        if "candidates" in response_json:
            generated_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            # Clean up formatting
            clean_code = generated_text.replace("```lua", "").replace("```", "")
            
            # 4. Put in Queue for Roblox
            code_queue.append(clean_code)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "AI refused request or error."})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/get_latest_code', methods=['GET'])
def get_latest_code():
    # Roblox calls this to get the finished code
    if len(code_queue) > 0:
        code = code_queue.pop(0)
        return jsonify({"has_code": True, "code": code})
    else:
        return jsonify({"has_code": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
