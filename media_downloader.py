import os
import re
import sys
import asyncio
from telethon import TelegramClient, utils
from telethon.tl.types import MessageMediaWebPage
from dotenv import load_dotenv
from tqdm import tqdm
from colorama import init, Fore

# Инициализация
init(autoreset=True)
load_dotenv()

class MediaDownloader:
    def __init__(self):
        self.api_id = int(os.getenv("TG_API_ID"))
        self.api_hash = os.getenv("TG_API_HASH")
        self.session_name = "media_downloader_session"
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)

    def parse_link(self, url: str):
        """
        Парсит ссылку на сообщение Telegram.
        Поддерживает форматы:
        - https://t.me/username/123
        - https://t.me/c/123456789/123
        """
        # Регулярка для приватных чатов (с /c/)
        private_match = re.search(r't\.me/c/(\d+)/(\d+)', url)
        if private_match:
            chat_id = int(private_match.group(1))
            msg_id = int(private_match.group(2))
            # Для Telethon приватные чаты должны начинаться с -100
            return f"-100{chat_id}", msg_id

        # Регулярка для публичных чатов
        public_match = re.search(r't\.me/([^/]+)/(\d+)', url)
        if public_match:
            username = public_match.group(1)
            msg_id = int(public_match.group(2))
            return username, msg_id

        return None, None

    async def progress_callback(self, current, total):
        """Обновление прогресс-бара."""
        if self.pbar is None:
            self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc="Скачивание")
        self.pbar.update(current - self.pbar.n)

    async def download_from_link(self, url: str):
        """Основная логика скачивания."""
        target, msg_id = self.parse_link(url)
        
        if not target:
            print(Fore.RED + "Некорректная ссылка!")
            return

        try:
            # Получаем сущность чата/канала
            entity = await self.client.get_input_entity(target)
            # Получаем сообщение по ID
            messages = await self.client.get_messages(entity, ids=msg_id)
            
            if not messages or not messages.media:
                print(Fore.YELLOW + "В сообщении не найдено медиафайлов.")
                return

            message = messages
            
            # Проверка на веб-страницу (превью ссылки), ее мы не качаем как файл обычно
            if isinstance(message.media, MessageMediaWebPage):
                 print(Fore.YELLOW + "Это ссылка с превью, файла для скачивания нет.")
                 return

            # Определяем имя файла
            file_name = "downloads/"
            if not os.path.exists("downloads"):
                os.makedirs("downloads")

            print(Fore.CYAN + f"Найдено медиа. Начинаю загрузку...")
            
            self.pbar = None # Сброс прогресс-бара
            path = await self.client.download_media(
                message,
                file=file_name,
                progress_callback=self.progress_callback
            )
            
            if self.pbar:
                self.pbar.close()

            print(Fore.GREEN + f"\nУспешно сохранено: {path}")

        except Exception as e:
            print(Fore.RED + f"Ошибка: {e}")

    async def run(self):
        await self.client.start()
        print(Fore.GREEN + "Клиент запущен.")
        
        while True:
            print(Fore.WHITE + "\nВведите ссылку на сообщение (или 'exit' для выхода):")
            url = input("> ").strip()
            
            if url.lower() in ['exit', 'quit', 'выход']:
                break
                
            if not url:
                continue
                
            await self.download_from_link(url)

if __name__ == "__main__":
    downloader = MediaDownloader()
    try:
        asyncio.run(downloader.run())
    except KeyboardInterrupt:
        print("\nПрограмма остановлена.")
