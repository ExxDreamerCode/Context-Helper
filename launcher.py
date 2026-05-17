import sys
import os
import importlib.util
import traceback
import time
import json
import tempfile
import threading

DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher_debug.log")

def debug(msg):
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{os.getpid()}] {msg}\n")

def run_module(module_id, files):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(script_dir, "modules", f"{module_id}.py")
    if not os.path.exists(module_path):
        debug(f"Модуль не найден: {module_path}")
        return
    spec = importlib.util.spec_from_file_location(module_id, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "process"):
        debug(f"Запуск module.process({files})")
        module.process(files)

def main():
    debug(f"Запуск с аргументами: {sys.argv}")
    if len(sys.argv) < 2:
        debug("ОШИБКА: не указан MODULE_ID")
        sys.exit(1)
    module_id = sys.argv[1]
    current_file = sys.argv[2] if len(sys.argv) > 2 else ""
    current_file = current_file.strip('"').strip("'")
    if not current_file or not os.path.exists(current_file):
        debug(f"Файл не найден или пуст: {current_file}")
        sys.exit(0)

    PID_FILE = os.path.join(tempfile.gettempdir(), f"contexthelper_main_{module_id}.pid")
    QUEUE_DIR = os.path.join(tempfile.gettempdir(), f"contexthelper_queue_{module_id}")

    try:
        fd = os.open(PID_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        os.makedirs(QUEUE_DIR, exist_ok=True)
        my_file = os.path.join(QUEUE_DIR, f"file_{os.getpid()}_{int(time.time() * 1000)}.json")
        with open(my_file, "w", encoding="utf-8") as f:
            json.dump({"file": current_file}, f)
        debug(f"Главный процесс, жду накопления...")
        time.sleep(0.5)
        for _ in range(5):
            queue_files = []
            if os.path.isdir(QUEUE_DIR):
                queue_files = [os.path.join(QUEUE_DIR, fn) for fn in os.listdir(QUEUE_DIR) if fn.endswith('.json')]
            if len(queue_files) >= 2:
                time.sleep(0.3)
            else:
                break
        accumulated = []
        if os.path.isdir(QUEUE_DIR):
            for fn in sorted(os.listdir(QUEUE_DIR)):
                if fn.endswith('.json'):
                    try:
                        with open(os.path.join(QUEUE_DIR, fn), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data.get("file") and data["file"] not in accumulated:
                                accumulated.append(data["file"])
                    except:
                        pass
        seen = set()
        unique_files = []
        for f in accumulated:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        try:
            if os.path.isdir(QUEUE_DIR):
                for fn in os.listdir(QUEUE_DIR):
                    try:
                        os.remove(os.path.join(QUEUE_DIR, fn))
                    except:
                        pass
                os.rmdir(QUEUE_DIR)
        except:
            pass
        try:
            os.remove(PID_FILE)
        except:
            pass
        debug(f"Накоплено файлов: {len(unique_files)} из {len(accumulated)} записей")
        run_module(module_id, unique_files)
    except FileExistsError:
        debug(f"Дополнительный процесс, добавляю в очередь: {current_file}")
        try:
            os.makedirs(QUEUE_DIR, exist_ok=True)
            my_file = os.path.join(QUEUE_DIR, f"file_{os.getpid()}_{int(time.time() * 1000)}.json")
            with open(my_file, "w", encoding="utf-8") as f:
                json.dump({"file": current_file}, f)
        except Exception as e:
            debug(f"Ошибка записи в очередь: {e}")
            run_module(module_id, [current_file])
        time.sleep(1.5)
    except Exception as e:
        debug(f"Общая ошибка: {e}")
        try:
            os.remove(PID_FILE)
        except:
            pass
        run_module(module_id, [current_file])

if __name__ == "__main__":
    main()