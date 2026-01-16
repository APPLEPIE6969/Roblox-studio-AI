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
    "BRAIN": "gemini-3-flash",                    # Smartest Text Logic
    "NATIVE_AUDIO": "gemini-2.5-flash-native-audio-dialog", # Speech-to-Speech
    "NEURAL_TTS": "gemini-2.5-flash-tts",         # Text-to-Speech
    "FALLBACK": "gemini-2.5-flash"                # Safety Net
}

# --- HELPER: GEMINI TEXT-TO-SPEECH ---
def generate_neural_speech(text):
    """
    Uses Gemini-2.5-Flash-TTS to generate high-quality audio from text.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['NEURAL_TTS']}:generateContent?key={GEMINI_KEY}"
    payload = { "contents": [{ "parts": [{ "text": text }] }] }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if "candidates" in data:
            for part in data["candidates"][0]["content"]["parts"]:
                if "inline_data" in part:
                    return part["inline_data"]["data"] # Base64 Audio
    except:
        return None
    return None

# --- MAIN AI CALLER ---
def call_ai(mode, prompt=None, audio_data=None):
    """
    Handles Text (Brain) and Voice (Native Audio) interactions.
    """
    
    # 1. TEXT MODE (Silent, Smart, Gemini 3.0)
    if mode == "text":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['BRAIN']}:generateContent?key={GEMINI_KEY}"
        payload = { "contents": [{ "parts": [{ "text": f"You are a helpful assistant. User says: {prompt}" }] }] }
        
        try:
            r = requests.post(url, json=payload)
            return {"text": r.json()["candidates"][0]["content"]["parts"][0]["text"], "audio": None}
        except:
            return {"text": "Connection error with Gemini 3.0.", "audio": None}

    # 2. VOICE MODE (Native Audio 2.5)
    if mode == "voice":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['NATIVE_AUDIO']}:generateContent?key={GEMINI_KEY}"
        
        payload = {
            "contents": [{
                "parts": [
                    { "text": "Listen to this audio. Respond naturally with Audio." },
                    { "inline_data": { "mime_type": "audio/mp3", "data": audio_data } }
                ]
            }]
        }
        
        try:
            r = requests.post(url, json=payload)
            data = r.json()
            
            response_text = "Audio Message Received."
            response_audio = None
            
            if "candidates" in data:
                parts = data["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "text" in part: response_text = part["text"]
                    if "inline_data" in part: response_audio = part["inline_data"]["data"]

            # FALLBACK: If Native Model gave text but NO audio, use Neural TTS
            if not response_audio and response_text:
                response_audio = generate_neural_speech(response_text)

            return {"text": response_text, "audio": response_audio}

        except Exception as e:
            return {"text": f"Voice error: {str(e)}", "audio": None}

# --- WEB SERVER ---

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Omni-Mobile</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <meta name="theme-color" content="#000000">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --bg: #000000;
                --surface: #121212;
                --primary: #3b82f6;
                --accent: #8b5cf6;
                --text: #ffffff;
            }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            body { 
                background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif;
                margin: 0; height: 100dvh; display: flex; flex-direction: column; overflow: hidden;
            }

            /* Header */
            .header {
                padding: 15px; text-align: center; background: linear-gradient(180deg, rgba(20,20,20,0.9), transparent);
                z-index: 10; display: flex; justify-content: center; align-items: center; gap: 10px;
            }
            .badge { 
                background: rgba(59, 130, 246, 0.2); color: var(--primary); 
                padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; text-transform: uppercase;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }

            /* Chat Area */
            .chat-container {
                flex-grow: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px;
                scroll-behavior: smooth;
            }
            .message {
                max-width: 85%; padding: 12px 16px; border-radius: 18px; font-size: 16px; line-height: 1.5;
                animation: popIn 0.2s ease; word-wrap: break-word;
            }
            .user-msg { 
                align-self: flex-end; background: var(--primary); color: white; 
                border-bottom-right-radius: 4px;
            }
            .ai-msg { 
                align-self: flex-start; background: var(--surface); color: #e0e0e0; border: 1px solid #333;
                border-bottom-left-radius: 4px;
            }
            @keyframes popIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

            /* Controls */
            .controls {
                padding: 15px; background: var(--surface); border-top: 1px solid #333;
                display: flex; align-items: center; gap: 10px;
                padding-bottom: max(20px, env(safe-area-inset-bottom));
            }
            
            input {
                flex-grow: 1; background: #222; border: none; color: white; padding: 14px 18px;
                border-radius: 25px; font-size: 16px; /* Prevents Zoom */
            }
            input:focus { outline: 1px solid var(--primary); background: #333; }

            /* Mic Button */
            #micBtn {
                width: 50px; height: 50px; border-radius: 50%; border: none;
                background: #222; color: #aaa; font-size: 20px;
                display: flex; align-items: center; justify-content: center;
                transition: 0.2s; touch-action: none;
            }
            #micBtn.active { background: #ef4444; color: white; transform: scale(1.1); box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }

            /* Send Button */
            #sendBtn {
                width: 50px; height: 50px; border-radius: 50%; border: none;
                background: var(--primary); color: white; font-size: 18px;
            }
            #sendBtn:active { transform: scale(0.95); opacity: 0.8; }

        </style>
    </head>
    <body>

        <div class="header">
            <h3>Gemini</h3> <span class="badge">3.0 Brain</span> <span class="badge">Native Voice</span>
        </div>

        <div class="chat-container" id="chat">
            <div class="message ai-msg">Online. Text is silent. Voice speaks back.</div>
        </div>

        <div class="controls">
            <button id="micBtn" ontouchstart="startRec()" ontouchend="stopRec()" onmousedown="startRec()" onmouseup="stopRec()">
                <i class="fa-solid fa-microphone"></i>
            </button>
            <input type="text" id="prompt" placeholder="Message..." autocomplete="off">
            <button id="sendBtn" onclick="sendText()"><i class="fa-solid fa-arrow-up"></i></button>
        </div>

        <audio id="audioPlayer" style="display:none"></audio>

        <script>
            function addMsg(text, type) {
                let div = document.createElement("div");
                div.className = "message " + type;
                div.innerText = text;
                document.getElementById("chat").appendChild(div);
                document.getElementById("chat").scrollTop = document.getElementById("chat").scrollHeight;
            }

            function sendText() {
                let p = document.getElementById("prompt");
                let txt = p.value.trim();
                if(!txt) return;

                addMsg(txt, "user-msg");
                p.value = "";

                // TEXT MODE: Silent (No Audio)
                fetch("/process_text", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: txt})
                }).then(r=>r.json()).then(d => {
                    addMsg(d.text, "ai-msg");
                });
            }

            // --- VOICE LOGIC ---
            let recorder, chunks = [];

            async function startRec() {
                let btn = document.getElementById("micBtn");
                btn.classList.add("active");
                try {
                    let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    recorder = new MediaRecorder(stream);
                    chunks = [];
                    recorder.ondataavailable = e => chunks.push(e.data);
                    recorder.start();
                } catch(e) { 
                    btn.classList.remove("active");
                    alert("Microphone access denied.");
                }
            }

            function stopRec() {
                document.getElementById("micBtn").classList.remove("active");
                if(!recorder) return;
                recorder.stop();
                
                addMsg("Listening...", "user-msg");

                recorder.onstop = () => {
                    let blob = new Blob(chunks, { type: 'audio/webm' });
                    let reader = new FileReader();
                    reader.readAsDataURL(blob);
                    reader.onloadend = () => {
                        let b64 = reader.result.split(',')[1];
                        
                        // VOICE MODE: Audio Response
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
    p = request.json.get('prompt')
    # Use BRAIN (Gemini 3.0) for high IQ text answers
    res = call_ai("text", prompt=p)
    return jsonify({"text": res["text"]}) # Audio is null

@app.route('/process_voice', methods=['POST'])
def process_voice():
    b64 = request.json.get('audio')
    # Use NATIVE AUDIO 2.5 for speech-to-speech
    res = call_ai("voice", audio_data=b64)
    return jsonify({"text": res["text"], "audio": res["audio"]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
