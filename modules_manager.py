import os
import sys
import json
import importlib.util
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(SCRIPT_DIR, "modules")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "modules_config.json")


def get_module_info(filepath):
    try:
        name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(name, filepath)
        if not spec:
            return None, None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mid = getattr(m, "MODULE_ID", None)
        label = getattr(m, "NAME", None)
        if not mid or " " in mid or not label:
            return None, None
        return mid, label
    except:
        return None, None


def scan_modules():
    modules = []
    if not os.path.isdir(MODULES_DIR):
        return modules
    for fn in sorted(os.listdir(MODULES_DIR)):
        if not fn.endswith(".py") or fn == "__init__.py":
            continue
        fp = os.path.join(MODULES_DIR, fn)
        mid, label = get_module_info(fp)
        if mid and label:
            modules.append((mid, label))
    return modules


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("enabled", {})
    except:
        return None


def save_config(enabled_dict):
    data = {
        "_comment": "Конфиг включения модулей. true = включён, false = отключён.",
        "enabled": enabled_dict
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер инструментов")
        self.root.geometry("520x450")
        self.root.minsize(400, 350)
        self.root.resizable(True, True)
        self.modules = scan_modules()
        self.config = load_config()

        if self.config is None:
            self.config = {mid: True for mid, _ in self.modules}
            save_config(self.config)

        self.vars = {}
        for mid, _ in self.modules:
            self.vars[mid] = tk.BooleanVar(value=self.config.get(mid, True))

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(header, text="ContextHelper", font=("Segoe UI", 14, "bold")
                 ).pack(side=tk.LEFT)

        tk.Label(header,
                 text=f"Найдено модулей: {len(self.modules)}",
                 font=("Segoe UI", 10)).pack(side=tk.RIGHT, padx=5)

        list_frame = tk.LabelFrame(self.root, text="Модули", font=("Segoe UI", 10),
                                  padx=10, pady=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas)

        self.scroll_frame.bind("<Configure>",
                               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.checkboxes = []
        if not self.modules:
            tk.Label(self.scroll_frame, text="Нет модулей в папке modules/",
                     font=("Segoe UI", 10)).pack(pady=20)
        else:
            for i, (mid, label) in enumerate(self.modules):
                row = tk.Frame(self.scroll_frame)
                row.pack(fill=tk.X, pady=2)

                var = self.vars[mid]
                cb = tk.Checkbutton(row, text=label, variable=var,
                                   font=("Segoe UI", 10),
                                   command=self._on_toggle)
                cb.pack(side=tk.LEFT, padx=(5, 5))
                self.checkboxes.append(cb)

                tk.Label(row, text=f"[{mid}]",
                        font=("Segoe UI", 8), fg="gray").pack(side=tk.LEFT)

                status = tk.Label(row, text="✓", fg="green",
                                 font=("Segoe UI", 10, "bold"))
                status.pack(side=tk.RIGHT, padx=(0, 10))
                status.bind("<Visibility>",
                            lambda e, m=mid, l=status: self._update_status(l, m))

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        left_btns = tk.Frame(btn_frame)
        left_btns.pack(side=tk.LEFT)

        tk.Button(left_btns, text="Включить все", command=self._enable_all,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=2)

        tk.Button(left_btns, text="Отключить все", command=self._disable_all,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=2)

        right_btns = tk.Frame(btn_frame)
        right_btns.pack(side=tk.RIGHT)

        tk.Button(right_btns, text="Сохранить", command=self._save,
                 font=("Segoe UI", 9), bg="#e0e0e0", width=12).pack(side=tk.LEFT, padx=2)

        tk.Button(right_btns, text="Установить", command=self._install,
                 font=("Segoe UI", 9, "bold"), bg="#4CAF50", fg="white",
                 width=18).pack(side=tk.LEFT, padx=2)

        instr = tk.Label(self.root,
                        text="Совет: для перезапуска проводника используйте:\n"
                             "  taskkill /f /im explorer.exe && start explorer.exe",
                        font=("Segoe UI", 8), fg="gray", justify=tk.LEFT)
        instr.pack(fill=tk.X, padx=10, pady=(0, 5))

    def _update_status(self, status_label, module_id):
        var = self.vars.get(module_id)
        if var:
            status_label.config(text="✓" if var.get() else "✗",
                               fg="green" if var.get() else "red")

    def _on_toggle(self):
        pass

    def _enable_all(self):
        for mid in self.vars:
            self.vars[mid].set(True)
        self._save()
        messagebox.showinfo("Готово", "Все модули включены. Нажмите 'Установить' для применения.")

    def _disable_all(self):
        for mid in self.vars:
            self.vars[mid].set(False)
        self._save()
        messagebox.showinfo("Готово", "Все модули отключены. Контекстное меню будет пустым.")

    def _save(self):
        enabled = {mid: var.get() for mid, var in self.vars.items()}
        save_config(enabled)
        self.config = enabled
        messagebox.showinfo("Сохранено",
                           f"Конфиг сохранён: {sum(1 for v in enabled.values() if v)}/{len(enabled)} модулей включено.\n"
                           "Нажмите 'Установить' для применения изменений.")

    def _install(self):
        registry_py = os.path.join(SCRIPT_DIR, "registry_manager.py")
        if not os.path.exists(registry_py):
            messagebox.showerror("Ошибка", f"Файл не найден:\n{registry_py}")
            return

        enabled = {mid: var.get() for mid, var in self.vars.items()}
        save_config(enabled)
        self.config = enabled

        msg = messagebox.askyesno(
            "Установка контекстного меню",
            "Для установки контекстного меню требуется запуск от имени администратора.\n\n"
            "Нажмите 'Да', чтобы открыть PowerShell с правами администратора.\n"
            "В открывшемся окне выполните команду:\n\n"
            f"  python \"{registry_py}\"\n"
            "  taskkill /f /im explorer.exe && start explorer.exe\n\n"
            "Применить сейчас?"
        )

        if msg:
            try:
                subprocess.run(
                    ["powershell", "Start-Process", "powershell",
                     "-Verb", "RunAs",
                     "-ArgumentList",
                     f"'-NoExit -Command \"cd \\\"{SCRIPT_DIR}\\\"; python \\\"{registry_py}\\\"; "
                     f"Write-Host \\\"`nГотово! Для перезапуска проводника введите: "
                     f"taskkill /f /im explorer.exe && start explorer.exe\\\"\"'"],
                    shell=True
                )
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось запустить админ-оболочку:\n{e}")

        messagebox.showinfo(
            "Готово к установке",
            "Конфиг сохранён. В окне администратора выполните:\n\n"
            "1. python registry_manager.py\n"
            "2. taskkill /f /im explorer.exe && start explorer.exe\n\n"
            "Или скопируйте команды из открывшегося окна."
        )


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        style.theme_use("vista")
    except:
        pass
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()