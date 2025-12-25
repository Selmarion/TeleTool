import json
import os
import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError
from telethon.tl.types import MessageMediaWebPage

# --- Менеджер Конфигурации ---
class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self, api_id, api_hash):
        self.data['api_id'] = api_id
        self.data['api_hash'] = api_hash
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f)

    def get_creds(self):
        return self.data.get('api_id'), self.data.get('api_hash')

# --- Логика Очистки (Адаптированная) ---
class GuiSmartCleaner:
    def __init__(self, client: TelegramClient, log_callback):
        self.client = client
        self.log = log_callback # Функция, принимающая str
        self.is_running = False

    async def start(self, dry_run=False):
        self.is_running = True
        self.log(f"=== Запуск очистки (Dry Run: {dry_run}) ===")
        
        try:
            me = await self.client.get_me()
            self.log(f"Пользователь: {me.first_name} (ID: {me.id})")
            
            self.log("Сканирование диалогов...")
            dialogs = await self.client.get_dialogs()
            self.log(f"Найдено диалогов: {len(dialogs)}")

            for dialog in dialogs:
                if not self.is_running:
                    self.log("Процесс остановлен пользователем.")
                    break
                
                # Пропускаем каналы, где мы не админы (обычно там нельзя удалять свои сообщения массово так же легко)
                # Но для упрощения оставим логику как было: ищем свои сообщения везде
                
                my_msgs = []
                try:
                    async for msg in self.client.iter_messages(dialog, from_user='me'):
                        my_msgs.append(msg.id)
                except Exception as e:
                    # self.log(f"Ошибка доступа к чату {dialog.name}: {e}")
                    continue

                if my_msgs:
                    self.log(f"Чат '{dialog.name}': найдено {len(my_msgs)} своих сообщений.")
                    
                    if dry_run:
                        self.log(f"  [DRY RUN] Пропуск удаления.")
                        continue

                    # Удаление
                    batch_size = 100
                    for i in range(0, len(my_msgs), batch_size):
                        if not self.is_running: break
                        batch = my_msgs[i:i+batch_size]
                        try:
                            await self.client.delete_messages(dialog, batch)
                            self.log(f"  Удалено {len(batch)} сообщений...")
                            await asyncio.sleep(1) # Пауза от флуда
                        except FloodWaitError as e:
                            self.log(f"  [FLOOD] Жду {e.seconds} сек...")
                            await asyncio.sleep(e.seconds + 2)
                        except Exception as e:
                            self.log(f"  Ошибка удаления: {e}")
            
            self.log("=== Цикл завершен ===")

        except Exception as e:
            self.log(f"Критическая ошибка: {e}")
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False

# --- Логика Загрузки (Адаптированная) ---
class GuiMediaDownloader:
    def __init__(self, client: TelegramClient, log_callback, progress_callback):
        self.client = client
        self.log = log_callback
        self.progress = progress_callback # Функция принимающая (current, total)
    
    async def download(self, url, save_folder="downloads"):
        import re
        self.log(f"Обработка ссылки: {url}")
        
        # Парсинг (упрощенный, копируем логику)
        target = None
        msg_id = None
        
        # Private /c/
        pm = re.search(r't\.me/c/(\d+)/(\d+)', url)
        if pm:
            target = int(f"-100{pm.group(1)}")
            msg_id = int(pm.group(2))
        else:
            # Public
            pubm = re.search(r't\.me/([^/]+)/(\d+)', url)
            if pubm:
                target = pubm.group(1)
                msg_id = int(pubm.group(2))
        
        if not target:
            self.log("Неверный формат ссылки.")
            return

        try:
            entity = await self.client.get_input_entity(target)
            message = await self.client.get_messages(entity, ids=msg_id)

            if not message or not message.media:
                self.log("Медиа не найдено в сообщении.")
                return
            
            if isinstance(message.media, MessageMediaWebPage):
                self.log("Это ссылка-превью, а не файл.")
                return

            # Создаем папку, если переданный путь не существует
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)

            self.log(f"Начинаю скачивание в: {save_folder}")
            
            async def _callback(current, total):
                self.progress(current, total)

            path = await self.client.download_media(
                message,
                file=save_folder,
                progress_callback=_callback
            )
            self.log(f"Сохранено: {path}")

        except Exception as e:
            self.log(f"Ошибка загрузки: {e}")
