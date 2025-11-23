"""
Lädt SVG-Icons und konvertiert sie für tkinter.
"""

from pathlib import Path
from PIL import Image, ImageDraw
from io import BytesIO
import xml.etree.ElementTree as ET
import re


def svg_to_pil(svg_path, size=16, fill_color="white", bg_color=None):
    """
    Konvertiert SVG zu PIL Image (vereinfachte Methode ohne cairosvg).

    Args:
        svg_path: Pfad zur SVG-Datei
        size: Zielgröße in Pixeln
        fill_color: Farbe für SVG-Pfade
        bg_color: Optionaler Hintergrund (None = transparent)

    Returns:
        PIL Image
    """
    try:
        # Versuche mit cairosvg (falls installiert)
        import cairosvg

        # Lese SVG und ersetze fill-Farbe
        with open(svg_path, 'r') as f:
            svg_content = f.read()

        # Ersetze alle fill-Attribute durch gewünschte Farbe
        svg_content = re.sub(r'fill="[^"]*"', f'fill="{fill_color}"', svg_content)
        svg_content = re.sub(r'stroke="[^"]*"', f'stroke="{fill_color}"', svg_content)

        # Konvertiere zu PNG
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            output_width=size,
            output_height=size
        )

        img = Image.open(BytesIO(png_data))

        # Füge Hintergrund hinzu falls gewünscht
        if bg_color:
            background = Image.new('RGBA', (size, size), bg_color)
            background.paste(img, (0, 0), img)
            img = background

        return img

    except ImportError:
        # Fallback: Erstelle einfaches Icon
        return _create_fallback_icon(svg_path, size, fill_color, bg_color)


def _create_fallback_icon(svg_path, size, fill_color, bg_color):
    """Erstellt Fallback-Icon wenn cairosvg nicht verfügbar."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Prüfe welches Icon basierend auf Dateiname
    if 'youtube' in str(svg_path).lower():
        # YouTube-Icon: Abgerundetes Rechteck mit Play
        if bg_color:
            draw.rounded_rectangle([0, 0, size-1, size-1], radius=size//6, fill=bg_color)
        else:
            draw.rounded_rectangle([0, 0, size-1, size-1], radius=size//6, fill='#CC0000')

        # Play-Dreieck
        center_x, center_y = size // 2, size // 2
        tri_size = size // 3
        draw.polygon([
            (center_x - tri_size//2, center_y - tri_size//2),
            (center_x - tri_size//2, center_y + tri_size//2),
            (center_x + tri_size//2, center_y)
        ], fill=fill_color)

    elif 'arrow' in str(svg_path).lower() or 'upload' in str(svg_path).lower():
        # Upload-Icon: Pfeil nach oben
        if bg_color:
            padding = 2
            draw.ellipse([padding, padding, size-padding-1, size-padding-1], fill=bg_color)

        center_x, center_y = size // 2, size // 2
        arrow_height = size // 2

        # Pfeil-Schaft
        draw.rectangle([center_x-1, center_y-arrow_height//2, center_x+1, center_y+arrow_height//2],
                      fill=fill_color)

        # Pfeil-Kopf
        draw.polygon([
            (center_x, center_y - arrow_height//2 - 3),
            (center_x - 4, center_y - arrow_height//2 + 2),
            (center_x + 4, center_y - arrow_height//2 + 2)
        ], fill=fill_color)

    return img


def load_youtube_icon(size=16, bg_color=None):
    """
    Lädt YouTube-Icon (weiß).

    Args:
        size: Icon-Größe
        bg_color: Optional Hintergrundfarbe (default: rot)
    """
    svg_path = Path(__file__).parent.parent / 'youtube-svgrepo-com.svg'
    if not svg_path.exists():
        # Fallback
        return _create_fallback_icon(svg_path, size, 'white', bg_color or '#CC0000')

    return svg_to_pil(svg_path, size, fill_color='white', bg_color=bg_color)


def load_upload_icon(size=24, fill_color='#ffffff'):
    """
    Simples Material-Style Upload-Icon (ohne Hintergrund).
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    arrow_h = size // 2

    # Schaft
    draw.rectangle([cx-1, cy-arrow_h//2, cx+1, cy+arrow_h//2], fill=fill_color)
    # Kopf
    draw.polygon(
        [
            (cx, cy - arrow_h//2 - 3),
            (cx - 5, cy - arrow_h//2 + 3),
            (cx + 5, cy - arrow_h//2 + 3)
        ],
        fill=fill_color
    )
    # Basis-Linie
    draw.rectangle([cx - 8, cy + arrow_h//2 - 2, cx + 8, cy + arrow_h//2 + 2], fill=fill_color)
    return img


def load_folder_icon(size=24, fill_color='#ffffff', stroke_color=None):
    """
    Material-Style Folder (flach, kein Hintergrund-Kreis).
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 8
    top = margin + 2
    left = margin
    right = size - margin
    bottom = size - margin

    tab_width = (right - left) // 3
    tab_height = size // 7

    # Tab
    draw.rectangle(
        [left, top, left + tab_width, top + tab_height],
        fill=fill_color,
        outline=stroke_color
    )

    draw.rectangle(
        [left, top + tab_height - 1, right, bottom],
        fill=fill_color,
        outline=stroke_color
    )

    return img


def load_close_icon(size=18, fill_color="#888888"):
    """Einfaches X (Material nah)."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 4
    draw.line([pad, pad, size - pad, size - pad], fill=fill_color, width=2)
    draw.line([size - pad, pad, pad, size - pad], fill=fill_color, width=2)
    return img
