from flask import Flask, request, jsonify

app = Flask(__name__)

# --- STORAGE ---
command_queue = []

# --- THE WEBSITE (Ultra Polished UI) ---
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
            :root {
                --primary: #00f2ea;
                --secondary: #ff0055;
                --bg-dark: #0a0a0a;
                --glass: rgba(255, 255, 255, 0.05);
            }

            * { box-sizing: border-box; margin: 0; padding: 0; outline: none; }

            body {
                font-family: 'Inter', sans-serif;
                background-color: var(--bg-dark);
                color: white;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
                background: radial-gradient(circle at 50% 50%, #1a1a2e 0%, #000000 100%);
            }

            /* Animated Background Blobs */
            .blob {
                position: absolute;
                filter: blur(80px);
                z-index: -1;
                opacity: 0.6;
                animation: float 10s infinite ease-in-out;
            }
            .blob-1 { top: -10%; left: -10%; width: 500px; height: 500px; background: var(--secondary); animation-delay: 0s; }
            .blob-2 { bottom: -10%; right: -10%; width: 600px; height: 600px; background: var(--primary); animation-delay: 5s; }

            @keyframes float {
                0%, 100% { transform: translate(0, 0); }
                50% { transform: translate(30px, -30px); }
            }

            /* Glass Card */
            .container {
                width: 90%;
                max-width: 450px;
                background: var(--glass);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 20px 50px rgba(0,0,0,0.5);
                text-align: center;
                transform: translateY(0);
                transition: transform 0.3s ease;
                animation: popIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            @keyframes popIn {
                from { opacity: 0; transform: scale(0.9) translateY(20px); }
                to { opacity: 1; transform: scale(1) translateY(0); }
            }

            h1 {
                font-size: 28px;
                font-weight: 800;
                margin-bottom: 10px;
                background: linear-gradient(to right, #fff, #aaa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: -1px;
            }

            p.subtitle {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.5);
                margin-bottom: 30px;
            }

            /* Input Field */
            .input-group {
                position: relative;
                margin-bottom: 20px;
            }

            input {
                width: 100%;
                padding: 16px 20px;
                background: rgba(0, 0, 0, 0.3);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                color: white;
                font-size: 16px;
                transition: all 0.3s ease;
            }

            input:focus {
                border-color: var(--primary);
                box-shadow: 0 0 15px rgba(0, 242, 234, 0.3);
                background: rgba(0, 0, 0, 0.5);
            }

            input::placeholder { color: rgba(255, 255, 255, 0.3); }

            /* Modern Button */
            button {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, var(--primary), #00a8a2);
                color: #000;
                font-weight: 800;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.2s ease;
                position: relative;
                overflow: hidden;
            }

            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0, 242, 234, 0.4);
            }

            button:active {
                transform: scale(0.98);
            }

            /* Status Text */
            #status {
                margin-top: 20px;
                font-size: 14px;
                font-weight: 600;
                height: 20px;
                opacity: 0;
                transition: opacity 0.3s;
            }
            
            .success { color: var(--primary); }
            .error { color: var(--secondary); }

            /* Loading Spinner */
            .spinner {
                display: none;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(0,0,0,0.3);
                border-radius: 50%;
                border-top-color: #000;
                animation: spin 1s ease-in-out infinite;
                margin: 0 auto;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

        </style>
    </head>
    <body>

        <!-- Background effects -->
        <div class="blob blob-1"></div>
        <div class="blob blob-2"></div>

        <div class="container">
            <h1>Roblox Architect</h1>
            <p class="subtitle">AI-Powered Construction Interface</p>
            
            <div class="input-group">
                <input type="text" id="cmd" placeholder="Describe your build..." autocomplete="off" onkeypress="handleEnter(event)">
            </div>
            
            <button id="sendBtn" onclick="send()">
                <span id="btnText">Send Command</span>
                <div class="spinner" id="btnSpinner"></div>
            </button>

            <p id="status">Waiting for input...</p>
        </div>

        <script>
            function handleEnter(e) {
                if(e.key === 'Enter') send();
            }

            function send() {
                const input = document.getElementById("cmd");
                const btnText = document.getElementById("btnText");
                const spinner = document.getElementById("btnSpinner");
                const status = document.getElementById("status");
                const txt = input.value.trim();

                if (!txt) {
                    status.innerText = "Please type something first.";
                    status.className = "error";
                    status.style.opacity = "1";
                    return;
                }

                // UI Loading State
                input.disabled = true;
                btnText.style.display = "none";
                spinner.style.display = "block";
                status.style.opacity = "0";

                fetch("/add_command", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({prompt: txt})
                }).then(r => r.text()).then(t => {
                    // Success State
                    status.innerText = "✓ Sent to Roblox Studio";
                    status.className = "success";
                    status.style.opacity = "1";
                    input.value = "";
                }).catch(err => {
                    // Error State
                    status.innerText = "Error connecting to server.";
                    status.className = "error";
                    status.style.opacity = "1";
                }).finally(() => {
                    // Reset UI
                    setTimeout(() => {
                        input.disabled = false;
                        input.focus();
                        btnText.style.display = "block";
                        spinner.style.display = "none";
                    }, 500);
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/add_command', methods=['POST'])
def add_command():
    data = request.json
    prompt = data.get('prompt')
    if prompt:
        command_queue.append(prompt)
        return "OK"
    return "Error", 400

@app.route('/get_latest', methods=['GET'])
def get_latest():
    if len(command_queue) > 0:
        cmd = command_queue.pop(0)
        return jsonify({"has_command": True, "prompt": cmd})
    else:
        return jsonify({"has_command": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
