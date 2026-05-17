import os
import json
import csv
from datetime import datetime

MODULE_ID = "metadata_extractor"
NAME = "Извлечь метаданные"


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024*1024:
        return f"{size_bytes/1024:.1f} КБ"
    else:
        return f"{size_bytes/(1024*1024):.1f} МБ"


def get_file_info(filepath):
    try:
        stat = os.stat(filepath)
        return {
            "filename": os.path.basename(filepath),
            "path": os.path.abspath(filepath),
            "extension": os.path.splitext(filepath)[1].lower(),
            "size_bytes": stat.st_size,
            "size_human": format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except:
        return {
            "filename": os.path.basename(filepath),
            "path": os.path.abspath(filepath),
            "error": "Не удалось прочитать информацию"
        }


def get_image_exif(filepath):
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        return {"error": "Pillow не установлен"}

    try:
        img = Image.open(filepath)
        result = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
        }

        exif = img._getexif()
        if exif:
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                if tag_name not in result:
                    if tag_name == "GPSInfo":
                        result["gps"] = str(value)
                    else:
                        result[tag_name] = str(value)[:500]

        img.close()
        return result
    except Exception as e:
        return {"error": str(e)}


def get_audio_tags(filepath):
    try:
        from mutagen import File
    except ImportError:
        return {"error": "mutagen не установлен"}

    try:
        audio = File(filepath)
        if audio is None:
            return {"error": "Неизвестный аудиоформат"}

        result = {}
        if hasattr(audio.info, 'length'):
            result["duration_seconds"] = round(audio.info.length, 1)
        if hasattr(audio.info, 'bitrate'):
            result["bitrate_kbps"] = audio.info.bitrate // 1000

        if hasattr(audio, 'tags') and audio.tags:
            for key, value in audio.tags.items():
                if isinstance(value, list):
                    result[key] = value[0] if value else None
                else:
                    result[key] = str(value)[:200]

        return result
    except Exception as e:
        return {"error": str(e)}


def get_pdf_info(filepath):
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return {"error": "PyPDF2 не установлен"}

    try:
        reader = PdfReader(filepath)
        result = {"num_pages": len(reader.pages)}

        if reader.metadata:
            for key, value in reader.metadata.items():
                key_clean = key.replace("/", "")
                result[key_clean] = str(value)[:200]

        return result
    except Exception as e:
        return {"error": str(e)}


def get_docx_info(filepath):
    try:
        from docx import Document
    except ImportError:
        return {"error": "python-docx не установлен"}

    try:
        doc = Document(filepath)
        result = {}

        props = doc.core_properties
        if props.author:
            result["author"] = props.author
        if props.title:
            result["title"] = props.title
        if props.subject:
            result["subject"] = props.subject
        if props.keywords:
            result["keywords"] = props.keywords
        if props.created:
            result["created"] = props.created.isoformat()
        if props.modified:
            result["modified"] = props.modified.isoformat()

        result["num_paragraphs"] = len(doc.paragraphs)

        return result
    except Exception as e:
        return {"error": str(e)}


def scan_files(filepaths):
    results = []
    supported_extensions = {
        '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp', '.gif',
        '.mp3', '.flac', '.ogg', '.m4a', '.wma',
        '.pdf', '.docx', '.doc'
    }

    total = len(filepaths)

    for i, filepath in enumerate(filepaths):
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filepath)[1].lower()

        print(f"  [{i+1}/{total}] {os.path.basename(filepath)}...")

        entry = get_file_info(filepath)

        if ext in supported_extensions:
            if ext in {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp', '.gif'}:
                entry["metadata"] = get_image_exif(filepath)
            elif ext in {'.mp3', '.flac', '.ogg', '.m4a', '.wma'}:
                entry["metadata"] = get_audio_tags(filepath)
            elif ext == '.pdf':
                entry["metadata"] = get_pdf_info(filepath)
            elif ext in {'.docx', '.doc'}:
                entry["metadata"] = get_docx_info(filepath)
        else:
            entry["metadata"] = {"note": f"Тип {ext} не поддерживается для глубокого извлечения"}

        results.append(entry)

    return results


def export_to_json(results, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return output_path


def export_to_csv(results, output_path):
    if not results:
        return

    all_keys = set()
    for entry in results:
        all_keys.update(entry.keys())
        if "metadata" in entry and isinstance(entry["metadata"], dict):
            for key in entry["metadata"].keys():
                all_keys.add(f"meta_{key}")

    all_keys = [k for k in all_keys if k not in ("metadata", "error")]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
        writer.writeheader()

        for entry in results:
            row = {}
            for key, value in entry.items():
                if key == "metadata" and isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        row[f"meta_{subkey}"] = str(subvalue)[:1000] if subvalue else ""
                elif isinstance(value, (str, int, float, bool, type(None))):
                    row[key] = value
                else:
                    row[key] = str(value)[:200]
            writer.writerow(row)

    return output_path


def show_export_dialog(file_count):
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox

        root = tk.Tk()
        root.withdraw()

        fmt = simpledialog.askstring(
            "Формат экспорта",
            f"Найдено файлов: {file_count}\n\n"
            "Выберите формат экспорта:\n"
            "  json - подробный, структурированный\n"
            "  csv  - плоская таблица (для Excel)\n\n"
            "Введите json или csv:",
            initialvalue="json"
        )

        root.destroy()

        if fmt and fmt.lower() in ['json', 'csv']:
            return fmt.lower()
        else:
            return "json"
    except:
        print("Использую формат JSON по умолчанию")
        return "json"


def collect_files_from_paths(paths):
    files = []

    for path in paths:
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for root, dirs, files_in_dir in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files_in_dir:
                    if f not in {'.DS_Store', 'Thumbs.db', 'desktop.ini'}:
                        files.append(os.path.join(root, f))

    return files


def process(files):
    if not files:
        print("Ошибка: не выбраны файлы или папки")
        return

    print("Сбор файлов для анализа...")

    all_files = collect_files_from_paths(files)

    if not all_files:
        print("Не найдено файлов для обработки")
        return

    print(f"Найдено файлов: {len(all_files)}")

    export_format = show_export_dialog(len(all_files))

    print("\nИзвлечение метаданных...")
    print("-" * 50)

    results = scan_files(all_files)

    print("-" * 50)
    print(f"Обработано: {len(results)} файлов")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.dirname(files[0]) if files else os.getcwd()

    if export_format == "json":
        output_file = os.path.join(output_dir, f"metadata_export_{timestamp}.json")
        export_to_json(results, output_file)
    else:
        output_file = os.path.join(output_dir, f"metadata_export_{timestamp}.csv")
        export_to_csv(results, output_file)

    print(f"\n✓ Экспорт завершён: {output_file}")