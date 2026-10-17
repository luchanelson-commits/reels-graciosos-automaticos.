import os
import io
import re
import math
import random
import asyncio
import subprocess
from pathlib import Path

import requests
import imageio_ffmpeg
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

# ==================================================
# CONFIGURACIÓN
# ==================================================

WIDTH = 720
HEIGHT = 1280
FPS = 12
DURATION = 30
SCENES = 4
SCENE_SECONDS = DURATION / SCENES
VOICE = "es-MX-DaliaNeural"

BRAND = "Nelson Lucha Reels Graciosos"
SIGNATURE = "Nelson Lucha"

OUT = Path("salida")
FRAMES = OUT / "frames"
PHOTOS = OUT / "fotos"
VIDEO = OUT / "reel_gracioso.mp4"
AUDIO = OUT / "narracion.mp3"

for folder in (OUT, FRAMES, PHOTOS):
    folder.mkdir(parents=True, exist_ok=True)

# ==================================================
# CHISTES CORTOS
# ==================================================

JOKES = [
    {
        "query": "funny dog real photo",
        "title": "CUANDO TE DESCUBREN",
        "text": "Yo no fui...",
        "punch": "¡Pero el perro ya confesó! 😂",
        "voice": "Yo no fui... ¡pero el perro ya confesó."
    },
    {
        "query": "funny cat expression photograph",
        "title": "EL JEFE DE LA CASA",
        "text": "Mi gato no paga alquiler...",
        "punch": "¡Y todavía me mira feo! 😹",
        "voice": "Mi gato no paga alquiler... ¡y todavía me mira feo!"
    },
    {
        "query": "funny surprised person photograph",
        "title": "EL SUELDO",
        "text": "Cobré y me sentí millonario...",
        "punch": "¡Hasta que pagué las cuentas! 😂",
        "voice": "Cobré y me sentí millonario... ¡hasta que pagué las cuentas!"
    },
    {
        "query": "funny dog looking at food photo",
        "title": "LA DIETA",
        "text": "Hoy sí comienzo la dieta...",
        "punch": "¡Después de esta última comida! 🤣",
        "voice": "Hoy sí comienzo la dieta... ¡después de esta última comida!"
    },
    {
        "query": "funny person reaction photo",
        "title": "EL LUNES",
        "text": "Mañana comienzo a hacer ejercicio...",
        "punch": "¡Eso dije el lunes pasado! 😅",
        "voice": "Mañana comienzo a hacer ejercicio... ¡eso dije el lunes pasado!"
    },
    {
        "query": "funny cat sitting photograph",
        "title": "TRABAJO EN EQUIPO",
        "text": "Mi gato me ayuda a trabajar...",
        "punch": "¡Se acuesta sobre el teclado! 😹",
        "voice": "Mi gato me ayuda a trabajar... ¡se acuesta sobre el teclado!"
    },
    {
        "query": "funny dog guilty expression photo",
        "title": "NO HAY EVIDENCIA",
        "text": "En esta casa nadie rompió nada...",
        "punch": "¡Solo falta interrogar al perro! 😂",
        "voice": "En esta casa nadie rompió nada... ¡solo falta interrogar al perro!"
    },
    {
        "query": "funny person eating food photograph",
        "title": "SOLO UNA PROBADITA",
        "text": "Dije que solo probaría un poquito...",
        "punch": "¡Y ya no quedó nada! 🤣",
        "voice": "Dije que solo probaría un poquito... ¡y ya no quedó nada!"
    },
]


# ==================================================
# TIPOGRAFÍA
# ==================================================

def get_font(size, italic=False):
    candidates = []

    if italic:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf",
        ]

    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ==================================================
# BUSCAR FOTOGRAFÍAS REALES CON LICENCIA
# ==================================================

def search_photo(query):
    api = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,
        "gsrlimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata|size",
    }

    headers = {
        "User-Agent": "NelsonLuchaReels/1.0 (video generator)"
    }

    try:
        response = requests.get(
            api,
            params=params,
            headers=headers,
            timeout=25
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})

        candidates = list(pages.values())
        random.shuffle(candidates)

        for page in candidates:
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue

            info = info_list[0]
            mime = info.get("mime", "")

            if mime not in ("image/jpeg", "image/png", "image/webp"):
                continue

            if info.get("width", 0) < 500:
                continue

            metadata = info.get("extmetadata", {})
            license_name = metadata.get("LicenseShortName", {}).get(
                "value", ""
            )
            license_lower = license_name.lower()

            allowed = (
                "cc0" in license_lower
                or "public domain" in license_lower
                or "cc by" in license_lower
            )

            if not allowed:
                continue

            return {
                "url": info["url"],
                "title": page.get("title", "Fotografía"),
                "license": license_name,
                "artist": metadata.get("Artist", {}).get(
                    "value", "Autor no indicado"
                ),
                "license_url": metadata.get("LicenseUrl", {}).get(
                    "value", ""
                ),
                "page_url": info.get("descriptionurl", ""),
            }

    except Exception as error:
        print(f"No se pudo buscar la fotografía: {error}")

    return None


def download_photo(photo, index):
    if not photo:
        return None

    try:
        response = requests.get(
            photo["url"],
            headers={"User-Agent": "NelsonLuchaReels/1.0"},
            timeout=30
        )
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))
        image.load()
        image = image.convert("RGB")

        path = PHOTOS / f"foto_{index}.jpg"
        image.save(path, quality=92)

        return path

    except Exception as error:
        print(f"No se pudo descargar la fotografía: {error}")
        return None


# ==================================================
# FONDO REALISTA Y MOVIMIENTO SUAVE
# ==================================================

def prepare_photo(path):
    if path and path.exists():
        try:
            image = Image.open(path).convert("RGB")
            image = ImageOpsFit(image, WIDTH, HEIGHT)
            return image
        except Exception:
            pass

    # Fondo fotográfico neutro si no se consigue una imagen.
    # Se evita presentar un dibujo como si fuera una fotografía.
    image = Image.new("RGB", (WIDTH, HEIGHT), (38, 42, 53))
    draw = ImageDraw.Draw(image)
    draw.text(
        (WIDTH // 2, HEIGHT // 2),
        "¡ESPERA EL REMATE!",
        font=get_font(36),
        fill="white",
        anchor="mm"
    )
    return image


def ImageOpsFit(image, width, height):
    from PIL import ImageOps
    return ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.45)
    )


def cinematic_frame(photo, progress):
    # Efecto de acercamiento progresivo para que la escena
    # tenga movimiento, aunque la fuente sea una fotografía.
    zoom = 1.0 + (0.045 * progress)
    crop_w = int(WIDTH / zoom)
    crop_h = int(HEIGHT / zoom)

    left = (WIDTH - crop_w) // 2
    top = (HEIGHT - crop_h) // 2

    frame = photo.crop((
        left,
        top,
        left + crop_w,
        top + crop_h
    ))
    frame = frame.resize(
        (WIDTH, HEIGHT),
        Image.Resampling.LANCZOS
    )

    # Contraste moderado y oscurecimiento para leer el texto.
    frame = ImageEnhance.Contrast(frame).enhance(1.08)
    shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 55))
    frame = Image.alpha_composite(frame.convert("RGBA"), shade)

    # Degradado oscuro en la zona inferior.
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(HEIGHT // 2, HEIGHT):
        alpha = int(150 * ((y - HEIGHT // 2) / (HEIGHT // 2)))
        draw.line((0, y, WIDTH, y), fill=(0, 0, 0, alpha))

    return Image.alpha_composite(frame, overlay)


# ==================================================
# TEXTO Y MARCA DE AGUA
# ==================================================

def draw_centered(draw, text, y, font, fill, stroke_width=2):
    draw.text(
        (WIDTH // 2, y),
        text,
        font=font,
        fill=fill,
        anchor="mm",
        align="center",
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, 230)
    )


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_panel(draw, y, text, font, fill, max_width=620):
    lines = wrap_text(draw, text, font, max_width)
    line_height = 57
    height = len(lines) * line_height + 34

    draw.rounded_rectangle(
        (35, y - height // 2, WIDTH - 35, y + height // 2),
        radius=24,
        fill=(0, 0, 0, 170),
        outline=(255, 255, 255, 80),
        width=2
    )

    start_y = y - ((len(lines) - 1) * line_height) // 2

    for index, line in enumerate(lines):
        draw.text(
            (WIDTH // 2, start_y + index * line_height),
            line,
            font=font,
            fill=fill,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 240)
        )


def render_frame(photo, joke, scene_index, progress, local_time):
    frame = cinematic_frame(photo, progress)
    draw = ImageDraw.Draw(frame, "RGBA")

    # Encabezado.
    draw.rounded_rectangle(
        (35, 45, WIDTH - 35, 125),
        radius=24,
        fill=(0, 0, 0, 165)
    )

    draw_centered(
        draw,
        joke["title"],
        85,
        get_font(31),
        (255, 220, 75, 255)
    )

    # Texto inicial y remate, con espacio entre ambos.
    if local_time < SCENE_SECONDS * 0.57:
        draw_panel(
            draw,
            740,
            joke["text"],
            get_font(39),
            (255, 255, 255, 255)
        )
    else:
        draw_panel(
            draw,
            740,
            joke["punch"],
            get_font(36),
            (255, 225, 85, 255)
        )

    # Barra de progreso de cada escena.
    bar_x = 50
    bar_y = 1165
    bar_width = WIDTH - 100

    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + 8),
        radius=4,
        fill=(255, 255, 255, 90)
    )

    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + int(bar_width * progress),
            bar_y + 8
        ),
        radius=4,
        fill=(255, 220, 65, 255)
    )

    # Marca de agua permanente.
    draw.rounded_rectangle(
        (65, 1190, WIDTH - 65, 1245),
        radius=20,
        fill=(0, 0, 0, 185),
        outline=(255, 255, 255, 60),
        width=1
    )

    draw_centered(
        draw,
        BRAND,
        1217,
        get_font(19),
        (255, 255, 255, 255),
        stroke_width=1
    )

    # Firma elegante al final de cada escena.
    if local_time >= SCENE_SECONDS - 1.3:
        alpha = int(
            255 * min(1, (local_time - (SCENE_SECONDS - 1.3)) / 0.5)
        )
        draw.rounded_rectangle(
            (145, 985, WIDTH - 145, 1060),
            radius=25,
            fill=(0, 0, 0, 175)
        )
        draw.text(
            (WIDTH // 2, 1022),
            SIGNATURE,
            font=get_font(31, italic=True),
            fill=(255, 235, 170, alpha),
            anchor="mm",
            stroke_width=1,
            stroke_fill=(0, 0, 0, 200)
        )

    return frame.convert("RGB")


# ==================================================
# NARRACIÓN
# ==================================================

async def create_voice(jokes):
    narration = " ".join(joke["voice"] for joke in jokes)

    # Voz algo rápida para que entren los chistes sin
    # perder claridad.
    communicate = edge_tts.Communicate(
        narration,
        VOICE,
        rate="+12%",
        volume="+0%"
    )
    await communicate.save(str(AUDIO))


# ==================================================
# CRÉDITOS DE FOTOGRAFÍAS
# ==================================================

def save_credits(photos):
    path = OUT / "creditos_imagenes.txt"

    with open(path, "w", encoding="utf-8") as file:
        file.write("CRÉDITOS DE LAS FOTOGRAFÍAS\n")
        file.write("===========================\n\n")

        for index, photo in enumerate(photos, start=1):
            if not photo:
                file.write(f"Escena {index}: no se obtuvo fotografía.\n\n")
                continue

            file.write(f"Escena {index}\n")
            file.write(f"Archivo: {photo['title']}\n")
            file.write(f"Autor: {photo['artist']}\n")
            file.write(f"Licencia: {photo['license']}\n")
            file.write(f"Licencia URL: {photo['license_url']}\n")
            file.write(f"Página: {photo['page_url']}\n\n")


# ==================================================
# GENERACIÓN DEL VIDEO
# ==================================================

def main():
    print("Preparando un Reel de 30 segundos...")

    selected = random.sample(JOKES, SCENES)
    photos = []
    backgrounds = []

    for index, joke in enumerate(selected, start=1):
        print(f"Buscando fotografía para escena {index}...")
        photo_info = search_photo(joke["query"])
        photos.append(photo_info)

        photo_path = download_photo(photo_info, index)
        backgrounds.append(prepare_photo(photo_path))

    save_credits(photos)

    print("Generando narración en español...")
    asyncio.run(create_voice(selected))

    total_frames = DURATION * FPS
    frame_number = 0

    print("Creando escenas con movimiento...")

    for scene_index, joke in enumerate(selected):
        background = backgrounds[scene_index]

        for frame_in_scene in range(int(SCENE_SECONDS * FPS)):
            progress = frame_in_scene / max(
                1, int(SCENE_SECONDS * FPS) - 1
            )
            local_time = frame_in_scene / FPS

            frame = render_frame(
                background,
                joke,
                scene_index,
                progress,
                local_time
            )

            frame_path = FRAMES / f"frame_{frame_number:05d}.jpg"
            frame.save(frame_path, quality=90)
            frame_number += 1

    # Asegurar exactamente la cantidad de cuadros prevista.
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_pattern = str(FRAMES / "frame_%05d.jpg")

    command = [
        ffmpeg,
        "-y",
        "-framerate", str(FPS),
        "-i", output_pattern,
        "-i", str(AUDIO),
        "-vf", "format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "24",
        "-c:a", "aac",
        "-b:a", "128k",
        "-af", f"apad,atrim=0:{DURATION}",
        "-t", str(DURATION),
        "-shortest",
        "-movflags", "+faststart",
        str(VIDEO)
    ]

    print("Montando video y audio...")
    subprocess.run(command, check=True)

    # Limpiar los cuadros temporales para ahorrar espacio.
    for file in FRAMES.glob("frame_*.jpg"):
        file.unlink()

    print(f"¡Reel terminado! Archivo: {VIDEO}")
    print(f"Duración configurada: {DURATION} segundos")
    print("Créditos de las fotos: salida/creditos_imagenes.txt")


if __name__ == "__main__":
    main()
