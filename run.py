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

# ================== CONFIGURACIÓN DE SEGURIDAD ==================
# IMPORTANTE: Configurar estas variables de entorno en producción
PASSWORD = os.environ.get("ADMIN_PASSWORD", "070927")  # CAMBIAR EN PRODUCCIÓN
MUSIC_FOLDER = "music"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB por archivo
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.aiff', '.opus', '.amr'}

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

# Cargar configuración una sola vez
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
                print("[RUN] ⚠️  El bot no puede iniciar sin este archivo")
                time.sleep(60)
                continue
            
            from main import Bot
            from highrise.__main__ import BotDefinition, main as highrise_main
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Validar configuración
            if "room_id" not in config or not config["room_id"]:
                print("[RUN] ❌ ERROR: 'room_id' no está configurado en config.json")
                time.sleep(60)
                continue
                
            if "api_token" not in config or not config["api_token"]:
                print("[RUN] ❌ ERROR: 'api_token' no está configurado en config.json")
                time.sleep(60)
                continue
                
            room_id = config["room_id"]
            api_token = config["api_token"]
            
            print(f"[RUN] 🔑 Room ID: {room_id[:20]}..." if len(room_id) > 20 else f"[RUN] 🔑 Room ID: {room_id}")
            print(f"[RUN] 🔐 Token configurado: {'✓' if api_token else '✗'}")
            
            print("[RUN] 🎵 Creando instancia del Bot con radio...")
            bot = Bot(radio_instance=radio)
            
            print("[RUN] 📋 Creando BotDefinition...")
            definitions = [BotDefinition(bot, room_id, api_token)]
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except Exception:
                pass
                
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

# ================== FLASK APP ==================
app = Flask(__name__)
# Usar variable de entorno o generar clave aleatoria
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24).hex()

# ================== VALIDACIÓN DE ARCHIVOS ==================
def allowed_file(filename):
    """Valida que el archivo tenga una extensión permitida"""
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Valida que el archivo no exceda el tamaño máximo"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= MAX_FILE_SIZE

# ================== DECORADORES ==================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ================== TEMPLATES HTML ==================
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

        * { margin: 0; padding: 0; box-sizing: border-box; }

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
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 500px;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            text-align: center;
        }

        @media (max-width: 600px) {
            .container {
                padding: 30px 20px;
                border-radius: 16px;
            }
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
            transition: all 0.3s ease;
        }

        .progress-bar {
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            margin-top: 15px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            width: 0%;
            transition: width 1s linear;
        }

        .time-display {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: rgba(248, 250, 252, 0.5);
            margin-top: 8px;
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
            width: 100%;
        }

        .file-input-wrapper input[type="file"] {
            position: absolute;
            opacity: 0;
            cursor: pointer;
            width: 100%;
            height: 100%;
        }

        .file-input-label {
            display: block;
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

        .selected-files {
            font-size: 0.85rem;
            color: rgba(248, 250, 252, 0.7);
            margin-top: 8px;
            min-height: 20px;
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

        .btn-upload:hover:not(:disabled) {
            background: rgba(0, 242, 254, 0.2);
            transform: translateY(-2px);
        }

        .btn-upload:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .upload-status {
            margin-top: 15px;
            padding: 12px;
            border-radius: 8px;
            font-size: 0.9rem;
            display: none;
        }

        .upload-status.success {
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            color: #4ade80;
            display: block;
        }

        .upload-status.error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
            display: block;
        }

        .upload-status.loading {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #60a5fa;
            display: block;
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
            <div class="track-name" id="trackName">{{ current_song }}</div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="time-display">
                <span id="elapsed">0:00</span>
                <span id="duration">0:00</span>
            </div>
        </div>

        <div class="upload-section">
            <h3>📤 Subir Música</h3>
            <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
                <div class="file-input-wrapper">
                    <input type="file" name="file" id="fileInput" accept="audio/*" multiple>
                    <label for="fileInput" class="file-input-label">
                        Seleccionar Archivos
                    </label>
                </div>
                <div class="selected-files" id="selectedFiles"></div>
                <button type="submit" class="btn-upload" id="uploadBtn">Subir</button>
            </form>
            <div class="upload-status" id="uploadStatus"></div>
        </div>

        <div class="music-list">
            <h3>📁 Biblioteca (<span id="songCount">{{ local_music|length }}</span> canciones)</h3>
            <div id="musicList">
                {% for song in local_music[:10] %}
                <div class="music-item">{{ song }}</div>
                {% endfor %}
                {% if local_music|length > 10 %}
                <div class="music-item" style="text-align: center; font-style: italic;">
                    ... y {{ local_music|length - 10 }} canciones más
                </div>
                {% endif %}
            </div>
        </div>

        <div class="footer">
            <p>Nocturno DJ Bot v2.1 Pro</p>
            <a href="/logout" class="logout-btn">Cerrar Sesión</a>
        </div>
    </div>

    <script>
        // Auto-actualización del "Now Playing"
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        function updateNowPlaying() {
            fetch('/api/now_playing')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('trackName').textContent = data.track;
                    document.getElementById('elapsed').textContent = formatTime(data.elapsed);
                    document.getElementById('duration').textContent = formatTime(data.duration);
                    
                    const progress = data.duration > 0 ? (data.elapsed / data.duration) * 100 : 0;
                    document.getElementById('progressFill').style.width = progress + '%';
                })
                .catch(err => console.error('Error al actualizar:', err));
        }

        // Actualizar cada 2 segundos
        setInterval(updateNowPlaying, 2000);
        updateNowPlaying();

        // Mostrar archivos seleccionados
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            const selectedFiles = document.getElementById('selectedFiles');
            
            if (files.length > 0) {
                selectedFiles.textContent = `${files.length} archivo(s) seleccionado(s)`;
            } else {
                selectedFiles.textContent = '';
            }
        });

        // Manejo del formulario de subida con feedback
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const files = document.getElementById('fileInput').files;
            const statusDiv = document.getElementById('uploadStatus');
            const uploadBtn = document.getElementById('uploadBtn');
            
            if (files.length === 0) {
                statusDiv.className = 'upload-status error';
                statusDiv.textContent = '⚠️ Selecciona al menos un archivo';
                return;
            }
            
            // Mostrar estado de carga
            statusDiv.className = 'upload-status loading';
            statusDiv.textContent = '⏳ Subiendo archivos...';
            uploadBtn.disabled = true;
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusDiv.className = 'upload-status success';
                    statusDiv.textContent = `✅ ${data.message}`;
                    document.getElementById('fileInput').value = '';
                    document.getElementById('selectedFiles').textContent = '';
                    
                    // Actualizar contador de canciones
                    if (data.total_songs) {
                        document.getElementById('songCount').textContent = data.total_songs;
                    }
                    
                    // Recargar la página después de 2 segundos
                    setTimeout(() => location.reload(), 2000);
                } else {
                    statusDiv.className = 'upload-status error';
                    statusDiv.textContent = `❌ ${data.message}`;
                }
            })
            .catch(err => {
                statusDiv.className = 'upload-status error';
                statusDiv.textContent = '❌ Error al subir archivos';
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
    current_song = radio.current_track["name"] if radio.current_track else "Ninguna"
    queue_count = radio.queue_requests.qsize()
    
    elapsed = 0
    duration = radio.current_duration if radio.current_duration else 0
    if radio.track_start_time > 0:
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
                
                # Validar tamaño
                if not validate_file_size(file):
                    errors.append(f"{file.filename}: Excede el tamaño máximo (50MB)")
                    continue
                
                # Sanitizar nombre de archivo
                filename = secure_filename(file.filename)
                
                # Subir a Mega
                try:
                    audio_io = io.BytesIO(file.read())
                    mega_mgr.upload_file(filename, audio_io)
                    uploaded_count += 1
                    print(f"[WEB] Archivo subido a Mega: {filename}")
                except Exception as e:
                    errors.append(f"{filename}: Error al subir ({str(e)})")
                    print(f"[WEB] Error al subir {filename}: {e}")
        
        # Refrescar la radio
        if uploaded_count > 0:
            radio.load_local_music()
        
        # Contar total de canciones
        valid_extensions = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff", ".opus", ".amr")
        total_songs = len([f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(valid_extensions)])
        
        # Preparar respuesta
        if uploaded_count > 0:
            message = f"{uploaded_count} archivo(s) subido(s) correctamente"
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
        print(f"[WEB] Error en upload: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error del servidor: {str(e)}"}), 500

# ================== INICIO DE LA APLICACIÓN ==================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎵 NOCTURNO DJ BOT PRO - INICIANDO SERVICIOS")
    print("="*60)
    
    # Configuración de puerto para Railway/Replit
    port = int(os.environ.get("PORT", 5000))
    
    # Asegurar que la radio esté iniciada
    if not radio_thread.is_alive():
        radio_thread.start()
    
    print(f"[RUN] 📻 Radio: ✓ Iniciada")
    print(f"[RUN] 🌐 Servidor Web: Puerto {port}")
    print(f"[RUN] 🔐 Seguridad: Variables de entorno {'configuradas' if os.environ.get('SECRET_KEY') else 'usando valores por defecto'}")
    
    # NOTA: Para producción, usar Gunicorn en lugar de app.run()
    # Comando: gunicorn -w 4 -b 0.0.0.0:$PORT run_mejorado_pro:app
    
    # Iniciar Flask en un hilo separado
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    print("[RUN] ✅ Servidor Web: ✓ Iniciado")
    
    print("\n" + "="*60)
    print("🤖 INICIANDO BOT DE HIGHRISE")
    print("="*60 + "\n")
    
    # El bot se ejecuta en el hilo principal
    run_highrise_bot()
