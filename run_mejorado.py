from radio import RadioStation
import threading
import asyncio
import json
import time
import traceback  # AGREGADO: para ver errores completos
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
    intentos = 0
    while True: # Bucle de autoreinicio en caso de desconexión
        try:
            intentos += 1
            print(f"[RUN] 🔄 Intento #{intentos} de conexión...")
            
            # MEJORA: Verificar que existan los archivos necesarios
            if not os.path.exists("main.py"):
                print("[RUN] ❌ ERROR CRÍTICO: No existe el archivo 'main.py'")
                print("[RUN] ⚠️  El bot no puede iniciar sin este archivo")
                time.sleep(60)
                continue
            
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
            
            # MEJORA: Validar configuración
            if "room_id" not in current_config or not current_config["room_id"]:
                print("[RUN] ❌ ERROR: 'room_id' no está configurado en config.json")
                time.sleep(60)
                continue
                
            if "api_token" not in current_config or not current_config["api_token"]:
                print("[RUN] ❌ ERROR: 'api_token' no está configurado en config.json")
                time.sleep(60)
                continue
                
            room_id = current_config["room_id"]
            api_token = current_config["api_token"]
            
            print(f"[RUN] 🔑 Room ID: {room_id[:20]}..." if len(room_id) > 20 else f"[RUN] 🔑 Room ID: {room_id}")
            print(f"[RUN] 🔐 Token configurado: {'✓' if api_token else '✗'}")
            
            # Pasar la instancia de radio al bot
            print("[RUN] 🎵 Creando instancia del Bot con radio...")
            bot = Bot(radio_instance=radio)
            
            print("[RUN] 📋 Creando BotDefinition...")
            definitions = [BotDefinition(bot, room_id, api_token)]
            
            # Check if there is an existing event loop and close it if necessary
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except Exception:
                pass
                
            # Crear un loop nuevo y limpio para cada intento
            print("[RUN] 🔄 Configurando event loop...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print("[RUN] 🚀 Ejecutando bot de Highrise...")
            loop.run_until_complete(highrise_main(definitions))
            
        except ImportError as e:
            print(f"[RUN] ❌ ERROR DE IMPORTACIÓN: {e}")
            print(f"[RUN] 📝 Detalles completos del error:")
            traceback.print_exc()
            print(f"[RUN] ⚠️  Revisa que existan los archivos 'main.py' y 'radio.py'")
            print(f"[RUN] ⚠️  Y que el paquete 'highrise' esté instalado: pip install highrise-bot-sdk")
            time.sleep(60)
            
        except KeyError as e:
            print(f"[RUN] ❌ ERROR EN CONFIG.JSON: Falta la clave {e}")
            print(f"[RUN] 📝 Asegúrate de que config.json tenga 'room_id' y 'api_token'")
            traceback.print_exc()
            time.sleep(60)
            
        except Exception as e:
            print(f"[RUN] ❌ El bot se desconectó o falló: {e}")
            print(f"[RUN] 📝 Detalles completos del error:")
            traceback.print_exc()
            print(f"[RUN] 🔄 Reiniciando en 15 segundos...")
            time.sleep(15)

# El bot ahora se inicia al final de run.py en el bloque if __name__ == "__main__":
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
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .subtitle {
            font-size: 1rem;
            color: rgba(248, 250, 252, 0.6);
            margin-bottom: 30px;
        }

        .playing-now {
            background: rgba(0, 242, 254, 0.05);
            border: 1px solid rgba(0, 242, 254, 0.2);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 30px;
        }

        .playing-now h2 {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--primary);
            margin-bottom: 10px;
        }

        .track-name {
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text);
        }

        .upload-section {
            margin-top: 30px;
        }

        .upload-section h3 {
            font-size: 1.2rem;
            margin-bottom: 15px;
        }

        .file-input-wrapper {
            position: relative;
            display: inline-block;
            cursor: pointer;
            margin-bottom: 15px;
        }

        .file-input-wrapper input[type="file"] {
            position: absolute;
            opacity: 0;
            cursor: pointer;
            width: 100%;
            height: 100%;
        }

        .file-input-label {
            display: inline-block;
            padding: 14px 32px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .file-input-label:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 242, 254, 0.3);
        }

        .btn-upload {
            width: 100%;
            padding: 16px;
            background: rgba(0, 242, 254, 0.1);
            border: 1px solid var(--primary);
            border-radius: 12px;
            color: var(--primary);
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn-upload:hover {
            background: rgba(0, 242, 254, 0.2);
            transform: translateY(-2px);
        }

        .music-list {
            margin-top: 30px;
            text-align: left;
        }

        .music-list h3 {
            font-size: 1.2rem;
            margin-bottom: 15px;
            text-align: center;
        }

        .music-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 8px;
            font-size: 0.9rem;
            color: rgba(248, 250, 252, 0.9);
        }

        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 0.85rem;
            color: rgba(248, 250, 252, 0.5);
        }

        .logout-btn {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: rgba(248, 250, 252, 0.7);
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }

        .logout-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎧 DJ Bot</h1>
        <p class="subtitle">Control Panel</p>

        <div class="playing-now">
            <h2>Reproduciendo ahora</h2>
            <div class="track-name">{{ current_song }}</div>
        </div>

        <div class="upload-section">
            <h3>📤 Subir Música</h3>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <div class="file-input-wrapper">
                    <input type="file" name="file" id="fileInput" accept="audio/*" multiple>
                    <label for="fileInput" class="file-input-label">
                        Seleccionar Archivos
                    </label>
                </div>
                <button type="submit" class="btn-upload">Subir</button>
            </form>
        </div>

        <div class="music-list">
            <h3>📁 Biblioteca ({{ local_music|length }} canciones)</h3>
            {% for song in local_music[:10] %}
            <div class="music-item">{{ song }}</div>
            {% endfor %}
            {% if local_music|length > 10 %}
            <div class="music-item" style="text-align: center; font-style: italic;">
                ... y {{ local_music|length - 10 }} canciones más
            </div>
            {% endif %}
        </div>

        <div class="footer">
            <p>Nocturno DJ Bot v2.0</p>
            <a href="/logout" class="logout-btn">Cerrar Sesión</a>
        </div>
    </div>
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

@app.route("/")
@login_required
def index():
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna"
    valid_extensions = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff", ".opus", ".amr")
    def sort_key(x):
        prefix = x.split('.')[0]
        return (int(prefix), x) if prefix.isdigit() else (float('inf'), x)

    local_music = sorted([f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(valid_extensions)], key=sort_key)
    return render_template_string(HTML_TEMPLATE, current_song=current_song, local_music=local_music)

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
    print("\n" + "="*60)
    print("🎵 NOCTURNO DJ BOT - INICIANDO SERVICIOS")
    print("="*60)
    
    # Configuración de puerto para Railway/Replit
    port = int(os.environ.get("PORT", 5000))
    
    # Asegurar que la radio esté iniciada
    if not radio_thread.is_alive():
        radio_thread.start()
    
    print(f"[RUN] 📻 Radio: ✓ Iniciada")
    print(f"[RUN] 🌐 Servidor Web: Puerto {port}")
    
    # Iniciar Flask en un hilo separado para que no bloquee al bot
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    print("[RUN] ✅ Servidor Web: ✓ Iniciado")
    
    print("\n" + "="*60)
    print("🤖 INICIANDO BOT DE HIGHRISE")
    print("="*60 + "\n")
    
    # ESTO ES LO MÁS IMPORTANTE: El bot se ejecuta en el hilo principal
    run_highrise_bot()
