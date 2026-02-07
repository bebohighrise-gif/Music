import os, time, random, json, io
from queue import Queue
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

MUSIC_FOLDER = "music"

def format_seconds(seconds):
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"

def remove_silence(audio, silence_thresh=-50):
    """Elimina silencio al inicio y final del audio"""
    # Detectar silencio al inicio
    start_trim = detect_leading_silence(audio, silence_threshold=silence_thresh)
    # Detectar silencio al final (invertir, detectar, invertir)
    end_trim = detect_leading_silence(audio.reverse(), silence_threshold=silence_thresh)
    
    duration = len(audio)
    # Asegurar que no recortamos demasiado
    if start_trim + end_trim >= duration:
        return audio
    
    return audio[start_trim:duration-end_trim]

class RadioStation:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RadioStation, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        # Cargar crossfade desde config
        try:
            with open("config.json", "r") as f:
                conf = json.load(f)
                self.crossfade = conf.get("crossfade", 10) # segundos
        except:
            self.crossfade = 10
            
        self.queue_requests = Queue()  # Pedidos de usuarios
        self.queue_local = []          # Música local (orden fijo)
        self._already_running = False  # Asegurar que solo corra un bucle
        self.running = True
        self.current_track = None
        self.skip_current = False
        self.owner_id = "64dc252537db1cdb8e202d8d"
        self.bot_wallet = 0
        self.bot_id = None
        self.played_indices = []
        self.bot_instance = None
        self.stream_played_track = None
        self.paused = False
        self.previous_track = None
        self.history = []
        self.track_start_time = 0
        self.current_duration = 0
        self.initialized = True
        
        # 🟢 BUFFER GLOBAL DE AUDIO PARA NUEVOS CLIENTES
        self.pre_buffer = bytearray()
        self.pre_buffer_size = 640000 # ~40 segundos de audio a 128k para asegurar ráfaga instantánea
        self.clients = [] # Lista de colas para cada cliente conectado
        self.load_local_music() # Cargamos desde Drive

    def _load_audio(self, track):
        """Carga un audio desde Mega.nz"""
        from mega_manager import MegaManager
        import io
        
        print(f"[RADIO] Cargando audio desde Mega: {track['name']}")
        mega_mgr = MegaManager()
        audio_io = mega_mgr.download_file(track['name'])
        if not audio_io:
            raise Exception("No se pudo descargar de Mega")
            
        audio = AudioSegment.from_file(audio_io)
        audio = remove_silence(audio)
        return audio

    def load_local_music(self):
        """Carga música desde Mega.nz"""
        from mega_manager import MegaManager
        mega_mgr = MegaManager()
        new_local = []
        try:
            files = mega_mgr.list_files()
            for file in files:
                new_local.append({
                    "id": file['id'],
                    "url": file['link'],
                    "name": file['name'],
                    "user": "Mega",
                    "username": "System",
                    "duration": 0
                })
            self.queue_local = new_local
            print(f"[RADIO] {len(self.queue_local)} canciones cargadas desde Mega")
        except Exception as e:
            print(f"[RADIO] Error cargando música de Mega: {e}")

    def add_to_queue(self, track):
        print(f"[RADIO] 📥 Agregando pedido a queue_requests: {track['name']}")
        self.queue_requests.put(track)

    def _get_next_track(self, local_index):
        """Obtiene la siguiente pista de la cola: Pedidos primero, si no hay pedidos, local"""
        if not self.queue_requests.empty():
            return self.queue_requests.get(), local_index, "request"
        elif self.queue_local:
            # Ordenamos la música local por nombre para asegurar que 1, 2, 3... funcione
            self.queue_local.sort(key=lambda x: x['name'])
            if local_index >= len(self.queue_local):
                local_index = 0
            track = self.queue_local[local_index]
            return track, local_index + 1, "local"
        return None, local_index, None

    def start(self):
        import asyncio
        if hasattr(self, "_already_running") and self._already_running:
            print("[RADIO] ⚠️ El bucle de radio ya está activo. Evitando duplicación.")
            return
        self._already_running = True
        
        local_index = 0
        next_audio_cache = None
        next_track_cache = None
        next_source_cache = None
        
        while self.running:
            track = None
            source = None
            
            # 1️⃣ Obtener la pista actual (PRIORIDAD: pedidos siempre primero)
            # Verificar si hay pedido nuevo aunque ya tengamos algo precargado
            if not self.queue_requests.empty():
                new_request = self.queue_requests.get()
                # Si teníamos algo precargado local, lo descartamos por el pedido
                if next_track_cache and next_source_cache == "local":
                    print(f"[RADIO] ⚡ Nuevo pedido reemplaza precarga local: {new_request['name']}")
                track = new_request
                source = "request"
                next_track_cache = None
                next_audio_cache = None
                next_source_cache = None
            elif next_track_cache:
                track = next_track_cache
                source = next_source_cache
                next_track_cache = None
                next_source_cache = None
            else:
                track, next_local_index, source = self._get_next_track(local_index)
                if source == "local":
                    local_index = next_local_index

            if track:
                if source == "request":
                    print(f"[RADIO] ⚡ Reproduciendo pedido: {track['name']}")
                else:
                    print(f"[RADIO] 📂 Reproduciendo música local ({local_index}/{len(self.queue_local)}): {track['name']}")
                
                # 📢 NOTIFICAR NOW PLAYING ANTES DE PROCESAR AUDIO
                # Movido a dentro del bucle de bytes para coincidir exactamente con el inicio del audio
                now_playing_sent = False

                self.current_track = track
                
                try:
                    audio = next_audio_cache if next_audio_cache is not None else self._load_audio(track)
                    next_audio_cache = None
                    
                    duration_ms = len(audio)
                    self.track_start_time = time.time()
                    self.current_duration = int(duration_ms / 1000)
                    
                    crossfade_ms = self.crossfade * 1000
                    preload_time_ms = 20000  # 20 segundos antes de que termine
                    
                    final_audio = audio
                    next_audio_cache = None
                    next_track_cache = None
                    next_source_cache = None
                    
                    # Streaming logic...
                    now_playing_sent = False
                    buffer = io.BytesIO()
                    final_audio.export(buffer, format="mp3", bitrate="128k")
                    mp3_data = buffer.getvalue()
                    
                    bytes_per_500ms = 8000
                    total_bytes = len(mp3_data)
                    preload_trigger_byte = max(0, int(total_bytes * (duration_ms - preload_time_ms) / duration_ms))
                    preload_done = False

                    start_time = time.time()
                    for i in range(0, total_bytes, bytes_per_500ms):
                        # 📢 NOTIFICAR NOW PLAYING JUSTO AL ENVIAR EL PRIMER CHUNK (música empieza AHORA)
                        if not now_playing_sent and self.bot_instance:
                            try:
                                duration_ms_actual = track.get("duration", 0) * 1000 if track.get("duration") else duration_ms
                                duration_str = format_seconds(int(duration_ms_actual / 1000))
                                msg = f"<#90EE90>🎧 Now playing:\n<#90EE90>{track['name']}\n<#90EE90>⏱️ ({duration_str})\n<#90EE90>👤 @{track.get('username', 'System')}"
                                asyncio.run_coroutine_threadsafe(self.bot_instance.highrise.chat(msg), self.bot_instance.loop)
                                now_playing_sent = True
                                self.track_start_time = time.time()
                                print(f"[RADIO] 📢 Now playing enviado JUSTO al iniciar streaming: {track['name']}")
                            except Exception as e:
                                print(f"[RADIO] Error enviando Now playing: {e}")
                                now_playing_sent = True  # Marcar como enviado para no reintentar
                        
                        if not self.running or self.skip_current: break
                        
                        # ⏸️ MANEJO DE PAUSA INSTANTÁNEA
                        while self.paused and self.running and not self.skip_current:
                            time.sleep(0.1)

                        chunk = mp3_data[i:i + bytes_per_500ms]
                        self.pre_buffer.extend(chunk)
                        if len(self.pre_buffer) > self.pre_buffer_size:
                            self.pre_buffer = self.pre_buffer[-self.pre_buffer_size:]

                        # 🎵 PRECARGAR 20 segundos antes del final - verificar pedidos primero
                        if not preload_done and i >= preload_trigger_byte:
                            preload_done = True
                            if not self.queue_requests.empty():
                                next_track_cache = self.queue_requests.get()
                                next_source_cache = "request"
                                print(f"[RADIO] ⚡ Precarga 20s antes: Pedido detectado - {next_track_cache['name']}")
                            else:
                                peek_track, peek_index, peek_source = self._get_next_track(local_index)
                                if peek_track:
                                    next_track_cache = peek_track
                                    next_source_cache = peek_source
                                    if peek_source == "local":
                                        local_index = peek_index
                                    print(f"[RADIO] 📂 Precarga 20s antes: Local - {next_track_cache['name']}")
                            
                            if next_track_cache:
                                try:
                                    next_audio_cache = self._load_audio(next_track_cache)
                                except Exception as e:
                                    print(f"[RADIO] ❌ Error precargando: {e}")
                                    next_audio_cache = None
                                    next_track_cache = None

                        for client_queue in self.clients[:]:
                            try: client_queue.put_nowait(chunk)
                            except:
                                if client_queue in self.clients: self.clients.remove(client_queue)
                        
                        expected_elapsed = (i / bytes_per_500ms) * 0.5
                        actual_elapsed = time.time() - start_time
                        sleep_time = expected_elapsed - actual_elapsed
                        if sleep_time > 0:
                            # Dividir sleep en pequeños intervalos para responder rápido a /next
                            # Reducido a 0.01 para respuesta instantánea
                            sleep_chunks = int(sleep_time / 0.01) + 1
                            for _ in range(sleep_chunks):
                                if self.skip_current: break
                                time.sleep(min(0.01, sleep_time / sleep_chunks))

                except Exception as e:
                    print(f"Error en playback: {e}")
                    time.sleep(1)
                
                self.skip_current = False
                self.current_track = None
            else:
                time.sleep(1)

    def generate_stream(self):
        # Cada vez que alguien entra a /stream, le damos su propia cola
        # que recibirá los bytes del bucle GLOBAL
        from queue import Queue as ClientQueue
        my_queue = ClientQueue(maxsize=1000) 
        
        # 🚀 ENVIAR RÁFAGA INICIAL (BURST) PARA EVITAR SILENCIO
        # Enviamos el buffer acumulado lo más rápido posible en bloques grandes
        if len(self.pre_buffer) > 0:
            burst_data = bytes(self.pre_buffer)
            # Enviar la ráfaga en bloques de 32KB para no saturar pero ser rápido
            chunk_size = 32768
            for i in range(0, len(burst_data), chunk_size):
                yield burst_data[i:i + chunk_size]
            print(f"[RADIO] 📡 Ráfaga inicial enviada ({len(burst_data)} bytes)")

        self.clients.append(my_queue)
        print(f"[RADIO] 📡 Nuevo cliente conectado al stream. Total: {len(self.clients)}")
        
        try:
            while self.running:
                # Leer bytes del buffer global (llenado por el hilo start())
                data = my_queue.get(timeout=10) 
                yield data
        except Exception:
            pass
        finally:
            if my_queue in self.clients:
                self.clients.remove(my_queue)
            print("[RADIO] 📡 Cliente desconectado.")
