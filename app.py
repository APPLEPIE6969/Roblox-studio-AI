import os
import requests
import json
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI")

# --- MODEL ROSTER ---
MODELS = {
    "GEMINI": "gemini-3-flash-preview",                   # Logic / Brain
    "GEMMA": "gemma-3-27b-it",                    # Open Model / Creative
    "NATIVE_AUDIO": "gemini-2.5-flash-native-audio-dialog", # Voice
    "NEURAL_TTS": "gemini-2.5-flash-tts"          # TTS Fallback
}

# --- HELPER: TTS ---
def generate_neural_speech(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['NEURAL_TTS']}:generateContent?key={GEMINI_KEY}"
    payload = { "contents": [{ "parts": [{ "text": text }] }] }
    try:
        r = requests.post(url, json=payload)
        data = r.json()
        if "candidates" in data:
            for part in data["candidates"][0]["content"]["parts"]:
                if "inline_data" in part: return part["inline_data"]["data"]
    except: return None
    return None

# --- MAIN AI CALLER ---
def call_ai(mode, model_id=None, prompt=None, audio_data=None, image_data=None):
    
    # 1. TEXT/IMAGE MODE
    if mode == "text":
        # Select the requested model (Gemini or Gemma)
        target_model = MODELS.get(model_id, MODELS["GEMINI"])
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={GEMINI_KEY}"
        
        parts = [{ "text": f"User: {prompt}" }]
        
        # Add Image if present
        if image_data:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg", # Assumes JPEG/PNG
                    "data": image_data
                }
            })

        payload = { "contents": [{ "parts": parts }] }
        
        try:
            r = requests.post(url, json=payload)
            return {"text": r.json()["candidates"][0]["content"]["parts"][0]["text"], "audio": None}
        except Exception as e: 
            return {"text": f"Error with {target_model}: {str(e)}", "audio": None}

    # 2. VOICE MODE (Native Audio 2.5)
    if mode == "voice":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['NATIVE_AUDIO']}:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    { "text": "Listen and respond." },
                    { "inline_data": { "mime_type": "audio/mp3", "data": audio_data } }
                ]
            }]
        }
        try:
            r = requests.post(url, json=payload)
            data = r.json()
            resp_text = "Audio Message."
            resp_audio = None
            
            if "candidates" in data:
                parts = data["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "text" in part: resp_text = part["text"]
                    if "inline_data" in part: resp_audio = part["inline_data"]["data"]

            if not resp_audio: resp_audio = generate_neural_speech(resp_text)
            return {"text": resp_text, "audio": resp_audio}
        except Exception as e: return {"text": str(e), "audio": None}

# --- WEB SERVER ---

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Omni-Chat Pro</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <meta name="theme-color" content="#050508">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --bg: #050508;
                --header-bg: rgba(20, 20, 30, 0.9);
                --glass-border: rgba(255, 255, 255, 0.08);
                --primary: #00f2ea;
                --secondary: #7000ff;
                --gemma: #ff0055;
                --text: #ffffff;
                --user-bubble: linear-gradient(135deg, var(--primary) 0%, #00a8a2 100%);
                --ai-bubble: rgba(255, 255, 255, 0.05);
            }

            * { box-sizing: border-box; margin: 0; padding: 0; outline: none; -webkit-tap-highlight-color: transparent; }

            body {
                background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif;
                height: 100dvh; display: flex; flex-direction: column; overflow: hidden; position: relative;
            }

            /* --- BACKGROUND --- */
            .orb { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.3; z-index: -1; animation: float 10s infinite alternate; }
            .orb-1 { width: 400px; height: 400px; background: var(--secondary); top: -10%; left: -10%; }
            .orb-2 { width: 300px; height: 300px; background: var(--primary); bottom: -10%; right: -10%; animation-delay: 2s; }
            @keyframes float { 0% { transform: translate(0,0); } 100% { transform: translate(30px, 30px); } }

            /* --- HEADER & MODEL SWITCHER --- */
            .header {
                padding: 15px 20px; background: var(--header-bg); backdrop-filter: blur(20px);
                border-bottom: 1px solid var(--glass-border); z-index: 10;
                display: flex; align-items: center; justify-content: space-between;
            }
            .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 18px; }
            .dot { width: 8px; height: 8px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 10px var(--primary); }
            
            .switcher {
                background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border);
                border-radius: 20px; padding: 3px; display: flex;
            }
            .model-btn {
                padding: 6px 12px; border-radius: 16px; font-size: 11px; font-weight: 600;
                color: #888; cursor: pointer; transition: 0.3s;
            }
            .model-btn.active-gemini { background: rgba(0, 242, 234, 0.2); color: var(--primary); }
            .model-btn.active-gemma { background: rgba(255, 0, 85, 0.2); color: var(--gemma); }

            /* --- CHAT --- */
            .chat-container {
                flex-grow: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; scroll-behavior: smooth;
            }
            .chat-container::-webkit-scrollbar { width: 4px; }
            .chat-container::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }

            .message {
                max-width: 80%; padding: 14px 18px; border-radius: 18px; font-size: 15px; line-height: 1.5;
                position: relative; word-wrap: break-word; animation: popIn 0.2s ease;
            }
            .user-msg { align-self: flex-end; background: var(--user-bubble); color: #000; font-weight: 500; border-bottom-right-radius: 4px; }
            .ai-msg { align-self: flex-start; background: var(--ai-bubble); color: #eee; border: 1px solid var(--glass-border); border-bottom-left-radius: 4px; }
            .img-preview { max-width: 100%; border-radius: 10px; margin-top: 5px; display: block; border: 1px solid rgba(0,0,0,0.2); }
            @keyframes popIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

            /* --- INPUT AREA --- */
            .input-area {
                padding: 15px; background: var(--header-bg); backdrop-filter: blur(20px);
                border-top: 1px solid var(--glass-border); display: flex; gap: 10px; align-items: flex-end;
                padding-bottom: max(15px, env(safe-area-inset-bottom));
            }

            .input-wrapper { flex-grow: 1; position: relative; }
            
            textarea {
                width: 100%; background: rgba(0,0,0,0.4); border: 1px solid var(--glass-border);
                padding: 12px 15px; border-radius: 20px; color: #fff; font-size: 16px; font-family: 'Outfit', sans-serif;
                resize: none; height: 48px; max-height: 120px; transition: 0.3s;
            }
            textarea:focus { border-color: var(--primary); }

            .icon-btn {
                width: 48px; height: 48px; border-radius: 50%; border: 1px solid var(--glass-border);
                background: rgba(255,255,255,0.05); color: #aaa; font-size: 18px;
                display: flex; align-items: center; justify-content: center; transition: 0.2s; cursor: pointer;
            }
            .icon-btn:hover { color: var(--primary); border-color: var(--primary); }
            
            #micBtn.recording { color: #ff0055; border-color: #ff0055; animation: breathe 1.5s infinite; }
            @keyframes breathe { 0% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(255, 0, 85, 0); } }

            /* --- IMAGE PREVIEW OVERLAY --- */
            #imageUploadPreview {
                position: absolute; bottom: 60px; left: 15px; width: 60px; height: 60px;
                border-radius: 10px; object-fit: cover; border: 2px solid var(--primary);
                display: none; box-shadow: 0 5px 20px rgba(0,0,0,0.5); z-index: 20; background: #000;
            }
            .remove-img {
                position: absolute; top: -8px; right: -8px; background: red; color: white;
                width: 18px; height: 18px; border-radius: 50%; font-size: 12px;
                display: flex; align-items: center; justify-content: center; cursor: pointer;
            }

        </style>
    </head>
    <body>

        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>

        <div class="header">
            <div class="brand"><div class="dot"></div> Omni-Chat</div>
            <div class="switcher">
                <div class="model-btn active-gemini" id="btnGemini" onclick="setModel('GEMINI')">Gemini 3.0</div>
                <div class="model-btn" id="btnGemma" onclick="setModel('GEMMA')">Gemma 3</div>
            </div>
        </div>

        <div class="chat-container" id="chat">
            <div class="message ai-msg">System Online. Select a model and start chatting.</div>
        </div>

        <div class="input-area">
            <!-- File Input -->
            <input type="file" id="fileInput" accept="image/*" style="display: none;" onchange="handleFile(this)">
            <div id="previewContainer" style="display:none;">
                <img id="imageUploadPreview">
                <div class="remove-img" onclick="clearImage()">×</div>
            </div>

            <button class="icon-btn" onclick="document.getElementById('fileInput').click()">
                <i class="fa-solid fa-paperclip"></i>
            </button>

            <div class="input-wrapper">
                <textarea id="prompt" placeholder="Message..." rows="1"></textarea>
            </div>

            <button class="icon-btn" id="micBtn" ontouchstart="startRec()" ontouchend="stopRec()" onmousedown="startRec()" onmouseup="stopRec()">
                <i class="fa-solid fa-microphone"></i>
            </button>
            <button class="icon-btn" style="background: var(--primary); color: #000; border: none;" onclick="sendText()">
                <i class="fa-solid fa-arrow-up"></i>
            </button>
        </div>

        <audio id="audioPlayer" style="display:none"></audio>

        <script>
            let currentModel = 'GEMINI';
            let currentImageBase64 = null;

            function setModel(model) {
                currentModel = model;
                document.getElementById('btnGemini').className = model === 'GEMINI' ? 'model-btn active-gemini' : 'model-btn';
                document.getElementById('btnGemma').className = model === 'GEMMA' ? 'model-btn active-gemma' : 'model-btn';
            }

            function addMsg(text, type, img=null) {
                let div = document.createElement("div");
                div.className = "message " + type;
                
                if (img) {
                    let i = document.createElement("img");
                    i.src = img;
                    i.className = "img-preview";
                    div.appendChild(i);
                }
                
                let t = document.createElement("div");
                t.innerText = text;
                div.appendChild(t);
                
                let container = document.getElementById("chat");
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            }

            // --- IMAGE HANDLING ---
            function handleFile(input) {
                if (input.files && input.files[0]) {
                    let reader = new FileReader();
                    reader.onload = function(e) {
                        currentImageBase64 = e.target.result.split(',')[1]; // Store Base64
                        let preview = document.getElementById('imageUploadPreview');
                        preview.src = e.target.result;
                        document.getElementById('previewContainer').style.display = 'block';
                        preview.style.display = 'block';
                    }
                    reader.readAsDataURL(input.files[0]);
                }
            }

            function clearImage() {
                currentImageBase64 = null;
                document.getElementById('fileInput').value = "";
                document.getElementById('previewContainer').style.display = 'none';
            }

            // --- TEXT MODE ---
            const promptInput = document.getElementById("prompt");
            promptInput.addEventListener("input", function() { this.style.height = "auto"; this.style.height = (this.scrollHeight) + "px"; });

            function sendText() {
                let txt = promptInput.value.trim();
                if(!txt && !currentImageBase64) return;

                // Show User Message (with image if exists)
                let imgSrc = currentImageBase64 ? "data:image/jpeg;base64," + currentImageBase64 : null;
                addMsg(txt, "user-msg", imgSrc);
                
                promptInput.value = "";
                promptInput.style.height = "48px";
                
                let payload = { prompt: txt, model: currentModel };
                if (currentImageBase64) {
                    payload.image = currentImageBase64;
                    clearImage(); // Clear after sending
                }

                fetch("/process_text", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(payload)
                }).then(r=>r.json()).then(d => {
                    addMsg(d.text, "ai-msg");
                });
            }

            // --- VOICE MODE ---
            let recorder, chunks = [];
            async function startRec() {
                document.getElementById("micBtn").classList.add("recording");
                try {
                    let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    recorder = new MediaRecorder(stream);
                    chunks = [];
                    recorder.ondataavailable = e => chunks.push(e.data);
                    recorder.start();
                } catch(e) { alert("Mic Error"); }
            }

            function stopRec() {
                document.getElementById("micBtn").classList.remove("recording");
                if(!recorder) return;
                recorder.stop();
                recorder.onstop = () => {
                    let blob = new Blob(chunks, { type: 'audio/webm' });
                    let reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = () => {
                        let b64 = reader.result.split(',')[1];
                        addMsg("🎤 Voice Input", "user-msg");
                        fetch("/process_voice", {
                            method: "POST", headers: {"Content-Type": "application/json"},
                            body: JSON.stringify({audio: b64})
                        }).then(r=>r.json()).then(d => {
                            addMsg(d.text, "ai-msg");
                            if(d.audio) {
                                let aud = document.getElementById("audioPlayer");
                                aud.src = "data:audio/mp3;base64," + d.audio;
                                aud.play();
                            }
                        });
                    };
                };
            }
        </script>
    </body>
    </html>
    '''

# --- BACKEND ---

@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    p = data.get('prompt', '')
    m = data.get('model', 'GEMINI') # Default to Gemini
    img = data.get('image') # Base64 Image
    
    res = call_ai("text", model_id=m, prompt=p, image_data=img)
    return jsonify({"text": res["text"]})

@app.route('/process_voice', methods=['POST'])
def process_voice():
    b64 = request.json.get('audio')
    res = call_ai("voice", audio_data=b64)
    return jsonify({"text": res["text"], "audio": res["audio"]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
