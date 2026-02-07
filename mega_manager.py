from mega import Mega
import os
import json
import io
import time

class MegaManager:
    """
    Gestor de archivos MEGA.nz con sesión persistente.
    IMPORTANTE: La sesión se mantiene abierta permanentemente para evitar bloqueos de cuenta.
    """
    _instance = None
    _session_active = False
    
    def __new__(cls, credentials_path='credentials.json'):
        """Singleton para reutilizar la misma sesión MEGA"""
        if cls._instance is None:
            cls._instance = super(MegaManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, credentials_path='credentials.json'):
        # Solo inicializar una vez (patrón Singleton)
        if self._initialized:
            return
        
        try:
            if not os.path.exists(credentials_path):
                print(f"[MEGA] ⚠️ Advertencia: No existe {credentials_path}")
                print(f"[MEGA] 💡 Crea el archivo con: {{'mega_user': 'tu@email.com', 'mega_pass': 'tu_password'}}")
                self.m = None
                self._initialized = True
                return
            
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            
            self.user = creds.get('mega_user')
            self.password = creds.get('mega_pass')
            
            if not self.user or not self.password:
                print(f"[MEGA] ❌ Credenciales incompletas en {credentials_path}")
                self.m = None
                self._initialized = True
                return
            
            print(f"[MEGA] 🔄 Iniciando sesión persistente...")
            self.mega_instance = Mega()
            self.m = self.mega_instance.login(self.user, self.password)
            MegaManager._session_active = True
            print(f"[MEGA] ✅ Sesión PERSISTENTE iniciada para: {self.user}")
            print(f"[MEGA] 📌 La sesión permanecerá abierta para evitar bloqueos")
            
        except Exception as e:
            print(f"[MEGA] ❌ Error de login en MEGA: {e}")
            self.m = None
            MegaManager._session_active = False
        
        self._initialized = True
    
    def is_connected(self):
        """Verifica si hay una sesión activa de MEGA"""
        return self.m is not None and MegaManager._session_active

    def upload_file(self, file_name, file_io):
        """
        Sube un archivo a MEGA con numeración automática.
        La sesión permanece abierta (NO se cierra).
        """
        if not self.is_connected(): 
            print("[MEGA] ❌ No hay sesión activa")
            return None
        
        # Calcular número correlativo - obtener el último número usado
        try:
            files = self.list_files()
            max_num = 0
            for f in files:
                name = f['name']
                # Buscar patrón "NÚMERO." al inicio (ej: "1.", "42.", "100.")
                if '.' in name:
                    first_part = name.split('.')[0].strip()
                    if first_part.isdigit():
                        num = int(first_part)
                        if num > max_num:
                            max_num = num
            
            # El siguiente número
            next_num = max_num + 1
            
            # Añadir numeración al nombre del archivo
            file_name = f"{next_num}. {file_name}"
            print(f"[MEGA] 📝 Numerando como: {file_name}")
            
        except Exception as e:
            print(f"[MEGA] ⚠️ Error calculando número: {e}")
            # Si falla, usar timestamp como fallback
            import time
            file_name = f"temp_{int(time.time())}_{file_name}"

        # Sanitizar nombre de archivo temporal
        safe_name = file_name.replace('/', '_').replace('\\', '_')
        temp_path = f"temp_{int(time.time())}_{safe_name}"
        
        try:
            # Escribir a temporal
            if hasattr(file_io, 'seek'): 
                file_io.seek(0)
            with open(temp_path, "wb") as f:
                f.write(file_io.read() if hasattr(file_io, 'read') else file_io)
            
            print(f"[MEGA] ⬆️ Subiendo a MEGA...")
            file = self.m.upload(temp_path)
            if not file: 
                print(f"[MEGA] ❌ Upload falló")
                return None
            
            # Extraer ID
            file_id = file.get('h')
            if not file_id and 'f' in file and len(file['f']) > 0:
                file_id = file['f'][0].get('h')
            
            # Link público (opcional)
            link = None
            try:
                link = self.m.get_upload_link(file)
            except:
                pass
            
            print(f"[MEGA] ✅ Subido exitosamente: {file_name}")
            return {"id": file_id or "unknown", "name": file_name, "link": link}
        except Exception as e:
            print(f"[MEGA] ❌ Error: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def list_files(self):
        """
        Lista todos los archivos de audio en MEGA.
        Mantiene sesión abierta.
        """
        if not self.is_connected(): 
            return []
        try:
            files = self.m.get_files()
            music_files = []
            for fid, f in files.items():
                name = f.get('a', {}).get('n', '')
                if name.lower().endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
                    try:
                        link = self.m.get_link(f)
                    except:
                        link = None
                    music_files.append({"id": fid, "name": name, "link": link})
            
            # Ordenar por nombre
            music_files.sort(key=lambda x: x['name'])
            return music_files
        except Exception as e:
            print(f"[MEGA] ❌ Error listando archivos: {e}")
            return []

    def download_file(self, file_name):
        """
        Descarga un archivo de MEGA a memoria (BytesIO).
        Sesión permanece abierta.
        """
        if not self.is_connected(): 
            return None
        try:
            file = self.m.find(file_name)
            if not file:
                print(f"[MEGA] ⚠️ Archivo no encontrado: {file_name}")
                return None
            
            print(f"[MEGA] ⬇️ Descargando: {file_name}...")
            path = self.m.download(file)
            
            if not os.path.exists(path):
                print(f"[MEGA] ❌ Descarga falló: {file_name}")
                return None
            
            # Leer y convertir a BytesIO
            with open(path, 'rb') as f:
                content = f.read()
            
            # Limpiar archivo temporal
            try:
                os.remove(path)
            except:
                pass
            
            print(f"[MEGA] ✅ Descargado: {file_name}")
            return io.BytesIO(content)
            
        except Exception as e:
            print(f"[MEGA] ❌ Error descargando {file_name}: {e}")
            return None
    
    def get_session_status(self):
        """Retorna el estado de la sesión MEGA"""
        return {
            "connected": self.is_connected(),
            "user": self.user if hasattr(self, 'user') else None,
            "active": MegaManager._session_active
        }
    
    def __del__(self):
        """
        IMPORTANTE: NO cerramos la sesión al destruir el objeto.
        La sesión debe permanecer abierta siempre.
        """
        pass  # Intencionalmente vacío - sesión persistente
