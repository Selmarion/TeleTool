
import time
import asyncio
from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError, MessageDeleteForbiddenError

# --- НАСТРОЙКИ ---
# Вставьте сюда ваши api_id и api_hash
API_ID = 25991218  # ЗАМЕНИТЕ НА ВАШ API_ID
API_HASH = 'e68c06c9558abc27975a1bf31e002775'  # ЗАМЕНИТЕ НА ВАШ API_HASH

# Имя файла сессии
SESSION_NAME = 'message_deleter'

# Период ожидания между полными циклами очистки (в секундах)
# 24 часа = 24 * 60 * 60 = 86400 секунд
SLEEP_PERIOD = 21100

# --- ОПЦИОНАЛЬНО: ДЛЯ ТЕСТИРОВАНИЯ ---
# Чтобы протестировать скрипт только на конкретных чатах, раскомментируйте
# следующую строку и впишите ID чатов (числа) или их юзернеймы (в кавычках).
# Например: TARGET_CHATS = [-100123456789, 'some_username']
# Если оставить закомментированным, скрипт будет работать во ВСЕХ чатах.
# TARGET_CHATS = []

async def delete_my_messages(client):
    """Функция для поиска и удаления сообщений."""
    print("Начинаю новый цикл удаления сообщений...")
    
    dialogs_to_process = []
    
    # Проверяем, задан ли список целевых чатов
    if 'TARGET_CHATS' in globals() and TARGET_CHATS:
        print(f"Работаю в тестовом режиме. Целевые чаты: {TARGET_CHATS}")
        for chat_id in TARGET_CHATS:
            try:
                dialogs_to_process.append(await client.get_entity(chat_id))
            except Exception as e:
                print(f"Не удалось найти чат {chat_id}: {e}")
    else:
        print("Сканирую все диалоги...")
        dialogs_to_process = await client.get_dialogs()

    for dialog in dialogs_to_process:
        if not dialog.is_user and not dialog.is_group and not dialog.is_channel:
            continue

        print(f"  -> Проверяю чат: '{dialog.name}' (ID: {dialog.id})")
        
        messages_to_delete = []
        # Ищем сообщения, отправленные "мной"
        async for message in client.iter_messages(dialog, from_user='me'):
            messages_to_delete.append(message.id)
        
        if messages_to_delete:
            print(f"     Найдено {len(messages_to_delete)} сообщений для удаления. Удаляю...")
            try:
                # Удаляем сообщения пакетами по 100 (максимум для одного запроса)
                for i in range(0, len(messages_to_delete), 100):
                    chunk = messages_to_delete[i:i+100]
                    await client.delete_messages(dialog, chunk)
                print("     Сообщения в этом чате успешно удалены.")
            except MessageDeleteForbiddenError:
                print("     [ОШИБКА] Нет прав на удаление сообщений в этом чате.")
            except Exception as e:
                print(f"     [ОШИБКА] Произошла ошибка при удалении: {e}")
        else:
            print("     Моих сообщений в этом чате не найдено.")

async def main():
    """Основной цикл, который запускает удаление раз в сутки."""
    # Используем async with для корректной работы с асинхронным клиентом
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print("Клиент успешно запущен. Скрипт работает в фоновом режиме.")
        me = await client.get_me()
        print(f"Авторизован как: {me.first_name} (ID: {me.id})")
        
        while True:
            try:
                await delete_my_messages(client)
                print(f"Цикл завершен. Следующая проверка через 24 часа.")
                print(f"Засыпаю на {SLEEP_PERIOD} секунд...")
                await asyncio.sleep(SLEEP_PERIOD)
            
            except FloodWaitError as e:
                print(f"[КРИТИЧЕСКАЯ ОШИБКА] Слишком много запросов. Жду {e.seconds} секунд...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"[КРИТИЧЕСКАЯ ОШИБКА] Произошла непредвиденная ошибка в главном цикле: {e}")
                print("Перезапускаю цикл через 60 секунд...")
                await asyncio.sleep(60)

if __name__ == "__main__":
    # Используем asyncio.run() для запуска асинхронной функции main
    try:
        asyncio.run(main())
    except (ValueError, TypeError):
        print("[ОШИБКА] Не удалось получить ваши API_ID/API_HASH.")
        print("Пожалуйста, откройте файл message_deleter.py и замените значения-заглушки.")
    except KeyboardInterrupt:
        print("\n[ИНФО] Скрипт остановлен пользователем.")