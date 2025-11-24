import requests
import os
import json
import uuid
import sys
import sqlite3
from datetime import datetime

# 判断是否为打包后的 EXE 环境
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONF_DIR = os.path.join(BASE_DIR, "conf")
CONFIG_FILE = os.path.join(CONF_DIR, "config.json")
TOKEN_FILE = os.path.join(CONF_DIR, "token.json")
DB_FILE = os.path.join(CONF_DIR, "mapping_history.db")


class ConfigManager:
    @staticmethod
    def load_config():
        """加载配置文件，不存在则生成模板"""
        if not os.path.exists(CONF_DIR):
            try:
                os.makedirs(CONF_DIR)
            except Exception as e:
                print(f"Error: Failed to create conf directory: {e}")
                return None

        if not os.path.exists(CONFIG_FILE):
            template = {
                "api_url": "http://your-cloudreve-domain.com/api/v4",
                "email": "your-email@example.com",
                "password": "your-password",
                "remote_folder": "uploads/typora",
                "use_random_filename": True,
                "save_filename_mapping": True
            }
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=4, ensure_ascii=False)
                print(f"Init: Configuration file created at: {CONFIG_FILE}")
                print("Action: Please open the config file and fill in your account details.")
                return None
            except Exception as e:
                print(f"Error: Failed to create config file: {e}")
                return None

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error: Failed to load config: {e}")
            return None


class MappingManager:
    @staticmethod
    def init_db():
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS uploads
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               local_path
                               TEXT,
                               original_name
                               TEXT,
                               remote_filename
                               TEXT,
                               remote_uri
                               TEXT,
                               direct_link
                               TEXT,
                               upload_time
                               TEXT
                           )
                           ''')
            conn.commit()
            conn.close()
        except:
            pass

    @staticmethod
    def append_mappings(new_records):
        if not new_records: return
        try:
            MappingManager.init_db()
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            data_to_insert = []
            for r in new_records:
                data_to_insert.append((
                    r.get('local_path', ''),
                    r.get('original_name', ''),
                    r.get('remote_filename', ''),
                    r.get('remote_uri', ''),
                    r.get('direct_link', ''),
                    r.get('upload_time', '')
                ))
            cursor.executemany('''
                               INSERT INTO uploads (local_path, original_name, remote_filename, remote_uri, direct_link,
                                                    upload_time)
                               VALUES (?, ?, ?, ?, ?, ?)
                               ''', data_to_insert)
            conn.commit()
            conn.close()
        except:
            pass


class CloudreveClient:
    def __init__(self, config):
        self.base_url = config.get('api_url', '').rstrip('/')
        self.email = config.get('email')
        self.password = config.get('password')
        self.session = requests.Session()
        self.token = None

    def _load_local_token(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    token = data.get('token')
                    if token:
                        self.token = token
                        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                        return True
            except:
                pass
        return False

    def _save_token_locally(self):
        try:
            if not os.path.exists(CONF_DIR):
                os.makedirs(CONF_DIR)
            with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
                json.dump({"token": self.token, "update_time": str(datetime.now())}, f)
        except:
            pass

    def _check_token_validity(self):
        if not self.token: return False
        url = f"{self.base_url}/user/capacity"
        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200 and response.json().get('code') == 0:
                return True
        except:
            pass
        return False

    def login(self):
        if self._load_local_token() and self._check_token_validity():
            return True

        url = f"{self.base_url}/session/token"
        payload = {"email": self.email, "password": self.password}
        try:
            response = self.session.post(url, json=payload)
            result = response.json()
            if result.get('code') == 0:
                token_data = result['data']['token']
                self.token = token_data if isinstance(token_data, str) else token_data.get('access_token')
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self._save_token_locally()
                return True
        except Exception as e:
            print(f"Error: Login failed: {e}")
        return False

    def upload_image(self, file_path, remote_dir="/", use_random_name=False):
        if not os.path.exists(file_path):
            return None, None, "File not found"

        original_filename = os.path.basename(file_path)
        original_ext = os.path.splitext(file_path)[1]

        if use_random_name:
            final_filename = f"{uuid.uuid4()}{original_ext}"
        else:
            final_filename = original_filename

        remote_dir = remote_dir.strip("/")
        remote_path_uri = f"cloudreve://my/{remote_dir}/{final_filename}" if remote_dir else f"cloudreve://my/{final_filename}"

        url = f"{self.base_url}/file/content"
        params = {"uri": remote_path_uri, "err_on_conflict": "false"}

        try:
            with open(file_path, 'rb') as f:
                response = self.session.put(url, params=params, data=f,
                                            headers={"Content-Type": "application/octet-stream"})
                result = response.json()

            if result.get('code') == 0:
                return remote_path_uri, final_filename, None
            else:
                return None, None, result.get('msg')
        except Exception as e:
            return None, None, str(e)

    def create_direct_link(self, file_uri):
        url = f"{self.base_url}/file/source"
        payload = {"uris": [file_uri]}
        try:
            response = self.session.put(url, json=payload)
            result = response.json()
            if result.get('code') == 0:
                items = result.get('data', [])
                if items:
                    return items[0].get('link'), None

            err_msg = result.get('msg', 'Unknown error')
            if result.get('aggregated_error'):
                err_msg += str(result.get('aggregated_error'))
            return None, err_msg
        except Exception as e:
            return None, str(e)

    def delete_files(self, uri_list):
        if not uri_list: return
        url = f"{self.base_url}/file"
        payload = {
            "uris": uri_list,
            "unlink": False,
            "skip_soft_delete": True
        }
        try:
            self.session.delete(url, json=payload)
        except:
            pass



if __name__ == "__main__":
    # 1. 加载配置
    config = ConfigManager.load_config()
    if not config:
        # 如果配置为空
        if len(sys.argv) == 1:
            input("\nPress Enter to exit...")
        sys.exit(1)

    # 2. 配置加载成功后，再检查是否传入了图片
    file_paths = sys.argv[1:]
    if not file_paths:
        print("Error: No files provided.")
        sys.exit(1)

    # 3. 初始化
    client = CloudreveClient(config)
    if not client.login():
        print("Error: Authentication failed.")
        sys.exit(1)

    # 4. 批量处理
    upload_history_uris = []
    mapping_records = []
    final_links = []

    try:
        use_random = config.get('use_random_filename', False)
        save_mapping = config.get('save_filename_mapping', False)

        for local_path in file_paths:
            # A. 上传
            uri, remote_name, err = client.upload_image(
                local_path,
                remote_dir=config.get('remote_folder', ''),
                use_random_name=use_random
            )

            if not uri:
                raise Exception(f"Upload failed for {local_path}: {err}")

            upload_history_uris.append(uri)

            # B. 获取直链
            link, err = client.create_direct_link(uri)
            if not link:
                raise Exception(f"Link generation failed for {local_path}: {err}")

            final_links.append(link)

            # C. 准备记录数据
            if use_random and save_mapping:
                mapping_records.append({
                    "local_path": local_path,
                    "original_name": os.path.basename(local_path),
                    "remote_filename": remote_name,
                    "remote_uri": uri,
                    "direct_link": link,
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        # 5. insert db
        if mapping_records:
            MappingManager.append_mappings(mapping_records)

        # Typora 成功标识
        print("Upload Success:")
        for link in final_links:
            print(link)

    except Exception as e:
        # 6. 发生错误，回滚
        if upload_history_uris:
            client.delete_files(upload_history_uris)

        print(f"Error: {str(e)}")
        sys.exit(1)