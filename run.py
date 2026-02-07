from radio import RadioStation
import threading
import asyncio
import json
import time
from flask import Flask, Response, render_template_string, request, redirect, url_for, session
from functools import wraps
import os

MUSIC_FOLDER = "music"
PASSWORD = "070927"
if not os.path.exists(MUSIC_FOLDER):
    os.makedirs(MUSIC_FOLDER)

# Radio Singleton
radio = RadioStation()

def start_radio():
    print("[RUN] 📻 Iniciando hilo global de radio...")
    radio.start()

# Iniciar la radio en un hilo global una sola vez al arrancar el script
radio_thread = threading.Thread(target=start_radio, daemon=True)
radio_thread.start()
print("Emisora iniciada globalmente")

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def run_highrise_bot():
    print("[RUN] 🤖 Iniciando bot de Highrise...")
    while True: # Bucle de autoreinicio en caso de desconexión
        try:
            from main import Bot
            from highrise.__main__ import BotDefinition, main as highrise_main
            
            # Railway specific: ensure we are using the correct event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            with open("config.json", "r", encoding="utf-8") as f:
                current_config = json.load(f)
                
            room_id = current_config["room_id"]
            api_token = current_config["api_token"]
            
            # Pasar la instancia de radio al bot
            bot = Bot(radio_instance=radio)
            
            definitions = [BotDefinition(bot, room_id, api_token)]
            
            # Check if there is an existing event loop and close it if necessary
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except Exception:
                pass
                
            # Crear un loop nuevo y limpio para cada intento
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(highrise_main(definitions))
        except Exception as e:
            print(f"[RUN] ❌ El bot se desconectó: {e}. Reiniciando en 15s...")
            time.sleep(15)

# El bot ya no se inicia aquí para evitar duplicación con el hilo principal
# bot_thread = threading.Thread(target=run_highrise_bot, daemon=True)
# bot_thread.start()
# print("[RUN] ✅ Hilo del bot de Highrise lanzado.")

app = Flask(__name__)
app.secret_key = "nocturno_dj_secret_key_2024"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nocturno DJ | Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            width: 340px;
            padding: 50px 40px;
            background: rgba(255,255,255,0.03);
            border-radius: 30px;
            border: 1px solid rgba(255,255,255,0.08);
            backdrop-filter: blur(20px);
            text-align: center;
        }
        .logo {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            margin: 0 auto 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
        }
        h1 {
            color: #fff;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .subtitle {
            color: rgba(255,255,255,0.5);
            font-size: 0.85rem;
            margin-bottom: 35px;
        }
        .input-group {
            position: relative;
            margin-bottom: 20px;
        }
        input[type="password"] {
            width: 100%;
            padding: 18px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            color: #fff;
            font-size: 1rem;
            text-align: center;
            letter-spacing: 8px;
            outline: none;
            transition: all 0.3s;
        }
        input[type="password"]:focus {
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.2);
        }
        input::placeholder {
            letter-spacing: 2px;
            color: rgba(255,255,255,0.3);
        }
        .btn-login {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 16px;
            color: #fff;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .error {
            color: #ff6b6b;
            font-size: 0.85rem;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🎧</div>
        <h1>Nocturno DJ</h1>
        <p class="subtitle">Ingresa tu clave de acceso</p>
        <form method="post">
            <div class="input-group">
                <input type="password" name="password" placeholder="******" maxlength="10" required autofocus>
            </div>
            <button type="submit" class="btn-login">Entrar</button>
        </form>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DJ Bot | Control Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #00f2fe;
            --secondary: #4facfe;
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text: #f8fafc;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: radial-gradient(circle at top left, #1e293b, #0f172a);
            color: var(--text);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .container {
            width: 90%;
            max-width: 500px;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            text-align: center;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            background: linear-gradient(to right, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }

        .status {
            font-size: 0.9rem;
            color: #94a3b8;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .status::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e;
        }

        .now-playing {
            background: rgba(15, 23, 42, 0.5);
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .now-playing p {
            margin: 0;
            font-size: 0.8rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .now-playing h2 {
            margin: 10px 0 0;
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--primary);
        }

        .upload-section {
            margin-bottom: 30px;
        }

        .custom-file-upload {
            display: inline-block;
            padding: 12px 24px;
            cursor: pointer;
            background: linear-gradient(135deg, var(--secondary), var(--primary));
            color: white;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
            box-sizing: border-box;
            border: none;
        }

        .custom-file-upload:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -10px var(--secondary);
            filter: brightness(1.1);
        }

        input[type="file"] {
            display: none;
        }

        .btn-submit {
            margin-top: 10px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            padding: 10px;
            border-radius: 12px;
            width: 100%;
            cursor: pointer;
            transition: 0.2s;
        }

        .btn-submit:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .local-music {
            text-align: left;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 20px;
            padding-right: 10px;
        }

        .local-music h3 {
            font-size: 0.9rem;
            color: #64748b;
            margin-bottom: 10px;
        }

        .music-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .music-item {
            padding: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.85rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: #cbd5e1;
        }

        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .stream-link {
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: 0.3s;
        }

        .stream-link:hover {
            text-shadow: 0 0 10px var(--primary);
        }

        /* Scrollbar custom */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Nocturno DJ</h1>
        <div class="status">Live Control Panel</div>

        <div class="now-playing">
            <p>Sonando ahora</p>
            <h2>{{ current_song }}</h2>
        </div>

        <div class="upload-section">
            <form method="post" action="/upload" enctype="multipart/form-data">
                <label for="file-upload" class="custom-file-upload">
                    Seleccionar Archivo de Audio
                </label>
                <input id="file-upload" type="file" name="file" multiple required onchange="this.form.submit()">
            </form>
        </div>

        <div class="local-music">
            <h3>Biblioteca Local</h3>
            <ul class="music-list">
                {% for song in local_music %}
                    <li class="music-item">{{ song }}</li>
                {% endfor %}
            </ul>
        </div>

        <div class="footer">
            <a href="/player" class="stream-link" target="_blank">📻 Abrir Reproductor Stream</a>
        </div>
    </div>
</body>
</html>
"""

PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nocturno DJ | Stream Player</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }

        .player-container {
            max-width: 420px;
            margin: 0 auto;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            padding: 20px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0 30px;
        }

        .header-btn {
            width: 40px;
            height: 40px;
            background: rgba(255,255,255,0.05);
            border: none;
            border-radius: 12px;
            color: #fff;
            font-size: 1.2rem;
            cursor: pointer;
            transition: 0.3s;
        }

        .header-btn:hover { background: rgba(255,255,255,0.1); }

        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            background: rgba(255, 59, 48, 0.15);
            border: 1px solid rgba(255, 59, 48, 0.3);
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            color: #ff3b30;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .live-dot {
            width: 6px;
            height: 6px;
            background: #ff3b30;
            border-radius: 50%;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .album-art {
            width: 280px;
            height: 280px;
            margin: 20px auto 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 6rem;
            box-shadow: 0 30px 60px rgba(102, 126, 234, 0.4);
            animation: float 6s ease-in-out infinite;
            position: relative;
            overflow: hidden;
        }

        .album-art::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.2) 0%, transparent 50%);
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .track-info {
            text-align: center;
            margin-bottom: 40px;
        }

        .track-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 8px;
            line-height: 1.4;
            max-height: 2.8em;
            overflow: hidden;
        }

        .track-artist {
            color: rgba(255,255,255,0.5);
            font-size: 0.9rem;
            font-weight: 400;
        }

        .progress-container {
            margin-bottom: 30px;
        }

        .progress-bar {
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 8px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            border-radius: 2px;
            animation: progress 180s linear infinite;
        }

        @keyframes progress {
            from { width: 0%; }
            to { width: 100%; }
        }

        .time-display {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: rgba(255,255,255,0.4);
        }

        .controls {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 30px;
            margin-bottom: 40px;
        }

        .ctrl-btn {
            background: none;
            border: none;
            color: rgba(255,255,255,0.7);
            font-size: 1.5rem;
            cursor: pointer;
            transition: 0.3s;
            padding: 10px;
        }

        .ctrl-btn:hover { color: #fff; transform: scale(1.1); }

        .play-btn {
            width: 70px;
            height: 70px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 50%;
            color: #fff;
            font-size: 1.8rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.5);
            transition: 0.3s;
        }

        .play-btn:hover {
            transform: scale(1.08);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
        }

        .volume-section {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 30px;
            padding: 0 10px;
        }

        .vol-icon { color: rgba(255,255,255,0.5); font-size: 0.9rem; }

        .volume-slider {
            flex: 1;
            -webkit-appearance: none;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            outline: none;
        }

        .volume-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 14px;
            height: 14px;
            background: #fff;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        .crossfade-section {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 20px;
        }

        .crossfade-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .crossfade-label span {
            font-size: 0.8rem;
            color: rgba(255,255,255,0.6);
        }

        .crossfade-value {
            font-size: 0.85rem;
            font-weight: 600;
            color: #667eea;
        }

        .crossfade-slider {
            width: 100%;
            -webkit-appearance: none;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            outline: none;
        }

        .crossfade-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.5);
        }

        .queue-section {
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 20px;
            margin-top: auto;
        }

        .queue-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .queue-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: rgba(255,255,255,0.8);
        }

        .queue-count {
            font-size: 0.7rem;
            color: rgba(255,255,255,0.4);
            background: rgba(255,255,255,0.05);
            padding: 4px 10px;
            border-radius: 10px;
        }

        .queue-list {
            max-height: 150px;
            overflow-y: auto;
        }

        .queue-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.03);
        }

        .queue-item:last-child { border-bottom: none; }

        .queue-thumb {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, #3a3a5c, #2a2a4c);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .queue-info {
            flex: 1;
            overflow: hidden;
        }

        .queue-song {
            font-size: 0.8rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .queue-user {
            font-size: 0.7rem;
            color: rgba(255,255,255,0.4);
        }

        .empty-queue {
            text-align: center;
            padding: 20px;
            color: rgba(255,255,255,0.3);
            font-size: 0.8rem;
        }

        audio { display: none; }

        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="player-container">
        <div class="header">
            <a href="/" class="header-btn">🏠</a>
            <div class="live-badge">
                <div class="live-dot"></div>
                En Vivo
            </div>
            <button class="header-btn" onclick="location.reload()">🔄</button>
        </div>

        <div class="album-art">🎵</div>

        <div class="track-info">
            <h1 class="track-title" id="track-name">{{ current_song }}</h1>
            <p class="track-artist">Nocturno Radio</p>
        </div>

        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="progress"></div>
            </div>
            <div class="time-display">
                <span id="current-time">0:00</span>
                <span id="duration-time">0:00</span>
            </div>
        </div>

        <div class="controls">
            <button class="ctrl-btn">⏮️</button>
            <button class="play-btn" id="playBtn" onclick="togglePlay()">▶️</button>
            <button class="ctrl-btn">⏭️</button>
        </div>

        <div class="volume-section">
            <span class="vol-icon">🔈</span>
            <input type="range" class="volume-slider" id="volumeSlider" min="0" max="100" value="80" oninput="setVolume(this.value)">
            <span class="vol-icon">🔊</span>
        </div>

        <div class="crossfade-section">
            <div class="crossfade-label">
                <span>Crossfade</span>
                <span class="crossfade-value" id="cfValue">{{ crossfade }}s</span>
            </div>
            <form id="cfForm" action="/set_crossfade" method="post">
                <input type="range" class="crossfade-slider" name="crossfade" min="0" max="30" value="{{ crossfade }}" 
                    oninput="document.getElementById('cfValue').innerText = this.value + 's'"
                    onchange="this.form.submit()">
            </form>
        </div>

        <div class="queue-section">
            <div class="queue-header">
                <span class="queue-title">Cola de Reproducción</span>
                <span class="queue-count" id="queue-count">{{ requests|length }} canciones</span>
            </div>
            <div class="queue-list" id="requests-list">
                {% for req in requests %}
                <div class="queue-item">
                    <div class="queue-thumb">🎧</div>
                    <div class="queue-info">
                        <div class="queue-song">{{ req.name }}</div>
                        <div class="queue-user">@{{ req.username }}</div>
                    </div>
                </div>
                {% else %}
                <div class="empty-queue">No hay canciones en cola</div>
                {% endfor %}
            </div>
        </div>
    </div>

    <audio id="audio-player" preload="none">
        <source src="/nocturno.mp3" type="audio/mpeg">
    </audio>

    <script>
        const audio = document.getElementById('audio-player');
        const playBtn = document.getElementById('playBtn');
        const progress = document.getElementById('progress');
        const currentTimeEl = document.getElementById('current-time');
        const durationEl = document.getElementById('duration-time');
        let isPlaying = false;
        let currentElapsed = 0;
        let currentDuration = 0;

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return mins + ':' + (secs < 10 ? '0' : '') + secs;
        }

        function togglePlay() {
            if (isPlaying) {
                audio.pause();
                playBtn.innerHTML = '▶️';
                isPlaying = false;
            } else {
                audio.play().then(() => {
                    playBtn.innerHTML = '⏸️';
                    isPlaying = true;
                }).catch(e => {
                    console.log('Autoplay blocked, user interaction needed');
                });
            }
        }

        function setVolume(val) {
            audio.volume = val / 100;
        }

        audio.volume = 0.8;

        // Manejar errores de audio
        audio.onerror = function() {
            console.log('Error loading audio, retrying...');
            setTimeout(() => {
                audio.load();
                if (isPlaying) audio.play();
            }, 2000);
        };

        function updatePlayer() {
            fetch('/api/now_playing')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('track-name').innerText = data.track;
                    document.getElementById('queue-count').innerText = data.queue_count + ' canciones';
                    
                    // Actualizar tiempo
                    currentElapsed = data.elapsed || 0;
                    currentDuration = data.duration || 0;
                    
                    currentTimeEl.innerText = formatTime(currentElapsed);
                    durationEl.innerText = formatTime(currentDuration);
                    
                    // Actualizar barra de progreso
                    if (currentDuration > 0) {
                        const percent = (currentElapsed / currentDuration) * 100;
                        progress.style.width = percent + '%';
                        progress.style.animation = 'none';
                    }
                })
                .catch(() => {});
        }
        
        // Actualizar más frecuente para tiempo más preciso
        setInterval(updatePlayer, 1000);
        updatePlayer();

        // Intentar reproducir al cargar
        document.addEventListener('click', function initAudio() {
            if (!isPlaying) {
                togglePlay();
            }
            document.removeEventListener('click', initAudio);
        }, { once: true });
    </script>
</body>
</html>
"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for("index"))
        else:
            error = "Contraseña incorrecta"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for("login"))

@app.route("/api/now_playing")
def api_now_playing():
    import json as json_module
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna"
    queue_count = radio.queue_requests.qsize()
    
    # Calcular tiempo transcurrido y duración
    elapsed = 0
    duration = radio.current_duration if radio.current_duration else 0
    if radio.track_start_time > 0:
        elapsed = int(time.time() - radio.track_start_time)
        if elapsed > duration:
            elapsed = duration
    
    return Response(
        json_module.dumps({
            "track": current_song, 
            "queue_count": queue_count,
            "elapsed": elapsed,
            "duration": duration
        }),
        mimetype="application/json"
    )

@app.route("/player")
@login_required
def player():
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna"
    
    requests_list = list(radio.queue_requests.queue)
    
    valid_extensions = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff", ".opus", ".amr")
    def sort_key(x):
        prefix = x.split('.')[0]
        return (int(prefix), x) if prefix.isdigit() else (float('inf'), x)

    local_music = sorted([f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(valid_extensions)], key=sort_key)
    
    return render_template_string(PLAYER_TEMPLATE, 
                                current_song=current_song, 
                                requests=requests_list, 
                                local_music=local_music,
                                crossfade=radio.crossfade)

@app.route("/set_crossfade", methods=["POST"])
@login_required
def set_crossfade():
    try:
        val = int(request.form.get("crossfade", 10))
        radio.crossfade = val
        # Persistir en config.json
        with open("config.json", "r") as f:
            conf = json.load(f)
        conf["crossfade"] = val
        with open("config.json", "w") as f:
            json.dump(conf, f, indent=4)
    except:
        pass
    return redirect(url_for("player"))

@app.route("/")
@login_required
def index():
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna"
    valid_extensions = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff", ".opus", ".amr")
    def sort_key(x):
        prefix = x.split('.')[0]
        return (int(prefix), x) if prefix.isdigit() else (float('inf'), x)

    local_music = sorted([f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(valid_extensions)], key=sort_key)
    return render_template_string(HTML_TEMPLATE, current_song=current_song, local_music=local_music, zfill=lambda s, n: str(s).zfill(n))

@app.route("/nocturno.mp3")
@app.route("/stream.mp3")
@app.route("/stream")
def stream():
    from flask import stream_with_context
    return Response(
        stream_with_context(radio.generate_stream()),
        mimetype="audio/mpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
            "X-Content-Type-Options": "nosniff"
        }
    )

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    files = request.files.getlist("file")
    if files:
        from mega_manager import MegaManager
        import io
        mega_mgr = MegaManager()
        
        for file in files:
            if file and file.filename:
                # Subir directamente a Mega en lugar de local
                audio_io = io.BytesIO(file.read())
                mega_mgr.upload_file(file.filename, audio_io)
                print(f"[WEB] Archivo subido a Mega: {file.filename}")
        
        # Refrescar la radio para que reconozca los nuevos archivos en Mega
        radio.load_local_music()
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Iniciar la radio en un hilo separado
    radio_thread = threading.Thread(target=start_radio, daemon=True)
    radio_thread.start()
    
    # Render y despliegues: El bot de Highrise debe correr en el hilo principal 
    # para mantener la conexión activa sin ser interrumpido por el worker de Flask.
    # Flask correrá en un hilo secundario para servir la web.
    
    # Configuración de puerto para Railway/Replit
    port = int(os.environ.get("PORT", 5000))
    print(f"[RUN] Servidor escuchando en el puerto {port}")
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    
    print("[RUN] 🚀 Todos los servicios iniciados. Ejecutando bot en hilo principal...")
    run_highrise_bot()
