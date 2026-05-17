import os
import sys

MODULE_ID = "watermark"
NAME = "Добавить водяной знак"
TEXT = "© Пример"
POSITION = "bottom-right"
FONT_SIZE = 36
OPACITY = 128


def process(files):
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    except ImportError:
        print("Ошибка: Для работы модуля 'Добавить водяной знак' требуется Pillow.", file=sys.stderr)
        print("Установите: pip install Pillow", file=sys.stderr)
        return

    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    processed = 0
    errors = 0
    skipped = 0

    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()

        if ext not in image_extensions:
            print(f"  ⤷ Пропущен (не изображение): {os.path.basename(filepath)}")
            skipped += 1
            continue

        try:
            img = Image.open(filepath).convert("RGBA")
            width, height = img.size
            txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)

            font = None
            for font_path in [
                "C:\\Windows\\Fonts\\arial.ttf",
                "C:\\Windows\\Fonts\\segoeui.ttf",
                "C:\\Windows\\Fonts\\tahoma.ttf",
                "C:\\Windows\\Fonts\\calibri.ttf",
            ]:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, FONT_SIZE)
                        break
                    except Exception:
                        continue

            if font is None:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), TEXT, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            margin = 20
            if POSITION == "top-left":
                pos = (margin, margin)
            elif POSITION == "top-right":
                pos = (width - text_width - margin, margin)
            elif POSITION == "bottom-left":
                pos = (margin, height - text_height - margin)
            elif POSITION == "center":
                pos = ((width - text_width) // 2, (height - text_height) // 2)
            else:
                pos = (width - text_width - margin, height - text_height - margin)

            shadow_color = (0, 0, 0, min(OPACITY // 2, 128))
            text_color = (255, 255, 255, OPACITY)

            draw.text((pos[0] + 2, pos[1] + 2), TEXT, font=font, fill=shadow_color)
            draw.text(pos, TEXT, font=font, fill=text_color)

            watermarked = Image.alpha_composite(img, txt_layer)
            watermarked = watermarked.convert("RGB")

            if ext in {'.jpg', '.jpeg'}:
                watermarked.save(filepath, "JPEG", quality=95)
            else:
                watermarked.save(filepath)

            img.close()
            processed += 1
            print(f"  ✓ Водяной знак добавлен: {os.path.basename(filepath)}")

        except Exception as e:
            print(f"  ✗ Ошибка при обработке {os.path.basename(filepath)}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nИтог: {processed} обработано, {skipped} пропущено, {errors} ошибок")