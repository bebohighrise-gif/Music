from radio import RadioStation
import threading
import asyncio
import json
import time
import traceback
import os
from flask import Flask, Response, render_template_string, request, redirect, url_for, session, jsonify
from functools import wraps
from werkzeug.utils import secure_filename

# ================== CONFIGURACIÓN SIMPLE ==================
PASSWORD = "070927"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.aiff', '.opus', '.amr'}

# Radio Singleton
radio = RadioStation()

def start_radio():
    print("[RUN] 📻 Iniciando hilo global de radio...")
    radio.start()

radio_thread = threading.Thread(target=start_radio, daemon=True)
radio_thread.start()
print("Emisora iniciada globalmente")

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def run_highrise_bot():
    print("[RUN] 🤖 Iniciando bot de Highrise...")
    intentos = 0
    while True:
        try:
            intentos += 1
            print(f"[RUN] 🔄 Intento #{intentos} de conexión...")
            
            if not os.path.exists("main.py"):
                print("[RUN] ❌ ERROR CRÍTICO: No existe el archivo 'main.py'")
                time.sleep(60)
                continue
            
            from main import Bot
            from highrise.__main__ import BotDefinition, main as highrise_main
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if "room_id" not in config or not config["room_id"]:
                print("[RUN] ❌ ERROR: 'room_id' no está configurado")
                time.sleep(60)
                continue
                
            if "api_token" not in config or not config["api_token"]:
                print("[RUN] ❌ ERROR: 'api_token' no está configurado")
                time.sleep(60)
                continue
                
            room_id = config["room_id"]
            api_token = config["api_token"]
            
            print(f"[RUN] 🔑 Room ID: {room_id[:20]}..." if len(room_id) > 20 else f"[RUN] 🔑 Room ID: {room_id}")
            
            bot = Bot(radio_instance=radio)
            definitions = [BotDefinition(bot, room_id, api_token)]
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except Exception:
                pass
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print("[RUN] 🚀 Ejecutando bot de Highrise...")
            loop.run_until_complete(highrise_main(definitions))
            
        except Exception as e:
            print(f"[RUN] ❌ Error: {e}")
            traceback.print_exc()
            print(f"[RUN] 🔄 Reiniciando en 15 segundos...")
            time.sleep(15)

# ================== FLASK APP ==================
app = Flask(__name__)
app.secret_key = "nocturno_dj_secret_key_2024_ultra"

def allowed_file(filename):
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ================== TEMPLATES HTML ULTRA MEJORADOS ==================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nocturno DJ | Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-20px); }
        }
        
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(102, 126, 234, 0.4), 0 0 40px rgba(118, 75, 162, 0.2); }
            50% { box-shadow: 0 0 30px rgba(102, 126, 234, 0.6), 0 0 60px rgba(118, 75, 162, 0.4); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(-45deg, #0f0f0f, #1a1a2e, #16213e, #0f3460);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow: hidden;
        }
        
        body::before {
            content: '';
            position: absolute;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(102, 126, 234, 0.1), transparent);
            border-radius: 50%;
            top: -250px;
            left: -250px;
            animation: float 6s ease-in-out infinite;
        }
        
        body::after {
            content: '';
            position: absolute;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(118, 75, 162, 0.1), transparent);
            border-radius: 50%;
            bottom: -200px;
            right: -200px;
            animation: float 8s ease-in-out infinite;
        }
        
        .login-container {
            width: 380px;
            padding: 60px 45px;
            background: rgba(255,255,255,0.03);
            border-radius: 35px;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(25px);
            text-align: center;
            position: relative;
            z-index: 10;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            animation: fadeIn 0.8s ease;
        }
        
        .logo {
            width: 90px;
            height: 90px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            margin: 0 auto 35px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            animation: glow 3s ease-in-out infinite;
        }
        
        h1 {
            color: #fff;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: 1px;
        }
        
        .subtitle {
            color: rgba(255,255,255,0.6);
            font-size: 0.9rem;
            margin-bottom: 40px;
            font-weight: 300;
        }
        
        .input-group {
            position: relative;
            margin-bottom: 25px;
        }
        
        input[type="password"] {
            width: 100%;
            padding: 20px 25px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 18px;
            color: #fff;
            font-size: 1.1rem;
            text-align: center;
            letter-spacing: 10px;
            outline: none;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            font-family: 'Poppins', sans-serif;
        }
        
        input[type="password"]:focus {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.05);
            box-shadow: 0 0 25px rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
        }
        
        input::placeholder {
            letter-spacing: 3px;
            color: rgba(255,255,255,0.3);
        }
        
        .btn-login {
            width: 100%;
            padding: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 18px;
            color: #fff;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            margin-top: 15px;
            letter-spacing: 1px;
        }
        
        .btn-login:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.5);
        }
        
        .btn-login:active {
            transform: translateY(-1px);
        }
        
        .error {
            color: #ff6b6b;
            font-size: 0.9rem;
            margin-top: 20px;
            padding: 12px;
            background: rgba(255, 107, 107, 0.1);
            border-radius: 12px;
            border: 1px solid rgba(255, 107, 107, 0.3);
            animation: fadeIn 0.3s ease;
        }
        
        @media (max-width: 480px) {
            .login-container {
                width: 90%;
                padding: 50px 30px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🎧</div>
        <h1>Nocturno DJ</h1>
        <p class="subtitle">Panel de Control Premium</p>
        <form method="post">
            <div class="input-group">
                <input type="password" name="password" placeholder="******" maxlength="10" required autofocus>
            </div>
            <button type="submit" class="btn-login">Acceder al Panel</button>
        </form>
        {% if error %}
        <p class="error">🔒 {{ error }}</p>
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
    <title>Nocturno DJ | Control Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #00f2fe;
            --secondary: #4facfe;
            --accent: #764ba2;
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.8);
            --text: #f8fafc;
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        @keyframes gradientBg {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes musicWave {
            0%, 100% { height: 10px; }
            50% { height: 25px; }
        }

        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(-45deg, #0f172a, #1e293b, #0f3460, #16213e);
            background-size: 400% 400%;
            animation: gradientBg 15s ease infinite;
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }

        .stars {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
        }

        .star {
            position: absolute;
            width: 2px;
            height: 2px;
            background: white;
            border-radius: 50%;
            animation: twinkle 3s infinite;
        }

        @keyframes twinkle {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
            z-index: 10;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            animation: slideUp 0.6s ease;
        }

        .header h1 {
            font-size: 3rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            font-weight: 800;
            letter-spacing: 2px;
        }

        .header .subtitle {
            font-size: 1.1rem;
            color: rgba(248, 250, 252, 0.6);
            font-weight: 300;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 25px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            animation: slideUp 0.8s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 30px 80px rgba(0, 242, 254, 0.2);
            border-color: rgba(0, 242, 254, 0.3);
        }

        .card-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-title::before {
            content: '';
            width: 4px;
            height: 25px;
            background: linear-gradient(180deg, var(--primary), var(--secondary));
            border-radius: 2px;
        }

        /* NOW PLAYING CARD */
        .now-playing {
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.05), rgba(79, 172, 254, 0.05));
            border: 1px solid rgba(0, 242, 254, 0.3);
            grid-column: 1 / -1;
        }

        .track-info {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }

        .album-art {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            animation: pulse 2s infinite;
            box-shadow: 0 10px 30px rgba(0, 242, 254, 0.3);
        }

        .track-details {
            flex: 1;
        }

        .track-name {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 5px;
            word-break: break-word;
        }

        .track-artist {
            font-size: 0.95rem;
            color: rgba(248, 250, 252, 0.6);
        }

        .music-waves {
            display: flex;
            gap: 4px;
            align-items: center;
            height: 30px;
        }

        .wave-bar {
            width: 4px;
            background: linear-gradient(180deg, var(--primary), var(--secondary));
            border-radius: 2px;
            animation: musicWave 0.6s ease-in-out infinite;
        }

        .wave-bar:nth-child(2) { animation-delay: 0.1s; }
        .wave-bar:nth-child(3) { animation-delay: 0.2s; }
        .wave-bar:nth-child(4) { animation-delay: 0.3s; }
        .wave-bar:nth-child(5) { animation-delay: 0.4s; }

        .progress-section {
            margin-top: 20px;
        }

        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 10px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            width: 0%;
            transition: width 1s linear;
            box-shadow: 0 0 10px var(--primary);
        }

        .time-display {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: rgba(248, 250, 252, 0.6);
        }

        /* UPLOAD SECTION */
        .upload-card {
            background: linear-gradient(135deg, rgba(118, 75, 162, 0.05), rgba(102, 126, 234, 0.05));
            border: 1px solid rgba(118, 75, 162, 0.3);
        }

        .file-input-wrapper {
            position: relative;
            margin-bottom: 20px;
        }

        .file-input-wrapper input[type="file"] {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        .file-input-label {
            display: block;
            padding: 20px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 15px;
            text-align: center;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1.05rem;
        }

        .file-input-label:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(0, 242, 254, 0.4);
        }

        .selected-files {
            font-size: 0.9rem;
            color: rgba(248, 250, 252, 0.7);
            margin: 15px 0;
            min-height: 25px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .file-count {
            background: rgba(0, 242, 254, 0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            color: var(--primary);
        }

        .btn-upload {
            width: 100%;
            padding: 18px;
            background: rgba(0, 242, 254, 0.1);
            border: 2px solid var(--primary);
            border-radius: 15px;
            color: var(--primary);
            font-weight: 600;
            font-size: 1.05rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn-upload:hover:not(:disabled) {
            background: rgba(0, 242, 254, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 242, 254, 0.3);
        }

        .btn-upload:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .upload-status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 12px;
            font-size: 0.95rem;
            display: none;
            align-items: center;
            gap: 10px;
        }

        .upload-status.success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--success);
            display: flex;
        }

        .upload-status.error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--error);
            display: flex;
        }

        .upload-status.loading {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #60a5fa;
            display: flex;
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid currentColor;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* STATS CARD */
        .stats-card {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(52, 211, 153, 0.05));
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.03);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--success), #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stat-label {
            font-size: 0.85rem;
            color: rgba(248, 250, 252, 0.6);
            margin-top: 5px;
        }

        /* LIBRARY */
        .library-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .library-count {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 6px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }

        .music-list {
            max-height: 300px;
            overflow-y: auto;
            padding-right: 5px;
        }

        .music-list::-webkit-scrollbar {
            width: 6px;
        }

        .music-list::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }

        .music-list::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, var(--primary), var(--secondary));
            border-radius: 10px;
        }

        .music-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
            font-size: 0.95rem;
            color: rgba(248, 250, 252, 0.9);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .music-item:hover {
            background: rgba(0, 242, 254, 0.05);
            border-color: rgba(0, 242, 254, 0.3);
            transform: translateX(5px);
        }

        .music-item::before {
            content: '🎵';
            font-size: 1.2rem;
        }

        /* FOOTER */
        .footer {
            margin-top: 40px;
            padding: 30px;
            text-align: center;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .footer-info {
            font-size: 0.9rem;
            color: rgba(248, 250, 252, 0.5);
            margin-bottom: 15px;
        }

        .logout-btn {
            display: inline-block;
            padding: 12px 30px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 12px;
            color: var(--error);
            text-decoration: none;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .logout-btn:hover {
            background: rgba(239, 68, 68, 0.2);
            transform: translateY(-2px);
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }

            .track-name {
                font-size: 1.2rem;
            }
        }
    </style>
</head>
<body>
    <!-- Estrellas de fondo -->
    <div class="stars" id="stars"></div>

    <div class="container">
        <div class="header">
            <h1>🎧 NOCTURNO DJ</h1>
            <p class="subtitle">Control Panel Premium</p>
        </div>

        <div class="grid">
            <!-- NOW PLAYING -->
            <div class="card now-playing">
                <div class="card-title">En Vivo Ahora</div>
                <div class="track-info">
                    <div class="album-art">🎵</div>
                    <div class="track-details">
                        <div class="track-name" id="trackName">{{ current_song }}</div>
                        <div class="track-artist">Nocturno Radio</div>
                    </div>
                    <div class="music-waves">
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                        <div class="wave-bar"></div>
                    </div>
                </div>
                <div class="progress-section">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="time-display">
                        <span id="elapsed">0:00</span>
                        <span id="duration">0:00</span>
                    </div>
                </div>
            </div>

            <!-- STATS -->
            <div class="card stats-card">
                <div class="card-title">Estadísticas</div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="songCount">{{ total_songs }}</div>
                        <div class="stat-label">Canciones</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="queueCount">0</div>
                        <div class="stat-label">En Cola</div>
                    </div>
                </div>
            </div>

            <!-- UPLOAD -->
            <div class="card upload-card">
                <div class="card-title">Subir a MEGA</div>
                <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
                    <div class="file-input-wrapper">
                        <input type="file" name="file" id="fileInput" accept="audio/*" multiple>
                        <label for="fileInput" class="file-input-label">
                            📁 Seleccionar Archivos
                        </label>
                    </div>
                    <div class="selected-files" id="selectedFiles"></div>
                    <button type="submit" class="btn-upload" id="uploadBtn">
                        ☁️ Subir a MEGA
                    </button>
                </form>
                <div class="upload-status" id="uploadStatus"></div>
            </div>
        </div>

        <!-- LIBRARY -->
        <div class="card">
            <div class="library-header">
                <div class="card-title" style="margin: 0;">Biblioteca MEGA</div>
                <div class="library-count" id="libraryCount">{{ total_songs }} canciones</div>
            </div>
            <div class="music-list" id="musicList">
                {% for song in mega_music[:15] %}
                <div class="music-item">{{ song }}</div>
                {% endfor %}
                {% if mega_music|length > 15 %}
                <div class="music-item" style="justify-content: center; font-style: italic; opacity: 0.7;">
                    ... y {{ mega_music|length - 15 }} canciones más en MEGA
                </div>
                {% endif %}
            </div>
        </div>

        <div class="footer">
            <p class="footer-info">⚡ Nocturno DJ Bot v3.0 Ultra | Powered by MEGA</p>
            <a href="/logout" class="logout-btn">🚪 Cerrar Sesión</a>
        </div>
    </div>

    <script>
        // Generar estrellas
        const starsContainer = document.getElementById('stars');
        for (let i = 0; i < 100; i++) {
            const star = document.createElement('div');
            star.className = 'star';
            star.style.left = Math.random() * 100 + '%';
            star.style.top = Math.random() * 100 + '%';
            star.style.animationDelay = Math.random() * 3 + 's';
            starsContainer.appendChild(star);
        }

        // Formatear tiempo
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        // Actualizar "Now Playing"
        function updateNowPlaying() {
            fetch('/api/now_playing')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('trackName').textContent = data.track;
                    document.getElementById('elapsed').textContent = formatTime(data.elapsed);
                    document.getElementById('duration').textContent = formatTime(data.duration);
                    document.getElementById('queueCount').textContent = data.queue_count;
                    
                    const progress = data.duration > 0 ? (data.elapsed / data.duration) * 100 : 0;
                    document.getElementById('progressFill').style.width = progress + '%';
                })
                .catch(err => console.error('Error:', err));
        }

        setInterval(updateNowPlaying, 2000);
        updateNowPlaying();

        // Manejo de archivos
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            const selectedFiles = document.getElementById('selectedFiles');
            
            if (files.length > 0) {
                selectedFiles.innerHTML = `<span class="file-count">${files.length}</span> archivo(s) seleccionado(s)`;
            } else {
                selectedFiles.textContent = '';
            }
        });

        // Upload con feedback
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const files = document.getElementById('fileInput').files;
            const statusDiv = document.getElementById('uploadStatus');
            const uploadBtn = document.getElementById('uploadBtn');
            
            if (files.length === 0) {
                statusDiv.className = 'upload-status error';
                statusDiv.innerHTML = '<span>⚠️</span><span>Selecciona al menos un archivo</span>';
                return;
            }
            
            statusDiv.className = 'upload-status loading';
            statusDiv.innerHTML = '<div class="spinner"></div><span>Subiendo a MEGA...</span>';
            uploadBtn.disabled = true;
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusDiv.className = 'upload-status success';
                    statusDiv.innerHTML = `<span>✅</span><span>${data.message}</span>`;
                    document.getElementById('fileInput').value = '';
                    document.getElementById('selectedFiles').textContent = '';
                    
                    if (data.total_songs) {
                        document.getElementById('songCount').textContent = data.total_songs;
                        document.getElementById('libraryCount').textContent = data.total_songs + ' canciones';
                    }
                    
                    setTimeout(() => location.reload(), 2000);
                } else {
                    statusDiv.className = 'upload-status error';
                    statusDiv.innerHTML = `<span>❌</span><span>${data.message}</span>`;
                }
            })
            .catch(err => {
                statusDiv.className = 'upload-status error';
                statusDiv.innerHTML = '<span>❌</span><span>Error al subir archivos</span>';
                console.error('Error:', err);
            })
            .finally(() => {
                uploadBtn.disabled = false;
            });
        });
    </script>
</body>
</html>
"""

# ================== RUTAS ==================
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
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna canción"
    queue_count = radio.queue_requests.qsize() if hasattr(radio, 'queue_requests') else 0
    
    elapsed = 0
    duration = radio.current_duration if hasattr(radio, 'current_duration') and radio.current_duration else 0
    if hasattr(radio, 'track_start_time') and radio.track_start_time > 0:
        elapsed = int(time.time() - radio.track_start_time)
        if elapsed > duration:
            elapsed = duration
    
    return jsonify({
        "track": current_song, 
        "queue_count": queue_count,
        "elapsed": elapsed,
        "duration": duration
    })

@app.route("/")
@login_required
def index():
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna canción"
    
    # Obtener canciones de MEGA
    mega_music = []
    total_songs = 0
    try:
        if hasattr(radio, 'mega_files'):
            mega_music = [f["name"] for f in radio.mega_files]
            total_songs = len(mega_music)
    except:
        pass
    
    return render_template_string(HTML_TEMPLATE, 
                                 current_song=current_song, 
                                 mega_music=mega_music,
                                 total_songs=total_songs)

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
    try:
        files = request.files.getlist("file")
        
        if not files or files[0].filename == '':
            return jsonify({"success": False, "message": "No se seleccionaron archivos"}), 400
        
        uploaded_count = 0
        errors = []
        
        from mega_manager import MegaManager
        import io
        mega_mgr = MegaManager()
        
        for file in files:
            if file and file.filename:
                # Validar extensión
                if not allowed_file(file.filename):
                    errors.append(f"{file.filename}: Formato no permitido")
                    continue
                
                # Sanitizar nombre
                filename = secure_filename(file.filename)
                
                # Subir a MEGA
                try:
                    audio_io = io.BytesIO(file.read())
                    mega_mgr.upload_file(filename, audio_io)
                    uploaded_count += 1
                    print(f"[WEB] ☁️ Subido a MEGA: {filename}")
                except Exception as e:
                    errors.append(f"{filename}: Error ({str(e)})")
                    print(f"[WEB] ❌ Error subiendo {filename}: {e}")
        
        # Refrescar la radio
        if uploaded_count > 0:
            radio.load_local_music()
        
        # Contar total de canciones en MEGA
        total_songs = 0
        try:
            if hasattr(radio, 'mega_files'):
                total_songs = len(radio.mega_files)
        except:
            pass
        
        if uploaded_count > 0:
            message = f"{uploaded_count} archivo(s) subido(s) a MEGA"
            if errors:
                message += f" ({len(errors)} con errores)"
            return jsonify({
                "success": True, 
                "message": message,
                "uploaded": uploaded_count,
                "errors": errors,
                "total_songs": total_songs
            })
        else:
            return jsonify({
                "success": False,
                "message": "No se pudo subir ningún archivo",
                "errors": errors
            }), 400
            
    except Exception as e:
        print(f"[WEB] ❌ Error en upload: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error del servidor: {str(e)}"}), 500

# ================== INICIO ==================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎵 NOCTURNO DJ BOT ULTRA - MEGA EDITION")
    print("="*60)
    
    port = int(os.environ.get("PORT", 5000))
    
    if not radio_thread.is_alive():
        radio_thread.start()
    
    print(f"[RUN] 📻 Radio: ✓ Iniciada")
    print(f"[RUN] 🌐 Web: Puerto {port}")
    print(f"[RUN] ☁️ Almacenamiento: MEGA.nz")
    print(f"[RUN] 🔐 Password: {PASSWORD}")
    
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    print("[RUN] ✅ Web: ✓ Iniciado")
    
    print("\n" + "="*60)
    print("🤖 INICIANDO BOT DE HIGHRISE")
    print("="*60 + "\n")
    
    run_highrise_bot()
