import winreg
import os
import sys
import json
import importlib.util
import subprocess

MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules_config.json")
LAUNCHER_BAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.bat")


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
        print(f"❌ Папка {MODULES_DIR} не найдена", file=sys.stderr)
        return modules

    for fn in sorted(os.listdir(MODULES_DIR)):
        if not fn.endswith(".py") or fn == "__init__.py":
            continue
        fp = os.path.join(MODULES_DIR, fn)
        mid, label = get_module_info(fp)
        if mid and label:
            modules.append((mid, label, fn))
        else:
            print(f"  ⚠ Пропущен {fn}: нет MODULE_ID или NAME", file=sys.stderr)
    return modules


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def save_config(enabled_dict):
    data = {
        "_comment": "Конфиг включения модулей. true = включён, false = отключён.",
        "enabled": enabled_dict
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sync_config(modules):
    config = load_config()
    if config is None:
        enabled = {mid: True for mid, _, _ in modules}
        save_config(enabled)
        return enabled

    enabled = config.get("enabled", {})

    changed = False
    for mid, _, _ in modules:
        if mid not in enabled:
            enabled[mid] = True
            changed = True

    mids = {mid for mid, _, _ in modules}
    for mid in list(enabled.keys()):
        if mid not in mids:
            del enabled[mid]
            changed = True

    if changed:
        save_config(enabled)

    return enabled


def filter_enabled_modules(modules, enabled):
    result = []
    for mid, label, fn in modules:
        if enabled.get(mid, True):
            result.append((mid, label, fn))
    return result


def deltree(pk, name):
    try:
        k = winreg.OpenKey(pk, name, 0, winreg.KEY_WRITE | winreg.KEY_READ)
        while True:
            try:
                deltree(k, winreg.EnumKey(k, 0))
            except:
                break
        winreg.CloseKey(k)
        try:
            winreg.DeleteKey(pk, name)
        except:
            pass
    except:
        pass


def clean_registry(silent=False):
    paths = [
        r"*\shell", r"AllFileSystemObjects\shell",
        r"Directory\shell", r"Directory\Background\shell",
        r"Drive\shell", r"Folder\shell",
    ]
    for base in paths:
        try:
            k = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, base, 0, winreg.KEY_WRITE)
            deltree(k, "MyTools")
            deltree(k, "WatermarkAction")
            winreg.CloseKey(k)
            if not silent:
                print(f"  ✓ Очищено: {base}")
        except PermissionError:
            if not silent:
                print("❌ Нет прав администратора!", file=sys.stderr)
            return False
        except:
            pass
    return True


def setup_context_menu(modules, silent=False):
    try:
        root = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\MyTools")
        winreg.SetValueEx(root, "", 0, winreg.REG_SZ, "ContextHelper")
        winreg.SetValueEx(root, "ExtendedSubCommandsKey", 0,
                          winreg.REG_SZ, r"*\shell\MyTools\menu")
        winreg.CloseKey(root)

        root2 = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT,
                                 r"AllFileSystemObjects\shell\MyTools")
        winreg.SetValueEx(root2, "", 0, winreg.REG_SZ, "ContextHelper")
        winreg.SetValueEx(root2, "ExtendedSubCommandsKey", 0,
                          winreg.REG_SZ, r"*\shell\MyTools\menu")
        winreg.CloseKey(root2)

        menu = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\MyTools\menu")
        winreg.SetValueEx(menu, "", 0, winreg.REG_SZ, "")
        winreg.CloseKey(menu)

        shell = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\MyTools\menu\shell")

        for mid, label, _ in modules:
            mk = winreg.CreateKey(shell, mid)
            winreg.SetValueEx(mk, "", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(mk, "MUIVerb", 0, winreg.REG_SZ, label)

            cmd = winreg.CreateKey(mk, "command")
            cmd_val = f'"{LAUNCHER_BAT}" {mid} "%1"'
            winreg.SetValueEx(cmd, "", 0, winreg.REG_SZ, cmd_val)
            winreg.CloseKey(cmd)
            winreg.CloseKey(mk)

        winreg.CloseKey(shell)

        if not silent:
            print(f"\n✓ Создано подменю 'ContextHelper'")
            for mid, label, _ in modules:
                print(f"    ✓ {label}")
        return True

    except PermissionError:
        if not silent:
            print("❌ Нет прав администратора!", file=sys.stderr)
        return False
    except Exception as e:
        if not silent:
            print(f"❌ Ошибка: {e}", file=sys.stderr)
        return False


def open_config_for_edit():
    if not os.path.exists(CONFIG_PATH):
        print("Конфиг не найден. Запустите сначала python registry_manager.py")
        return
    print(f"Открываю {CONFIG_PATH} в блокноте...")
    print("Измените значения true/false и сохраните файл.")
    print("После закрытия блокнота конфиг будет применён.")
    print()
    subprocess.run(["notepad", CONFIG_PATH], check=True)
    print("Конфиг сохранён. Для применения изменений запустите:")
    print("  python registry_manager.py")


def interactive_setup(modules):
    print("Выберите модули для включения (y/n):")
    enabled = {}
    for mid, label, _ in modules:
        ans = input(f"  {label} [{mid}]? (Y/n): ").strip().lower()
        enabled[mid] = ans != "n"

    save_config(enabled)
    print(f"\nКонфиг сохранён. Запустите:")
    print("  python registry_manager.py")


def main():
    silent = "--silent" in sys.argv
    edit = "--edit" in sys.argv
    setup = "--setup" in sys.argv

    if edit:
        open_config_for_edit()
        return

    if not silent and not setup:
        print("=" * 60)
        print("  Менеджер контекстного меню 'Мои инструменты'")
        print("=" * 60)
        print()

    if not silent and not setup:
        print("Сканирование модулей...")
        print("-" * 60)
    modules = scan_modules()

    if not modules:
        if not silent:
            print("\nНет валидных модулей в папке modules/.")
        sys.exit(1)

    if not silent and not setup:
        print(f"\nНайдено модулей: {len(modules)}")

    if setup:
        interactive_setup(modules)
        return

    enabled = sync_config(modules)
    active_modules = filter_enabled_modules(modules, enabled)

    if not silent:
        print(f"\nВключено: {len(active_modules)}/{len(modules)} модулей")
        for mid, label, _ in modules:
            status = "✓" if enabled.get(mid, True) else "✗"
            print(f"  {status} {label}")

    try:
        tk = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\._test_admin")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\._test_admin")
    except PermissionError:
        if not silent:
            print("\n❌ ОШИБКА: Запустите от имени администратора!", file=sys.stderr)
            print(f'  python "{os.path.abspath(__file__)}"')
        sys.exit(1)
    except:
        pass

    if not silent:
        print("\nОчистка старой регистрации...")
        print("-" * 60)
    if not clean_registry(silent):
        sys.exit(1)

    if not silent:
        print("\nСоздание контекстного меню...")
        print("-" * 60)
    if not setup_context_menu(active_modules, silent):
        sys.exit(1)

    if not silent:
        print("\n✓ Готово! Выполните:")
        print("  taskkill /f /im explorer.exe && start explorer.exe")
        print()
        print("Для изменения состава модулей:")
        print(f"  python \"{os.path.abspath(__file__)}\" --edit")
        print(f"  python \"{os.path.abspath(__file__)}\" --setup")


if __name__ == "__main__":
    main()