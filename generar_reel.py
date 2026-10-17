import os
import io
import random
import asyncio
import subprocess
from pathlib import Path

import requests
import imageio_ffmpeg
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

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

HEADERS = {
    "User-Agent": "NelsonLuchaReels/1.0 (photo retrieval)"
}

# =========================================================
# CHISTES
# =========================================================

JOKES = [
    {
        "query": "funny dog real photo",
        "title": "CUANDO TE DESCUBREN",
        "text": "Yo no fui...",
        "punch": "¡Pero el perro ya confesó! 😂",
        "voice": "Yo no fui... ¡pero el perro ya confesó!"
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
        "query": "funny person reaction photograph",
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
    {
        "query": "funny surprised dog photograph",
        "title": "EL SUSTO",
        "text": "Escuché un ruido en la noche...",
        "punch": "¡Y desperté hasta al vecino! 😂",
        "voice": "Escuché un ruido en la noche... ¡y desperté hasta al vecino!"
    },
    {
        "query": "funny cat looking at camera photograph",
        "title": "MI CARA EL LUNES",
        "text": "Yo llegando al trabajo...",
        "punch": "¡Y apenas es lunes! 😹",
        "voice": "Yo llegando al trabajo... ¡y apenas es lunes!"
    },
]


# =========================================================
# FUENTES
# =========================================================

def get_font(size, italic=False):
    if italic:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# =========================================================
# BÚSQUEDA DE FOTOGRAFÍAS
# =========================================================

def search_photo(query):
    api = "https://commons.wikimedia.org/w/api.php"

    queries = [
        query,
        query.replace("funny ", ""),
        "dog photograph" if "dog" in query else "cat photograph",
        "person photograph" if "person" in query else "animal photograph",
        "funny animal photograph",
    ]

    for search_term in queries:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrnamespace": 6,
            "gsrlimit": 30,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata|size",
        }

        try:
            response = requests.get(
                api,
                params=params,
                headers=HEADERS,
                timeout=25
            )
            response.raise_for_status()

            pages = response.json().get(
                "query", {}
            ).get("pages", {})

            candidates = list(pages.values())
            random.shuffle(candidates)

            for page in candidates:
                image_info_list = page.get("imageinfo", [])

                if not image_info_list:
                    continue

                info = image_info_list[0]
                mime = info.get("mime", "")

                if mime not in (
                    "image/jpeg",
                    "image/png",
                    "image/webp"
                ):
                    continue

                if info.get("width", 0) < 400:
                    continue

                metadata = info.get("extmetadata", {})
                license_name = metadata.get(
                    "LicenseShortName", {}
                ).get("value", "")

                license_lower = license_name.lower()

                allowed = (
                    "cc0" in license_lower
                    or "public domain" in license_lower
                    or "cc by" in license_lower
                )

                if not allowed:
                    continue

                result = {
                    "url": info["url"],
                    "title": page.get("title", "Fotografía"),
                    "license": license_name,
                    "artist": metadata.get(
                        "Artist", {}
                    ).get("value", "Autor no indicado"),
                    "license_url": metadata.get(
                        "LicenseUrl", {}
                    ).get("value", ""),
                    "page_url": info.get("descriptionurl", ""),
                }

                print(
                    f"Fotografía encontrada: {result['title']}"
                )

                return result

        except Exception as error:
            print(
                f"Error buscando '{search_term}': {error}"
            )

    print(f"No se encontró fotografía para: {query}")
    return None


# =========================================================
# DESCARGA Y VALIDACIÓN DE FOTOGRAFÍAS
# =========================================================

def download_photo(photo, index):
    if not photo:
        return None

    try:
        response = requests.get(
            photo["url"],
            headers=HEADERS,
            timeout=35
        )
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))
        image.load()
        image = image.convert("RGB")

        path = PHOTOS / f"foto_{index}.jpg"
        image.save(path, quality=94)

        print(f"Fotografía descargada: {path}")
        return path

    except Exception as error:
        print(f"Error descargando fotografía {index}: {error}")
        return None


def get_background(path):
    if path and path.exists():
        try:
            image = Image.open(path).convert("RGB")
            return ImageOps.fit(
                image,
                (WIDTH, HEIGHT),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.42)
            )
        except Exception as error:
            print(f"Error preparando fotografía: {error}")

    # Si no se consigue una foto, usar un fondo neutro.
    # No se presenta una ilustración como si fuera fotografía.
    image = Image.new("RGB", (WIDTH, HEIGHT), (45, 48, 58))
    draw = ImageDraw.Draw(image)
    draw.text(
        (WIDTH // 2, HEIGHT // 2),
        "¡ESPERA EL REMATE!",
        font=get_font(36),
        fill="white",
        anchor="mm"
    )
    return image


# =========================================================
# MOVIMIENTO Y ASPECTO CINEMATOGRÁFICO
# =========================================================

def cinematic_frame(photo, progress):
    zoom = 1.0 + (0.055 * progress)
    crop_w = max(1, int(WIDTH / zoom))
    crop_h = max(1, int(HEIGHT / zoom))

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

    frame = ImageEnhance.Contrast(frame).enhance(1.08)
    frame = ImageEnhance.Color(frame).enhance(1.05)

    shade = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 55)
    )

    frame = Image.alpha_composite(
        frame.convert("RGBA"),
        shade
    )

    # Oscurecimiento gradual inferior para mejorar la lectura.
    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    for y in range(HEIGHT // 2, HEIGHT):
        alpha = int(
            150 * ((y - HEIGHT // 2) / (HEIGHT // 2))
        )
        draw.line(
            (0, y, WIDTH, y),
            fill=(0, 0, 0, alpha)
        )

    return Image.alpha_composite(frame, gradient)


# =========================================================
# TEXTO
# =========================================================

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textbbox(
            (0, 0),
            candidate,
            font=font
        )[2]

        if width <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_centered(draw, text, y, font, fill):
    draw.text(
        (WIDTH // 2, y),
        text,
        font=font,
        fill=fill,
        anchor="mm",
        align="center",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 230)
    )


def draw_panel(draw, y, text, font, fill):
    lines = wrap_text(draw, text, font, WIDTH - 110)
    line_height = 55
    panel_height = len(lines) * line_height + 38

    draw.rounded_rectangle(
        (
            35,
            y - panel_height // 2,
            WIDTH - 35,
            y + panel_height // 2
        ),
        radius=24,
        fill=(0, 0, 0, 180),
        outline=(255, 255, 255, 75),
        width=2
    )

    first_y = y - ((len(lines) - 1) * line_height) // 2

    for i, line in enumerate(lines):
        draw.text(
            (WIDTH // 2, first_y + i * line_height),
            line,
            font=font,
            fill=fill,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 240)
        )


# =========================================================
# MARCA DE AGUA Y FIRMA
# =========================================================

def add_branding(draw, progress, local_time):
    draw.rounded_rectangle(
        (45, 45, WIDTH - 45, 125),
        radius=22,
        fill=(0, 0, 0, 165)
    )

    draw_centered(
        draw,
        BRAND,
        85,
        get_font(23),
        (255, 255, 255, 255)
    )

    # Marca de agua permanente en la parte inferior.
    draw.rounded_rectangle(
        (50, 1190, WIDTH - 50, 1245),
        radius=20,
        fill=(0, 0, 0, 185)
    )

    draw_centered(
        draw,
        "Nelson Lucha Reels Graciosos",
        1217,
        get_font(17),
        (255, 255, 255, 255)
    )

    # Firma elegante al final de cada escena.
    if local_time >= SCENE_SECONDS - 1.3:
        draw.rounded_rectangle(
            (155, 985, WIDTH - 155, 1060),
            radius=24,
            fill=(0, 0, 0, 185)
        )

        draw.text(
            (WIDTH // 2, 1022),
            SIGNATURE,
            font=get_font(32, italic=True),
            fill=(255, 230, 165, 255),
            anchor="mm",
            stroke_width=1,
            stroke_fill=(0, 0, 0, 200)
        )


# =========================================================
# CONSTRUIR CADA CUADRO
# =========================================================

def render_frame(photo, joke, progress, local_time):
    frame = cinematic_frame(photo, progress)
    draw = ImageDraw.Draw(frame, "RGBA")

    add_branding(draw, progress, local_time)

    if local_time < SCENE_SECONDS * 0.58:
        draw_panel(
            draw,
            735,
            joke["text"],
            get_font(39),
            (255, 255, 255, 255)
        )
    else:
        draw_panel(
            draw,
            735,
            joke["punch"],
            get_font(35),
            (255, 225, 75, 255)
        )

    # Barra de progreso.
    bar_x = 50
    bar_y = 1155
    bar_width = WIDTH - 100

    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + 7),
        radius=4,
        fill=(255, 255, 255, 90)
    )

    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + int(bar_width * progress),
            bar_y + 7
        ),
        radius=4,
        fill=(255, 220, 65, 255)
    )

    return frame.convert("RGB")


# =========================================================
# NARRACIÓN EN ESPAÑOL
# =========================================================

async def create_voice(jokes):
    narration = " ... ".join(joke["voice"] for joke in jokes)

    communicate = edge_tts.Communicate(
        narration,
        VOICE,
        rate="+10%",
        volume="+0%"
    )

    await communicate.save(str(AUDIO))


# =========================================================
# CRÉDITOS DE LAS FOTOGRAFÍAS
# =========================================================

def save_credits(photos):
    path = OUT / "creditos_imagenes.txt"

    with open(path, "w", encoding="utf-8") as file:
        file.write("CRÉDITOS DE FOTOGRAFÍAS\n")
        file.write("=======================\n\n")

        for index, photo in enumerate(photos, start=1):
            file.write(f"ESCENA {index}\n")

            if not photo:
                file.write("No se encontró fotografía.\n\n")
                continue

            file.write(f"Archivo: {photo['title']}\n")
            file.write(f"Autor: {photo['artist']}\n")
            file.write(f"Licencia: {photo['license']}\n")
            file.write(f"Licencia: {photo['license_url']}\n")
            file.write(f"Página: {photo['page_url']}\n\n")


# =========================================================
# GENERAR REEL
# =========================================================

def main():
    print("Iniciando generador de Reels...")
    print(f"Duración prevista: {DURATION} segundos")

    selected = random.sample(JOKES, SCENES)
    photo_info_list = []
    backgrounds = []

    for index, joke in enumerate(selected, start=1):
        print(f"\nBuscando foto para escena {index}...")

        photo_info = search_photo(joke["query"])
        photo_info_list.append(photo_info)

        photo_path = download_photo(photo_info, index)
        background = get_background(photo_path)

        backgrounds.append(background)

    save_credits(photo_info_list)

    print("\nGenerando narración...")
    asyncio.run(create_voice(selected))

    # Eliminar cuadros antiguos para evitar mezclar ejecuciones.
    for old_frame in FRAMES.glob("frame_*.jpg"):
        old_frame.unlink()

    frames_per_scene = int(SCENE_SECONDS * FPS)
    frame_number = 0

    print("Creando las escenas...")

    for scene_index, joke in enumerate(selected):
        background = backgrounds[scene_index]

        for frame_index in range(frames_per_scene):
            progress = frame_index / max(1, frames_per_scene - 1)
            local_time = frame_index / FPS

            frame = render_frame(
                background,
                joke,
                progress,
                local_time
            )

            frame_path = FRAMES / f"frame_{frame_number:05d}.jpg"
            frame.save(frame_path, quality=91)
            frame_number += 1

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    input_pattern = str(FRAMES / "frame_%05d.jpg")

    command = [
        ffmpeg,
        "-y",
        "-framerate", str(FPS),
        "-i", input_pattern,
        "-i", str(AUDIO),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", "format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-af", f"apad,atrim=0:{DURATION}",
        "-t", str(DURATION),
        "-movflags", "+faststart",
        str(VIDEO)
    ]

    print("\nMontando el video...")
    subprocess.run(command, check=True)

    # Limpiar únicamente los cuadros temporales.
    for frame in FRAMES.glob("frame_*.jpg"):
        frame.unlink()

    print("\n¡Reel terminado!")
    print(f"Video: {VIDEO}")
    print(f"Duración prevista: {DURATION} segundos")
    print(f"Créditos: {OUT / 'creditos_imagenes.txt'}")

    missing = sum(1 for photo in photo_info_list if photo is None)

    if missing:
        print(
            f"AVISO: {missing} escena(s) no consiguieron foto. "
            "Revisa los mensajes de búsqueda anteriores."
        )
    else:
        print("Las cuatro escenas encontraron fotografías.")


if __name__ == "__main__":
    main()
