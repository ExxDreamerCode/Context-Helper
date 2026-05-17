import os
import sys

MODULE_ID = "to_png"
NAME = "Конвертировать в PNG"

INPUT_EXTENSIONS = {".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}

def process(files):
    try:
        from PIL import Image
    except ImportError:
        print("Ошибка: требуется Pillow. pip install Pillow", file=sys.stderr)
        return

    converted = 0
    skipped = 0
    errors = 0

    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()

        if ext not in INPUT_EXTENSIONS:
            print(f"  ⤷ Неподдерживаемый формат: {os.path.basename(filepath)}")
            skipped += 1
            continue

        try:
            img = Image.open(filepath)
            new_path = os.path.splitext(filepath)[0] + ".png"
            img.save(new_path, "PNG")
            img.close()

            converted += 1
            print(f"  ✓ {os.path.basename(filepath)} -> {os.path.basename(new_path)}")

        except Exception as e:
            print(f"  ✗ Ошибка: {os.path.basename(filepath)}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nИтог: {converted} конвертировано, {skipped} пропущено, {errors} ошибок")