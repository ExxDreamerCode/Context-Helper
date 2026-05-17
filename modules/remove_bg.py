import os

MODULE_ID = "remove_bg"
NAME = "Удалить фон"

INPUT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

def process(files):
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        print("Ошибка: требуется rembg. Установите: pip install rembg", file=sys.stderr)
        return

    processed = 0
    skipped = 0
    errors = 0

    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()

        if ext not in INPUT_EXTENSIONS:
            print(f"  ⤷ Пропущен (не изображение): {os.path.basename(filepath)}")
            skipped += 1
            continue

        try:
            basename = os.path.splitext(os.path.basename(filepath))[0]
            dirname = os.path.dirname(filepath)
            out_path = os.path.join(dirname, f"{basename}_no_bg.png")

            print(f"  → {basename}...", end=" ")

            with open(filepath, "rb") as inp:
                input_data = inp.read()
                output_data = remove(input_data)

            with open(out_path, "wb") as out:
                out.write(output_data)

            processed += 1
            print(f"✓ сохранён как {basename}_no_bg.png")

        except Exception as e:
            print(f"\n  ✗ Ошибка: {os.path.basename(filepath)}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nИтог: {processed} обработано, {skipped} пропущено, {errors} ошибок")