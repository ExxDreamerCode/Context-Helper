import winreg
import sys
import subprocess

def deltree(pk, name):
    try:
        k = winreg.OpenKey(pk, name, 0, winreg.KEY_WRITE | winreg.KEY_READ)
        while True:
            try:
                subkey = winreg.EnumKey(k, 0)
                deltree(k, subkey)
            except (OSError, WindowsError):
                break
        winreg.CloseKey(k)
        try:
            winreg.DeleteKey(pk, name)
            return True
        except Exception as e:
            return False
    except (OSError, WindowsError):
        return False

def clean_path(pk, path, name_to_delete):
    try:
        k = winreg.OpenKey(pk, path, 0, winreg.KEY_WRITE | winreg.KEY_READ)
        try:
            subkey = winreg.OpenKey(k, name_to_delete, 0, winreg.KEY_WRITE | winreg.KEY_READ)
            winreg.CloseKey(subkey)
            print(f"  Найдено: {path}\\{name_to_delete}")
            if deltree(k, name_to_delete):
                print(f"    ✓ Удалено")
            else:
                print(f"    ✗ Не удалось удалить")
        except:
            pass
        winreg.CloseKey(k)
    except:
        pass

def clean_registry():
    print("=" * 70)
    print("  ПОЛНАЯ ОЧИСТКА РЕЕСТРА")
    print("  Удаление: ContextHelper, MyTools, WatermarkAction")
    print("=" * 70)
    print()

    try:
        test_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "test_admin")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "test_admin")
    except PermissionError:
        print("❌ ОШИБКА: Запустите от имени администратора!", file=sys.stderr)
        print(f'  Щёлкните правой кнопкой по PowerShell/cmd → "Запуск от имени администратора"')
        print(f'  Затем выполните: python "{sys.argv[0]}"')
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    paths_to_clean = [
        r"*\shell",
        r"*\shellex\ContextMenuHandlers",
        r"AllFileSystemObjects\shell",
        r"Directory\shell",
        r"Directory\Background\shell",
        r"Drive\shell",
        r"Folder\shell",
        r"*\ShellEx\ContextMenuHandlers",
    ]

    names_to_delete = [
        "MyTools",
        "MyTools_duplicate_finder",
        "MyTools_metadata_extractor",
        "MyTools_remove_bg",
        "MyTools_to_png",
        "WatermarkAction",
        "ContextHelper",
    ]

    print("🔍 Поиск и удаление записей...")
    print("-" * 70)

    deleted_count = 0

    for base_path in paths_to_clean:
        for name in names_to_delete:
            try:
                full_path = f"{base_path}\\{name}"
                k = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, full_path, 0, winreg.KEY_READ)
                winreg.CloseKey(k)
                print(f"  Найдено: {full_path}")
                if deltree(winreg.HKEY_CLASSES_ROOT, full_path):
                    print(f"    ✓ Удалено")
                    deleted_count += 1
                else:
                    print(f"    ✗ Не удалось удалить")
            except:
                pass

    print("\n🔍 Проверка вложенных команд...")
    nested_paths = [
        r"*\shell\MyTools\menu\shell",
        r"*\shell\ContextHelper\menu\shell",
        r"AllFileSystemObjects\shell\MyTools\menu\shell",
        r"AllFileSystemObjects\shell\ContextHelper\menu\shell",
    ]

    for nested_path in nested_paths:
        try:
            k = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, nested_path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(k, i)
                    if subkey_name in names_to_delete or subkey_name in ["to_png", "watermark", "remove_bg", "duplicate_finder", "metadata_extractor"]:
                        print(f"  Найдена команда: {nested_path}\\{subkey_name}")
                        full_path = f"{nested_path}\\{subkey_name}"
                        if deltree(winreg.HKEY_CLASSES_ROOT, full_path):
                            print(f"    ✓ Удалено")
                            deleted_count += 1
                    i += 1
                except:
                    break
            winreg.CloseKey(k)
        except:
            pass

    print("\n🔍 Удаление пустых родительских ключей...")
    parent_keys = [
        r"*\shell\MyTools",
        r"*\shell\ContextHelper",
        r"AllFileSystemObjects\shell\MyTools",
        r"AllFileSystemObjects\shell\ContextHelper",
        r"Directory\shell\MyTools",
        r"Directory\shell\ContextHelper",
        r"Directory\Background\shell\MyTools",
        r"Directory\Background\shell\ContextHelper",
    ]

    for parent in parent_keys:
        try:
            full_path = parent
            k = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, full_path, 0, winreg.KEY_READ)
            winreg.CloseKey(k)
            print(f"  Найдено: {full_path}")
            if deltree(winreg.HKEY_CLASSES_ROOT, full_path):
                print(f"    ✓ Удалено")
                deleted_count += 1
        except:
            pass

    print("-" * 70)

    if deleted_count > 0:
        print(f"\n✅ Удалено {deleted_count} записей")
    else:
        print("\n✅ Ничего не найдено — реестр уже чист")

    print("\n" + "=" * 70)
    print("  ОЧИСТКА ЗАВЕРШЕНА!")
    print("=" * 70)

    print("\n⚠️  ВАЖНО: Для применения изменений нужно перезапустить Проводник")
    print("   (контекстное меню обновится только после перезапуска)")

    answer = input("\nПерезапустить Проводник сейчас? (y/n): ").strip().lower()
    if answer == 'y':
        print("\n🔄 Перезапуск Проводника...")
        subprocess.run("taskkill /f /im explorer.exe", shell=True, capture_output=True)
        subprocess.run("start explorer.exe", shell=True)
        print("✅ Проводник перезапущен")
    else:
        print("\n📌 Выполните вручную:")
        print("   taskkill /f /im explorer.exe && start explorer.exe")

    print("\n✨ Готово!")

if __name__ == "__main__":
    clean_registry()