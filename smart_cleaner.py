import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import List, Optional

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError
from telethon.tl.types import User, Chat, Channel
from dotenv import load_dotenv
from colorama import init, Fore, Style
from tqdm.asyncio import tqdm

# Инициализация colorama для Windows
init(autoreset=True)

# Загрузка переменных окружения
load_dotenv()

class Config:
    API_ID = os.getenv("TG_API_ID")
    API_HASH = os.getenv("TG_API_HASH")
    SESSION_NAME = os.getenv("SESSION_NAME", "cleaner_session")
    SLEEP_PERIOD = int(os.getenv("SLEEP_PERIOD", 86400))
    DRY_RUN = os.getenv("DRY_RUN", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def validate():
        if not Config.API_ID or not Config.API_HASH:
            print(Fore.RED + "ОШИБКА: Не заданы TG_API_ID или TG_API_HASH в файле .env")
            sys.exit(1)

class SmartCleaner:
    def __init__(self):
        self.setup_logging()
        self.client = TelegramClient(Config.SESSION_NAME, int(Config.API_ID), Config.API_HASH)
        self.me = None

    def setup_logging(self):
        """Настройка логирования в файл и консоль."""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL.upper(), "INFO"),
            format=log_format,
            handlers=[
                logging.FileHandler("cleaner.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def get_target_dialogs(self) -> List:
        """Сканирует диалоги и возвращает список для обработки."""
        self.logger.info("Сканирование диалогов...")
        dialogs = await self.client.get_dialogs()
        self.logger.info(f"Найдено всего диалогов: {len(dialogs)}")
        
        # Здесь можно добавить логику фильтрации (например, только группы или ЛС)
        # Пока возвращаем все, где мы не забанены
        targets = []
        for d in dialogs:
            if d.is_channel and d.entity.left:
                continue # Пропускаем каналы, из которых вышли
            targets.append(d)
        
        return targets

    async def process_dialog(self, dialog):
        """Обработка одного диалога: поиск и удаление своих сообщений."""
        chat_name = dialog.name
        chat_id = dialog.id
        
        self.logger.info(f"Анализ чата: {chat_name} (ID: {chat_id})")
        
        my_messages = []
        try:
            # Ищем сообщения от 'me' (себя)
            # limit=None означает искать все сообщения. Это может быть долго.
            # Можно добавить offset_date для удаления только старых сообщений.
            async for msg in self.client.iter_messages(dialog, from_user='me'):
                my_messages.append(msg.id)
        except Exception as e:
            self.logger.error(f"Ошибка при сканировании чата {chat_name}: {e}")
            return

        if not my_messages:
            self.logger.info(f"  -> В чате {chat_name} нет моих сообщений.")
            return

        self.logger.info(f"  -> Найдено {len(my_messages)} сообщений для удаления в {chat_name}.")

        if Config.DRY_RUN:
            print(Fore.YELLOW + f"  [DRY RUN] Было бы удалено {len(my_messages)} сообщений в {chat_name}")
            return

        # Удаление
        await self.delete_messages_batched(dialog, my_messages)

    async def delete_messages_batched(self, dialog, message_ids: List[int]):
        """Пакетное удаление сообщений с обработкой FloodWait."""
        batch_size = 100
        total = len(message_ids)
        
        # tqdm для визуализации
        pbar = tqdm(total=total, desc="Удаление", unit="msg", leave=False)
        
        for i in range(0, total, batch_size):
            batch = message_ids[i:i + batch_size]
            try:
                await self.client.delete_messages(dialog, batch)
                pbar.update(len(batch))
                # Небольшая пауза, чтобы не спамить API слишком агрессивно
                await asyncio.sleep(0.5) 
            except FloodWaitError as e:
                pbar.write(Fore.RED + f"  [FLOOD WAIT] Жду {e.seconds} секунд...")
                await asyncio.sleep(e.seconds + 1)
                # Повторяем попытку для этого же батча? 
                # Простая реализация: просто пропускаем или рекурсивно вызываем. 
                # Для надежности лучше использовать цикл retry, но пока оставим пропуск.
                self.logger.warning(f"Пропущен батч из-за флуда в диалоге {dialog.name}")
            except MessageDeleteForbiddenError:
                pbar.write(Fore.RED + f"  [ERROR] Нет прав на удаление в {dialog.name}")
                break
            except Exception as e:
                pbar.write(Fore.RED + f"  [ERROR] Ошибка удаления: {e}")
        
        pbar.close()

    async def run(self):
        """Основной цикл приложения."""
        Config.validate()
        
        print(Fore.CYAN + "=== Smart Telegram Cleaner v2.0 ===")
        if Config.DRY_RUN:
            print(Fore.YELLOW + "РЕЖИМ: DRY RUN (Без удаления)")
        else:
            print(Fore.RED + "РЕЖИМ: БОЕВОЙ (Удаление активно)")
        
        await self.client.start()
        self.me = await self.client.get_me()
        self.logger.info(f"Авторизован как: {self.me.first_name} (ID: {self.me.id})")

        while True:
            start_time = datetime.now()
            dialogs = await self.get_target_dialogs()
            
            for dialog in dialogs:
                await self.process_dialog(dialog)
                
            end_time = datetime.now()
            duration = end_time - start_time
            self.logger.info(f"Цикл очистки завершен за {duration}.")
            
            self.logger.info(f"Ожидание {Config.SLEEP_PERIOD} секунд...")
            await asyncio.sleep(Config.SLEEP_PERIOD)

if __name__ == "__main__":
    cleaner = SmartCleaner()
    try:
        asyncio.run(cleaner.run())
    except KeyboardInterrupt:
        print(Fore.GREEN + "\nРабота завершена пользователем.")
    except Exception as e:
        print(Fore.RED + f"\nКритическая ошибка: {e}")
