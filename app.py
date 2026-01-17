import os
import requests
import json
import base64
import markdown2
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI")

# --- MARKDOWN PARSING ---
def parse_markdown(text):
    """Convert markdown text to HTML with support for tables, code highlighting, and math"""
    extras = [
        "tables",
        "code-friendly", 
        "fenced-code-blocks",
        "strike",
        "footnotes",
        "header-ids",
        "toc",
        "spoiler",
        "smarty-pants",
        "link-patterns"
    ]
    return markdown2.markdown(text, extras=extras)

# --- MODEL ROSTER ---
MODELS = {
    "GEMINI": "gemini-3-flash-preview",                   # Standard Brain
    "GEMMA": "gemma-3-27b-it",                    # Creative / Open Model
    "DIRECTOR": "gemini-3-flash-preview",                 # Deep Think Reviewer
    "NATIVE_AUDIO": "gemini-2.5-flash-native-audio-dialog", # Voice Mode
    "NEURAL_TTS": "gemini-2.5-flash-tts"          # Fallback TTS
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

# --- DEEP THINK LOGIC ---
def director_review(prompt, initial_response):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['DIRECTOR']}:generateContent?key={GEMINI_KEY}"
    
    review_prompt = (
        f"User Prompt: {prompt}\n"
        f"AI Draft Response: {initial_response}\n\n"
        "You are the Director. Review the draft for accuracy, tone, and safety. "
        "If it's good, return it exactly as is. If it needs improvement, rewrite it better."
    )
    
    payload = { "contents": [{ "parts": [{ "text": review_prompt }] }] }
    try:
        r = requests.post(url, json=payload)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return initial_response # Fallback to original if review fails

# --- MAIN AI CALLER ---
def call_ai(mode, model_id=None, prompt=None, audio_data=None, image_data=None, deep_think=False):
    
    # 1. TEXT/IMAGE MODE (Silent)
    if mode == "text":
        target_model = MODELS.get(model_id, MODELS["GEMINI"])
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={GEMINI_KEY}"
        
        parts = [{ "text": f"User: {prompt}" }]
        
        if image_data:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg", 
                    "data": image_data
                }
            })

        payload = { "contents": [{ "parts": parts }] }
        
        try:
            r = requests.post(url, json=payload)
            response_text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            # Apply Deep Think if requested
            if deep_think:
                response_text = director_review(prompt, response_text)
                
            return {"text": response_text, "audio": None}
        except Exception as e: 
            return {"text": f"Error: {str(e)}", "audio": None}

    # 2. VOICE MODE (Audible)
    if mode == "voice":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['NATIVE_AUDIO']}:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    { "text": "Listen and respond naturally." },
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
        <title>Omni-Chat Ultimate</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <meta name="theme-color" content="#050508">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --bg: #050508;
                --header-bg: rgba(20, 20, 30, 0.95);
                --glass-border: rgba(255, 255, 255, 0.08);
                --primary: #00f2ea;
                --secondary: #7000ff;
                --gemma: #ff0055;
                --director: #ffd700;
                --text: #ffffff;
                --user-bubble: linear-gradient(135deg, var(--primary) 0%, #00a8a2 100%);
                --ai-bubble: rgba(255, 255, 255, 0.05);
            }

            * { box-sizing: border-box; margin: 0; padding: 0; outline: none; -webkit-tap-highlight-color: transparent; }

            body {
                background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif;
                height: 100dvh; display: flex; flex-direction: column; overflow: hidden; position: relative;
            }

            /* --- ANIMATED BACKGROUND --- */
            .orb { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.3; z-index: -1; animation: float 10s infinite alternate; }
            .orb-1 { width: 400px; height: 400px; background: var(--secondary); top: -10%; left: -10%; }
            .orb-2 { width: 300px; height: 300px; background: var(--primary); bottom: -10%; right: -10%; animation-delay: 2s; }
            @keyframes float { 0% { transform: translate(0,0); } 100% { transform: translate(30px, 30px); } }

            /* --- HEADER --- */
            .header {
                padding: 10px 15px; background: var(--header-bg); backdrop-filter: blur(20px);
                border-bottom: 1px solid var(--glass-border); z-index: 10;
                display: flex; flex-direction: column; gap: 10px;
            }
            .top-row { display: flex; align-items: center; justify-content: space-between; width: 100%; }
            
            .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 18px; }
            .dot { width: 8px; height: 8px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 10px var(--primary); }
            
            .controls-row { display: flex; justify-content: space-between; width: 100%; align-items: center; }

            /* Switcher */
            .switcher {
                background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border);
                border-radius: 20px; padding: 2px; display: flex;
            }
            .model-btn {
                padding: 5px 10px; border-radius: 16px; font-size: 10px; font-weight: 600;
                color: #888; cursor: pointer; transition: 0.3s;
            }
            .model-btn.active-gemini { background: rgba(0, 242, 234, 0.2); color: var(--primary); }
            .model-btn.active-gemma { background: rgba(255, 0, 85, 0.2); color: var(--gemma); }

            /* Deep Think Toggle */
            .dt-toggle {
                display: flex; align-items: center; gap: 8px; font-size: 11px; color: #888; cursor: pointer;
            }
            .dt-box {
                width: 14px; height: 14px; border: 1px solid #555; border-radius: 3px; display: flex; align-items: center; justify-content: center;
            }
            .dt-toggle.active { color: var(--director); text-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }
            .dt-toggle.active .dt-box { background: var(--director); border-color: var(--director); box-shadow: 0 0 8px var(--director); }

            /* --- CHAT --- */
            .chat-container {
                flex-grow: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; scroll-behavior: smooth;
            }
            .message {
                max-width: 85%; padding: 12px 16px; border-radius: 18px; font-size: 15px; line-height: 1.5;
                position: relative; word-wrap: break-word; animation: popIn 0.2s ease;
            }
            .user-msg { align-self: flex-end; background: var(--user-bubble); color: #000; font-weight: 500; border-bottom-right-radius: 4px; }
            .ai-msg { align-self: flex-start; background: var(--ai-bubble); color: #eee; border: 1px solid var(--glass-border); border-bottom-left-radius: 4px; }
            .img-preview { max-width: 100%; border-radius: 10px; margin-top: 5px; display: block; }
            @keyframes popIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

            /* --- INPUT --- */
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
                display: flex; align-items: center; justify-content: center; transition: 0.2s; cursor: pointer; flex-shrink: 0;
            }
            .icon-btn:hover { color: var(--primary); border-color: var(--primary); }
            #micBtn.recording { color: #ff0055; border-color: #ff0055; animation: breathe 1.5s infinite; }
            @keyframes breathe { 0% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(255, 0, 85, 0); } }

            /* Image Preview */
            #imageUploadPreview {
                position: absolute; bottom: 60px; left: 15px; width: 60px; height: 60px;
                border-radius: 10px; object-fit: cover; border: 2px solid var(--primary);
                display: none; background: #000; z-index: 20;
            }
            .remove-img {
                position: absolute; top: -8px; right: -8px; background: red; color: white;
                width: 18px; height: 18px; border-radius: 50%; font-size: 12px;
                display: flex; align-items: center; justify-content: center; cursor: pointer;
            }

            /* --- MARKDOWN STYLES --- */
            .ai-msg h1, .ai-msg h2, .ai-msg h3, .ai-msg h4, .ai-msg h5, .ai-msg h6 {
                margin: 15px 0 10px 0; font-weight: 700; line-height: 1.3;
            }
            .ai-msg h1 { font-size: 1.8em; color: var(--primary); border-bottom: 2px solid var(--primary); padding-bottom: 5px; }
            .ai-msg h2 { font-size: 1.5em; color: var(--secondary); border-bottom: 1px solid var(--secondary); padding-bottom: 3px; }
            .ai-msg h3 { font-size: 1.3em; color: #fff; }
            .ai-msg h4 { font-size: 1.1em; color: #ddd; }
            .ai-msg h5 { font-size: 1em; color: #ccc; }
            .ai-msg h6 { font-size: 0.9em; color: #bbb; }

            .ai-msg p { margin: 10px 0; line-height: 1.6; }

            .ai-msg em, .ai-msg i { font-style: italic; color: #ddd; }
            .ai-msg strong, .ai-msg b { font-weight: 700; color: #fff; }
            .ai-msg strong em, .ai-msg b i { font-weight: 700; font-style: italic; color: #fff; }
            .ai-msg del, .ai-msg strike { text-decoration: line-through; color: #888; }

            .ai-msg ul, .ai-msg ol { margin: 10px 0; padding-left: 25px; }
            .ai-msg li { margin: 5px 0; line-height: 1.5; }
            .ai-msg ul li { list-style-type: disc; }
            .ai-msg ol li { list-style-type: decimal; }
            .ai-msg ul li input[type="checkbox"] { margin-right: 8px; }

            .ai-msg code {
                background: rgba(0, 242, 234, 0.1); color: var(--primary);
                padding: 2px 6px; border-radius: 4px; font-family: 'JetBrains Mono', monospace;
                font-size: 0.9em; border: 1px solid rgba(0, 242, 234, 0.3);
            }

            .ai-msg pre {
                background: rgba(0, 0, 0, 0.6); border: 1px solid var(--glass-border);
                border-radius: 8px; padding: 15px; margin: 15px 0; overflow-x: auto;
                position: relative;
            }
            .ai-msg pre code {
                background: none; padding: 0; border: none; color: #fff; font-size: 0.9em;
                line-height: 1.5;
            }

            .ai-msg blockquote {
                border-left: 4px solid var(--primary); margin: 15px 0; padding: 10px 20px;
                background: rgba(0, 242, 234, 0.05); border-radius: 0 8px 8px 0;
                font-style: italic; color: #ddd;
            }
            .ai-msg blockquote blockquote {
                border-left: 4px solid var(--secondary); margin: 10px 0; padding: 8px 15px;
                background: rgba(112, 0, 255, 0.05);
            }

            .ai-msg table {
                border-collapse: collapse; width: 100%; margin: 15px 0; background: rgba(0, 0, 0, 0.3);
                border-radius: 8px; overflow: hidden;
            }
            .ai-msg th, .ai-msg td {
                border: 1px solid var(--glass-border); padding: 10px 15px; text-align: left;
            }
            .ai-msg th {
                background: rgba(0, 242, 234, 0.1); font-weight: 700; color: var(--primary);
            }
            .ai-msg tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }
            .ai-msg tr:hover { background: rgba(0, 242, 234, 0.05); }

            .ai-msg hr {
                border: none; height: 2px; background: linear-gradient(90deg, transparent, var(--primary), transparent);
                margin: 20px 0; opacity: 0.5;
            }

            .ai-msg a {
                color: var(--primary); text-decoration: none; border-bottom: 1px solid transparent;
                transition: all 0.3s;
            }
            .ai-msg a:hover { color: var(--secondary); border-bottom-color: var(--secondary); }

            .ai-msg img {
                max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0;
                border: 1px solid var(--glass-border);
            }

            .ai-msg .math-inline, .ai-msg .math-block {
                font-family: 'JetBrains Mono', monospace; background: rgba(112, 0, 255, 0.1);
                padding: 2px 6px; border-radius: 4px; color: var(--secondary);
            }
            .ai-msg .math-block {
                display: block; padding: 15px; margin: 15px 0; text-align: center;
                background: rgba(112, 0, 255, 0.05); border: 1px solid rgba(112, 0, 255, 0.3);
                border-radius: 8px; font-size: 1.1em;
            }

            .ai-msg sub, .ai-msg sup { font-size: 0.8em; line-height: 0; position: relative; }
            .ai-msg sub { bottom: -0.3em; }
            .ai-msg sup { top: -0.3em; }
            .ai-msg u { text-decoration: underline; color: #ddd; }

            .ai-msg .footnote-ref {
                font-size: 0.8em; vertical-align: super; color: var(--primary);
                cursor: pointer;
            }
            .ai-msg .footnotes {
                margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--glass-border);
                font-size: 0.9em; color: #888;
            }

            /* --- THINKING INDICATOR --- */
            .thinking-msg {
                align-self: flex-start; background: var(--ai-bubble); color: #eee;
                border: 1px solid var(--glass-border); border-bottom-left-radius: 4px;
                max-width: 85%; padding: 12px 16px; border-radius: 18px; font-size: 15px;
                position: relative; word-wrap: break-word; animation: popIn 0.2s ease;
            }
            .thinking-content {
                display: flex; align-items: center; gap: 8px;
            }
            .thinking-dots {
                display: flex; gap: 4px; align-items: center;
            }
            .thinking-dot {
                width: 8px; height: 8px; background: var(--primary); border-radius: 50%;
                animation: thinkingPulse 1.4s infinite ease-in-out both;
            }
            .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
            .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
            .thinking-dot:nth-child(3) { animation-delay: 0s; }
            @keyframes thinkingPulse {
                0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
                40% { transform: scale(1.2); opacity: 1; }
            }
            .thinking-text {
                color: #aaa; font-size: 14px; font-style: italic;
            }
            .thinking-pulse {
                display: inline-block; width: 6px; height: 6px; background: var(--primary);
                border-radius: 50%; margin-left: 8px; animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.5); opacity: 0.7; }
                100% { transform: scale(1); opacity: 1; }
            }

        </style>
    </head>
    <body>

        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>

        <div class="header">
            <div class="top-row">
                <div class="brand"><div class="dot"></div> Omni-Chat</div>
                <div class="switcher">
                    <div class="model-btn active-gemini" id="btnGemini" onclick="setModel('GEMINI')">Gemini 3</div>
                    <div class="model-btn" id="btnGemma" onclick="setModel('GEMMA')">Gemma 27B</div>
                </div>
            </div>
            <div class="controls-row">
                <div class="dt-toggle" id="dtToggle" onclick="toggleDT()">
                    <div class="dt-box"><i class="fa-solid fa-check" style="font-size: 8px; color: black; display: none;" id="dtCheck"></i></div>
                    Deep Think (Director)
                </div>
            </div>
        </div>

        <div class="chat-container" id="chat">
            <div class="message ai-msg">Online. Shift+Enter for new line.</div>
        </div>

        <div class="input-area">
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
            let deepThinkEnabled = false;
            let currentImageBase64 = null;

            function setModel(model) {
                currentModel = model;
                document.getElementById('btnGemini').className = model === 'GEMINI' ? 'model-btn active-gemini' : 'model-btn';
                document.getElementById('btnGemma').className = model === 'GEMMA' ? 'model-btn active-gemma' : 'model-btn';
            }

            function toggleDT() {
                deepThinkEnabled = !deepThinkEnabled;
                document.getElementById('dtToggle').className = deepThinkEnabled ? 'dt-toggle active' : 'dt-toggle';
                document.getElementById('dtCheck').style.display = deepThinkEnabled ? 'block' : 'none';
            }

            function addMsg(text, type, img=null, isHtml=false) {
                let div = document.createElement("div");
                div.className = "message " + type;
                if (img) {
                    let i = document.createElement("img");
                    i.src = img;
                    i.className = "img-preview";
                    div.appendChild(i);
                }
                let t = document.createElement("div");
                if (isHtml && type === "ai-msg") {
                    t.innerHTML = text;
                } else {
                    t.innerText = text;
                }
                div.appendChild(t);
                let container = document.getElementById("chat");
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            }

            function addThinkingMsg(text = "Thinking") {
                let div = document.createElement("div");
                div.className = "thinking-msg";
                div.id = "thinkingMsg";
                
                let content = document.createElement("div");
                content.className = "thinking-content";
                
                let textSpan = document.createElement("span");
                textSpan.className = "thinking-text";
                textSpan.textContent = text;
                
                let dots = document.createElement("div");
                dots.className = "thinking-dots";
                
                for (let i = 0; i < 3; i++) {
                    let dot = document.createElement("div");
                    dot.className = "thinking-dot";
                    dots.appendChild(dot);
                }
                
                content.appendChild(textSpan);
                content.appendChild(dots);
                div.appendChild(content);
                
                let container = document.getElementById("chat");
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
                
                return div;
            }

            function removeThinkingMsg() {
                let thinkingMsg = document.getElementById("thinkingMsg");
                if (thinkingMsg) {
                    thinkingMsg.remove();
                }
            }

            function updateThinkingText(text) {
                let thinkingMsg = document.getElementById("thinkingMsg");
                if (thinkingMsg) {
                    let textSpan = thinkingMsg.querySelector(".thinking-text");
                    if (textSpan) {
                        textSpan.textContent = text;
                    }
                }
            }

            // Image Logic
            function handleFile(input) {
                if (input.files && input.files[0]) {
                    let reader = new FileReader();
                    reader.onload = function(e) {
                        currentImageBase64 = e.target.result.split(',')[1];
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

            // Textarea Logic (Shift+Enter)
            const promptInput = document.getElementById("prompt");
            promptInput.addEventListener("input", function() { this.style.height = "auto"; this.style.height = (this.scrollHeight) + "px"; });
            promptInput.addEventListener("keydown", function(e) {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendText(); }
            });

            function sendText() {
                let txt = promptInput.value.trim();
                if(!txt && !currentImageBase64) return;

                let imgSrc = currentImageBase64 ? "data:image/jpeg;base64," + currentImageBase64 : null;
                addMsg(txt, "user-msg", imgSrc);
                
                promptInput.value = "";
                promptInput.style.height = "48px";
                
                let payload = { prompt: txt, model: currentModel, deep_think: deepThinkEnabled };
                if (currentImageBase64) { payload.image = currentImageBase64; clearImage(); }

                // Show thinking indicator
                let thinkingMsg = addThinkingMsg("Thinking...");

                // Use fetch with streaming
                fetch('/process_text_stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                }).then(response => {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    
                    function readStream() {
                        return reader.read().then(({ done, value }) => {
                            if (done) {
                                removeThinkingMsg();
                                return;
                            }
                            
                            const chunk = decoder.decode(value, { stream: true });
                            const lines = chunk.split('\n');
                            
                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const data = JSON.parse(line.slice(6));
                                        if (data.type === 'thinking') {
                                            updateThinkingText(data.text);
                                        } else if (data.type === 'response') {
                                            removeThinkingMsg();
                                            addMsg(data.html || data.text, "ai-msg", null, !!data.html);
                                        } else if (data.type === 'done') {
                                            return;
                                        }
                                    } catch (e) {
                                        console.error('Error parsing data:', e);
                                    }
                                }
                            }
                            
                            return readStream();
                        });
                    }
                    
                    return readStream();
                }).catch(error => {
                    removeThinkingMsg();
                    console.error('Streaming error:', error);
                    // Fallback to regular endpoint
                    fetch("/process_text", {
                        method: "POST", headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(payload)
                    }).then(r=>r.json()).then(d => {
                        addMsg(d.html || d.text, "ai-msg", null, !!d.html);
                    });
                });
            }

            // Voice Logic
            let recorder, chunks = [];
            async function startRec() {
                document.getElementById("micBtn").classList.add("recording");
                try {
                    let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    recorder = new MediaRecorder(stream);
                    chunks = [];
                    recorder.ondataavailable = e => chunks.push(e.data);
                    recorder.start();
                } catch(e) { alert("Mic denied"); }
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
                        addMsg("🎤 Processing Audio...", "user-msg");
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
    res = call_ai("text", model_id=data.get('model'), prompt=data.get('prompt'), image_data=data.get('image'), deep_think=data.get('deep_think'))
    html_content = parse_markdown(res["text"])
    return jsonify({"text": res["text"], "html": html_content})

@app.route('/process_text_stream', methods=['POST'])
def process_text_stream():
    data = request.json
    
    def generate():
        # Send thinking status updates
        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Analyzing your request...'})}\n\n"
        
        # Simulate processing steps
        import time
        time.sleep(0.5)
        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Processing with AI model...'})}\n\n"
        
        if data.get('deep_think'):
            time.sleep(0.5)
            yield f"data: {json.dumps({'type': 'thinking', 'text': 'Director is reviewing...'})}\n\n"
            time.sleep(0.5)
            yield f"data: {json.dumps({'type': 'thinking', 'text': 'Refining response...'})}\n\n"
        
        # Get actual AI response
        res = call_ai("text", model_id=data.get('model'), prompt=data.get('prompt'), 
                     image_data=data.get('image'), deep_think=data.get('deep_think'))
        
        # Send final response
        html_content = parse_markdown(res["text"])
        yield f"data: {json.dumps({'type': 'response', 'text': res['text'], 'html': html_content})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/process_voice', methods=['POST'])
def process_voice():
    res = call_ai("voice", audio_data=request.json.get('audio'))
    return jsonify({"text": res["text"], "audio": res["audio"]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
