import customtkinter as ctk
import threading
import asyncio
import sys
import os
import webbrowser
import tkinter as tk # Для меню
from telethon import TelegramClient
from backend import ConfigManager, GuiSmartCleaner, GuiMediaDownloader
from localization import TRANS

# Настройка темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class TeleToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Конфигурация
        self.lang = "en"
        self.config_mgr = ConfigManager()
        self.client = None
        
        # Окно
        self.title(TRANS[self.lang]["app_title"])
        self.geometry("900x700")
        
        # Асинхронность
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_loop, daemon=True)
        self.loop_thread.start()
        
        # Сетка
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === ЛЕВОЕ МЕНЮ (Sidebar) ===
        self.sidebar = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1) # spacer

        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="TeleTool", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_nav_settings = ctk.CTkButton(self.sidebar, command=lambda: self.show_frame("settings"))
        self.btn_nav_settings.grid(row=1, column=0, padx=20, pady=10)

        self.btn_nav_cleaner = ctk.CTkButton(self.sidebar, command=lambda: self.show_frame("cleaner"), state="disabled")
        self.btn_nav_cleaner.grid(row=2, column=0, padx=20, pady=10)

        self.btn_nav_downloader = ctk.CTkButton(self.sidebar, command=lambda: self.show_frame("downloader"), state="disabled")
        self.btn_nav_downloader.grid(row=3, column=0, padx=20, pady=10)
        
        # Переключатель языка (внизу меню)
        self.btn_lang = ctk.CTkButton(self.sidebar, text="Language: EN", fg_color="transparent", border_width=1, 
                                      command=self.toggle_language)
        self.btn_lang.grid(row=6, column=0, padx=20, pady=20)

        # === КОНТЕЙНЕР СТРАНИЦ ===
        self.frames = {}
        self.create_settings_frame()
        self.create_cleaner_frame()
        self.create_downloader_frame()

        # Инициализация текстов
        self.update_texts()
        self.show_frame("settings")
        
        # Автозаполнение
        aid, ahash = self.config_mgr.get_creds()
        if aid and ahash:
            self.entry_api_id.insert(0, str(aid))
            self.entry_api_hash.insert(0, ahash)

    # --- СИСТЕМНЫЕ МЕТОДЫ ---
    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def open_link(self):
        webbrowser.open("https://my.telegram.org/apps")

    # --- ЛОКАЛИЗАЦИЯ И UX ---
    def toggle_language(self):
        self.lang = "ru" if self.lang == "en" else "en"
        self.btn_lang.configure(text=f"Language: {self.lang.upper()}")
        self.update_texts()

    def update_texts(self):
        t = TRANS[self.lang]
        self.title(t["app_title"])
        
        # Меню
        self.btn_nav_settings.configure(text=t["menu_settings"])
        self.btn_nav_cleaner.configure(text=t["menu_cleaner"])
        self.btn_nav_downloader.configure(text=t["menu_downloader"])
        
        # Настройки
        self.lbl_settings_title.configure(text=t["settings_title"])
        self.lbl_instr.configure(text=t["instr_text"])
        self.btn_open_web.configure(text=t["btn_open_web"])
        self.lbl_api_id.configure(text=t["lbl_api_id"])
        self.lbl_api_hash.configure(text=t["lbl_api_hash"])
        
        # Кнопки Paste обновляем
        self.btn_paste_id.configure(text=t["btn_paste"])
        self.btn_paste_hash.configure(text=t["btn_paste"])
        
        # Статус кнопки подключения
        current_conn_text = self.btn_connect.cget("text")
        if "Authorize" in current_conn_text or "Подключиться" in current_conn_text:
             self.btn_connect.configure(text=t["btn_connect"])
        
        # Cleaner
        self.lbl_cleaner_title.configure(text=t["cleaner_title"])
        self.chk_dry_run.configure(text=t["chk_dry_run"])
        self.btn_start_clean.configure(text=t["btn_start_clean"])
        self.btn_stop_clean.configure(text=t["btn_stop_clean"])
        
        # Downloader
        self.lbl_downloader_title.configure(text=t["downloader_title"])
        self.entry_link.configure(placeholder_text=t["placeholder_link"])
        self.btn_download.configure(text=t["btn_download"])
        self.btn_paste_link.configure(text=t["btn_paste"])

    def paste_from_clipboard(self, entry):
        try:
            # Пытаемся получить текст из буфера (пробуем разные методы)
            text = self.clipboard_get()
            if text:
                entry.delete(0, 'end')
                entry.insert(0, text)
        except:
            pass

    def create_paste_button(self, parent, entry, row, col):
        btn = ctk.CTkButton(parent, text="Paste", width=60, height=25, 
                            fg_color="#444", hover_color="#555",
                            command=lambda: self.paste_from_clipboard(entry))
        btn.grid(row=row, column=col, padx=(5, 0), sticky="w")
        return btn

    def bind_context_menu(self, widget):
        # Стандартное меню tkinter
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Paste / Вставить", command=lambda: self.paste_from_clipboard(widget))
        
        def show_popup(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        
        # Привязка к правому клику
        widget.bind("<Button-3>", show_popup)

    # --- СОЗДАНИЕ UI ---
    def create_settings_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["settings"] = f
        
        self.lbl_settings_title = ctk.CTkLabel(f, text="API Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_settings_title.pack(pady=(20, 10))
        
        # Инструкция
        instr_frame = ctk.CTkFrame(f, fg_color="#2B2B2B", corner_radius=10)
        instr_frame.pack(pady=10, padx=40, fill="x")
        
        self.lbl_instr = ctk.CTkLabel(instr_frame, text="...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_instr.pack(pady=10, padx=20)
        
        self.btn_open_web = ctk.CTkButton(instr_frame, text="Open Web", fg_color="#1f538d", command=self.open_link)
        self.btn_open_web.pack(pady=(0, 15))

        # Поля ввода с Grid для кнопки Paste
        input_frame = ctk.CTkFrame(f, fg_color="transparent")
        input_frame.pack(pady=10)
        
        self.lbl_api_id = ctk.CTkLabel(input_frame, text="ID:")
        self.lbl_api_id.grid(row=0, column=0, sticky="e", padx=5)
        self.entry_api_id = ctk.CTkEntry(input_frame, width=300)
        self.entry_api_id.grid(row=0, column=1)
        self.bind_context_menu(self.entry_api_id)
        self.btn_paste_id = self.create_paste_button(input_frame, self.entry_api_id, 0, 2)
        
        self.lbl_api_hash = ctk.CTkLabel(input_frame, text="Hash:")
        self.lbl_api_hash.grid(row=1, column=0, sticky="e", padx=5, pady=10)
        self.entry_api_hash = ctk.CTkEntry(input_frame, width=300)
        self.entry_api_hash.grid(row=1, column=1, pady=10)
        self.bind_context_menu(self.entry_api_hash)
        self.btn_paste_hash = self.create_paste_button(input_frame, self.entry_api_hash, 1, 2)
        
        self.btn_connect = ctk.CTkButton(f, text="Connect", height=40, font=ctk.CTkFont(size=14, weight="bold"),
                                         command=self.connect_telegram)
        self.btn_connect.pack(pady=30)
        
        self.lbl_status = ctk.CTkLabel(f, text="Status: ...", text_color="gray")
        self.lbl_status.pack(pady=5)

    def create_cleaner_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["cleaner"] = f
        
        self.lbl_cleaner_title = ctk.CTkLabel(f, text="Cleaner", font=ctk.CTkFont(size=20))
        self.lbl_cleaner_title.pack(pady=10)
        
        controls = ctk.CTkFrame(f)
        controls.pack(pady=10, padx=20, fill="x")
        
        self.chk_dry_run = ctk.CTkCheckBox(controls, text="Dry Run")
        self.chk_dry_run.pack(side="left", padx=20, pady=10)
        self.chk_dry_run.select()
        
        self.btn_start_clean = ctk.CTkButton(controls, text="Start", fg_color="green", command=self.start_cleaning)
        self.btn_start_clean.pack(side="right", padx=20, pady=10)
        
        self.btn_stop_clean = ctk.CTkButton(controls, text="Stop", fg_color="red", command=self.stop_cleaning, state="disabled")
        self.btn_stop_clean.pack(side="right", padx=5)

        self.txt_clean_log = ctk.CTkTextbox(f, width=500, height=300, font=ctk.CTkFont(family="Consolas"))
        self.txt_clean_log.pack(pady=10, padx=20, fill="both", expand=True)

    def create_downloader_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["downloader"] = f
        
        self.lbl_downloader_title = ctk.CTkLabel(f, text="Downloader", font=ctk.CTkFont(size=20))
        self.lbl_downloader_title.pack(pady=10)
        
        input_f = ctk.CTkFrame(f, fg_color="transparent")
        input_f.pack(pady=20)
        
        self.entry_link = ctk.CTkEntry(input_f, width=400)
        self.entry_link.grid(row=0, column=0)
        self.bind_context_menu(self.entry_link)
        
        self.btn_paste_link = self.create_paste_button(input_f, self.entry_link, 0, 1)
        
        self.btn_download = ctk.CTkButton(f, text="Download", height=40, command=self.start_download)
        self.btn_download.pack(pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(f, width=500)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=25)
        
        self.lbl_download_status = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=12))
        self.lbl_download_status.pack(pady=5)

    # --- ЛОГИКА (БЭКЕНД) ---
    def show_frame(self, name):
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=1, sticky="nsew")

    def connect_telegram(self):
        api_id = self.entry_api_id.get()
        api_hash = self.entry_api_hash.get()
        if not api_id or not api_hash:
            self.lbl_status.configure(text=TRANS[self.lang]["error_prefix"].format("Empty ID/Hash"), text_color="#E74C3C")
            return
        
        self.lbl_status.configure(text=TRANS[self.lang]["status_connecting"], text_color="yellow")
        self.config_mgr.save_config(api_id, api_hash)
        self.run_async(self.async_connect(api_id, api_hash))

    async def async_connect(self, api_id, api_hash):
        try:
            self.client = TelegramClient('gui_session', int(api_id), api_hash, loop=self.loop)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                # УВЕДОМЛЕНИЕ ПРО КОНСОЛЬ
                self.after(0, lambda: self.lbl_status.configure(
                    text="CHECK CONSOLE FOR LOGIN CODE! / СМОТРИ КОНСОЛЬ!", 
                    text_color="#E74C3C"
                ))
                print("\n" + "="*40)
                print("ВНИМАНИЕ: Введите номер телефона и код здесь, в консоли!")
                print("WARNING: Enter phone and code here, in console!")
                print("="*40 + "\n")
                await self.client.start()

            me = await self.client.get_me()
            self.update_ui_connected(me.first_name)
        except Exception as e:
            self.update_ui_error(str(e))

    def update_ui_connected(self, name):
        self.after(0, lambda: self._ui_connected(name))

    def _ui_connected(self, name):
        txt = TRANS[self.lang]["status_connected"].format(name)
        self.lbl_status.configure(text=txt, text_color="#2ECC71")
        self.btn_nav_cleaner.configure(state="normal")
        self.btn_nav_downloader.configure(state="normal")
        self.btn_connect.configure(text=TRANS[self.lang]["btn_reconnect"])

    def update_ui_error(self, error):
        txt = TRANS[self.lang]["error_prefix"].format(error[:40])
        self.after(0, lambda: self.lbl_status.configure(text=txt, text_color="#E74C3C"))

    # Cleaner & Downloader Logic (Same as before)
    def start_cleaning(self):
        if not self.client: return
        self.btn_start_clean.configure(state="disabled")
        self.btn_stop_clean.configure(state="normal")
        self.cleaner_logic = GuiSmartCleaner(self.client, self.log_cleaner)
        
        # Лог старта
        msg = TRANS[self.lang]["log_start"].format(bool(self.chk_dry_run.get()))
        self.log_cleaner(msg)
        
        self.run_async(self.cleaner_logic.start(dry_run=bool(self.chk_dry_run.get())))

    def stop_cleaning(self):
        if hasattr(self, 'cleaner_logic'): self.cleaner_logic.stop()
        self.log_cleaner(TRANS[self.lang]["log_stop"])
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
        self.lbl_download_status.configure(text=TRANS[self.lang]["status_init"])
        self.progress_bar.set(0)
        
        downloader = GuiMediaDownloader(self.client, self.log_download, self.progress_download)
        self.run_async(self._download_wrapper(downloader, link))

    async def _download_wrapper(self, downloader, link):
        await downloader.download(link)
        self.after(0, lambda: self.btn_download.configure(state="normal"))
        self.after(0, lambda: self.lbl_download_status.configure(text=TRANS[self.lang]["status_done"]))

    def log_download(self, text):
        self.after(0, lambda: self.lbl_download_status.configure(text=text))

    def progress_download(self, current, total):
        if total > 0: self.after(0, lambda: self.progress_bar.set(current / total))

if __name__ == "__main__":
    app = TeleToolApp()
    app.mainloop()
