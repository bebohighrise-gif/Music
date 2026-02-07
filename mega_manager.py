from mega import Mega
import os
import json
import io
import time

class MegaManager:
    def __init__(self, credentials_path='credentials.json'):
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            self.user = creds.get('mega_user')
            self.password = creds.get('mega_pass')
            
            self.mega_instance = Mega()
            self.m = self.mega_instance.login(self.user, self.password)
            print(f"[MEGA] Ses_ion iniciada para: {self.user}")
        except Exception as e:
            print(f"[MEGA] Error de login en MEGA: {e}")
            self.m = None

    def upload_file(self, file_name, file_io):
        if not self.m: return None
        
        # Obtener el número siguiente al último
        try:
            files = self.list_files()
            max_num = 0
            for f in files:
                name = f['name']
                # Buscar si el nombre empieza con un número seguido de un punto o espacio
                parts = name.split(' ', 1)
                if parts[0].replace('.', '').isdigit():
                    num = int(parts[0].replace('.', ''))
                    if num > max_num:
                        max_num = num
            
            next_num = max_num + 1
            file_name = f"{next_num}. {file_name}"
        except Exception as e:
            print(f"[MEGA] Error calculando número correlativo: {e}")

        temp_path = f"temp_{int(time.time())}_{file_name}"
        try:
            if hasattr(file_io, 'seek'): file_io.seek(0)
            with open(temp_path, "wb") as f:
                f.write(file_io.read() if hasattr(file_io, 'read') else file_io)
            
            file = self.m.upload(temp_path)
            if not file: return None
            
            # El ID del archivo puede estar en 'h' o 'f[0][h]' según la versión de la API
            file_id = file.get('h')
            if not file_id and 'f' in file and len(file['f']) > 0:
                file_id = file['f'][0].get('h')
            
            # Obtener el link público si es posible
            try:
                link = self.m.get_upload_link(file)
            except:
                link = None
            return {"id": file_id or "unknown", "name": file_name, "link": link}
        except Exception as e:
            print(f"[MEGA] Error subiendo: {e}")
            return None
        finally:
            if os.path.exists(temp_path): os.remove(temp_path)

    def list_files(self):
        if not self.m: return []
        try:
            files = self.m.get_files()
            music_files = []
            for fid, f in files.items():
                name = f.get('a', {}).get('n', '')
                if name.lower().endswith(('.mp3', '.wav', '.ogg')):
                    try:
                        link = self.m.get_link(f)
                    except:
                        link = None
                    music_files.append({"id": fid, "name": name, "link": link})
            return music_files
        except Exception as e:
            print(f"[MEGA] Error listando: {e}")
            return []

    def download_file(self, file_name):
        if not self.m: return None
        try:
            file = self.m.find(file_name)
            if file:
                path = self.m.download(file)
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        content = f.read()
                    os.remove(path)
                    return io.BytesIO(content)
            return None
        except Exception as e:
            print(f"[MEGA] Error descargando: {e}")
            return None
