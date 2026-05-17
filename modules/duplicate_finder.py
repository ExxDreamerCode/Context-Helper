import os
import hashlib
from collections import defaultdict

MODULE_ID = "duplicate_finder"
NAME = "Найти дубликаты"

IGNORED = {".DS_Store", "Thumbs.db", "desktop.ini"}


class MessageCollector:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def add_info(self, msg):
        self.info.append(msg)

    def show(self):
        if self.errors or self.warnings or self.info:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                text = ""
                if self.errors:
                    text += "❌ ОШИБКИ:\n" + "\n".join(self.errors[:10])
                    if len(self.errors) > 10:
                        text += f"\n... и ещё {len(self.errors)-10}"
                    text += "\n\n"
                if self.warnings:
                    text += "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n" + "\n".join(self.warnings[:5])
                    text += "\n\n"
                if self.info:
                    text += "ℹ️ ИНФО:\n" + "\n".join(self.info[:5])

                if self.errors:
                    messagebox.showerror("Результаты", text[:2000])
                elif self.warnings:
                    messagebox.showwarning("Внимание", text[:2000])
                elif self.info:
                    messagebox.showinfo("Информация", text[:2000])

                root.destroy()
            except:
                for e in self.errors:
                    print(f"ERROR: {e}")


def collect_files_from_paths(paths, msg_collector):
    files = []

    for path in paths:
        if not path or not path.strip():
            continue

        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            try:
                for root, dirs, filenames in os.walk(path):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for filename in filenames:
                        if filename in IGNORED:
                            continue
                        files.append(os.path.join(root, filename))
            except Exception as e:
                msg_collector.add_error(f"Не удалось просканировать {path}: {e}")
        else:
            msg_collector.add_warning(f"Пропущен (не файл и не папка): {path}")

    return files


def get_file_hash(filepath, msg_collector):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        msg_collector.add_error(f"Не удалось прочитать {os.path.basename(filepath)}: {e}")
        return None


def get_partial_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(65536)
            hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None


def find_duplicates(files, msg_collector):
    if len(files) < 2:
        return {}

    size_map = defaultdict(list)
    for filepath in files:
        try:
            size = os.path.getsize(filepath)
            size_map[size].append(filepath)
        except:
            msg_collector.add_error(f"Не удалось получить размер {os.path.basename(filepath)}")

    potential_duplicates = defaultdict(list)

    for size, filepaths in size_map.items():
        if len(filepaths) < 2:
            continue

        for filepath in filepaths:
            partial_hash = get_partial_hash(filepath)
            if partial_hash:
                key = (size, partial_hash)
                potential_duplicates[key].append(filepath)

    duplicates = defaultdict(list)

    for key, filepaths in potential_duplicates.items():
        if len(filepaths) < 2:
            continue

        for filepath in filepaths:
            full_hash = get_file_hash(filepath, msg_collector)
            if full_hash:
                duplicates[full_hash].append(filepath)

    return {h: paths for h, paths in duplicates.items() if len(paths) > 1}


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024*1024:
        return f"{size_bytes/1024:.1f} КБ"
    else:
        return f"{size_bytes/(1024*1024):.1f} МБ"


def show_duplicates_window(duplicates):
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        return

    root = tk.Tk()
    root.title("Найдены дубликаты")
    root.geometry("1000x700")

    total_savings = 0
    for paths in duplicates.values():
        if paths:
            total_savings += os.path.getsize(paths[0]) * (len(paths) - 1)

    header_frame = tk.Frame(root, bg="#f0f0f0")
    header_frame.pack(fill=tk.X, padx=0, pady=0)

    tk.Label(header_frame, text=f"Найдено {len(duplicates)} групп дубликатов",
             font=("Segoe UI", 14, "bold"), bg="#f0f0f0").pack(pady=10)
    tk.Label(header_frame, text=f"Можно освободить: {format_size(total_savings)}",
             font=("Segoe UI", 11), fg="green", bg="#f0f0f0").pack(pady=(0, 10))

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    group_data = []

    for i, (hash_val, paths) in enumerate(duplicates.items()):
        frame = tk.Frame(notebook)
        notebook.add(frame, text=f"Группа {i+1} ({len(paths)} файлов)")

        size = os.path.getsize(paths[0])

        info_frame = tk.Frame(frame, bg="#e8e8e8")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(info_frame, text=f"Размер каждого файла: {format_size(size)}",
                 font=("Segoe UI", 9), bg="#e8e8e8").pack(side=tk.LEFT, padx=10, pady=5)
        tk.Label(info_frame, text=f"Всего места: {format_size(size * len(paths))}",
                 font=("Segoe UI", 9), bg="#e8e8e8").pack(side=tk.RIGHT, padx=10, pady=5)

        list_frame = tk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                             selectmode=tk.EXTENDED, font=("Consolas", 9))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        for path in paths:
            display = f"{path} ({format_size(size)})"
            listbox.insert(tk.END, display)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        def make_select_all_cb(lb):
            return lambda: lb.selection_set(0, tk.END)

        def make_deselect_all_cb(lb):
            return lambda: lb.selection_clear(0, tk.END)

        def make_delete_selected_cb(lb, paths_list, root_window):
            return lambda: delete_selected(lb, paths_list, root_window)

        tk.Button(btn_frame, text="✓ Выделить все",
                 command=make_select_all_cb(listbox)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✗ Снять выделение",
                 command=make_deselect_all_cb(listbox)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑 Удалить выделенные", bg="#ff4444", fg="white",
                 command=make_delete_selected_cb(listbox, paths, root)).pack(side=tk.RIGHT, padx=5)

        group_data.append({
            "listbox": listbox,
            "paths": paths
        })

    def delete_selected(listbox, paths_list, parent_root):
        selected = listbox.curselection()
        if not selected:
            messagebox.showinfo("Нет выделения", "Выберите файлы для удаления")
            return

        files_to_delete = [paths_list[idx] for idx in selected]

        confirm = messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить {len(files_to_delete)} файлов?\n\n" +
            "\n".join(f"  • {os.path.basename(f)}" for f in files_to_delete[:10]) +
            (f"\n\n... и ещё {len(files_to_delete)-10}" if len(files_to_delete) > 10 else ""),
            parent=parent_root,
            icon='warning'
        )

        if not confirm:
            return

        deleted = 0
        errors = 0
        for f in files_to_delete:
            try:
                os.remove(f)
                deleted += 1
            except Exception as e:
                errors += 1

        messagebox.showinfo("Удаление завершено",
                           f"✓ Удалено: {deleted}\n✗ Ошибок: {errors}")
        parent_root.destroy()

    bottom_frame = tk.Frame(root, bg="#f0f0f0")
    bottom_frame.pack(fill=tk.X, padx=10, pady=10)

    tk.Button(bottom_frame, text="Закрыть", command=root.destroy,
              width=15, height=1).pack(side=tk.RIGHT, padx=5)

    def select_all_groups():
        for gd in group_data:
            gd["listbox"].selection_set(0, tk.END)

    def deselect_all_groups():
        for gd in group_data:
            gd["listbox"].selection_clear(0, tk.END)

    tk.Button(bottom_frame, text="Выделить всё во всех группах",
              command=select_all_groups).pack(side=tk.LEFT, padx=5)
    tk.Button(bottom_frame, text="Снять выделение везде",
              command=deselect_all_groups).pack(side=tk.LEFT, padx=5)

    root.mainloop()


def process(files):
    files = [f for f in files if f and f.strip()]

    if not files:
        print("Ошибка: не выбраны папки или файлы")
        return

    msg_collector = MessageCollector()

    all_files = collect_files_from_paths(files, msg_collector)

    if len(all_files) < 2:
        msg_collector.add_warning(f"Найдено только {len(all_files)} файлов. Нужно минимум 2 для поиска дубликатов.")
        msg_collector.show()
        return

    duplicates = find_duplicates(all_files, msg_collector)

    if not duplicates:
        msg_collector.add_info(f"Дубликатов не найдено среди {len(all_files)} файлов.")
        msg_collector.show()
        return

    show_duplicates_window(duplicates)