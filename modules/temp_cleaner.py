import os
import tempfile
from datetime import datetime, timedelta
import winreg
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import time

MODULE_ID = "temp_cleaner"
NAME = "Очистить Temp папки"

def get_all_users_temp_folders():
    temp_folders = set()
    
    temp_folders.add(tempfile.gettempdir())
    
    if os.environ.get("TEMP"):
        temp_folders.add(os.environ["TEMP"])
    if os.environ.get("TMP"):
        temp_folders.add(os.environ["TMP"])
    
    temp_folders.add(r"C:\Windows\Temp")
    
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList")
        num_users = winreg.QueryInfoKey(key)[0]
        
        for i in range(num_users):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                profile_path = winreg.QueryValueEx(subkey, "ProfileImagePath")[0]
                winreg.CloseKey(subkey)
                
                if os.path.exists(profile_path):
                    user_temp = os.path.join(profile_path, "AppData", "Local", "Temp")
                    if os.path.exists(user_temp):
                        temp_folders.add(user_temp)
            except:
                continue
        winreg.CloseKey(key)
    except:
        pass
    
    return [f for f in temp_folders if f and os.path.exists(f)]

def get_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_size(entry.path)
    except:
        pass
    return total

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024*1024:
        return f"{size_bytes/1024:.1f} КБ"
    elif size_bytes < 1024*1024*1024:
        return f"{size_bytes/(1024*1024):.1f} МБ"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} ГБ"

def clean_folder(path, age_hours=24):
    deleted_count = 0
    deleted_size = 0
    cutoff = datetime.now() - timedelta(hours=age_hours)
    
    if not os.path.exists(path):
        return 0, 0
    
    try:
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                try:
                    filepath = os.path.join(root, name)
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_count += 1
                        deleted_size += size
                except:
                    pass
            
            for name in dirs:
                try:
                    dirpath = os.path.join(root, name)
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                except:
                    pass
    except:
        pass
    
    return deleted_count, deleted_size

class CleanerWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Очистка Temp папок")
        self.root.geometry("700x550")
        self.root.resizable(True, True)
        
        self.root.columnconfigure(0, weight=1)
        
        self.header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)
        
        tk.Label(self.header_frame, text="🧹 Очистка временных файлов", 
                font=("Segoe UI", 16, "bold"), bg="#2c3e50", fg="white").pack(pady=(20, 5))
        
        tk.Label(self.header_frame, text="Удаляет файлы старше 24 часов", 
                font=("Segoe UI", 9), bg="#2c3e50", fg="#bdc3c7").pack()
        
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.info_frame = tk.LabelFrame(self.main_frame, text="📁 Temp папки", font=("Segoe UI", 10, "bold"))
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.tree = ttk.Treeview(self.info_frame, columns=("size", "status"), show="tree headings", height=8)
        self.tree.heading("#0", text="Путь")
        self.tree.heading("size", text="Размер")
        self.tree.heading("status", text="Статус")
        self.tree.column("#0", width=380)
        self.tree.column("size", width=100)
        self.tree.column("status", width=120)
        
        scrollbar = ttk.Scrollbar(self.info_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_frame = tk.LabelFrame(self.main_frame, text="📊 Результат", font=("Segoe UI", 10, "bold"))
        self.result_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.result_text = tk.Text(self.result_frame, height=5, font=("Consolas", 9), state=tk.DISABLED, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, padx=5, pady=5)
        
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X)
        
        self.scan_btn = tk.Button(self.button_frame, text="🔍 Начать сканирование", 
                                  command=self.start_scan, bg="#3498db", fg="white",
                                  font=("Segoe UI", 10, "bold"), padx=20, pady=8)
        self.scan_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.clean_btn = tk.Button(self.button_frame, text="🧹 Очистить (старше 24ч)", 
                                   command=self.start_clean, bg="#27ae60", fg="white",
                                   font=("Segoe UI", 10, "bold"), padx=20, pady=8, state=tk.DISABLED)
        self.clean_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.progress_bar = ttk.Progressbar(self.main_frame, mode='indeterminate')
        
        self.temp_folders = []
        self.folder_sizes = {}
        
    def update_result(self, text, clear=False):
        self.result_text.config(state=tk.NORMAL)
        if clear:
            self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text + "\n")
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)
    
    def scan_folders(self):
        self.temp_folders = get_all_users_temp_folders()
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for path in self.temp_folders:
            size = get_size(path)
            self.folder_sizes[path] = size
            display_path = path
            if len(display_path) > 55:
                display_path = "..." + display_path[-52:]
            item = self.tree.insert("", tk.END, text=display_path, 
                                    values=(format_size(size), "ожидание"))
            self.tree.item(item, tags=(path,))
        
        self.root.after(0, lambda: self.update_result(f"✓ Найдено {len(self.temp_folders)} Temp-папок\n"))
        self.root.after(0, lambda: self.clean_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.scan_btn.config(text="🔍 Пересканировать"))
    
    def start_scan(self):
        self.scan_btn.config(state=tk.DISABLED)
        self.clean_btn.config(state=tk.DISABLED)
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        self.progress_bar.start(10)
        self.update_result("🔍 Сканирование Temp-папок...", clear=True)
        
        thread = threading.Thread(target=self.scan_folders)
        thread.daemon = True
        thread.start()
        
        self.check_thread(thread, "scan")
    
    def clean_folders(self):
        total_deleted = 0
        total_freed = 0
        
        for path in self.temp_folders:
            for item in self.tree.get_children():
                if self.tree.item(item, "tags")[0] == path:
                    self.tree.item(item, values=(format_size(self.folder_sizes[path]), "очистка..."))
                    self.tree.item(item, tags=(path,))
                    self.root.update()
                    break
            
            count, size = clean_folder(path, age_hours=24)
            
            if count > 0:
                total_deleted += count
                total_freed += size
                for item in self.tree.get_children():
                    if self.tree.item(item, "tags")[0] == path:
                        remaining = get_size(path)
                        self.tree.item(item, values=(format_size(remaining), f"✓ {count} файлов"))
                        self.tree.item(item, tags=(path,))
                        break
            else:
                for item in self.tree.get_children():
                    if self.tree.item(item, "tags")[0] == path:
                        self.tree.item(item, values=(format_size(self.folder_sizes[path]), "чисто"))
                        self.tree.item(item, tags=(path,))
                        break
            
            self.root.update()
        
        result_text = f"\n{'='*50}\n"
        result_text += f"✅ Удалено файлов: {total_deleted}\n"
        result_text += f"💾 Освобождено места: {format_size(total_freed)}\n"
        result_text += f"{'='*50}"
        self.update_result(result_text)
        
        if total_freed > 10 * 1024 * 1024:
            self.update_result("\n💡 Для полной очистки диска: Пуск → Очистка диска")
        
        self.root.after(0, lambda: self.clean_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.scan_btn.config(state=tk.NORMAL))
    
    def start_clean(self):
        if messagebox.askyesno("Подтверждение", 
                               "Будут удалены временные файлы старше 24 часов.\n\n"
                               "Продолжить?", icon="warning"):
            self.scan_btn.config(state=tk.DISABLED)
            self.clean_btn.config(state=tk.DISABLED)
            self.progress_bar.pack(fill=tk.X, pady=(10, 0))
            self.progress_bar.start(10)
            self.update_result("\n🧹 Начало очистки...", clear=False)
            
            thread = threading.Thread(target=self.clean_folders)
            thread.daemon = True
            thread.start()
            
            self.check_thread(thread, "clean")
    
    def check_thread(self, thread, task_type):
        if thread.is_alive():
            self.root.after(100, lambda: self.check_thread(thread, task_type))
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            if task_type == "scan":
                self.scan_btn.config(state=tk.NORMAL)
            else:
                messagebox.showinfo("Завершено", "Очистка временных файлов выполнена!")
    
    def run(self):
        self.root.mainloop()

def process(files):
    import sys
    import os
    
    lock_file = os.path.join(tempfile.gettempdir(), "temp_cleaner_gui.lock")
    
    try:
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            import subprocess
            try:
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True)
            except:
                pass
            os.remove(lock_file)
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        app = CleanerWindow()
        app.run()
    finally:
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass