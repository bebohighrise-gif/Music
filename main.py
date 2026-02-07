from highrise import BaseBot, User
import asyncio
import threading
import os
import json
from yt_dlp import YoutubeDL
from typing import Any
from radio import RadioStation, format_seconds

USERS_FILE = "users.json"
LIBRARY_FILE = "library.json"
FAVORITES_FILE = "favorites.json"
CONFIG_FILE = "config.json"
BANNED_FILE = "banned.json"

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file,data):
    try:
        with open(file,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
    except Exception as e:
        print(f"Error saving {file}: {e}")

def get_user_data(user_id):
    data = load_json(USERS_FILE)
    if user_id not in data:
        data[user_id] = {"gold":0,"requests":3,"history":[]}
        save_json(USERS_FILE, data)
    if "history" not in data[user_id]:
        data[user_id]["history"] = []
        save_json(USERS_FILE, data)
    return data[user_id]

def get_favorites(user_id):
    data = load_json(FAVORITES_FILE)
    return data.get(user_id, [])

def save_favorite(user_id, song_name):
    data = load_json(FAVORITES_FILE)
    if user_id not in data:
        data[user_id] = []
    if song_name not in data[user_id]:
        data[user_id].append(song_name)
        save_json(FAVORITES_FILE, data)
        return True
    return False

def clear_favorites(user_id):
    data = load_json(FAVORITES_FILE)
    if user_id in data:
        data[user_id] = []
        save_json(FAVORITES_FILE, data)

def add_to_history(user_id, song_name):
    data = load_json(USERS_FILE)
    if user_id not in data:
        data[user_id] = {"gold":0,"requests":3,"history":[]}
    if "history" not in data[user_id]:
        data[user_id]["history"] = []
    data[user_id]["history"].append(song_name)
    if len(data[user_id]["history"]) > 50:
        data[user_id]["history"] = data[user_id]["history"][-50:]
    save_json(USERS_FILE, data)

def is_banned(user_id):
    data = load_json(BANNED_FILE)
    return user_id in data.get("banned", [])

def ban_user(user_id):
    data = load_json(BANNED_FILE)
    if "banned" not in data:
        data["banned"] = []
    if user_id not in data["banned"]:
        data["banned"].append(user_id)
        save_json(BANNED_FILE, data)

def is_admin(user_id, radio):
    conf = load_json(CONFIG_FILE)
    return user_id == radio.owner_id or user_id in conf.get("admins", [])

def get_next_song_number():
    """Obtiene el siguiente número consecutivo para la canción"""
    return 1

def buscar_y_descargar(song_or_link):
    import io
    from mega_manager import MegaManager
    mega_mgr = MegaManager()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
    }
    search_query = song_or_link if song_or_link.startswith("http") else f"ytsearch1:{song_or_link}"
    try:
        print(f"[YT-DLP] Iniciando descarga en memoria para: {search_query}")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if not info: 
                return None
            entry = info['entries'][0] if 'entries' in info else info
            url = entry['url']
            title = entry.get('title', 'Unknown')
            
            # Streaming download using requests
            import requests
            response = requests.get(url, stream=True)
            audio_io = io.BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    audio_io.write(chunk)
            audio_io.seek(0)
            
            # Upload to Mega
            print(f"[MEGA] Subiendo a Mega.nz: {title}")
            mega_file = mega_mgr.upload_file(f"{title}.mp3", audio_io)
            
            if mega_file:
                return {
                    "id": mega_file['id'],
                    "name": title,
                    "duration": int(entry.get("duration", 0))
                }
            return None
    except Exception as e:
        print(f"[YT-DLP] Error crítico: {e}")
        return None

class HighriseBot(BaseBot):
    def __init__(self, radio_instance=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.radio = radio_instance
        if self.radio:
            self.radio.bot_instance = self
        self.bot_id = None
        self.loop = None
        self._tasks = []

    async def auto_messages_loop(self):
        while True:
            try:
                conf = load_json(CONFIG_FILE)
                auto_msg_full = conf.get("auto_message", "")
                interval = 300 # Default 5 min
                
                if auto_msg_full:
                    # Intentar extraer intervalo al final (ej: "hola 120")
                    parts = auto_msg_full.rsplit(" ", 1)
                    auto_msg = auto_msg_full
                    if len(parts) == 2 and parts[1].isdigit():
                        auto_msg = parts[0]
                        interval = int(parts[1])
                    
                    await self.highrise.chat(f"🔁 {auto_msg}")
                else:
                    await self.highrise.chat("🤖 Soy el DJ automático. Usa /help para ver mis comandos.")
                
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"[BOT] Error en auto_messages_loop: {e}")
                await asyncio.sleep(60)

    async def emote_loop(self):
        emotes = ["dance-handsup", "dance-casual", "dance-snake", "dance-sway", "dance-wrong"]
        while True:
            try:
                emote = emotes[0]
                await self.highrise.send_emote(emote)
            except Exception as e:
                print(f"[BOT] Error enviando emote: {e}")
            await asyncio.sleep(23.18)

    async def on_start(self, session_metadata: Any) -> None:
        try:
            self.bot_id = session_metadata.user_id
            self.loop = asyncio.get_event_loop()
            if self.radio:
                self.radio.bot_id = self.bot_id
                self.radio.bot_instance = self
            print(f"[BOT] 🤖 Bot iniciado con ID: {self.bot_id}")
            
            # Teletransportar a la posición de ancla si existe
            conf = load_json(CONFIG_FILE)
            spawn = conf.get("spawn_position")
            if spawn:
                try:
                    from highrise.models import Position
                    pos = Position(spawn["x"], spawn["y"], spawn["z"], spawn.get("facing", "FrontRight"))
                    await self.highrise.teleport(self.bot_id, pos)
                    print(f"[BOT] ⚓ Teletransportado a posición de ancla: {spawn['x']}, {spawn['y']}, {spawn['z']}")
                except Exception as e:
                    print(f"[BOT] Error teletransportando al ancla: {e}")

            for task in self._tasks:
                if not task.done():
                    task.cancel()
            self._tasks.clear()
            
            task1 = asyncio.create_task(self.auto_messages_loop())
            task2 = asyncio.create_task(self.emote_loop())
            self._tasks.extend([task1, task2])
            print("[BOT] 🔁 Bucles de mensajes y emotes iniciados.")
        except Exception as e:
            print(f"Error en on_start: {e}")

    async def on_user_join(self, user: User, position: Any) -> None:
        try:
            print(f"[BOT] 👤 Usuario unido: @{user.username}")
            # Restauramos la bienvenida con un delay ligero para no interferir con la ráfaga de audio inicial
            async def welcome():
                await asyncio.sleep(2.0) # Esperamos a que la ráfaga de audio (Burst) se complete
                await self.highrise.send_whisper(user.id, f"👋 Bienvenido @{user.username}\n🎶 Usa /play para pedir música")
            asyncio.create_task(welcome())
        except Exception as e:
            print(f"Error en on_user_join: {e}")

    async def on_chat(self, user: User, message: str) -> None:
        try:
            self.loop = asyncio.get_event_loop()
            if is_banned(user.id): return

            conf = load_json(CONFIG_FILE)
            # Volvemos a usar la lógica de admin vinculada a la radio si existe
            admin = user.id == (self.radio.owner_id if self.radio else "64dc252537db1cdb8e202d8d") or user.id in conf.get("admins", [])
            msg_lower = message.strip().lower()

            if message.startswith("/stream") and admin:
                # Obtener el dominio actual de la URL de Replit o Render de forma dinámica
                domain = os.environ.get('REPLIT_DEV_DOMAIN') or os.environ.get('RENDER_EXTERNAL_HOSTNAME')
                if not domain:
                    # Fallback por si no hay variables de entorno (por ejemplo, local con Replit)
                    domain = "localhost:5000"
                await self.highrise.send_whisper(user.id, f"🌐 Tu URL personalizada:\nhttps://{domain}/nocturno.mp3")

            elif message.startswith("/wallet"):
                # Cargamos datos de forma independiente
                user_data = get_user_data(user.id)
                await self.highrise.send_whisper(user.id, f"💰 @{user.username}, tienes {user_data['requests']} créditos para canciones.")

            elif message.startswith("/play"):
                song = message.split(" ", 1)[1].strip() if " " in message else ""
                if not song:
                    await self.highrise.chat("🎵 Usa: /play <nombre o link>")
                    return
                
                user_data = get_user_data(user.id)
                if not admin and user_data["requests"] <= 0:
                    await self.highrise.send_whisper(user.id, f"⛔ Límite alcanzado @{user.username}. Envía 10 de oro.")
                    return

                # El bot solo gestiona la descarga y el archivo, no el objeto radio
                # Simplemente avisamos que se ha añadido (la radio lo detectará por archivo)
                await self.highrise.send_whisper(user.id, "⏳ Preparando tu solicitud...")
                await self.highrise.send_whisper(user.id, f"<#FFD580>🎧 Buscando:\n{song}\n📡 Fuente: YouTube")
                threading.Thread(target=self.cmd_play_thread, args=(user, song, self.loop), daemon=True).start()

            elif message.startswith("/fav clear"):
                clear_favorites(user.id)
                await self.highrise.send_whisper(user.id, "⭐ Tus favoritos han sido eliminados.")

            elif msg_lower == "/fav":
                favs = get_favorites(user.id)
                if favs:
                    await self.highrise.send_whisper(user.id, f"⭐ Tus favoritos:\n" + "\n".join(f"• {f}" for f in favs[:10]))
                else:
                    await self.highrise.send_whisper(user.id, "⭐ No tienes canciones favoritas aún.")

            elif message.startswith("/favr"):
                song_name = message.split(" ", 1)[1].strip() if " " in message else ""
                if song_name:
                    if save_favorite(user.id, song_name):
                        await self.highrise.send_whisper(user.id, f"⭐ '{song_name}' añadido a favoritos.")
                    else:
                        await self.highrise.send_whisper(user.id, f"⭐ '{song_name}' ya está en favoritos.")
                else:
                    await self.highrise.send_whisper(user.id, "⭐ Usa: /favr <nombre de canción>")

            elif message.startswith("/profile"):
                user_data = get_user_data(user.id)
                history = user_data.get("history", [])
                if history:
                    for song in history[-10:]:
                        await self.highrise.send_whisper(user.id, f"👤 🎵 {song}")
                else:
                    await self.highrise.send_whisper(user.id, "👤 No has pedido canciones aún.")

            elif message.startswith("/q"):
                if self.radio:
                    cola = list(self.radio.queue_requests.queue) if hasattr(self.radio.queue_requests, 'queue') else []
                    
                    if cola:
                        msg = "👣 Cola de pedidos:\n" + "\n".join(f"{i+1}. {t.get('name','?')} (@{t.get('username','?')})" for i, t in enumerate(cola[:10]))
                        await self.highrise.chat(msg)
                    else:
                        await self.highrise.chat("👣 No hay pedidos en cola.")
                else:
                    await self.highrise.chat("🎵 Revisa la cola en el Panel Web.")

            elif message.startswith("/pedidos"):
                user_data = get_user_data(user.id)
                await self.highrise.send_whisper(user.id, f"📋 Tienes {user_data['requests']} pedidos activos.")

            elif msg_lower == "/help":
                try:
                    if admin:
                        admin_help = (
                            "📖 COMANDOS ADMIN:\n"
                            "• /room <id> - Cambiar sala\n"
                            "• /next - Saltar canción\n"
                            "• /prev - Canción anterior\n"
                            "• /pause | /resume\n"
                            "• /auto <msg> | /autostop\n"
                            "• /copy - Copiar outfit\n"
                            "• /delete @user - Bloquear\n"
                            "• /stream - URL Radio\n"
                            "• /ancla - Posición bot"
                        )
                        await self.highrise.send_whisper(user.id, admin_help)
                    
                    help_msg = (
                        "❓ COMANDOS:\n"
                        "• /play <nombre> - Pedir música\n"
                        "• /q - Ver la cola\n"
                        "• /fav | /favr <nombre>\n"
                        "• /profile - Historial\n"
                        "• /pedidos - Ver créditos"
                    )
                    await self.highrise.send_whisper(user.id, help_msg)
                except Exception as e:
                    print(f"[BOT] Error en /help: {e}")

            elif message.startswith("/stop") and admin:
                if self.radio:
                    self.radio.skip_current = True
                    self.radio.running = False
                    await self.highrise.chat("⏸️ Reproducción detenida y radio apagada.")
                else:
                    await self.highrise.chat("⏸️ Usa el Panel Web.")

            elif message.startswith("/next") and admin:
                if self.radio:
                    self.radio.skip_current = True
                    self.radio.current_track = None
                    await self.highrise.chat("⏭️ Siguiente...")
                else:
                    await self.highrise.chat("⏭️ Usa el Panel Web.")

            elif message.startswith("/prev") and admin:
                if self.radio and self.radio.previous_track:
                    self.radio.add_to_queue(self.radio.previous_track)
                    self.radio.skip_current = True
                    await self.highrise.chat("⏮️ Volviendo a la canción anterior...")
                else:
                    await self.highrise.chat("⏮️ No hay canción anterior o radio no disponible.")

            elif message.startswith("/pause") and admin:
                if self.radio:
                    self.radio.paused = True
                    await self.highrise.chat("⏸️ Música pausada.")
                else:
                    await self.highrise.chat("⏸️ Usa el Panel Web.")

            elif message.startswith("/resume") and admin:
                if self.radio:
                    self.radio.paused = False
                    await self.highrise.chat("▶️ Música reanudada.")
                else:
                    await self.highrise.chat("▶️ Usa el Panel Web.")

            elif message.startswith("/auto") and admin:
                msg_auto = message.split(" ", 1)[1].strip() if " " in message else ""
                if msg_auto:
                    conf = load_json(CONFIG_FILE)
                    conf["auto_message"] = msg_auto
                    save_json(CONFIG_FILE, conf)
                    await self.highrise.chat(f"🔁 Mensaje automático configurado: {msg_auto}")
                else:
                    await self.highrise.chat("🔁 Usa: /auto <mensaje>")

            elif message.startswith("/autostop") and admin:
                conf = load_json(CONFIG_FILE)
                conf["auto_message"] = ""
                save_json(CONFIG_FILE, conf)
                await self.highrise.chat("🛑 Mensaje automático detenido.")

            elif message.startswith("/copy") and admin:
                try:
                    from highrise.models import GetOutfitRequest
                    response = await self.highrise.get_user_outfit(user.id)
                    # Check if response is a GetOutfitRequest.GetOutfitResponse and not an Error
                    if hasattr(response, 'outfit'):
                        await self.highrise.set_outfit(response.outfit)
                        await self.highrise.chat(f"👤 He copiado el outfit de @{user.username}")
                    else:
                        await self.highrise.chat("👤 No se pudo obtener el outfit.")
                except Exception as e:
                    print(f"[BOT] Error en /copy: {e}")
                    await self.highrise.chat("👤 No se pudo copiar el outfit.")

            elif message.startswith("/cambiar") and admin:
                try:
                    precio = int(message.split(" ", 1)[1].strip())
                    conf = load_json(CONFIG_FILE)
                    conf["request_price"] = precio
                    save_json(CONFIG_FILE, conf)
                    await self.highrise.chat(f"💰 Precio de pedido cambiado a {precio} oro.")
                except:
                    await self.highrise.chat("💰 Usa: /cambiar <número>")

            elif message.startswith("/delete") and admin:
                parts = message.split()
                if len(parts) >= 2:
                    target = parts[1].replace("@", "")
                    try:
                        from highrise.models import GetRoomUsersRequest
                        response = await self.highrise.get_room_users()
                        # Check if response is GetRoomUsersRequest.GetRoomUsersResponse
                        if hasattr(response, 'content'):
                            for room_user, _ in response.content:
                                if room_user.username.lower() == target.lower():
                                    ban_user(room_user.id)
                                    await self.highrise.chat(f"❌ @{target} ha sido bloqueado del bot.")
                                    return
                            await self.highrise.chat(f"❌ Usuario @{target} no encontrado.")
                        else:
                            await self.highrise.chat("❌ Error al obtener usuarios de la sala.")
                    except:
                        await self.highrise.chat("❌ Error al buscar usuario.")
                else:
                    await self.highrise.chat("❌ Usa: /delete @usuario")

            elif message.startswith("/room") and admin:
                try:
                    target_room = message.split(" ", 1)[1].strip() if " " in message else ""
                    if not target_room:
                        await self.highrise.chat("🏠 Usa: /room <ID de sala>")
                        return
                    await self.highrise.chat(f"🚀 Cambiando a la sala {target_room} en 10 segundos...")
                    conf = load_json(CONFIG_FILE)
                    conf["room_id"] = target_room
                    save_json(CONFIG_FILE, conf)
                    await asyncio.sleep(10)
                    os._exit(0)
                except Exception as e:
                    print(f"[BOT] Error en /room: {e}")
                    await self.highrise.chat("🏠 Error al cambiar de sala.")

            elif message.startswith("/ancla") and admin:
                try:
                    from highrise.models import GetRoomUsersRequest, Position
                    # Obtener la posición actual del admin que ejecutó el comando
                    response = await self.highrise.get_room_users()
                    # Check if response is GetRoomUsersRequest.GetRoomUsersResponse
                    if hasattr(response, 'content'):
                        for room_user, position in response.content:
                            if room_user.id == user.id:
                                # Acceder a los atributos de la posición de forma segura
                                px = getattr(position, 'x', None)
                                py = getattr(position, 'y', None)
                                pz = getattr(position, 'z', None)
                                facing = getattr(position, 'facing', 'FrontRight')
                                
                                if px is not None and py is not None and pz is not None:
                                    conf = load_json(CONFIG_FILE)
                                    conf["spawn_position"] = {
                                        "x": px,
                                        "y": py,
                                        "z": pz,
                                        "facing": facing
                                    }
                                    save_json(CONFIG_FILE, conf)
                                    
                                    # Teletransportar de inmediato
                                    pos = Position(px, py, pz, facing)
                                    if self.bot_id:
                                        await self.highrise.teleport(self.bot_id, pos)
                                    
                                    await self.highrise.chat(f"⚓ Posición de ancla guardada y bot teletransportado a: {px}, {py}, {pz}")
                                    return
                        await self.highrise.chat("⚓ No pude detectar tu posición actual.")
                    else:
                        await self.highrise.chat("⚓ Error al obtener usuarios de la sala.")
                except Exception as e:
                    print(f"[BOT] Error en /ancla: {e}")
                    await self.highrise.chat("⚓ Error al guardar el ancla.")

            elif message.startswith("/now"):
                if self.radio and self.radio.current_track:
                    duration_str = format_seconds(self.radio.current_duration)
                    await self.highrise.send_whisper(user.id, f"📻 Sonando ahora: {self.radio.current_track['name']}\n⏱️ Duración: {duration_str}")
                else:
                    await self.highrise.send_whisper(user.id, "📻 No hay música sonando ahora.")

        except Exception as e:
            print(f"Error en on_chat: {e}")

    async def on_tip(self, sender: User, receiver: User, tip: Any) -> None:
        # El bot ya no necesita saber su propio ID desde la radio
        if receiver.id == self.bot_id:
            if tip.amount < 10:
                await self.highrise.send_whisper(sender.id, f"⚠️ @{sender.username}, debes enviar al menos 10 de oro para obtener pedidos (10, 20, 30...).")
                return
            data = load_json(USERS_FILE)
            if sender.id not in data:
                data[sender.id] = {"gold": 0, "requests": 0, "history": []}
            multiplo_10 = tip.amount // 10
            nuevos_pedidos = multiplo_10 * 3
            data[sender.id]["requests"] += nuevos_pedidos
            save_json(USERS_FILE, data)
            await self.highrise.send_whisper(sender.id, f"✅ @{sender.username}, recibidos {tip.amount} oro. Se han validado {multiplo_10 * 10} oro para +{nuevos_pedidos} pedidos!")

    def cmd_play_thread(self, user, song, loop):
        try:
            track = buscar_y_descargar(song)
            if track:
                track["username"] = user.username
                if self.radio:
                    self.radio.add_to_queue(track)
                add_to_history(user.id, track['name'])
                duration_str = format_seconds(track['duration'])
                asyncio.run_coroutine_threadsafe(self.highrise.send_whisper(user.id, f"<#90EE90>💾 Descargado:\n{track['name']}\n⏳ Duración: ({duration_str})"), loop)
                msg_pub = (f"<#FF69B4>🎵 Pedido añadido:\n" f"<#FF69B4>{track['name']}\n" f"<#FF69B4>⏱️ Duración: ({duration_str})\n" f"<#FF69B4>👤 Por: @{user.username}")
                asyncio.run_coroutine_threadsafe(self.highrise.chat(msg_pub), loop)
            else:
                asyncio.run_coroutine_threadsafe(self.highrise.send_whisper(user.id, f"❌ No encontré o no pude descargar: {song}"), loop)
        except Exception as e:
            print(f"Error en cmd_play_thread: {e}")

class Bot(HighriseBot):
    pass
