import customtkinter as ctk
import threading
import asyncio
import sys
import os
import webbrowser
from telethon import TelegramClient
from backend import ConfigManager, GuiSmartCleaner, GuiMediaDownloader

# Настройка внешнего вида
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class TeleToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.title("TeleTool Ultimate v01")
        self.geometry("850x650")
        
        # Данные
        self.config_mgr = ConfigManager()
        self.client = None
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_loop, daemon=True)
        self.loop_thread.start()
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === ЛЕВОЕ МЕНЮ ===
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TeleTool GUI", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Настройки", command=lambda: self.show_frame("settings"))
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Сканирование/Очистка", command=lambda: self.show_frame("cleaner"), state="disabled")
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Загрузчик", command=lambda: self.show_frame("downloader"), state="disabled")
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)
        
        # === ФРЕЙМЫ ===
        self.frames = {}
        self.create_settings_frame()
        self.create_cleaner_frame()
        self.create_downloader_frame()

        # Показываем настройки по умолчанию
        self.show_frame("settings")
        
        # Автозаполнение
        aid, ahash = self.config_mgr.get_creds()
        if aid and ahash:
            self.entry_api_id.insert(0, str(aid))
            self.entry_api_hash.insert(0, ahash)

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def open_link(self):
        webbrowser.open("https://my.telegram.org/apps")

    # --- UI CREATION ---
    def create_settings_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["settings"] = f
        
        ctk.CTkLabel(f, text="Настройки API", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 10))
        
        # Блок инструкций
        instr_frame = ctk.CTkFrame(f, fg_color="#2B2B2B", corner_radius=10)
        instr_frame.pack(pady=10, padx=40, fill="x")
        
        instr_text = (
            "Для работы программы вам необходимо получить API ключи:\n"
            "1. Авторизуйтесь на сайте Telegram (ссылка ниже).\n"
            "2. Перейдите в 'API development tools'.\n"
            "3. Создайте приложение (App title и Short name - любые).\n"
            "4. Скопируйте API ID и API Hash в поля ниже."
        )
        ctk.CTkLabel(instr_frame, text=instr_text, justify="left", font=ctk.CTkFont(size=12)).pack(pady=10, padx=20)
        
        btn_link = ctk.CTkButton(instr_frame, text="Открыть my.telegram.org", 
                                 fg_color="#1f538d", hover_color="#14375e",
                                 command=self.open_link)
        btn_link.pack(pady=(0, 15))

        # Поля ввода
        ctk.CTkLabel(f, text="App api_id:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        self.entry_api_id = ctk.CTkEntry(f, width=350, placeholder_text="Например: 12345678")
        self.entry_api_id.pack(pady=5)
        
        ctk.CTkLabel(f, text="App api_hash:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        self.entry_api_hash = ctk.CTkEntry(f, width=350, placeholder_text="Например: e68c06c9558abc2...")
        self.entry_api_hash.pack(pady=5)
        
        self.btn_connect = ctk.CTkButton(f, text="Подключиться и авторизоваться", 
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         height=40,
                                         command=self.connect_telegram)
        self.btn_connect.pack(pady=30)
        
        self.lbl_status = ctk.CTkLabel(f, text="Статус: Не подключено", text_color="gray")
        self.lbl_status.pack(pady=5)

    def create_cleaner_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["cleaner"] = f
        ctk.CTkLabel(f, text="Очистка Сообщений", font=ctk.CTkFont(size=20)).pack(pady=10)
        
        controls = ctk.CTkFrame(f)
        controls.pack(pady=10, padx=20, fill="x")
        
        self.chk_dry_run = ctk.CTkCheckBox(controls, text="Dry Run (Безопасный режим)")
        self.chk_dry_run.pack(side="left", padx=20, pady=10)
        self.chk_dry_run.select()
        
        self.btn_start_clean = ctk.CTkButton(controls, text="Запустить очистку", fg_color="green", command=self.start_cleaning)
        self.btn_start_clean.pack(side="right", padx=20, pady=10)
        
        self.btn_stop_clean = ctk.CTkButton(controls, text="Стоп", fg_color="red", command=self.stop_cleaning, state="disabled")
        self.btn_stop_clean.pack(side="right", padx=5)

        self.txt_clean_log = ctk.CTkTextbox(f, width=500, height=300, font=ctk.CTkFont(family="Consolas"))
        self.txt_clean_log.pack(pady=10, padx=20, fill="both", expand=True)

    def create_downloader_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["downloader"] = f
        ctk.CTkLabel(f, text="Загрузчик Медиа (Анти-защита)", font=ctk.CTkFont(size=20)).pack(pady=10)
        
        self.entry_link = ctk.CTkEntry(f, width=500, placeholder_text="Вставьте ссылку на сообщение: https://t.me/c/ப்புகளை")
        self.entry_link.pack(pady=20)
        
        self.btn_download = ctk.CTkButton(f, text="Скачать файл", height=40, command=self.start_download)
        self.btn_download.pack(pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(f, width=500)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=25)
        
        self.lbl_download_status = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12))
        self.lbl_download_status.pack(pady=5)

    # --- LOGIC INTEGRATION (Сходна с main_gui.py) ---
    def show_frame(self, name):
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=1, sticky="nsew")

    def connect_telegram(self):
        api_id = self.entry_api_id.get()
        api_hash = self.entry_api_hash.get()
        if not api_id or not api_hash:
            self.lbl_status.configure(text="Ошибка: Введите ключи!", text_color="#E74C3C")
            return
        self.lbl_status.configure(text="Попытка подключения...", text_color="yellow")
        self.config_mgr.save_config(api_id, api_hash)
        self.run_async(self.async_connect(api_id, api_hash))

    async def async_connect(self, api_id, api_hash):
        try:
            self.client = TelegramClient('gui_session', int(api_id), api_hash, loop=self.loop)
            await self.client.connect()
            if not await self.client.is_user_authorized():
                print("Авторизация через консоль...")
                await self.client.start()
            me = await self.client.get_me()
            self.update_ui_connected(me.first_name)
        except Exception as e:
            self.update_ui_error(str(e))

    def update_ui_connected(self, name):
        self.after(0, lambda: self._ui_connected(name))

    def _ui_connected(self, name):
        self.lbl_status.configure(text=f"Авторизован: {name}", text_color="#2ECC71")
        self.sidebar_button_2.configure(state="normal")
        self.sidebar_button_3.configure(state="normal")
        self.btn_connect.configure(text="Обновить подключение")

    def update_ui_error(self, error):
        self.after(0, lambda: self.lbl_status.configure(text=f"Ошибка: {error[:50]}...", text_color="#E74C3C"))

    def start_cleaning(self):
        if not self.client: return
        self.btn_start_clean.configure(state="disabled")
        self.btn_stop_clean.configure(state="normal")
        self.cleaner_logic = GuiSmartCleaner(self.client, self.log_cleaner)
        self.run_async(self.cleaner_logic.start(dry_run=bool(self.chk_dry_run.get())))

    def stop_cleaning(self):
        if hasattr(self, 'cleaner_logic'): self.cleaner_logic.stop()
        self.btn_start_clean.configure(state="normal")
        self.btn_stop_clean.configure(state="disabled")

    def log_cleaner(self, text):
        self.after(0, lambda: self._append_clean_log(text))

    def _append_clean_log(self, text):
        self.txt_clean_log.insert("end", text + "\n")
        self.txt_clean_log.see("end")

    def start_download(self):
        link = self.entry_link.get()
        if not link: return
        self.btn_download.configure(state="disabled")
        self.progress_bar.set(0)
        downloader = GuiMediaDownloader(self.client, self.log_download, self.progress_download)
        self.run_async(self._download_wrapper(downloader, link))

    async def _download_wrapper(self, downloader, link):
        await downloader.download(link)
        self.after(0, lambda: self.btn_download.configure(state="normal"))

    def log_download(self, text):
        self.after(0, lambda: self.lbl_download_status.configure(text=text))

    def progress_download(self, current, total):
        if total > 0: self.after(0, lambda: self.progress_bar.set(current / total))

if __name__ == "__main__":
    app = TeleToolApp()
    app.mainloop()
