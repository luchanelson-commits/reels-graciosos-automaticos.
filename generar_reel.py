import os
import math
import random
import asyncio
import subprocess
import textwrap
from pathlib import Path

import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ==================================================
# CONFIGURACION GENERAL
# ==================================================

WIDTH = 720
HEIGHT = 1280
FPS = 15
MIN_DURATION = 30

VOICE = "es-MX-DaliaNeural"
OUTPUT = "reel_gracioso.mp4"

WATERMARK = "Nelson Lucha Reels Graciosos"
SIGNATURE = "Nelson Lucha"

WORK = Path("trabajo_reel")
WORK.mkdir(exist_ok=True)

API_URL = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": "NelsonLuchaReels/1.0 (personal video project)"
}

# ==================================================
# CHISTES
# ==================================================

JOKES = [
    {
        "query": "funny dog",
        "title": "MI PERRO ES INTELIGENTE",
        "text": "Mi perro ya sabe cuándo voy a salir de casa.",
        "punch": "¡Se esconde para no cuidar la casa!",
        "voice": (
            "Mi perro es tan inteligente que ya sabe cuándo voy a salir "
            "de casa. Apenas me ve buscando las llaves, comienza a mirarme "
            "con tristeza. Yo pensaba que era porque me quería mucho. "
            "Pero descubrí la verdad: se esconde para que no lo deje "
            "cuidando la casa."
        ),
    },
    {
        "query": "funny cat",
        "title": "EL GATO Y LA COMIDA",
        "text": "Mi gato se cree el dueño de toda la casa.",
        "punch": "¡Y yo soy el empleado que paga la comida!",
        "voice": (
            "Mi gato se comporta como si fuera el dueño de toda la casa. "
            "Duerme donde quiere y me mira como si yo le debiera dinero. "
            "Cuando tiene hambre, maúlla como si llevara tres días sin comer. "
            "Y yo soy el empleado que paga la comida."
        ),
    },
    {
        "query": "funny man sleeping",
        "title": "EL LUNES POR LA MAÑANA",
        "text": "El lunes pongo cinco alarmas para levantarme temprano.",
        "punch": "¡Y las cinco se levantan menos yo!",
        "voice": (
            "El lunes pongo cinco alarmas para levantarme temprano. "
            "La primera suena y digo: cinco minutos más. La segunda suena "
            "y digo: ahora sí me levanto. Cuando suena la tercera, comienzo "
            "a negociar con la vida. Al final, las cinco alarmas se levantan "
            "menos yo."
        ),
    },
    {
        "query": "funny man cooking",
        "title": "SOY CHEF PROFESIONAL",
        "text": "Hoy cociné algo especial para mi familia.",
        "punch": "¡Terminé sorprendiendo hasta a los bomberos!",
        "voice": (
            "Hoy decidí cocinar algo especial para sorprender a mi familia. "
            "Busqué una receta en internet y pensé que sería facilísimo. "
            "Agregué los ingredientes, encendí la estufa y esperé el milagro. "
            "A los diez minutos, toda la cocina estaba llena de humo. "
            "Terminé sorprendiendo hasta a los bomberos."
        ),
    },
    {
        "query": "funny man phone",
        "title": "EL MENSAJE SIN RESPUESTA",
        "text": "Le mandé un mensaje y me dejó en visto.",
        "punch": "¡Hasta mi orgullo dejó de responder!",
        "voice": (
            "Le mandé un mensaje y me dejó en visto. Esperé cinco minutos, "
            "después diez y luego media hora. Revisé si tenía internet y "
            "si el teléfono funcionaba. Todo estaba bien, menos mi "
            "tranquilidad. Hasta mi orgullo dejó de responder."
        ),
    },
    {
        "query": "funny man exercising",
        "title": "MI VIDA SALUDABLE",
        "text": "Hoy me inscribí al gimnasio para cambiar mi vida.",
        "punch": "¡Ya estoy cansado de pensarlo!",
        "voice": (
            "Hoy me inscribí al gimnasio para cambiar mi vida. Compré ropa "
            "deportiva, preparé mi botella de agua y puse música motivadora. "
            "Después me senté a descansar antes de ir. Ya pasó una semana "
            "y sigo preparándome mentalmente. Ya pagué un mes y estoy "
            "cansado de pensarlo."
        ),
    },
    {
        "query": "funny man shopping",
        "title": "SOLO IBA POR UN PAN",
        "text": "Entré al supermercado por un solo pan.",
        "punch": "¡Salí con diez bolsas y sin el pan!",
        "voice": (
            "Entré al supermercado por un solo pan. Me repetí que no "
            "necesitaba nada más. Vi una oferta, después otra y recordé "
            "que necesitaba algunas cositas. Cuando llegué a casa, revisé "
            "las bolsas. Había comprado de todo menos el pan."
        ),
    },
    {
        "query": "funny man talking",
        "title": "LA LLAMADA CORTITA",
        "text": "Mi amigo dijo que tenía algo rápido que contarme.",
        "punch": "¡Dos horas después conocía a toda su familia!",
        "voice": (
            "Mi amigo me llamó y me dijo: te cuento algo rapidito. "
            "Yo tenía unos minutos libres, así que acepté. Me contó el "
            "problema, la solución, lo que dijo el vecino y lo que respondió "
            "la prima. Cuando miré el reloj, habían pasado dos horas y "
            "ya conocía a toda su familia."
        ),
    },
]

# ==================================================
# BUSCAR Y DESCARGAR FOTOGRAFIAS
# ==================================================

def allowed_license(metadata):
    name = metadata.get("LicenseShortName", {}).get("value", "")
    license_text = name.lower().replace("-", " ").strip()

    # No usar licencias que prohíban uso comercial o modificaciones.
    if "nc" in license_text.split():
        return False
    if "nd" in license_text.split():
        return False

    if "public domain" in license_text:
        return True
    if "cc0" in license_text:
        return True
    if "cc by" in license_text:
        return True

    return False


def search_photo(query, index):
    searches = [
        query,
        "funny people",
        "people laughing",
        "funny animals",
        "people at home",
        "funny situation",
    ]

    seen_titles = set()

    for term in searches:
        print(f"Buscando imágenes: {term}")

        try:
            response = requests.get(
                API_URL,
                params={
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": term,
                    "srnamespace": 6,
                    "srlimit": 30,
                },
                headers=HEADERS,
                timeout=30,
            )
            response.raise_for_status()

            results = response.json().get(
                "query", {}
            ).get("search", [])

            titles = [
                item["title"]
                for item in results
                if item.get("title")
                and item["title"] not in seen_titles
            ]

            seen_titles.update(titles)
            random.shuffle(titles)

            for start in range(0, len(titles), 10):
                batch = titles[start:start + 10]

                detail_response = requests.get(
                    API_URL,
                    params={
                        "action": "query",
                        "format": "json",
                        "titles": "|".join(batch),
                        "prop": "imageinfo",
                        "iiprop": "url|mime|extmetadata",
                    },
                    headers=HEADERS,
                    timeout=30,
                )
                detail_response.raise_for_status()

                pages = detail_response.json().get(
                    "query", {}
                ).get("pages", {})

                for page in pages.values():
                    info_list = page.get("imageinfo", [])
                    if not info_list:
                        continue

                    info = info_list[0]
                    mime = info.get("mime", "")

                    if not mime.startswith("image/"):
                        continue

                    if mime in (
                        "image/svg+xml",
                        "image/gif",
                    ):
                        continue

                    metadata = info.get("extmetadata", {})

                    if not allowed_license(metadata):
                        continue

                    image_url = info.get("url")
                    if not image_url:
                        continue

                    image_response = requests.get(
                        image_url,
                        headers=HEADERS,
                        timeout=45,
                    )
                    image_response.raise_for_status()

                    path = WORK / f"foto_{index}.jpg"
                    path.write_bytes(image_response.content)

                    try:
                        with Image.open(path) as img:
                            img.verify()
                    except Exception:
                        path.unlink(missing_ok=True)
                        continue

                    author = metadata.get(
                        "Artist", {}
                    ).get("value", "Autor no indicado")

                    print(f"Foto: {page.get('title')}")
                    print(f"Licencia: {metadata.get('LicenseShortName', {}).get('value', '')}")
                    print(f"Autor: {author}")

                    return path

        except Exception as exc:
            print(
                f"Error con búsqueda '{term}': "
                f"{type(exc).__name__}: {exc}"
            )

    return None


# ==================================================
# FUENTES Y FONDO
# ==================================================

def get_font(size, bold=False):
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for filename in candidates:
        if os.path.exists(filename):
            return ImageFont.truetype(filename, size)

    return ImageFont.load_default()


def fit_background(photo_path):
    with Image.open(photo_path) as source:
        image = source.convert("RGB")

    target_ratio = WIDTH / HEIGHT
    ratio = image.width / image.height

    if ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop(
            (left, 0, left + new_width, image.height)
        )
    else:
        new_height = int(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop(
            (0, top, image.width, top + new_height)
        )

    image = image.resize(
        (WIDTH, HEIGHT), Image.Resampling.LANCZOS
    )
    return ImageEnhance.Brightness(image).enhance(0.52)


def draw_centered(draw, text, y, font, color="white"):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    x = (WIDTH - (box[2] - box[0])) // 2

    draw.text(
        (x, y),
        text,
        font=font,
        fill=color,
        stroke_width=2,
        stroke_fill="black",
    )


def draw_wrapped(draw, text, y, font, max_chars=25, color="white"):
    lines = textwrap.wrap(text, width=max_chars)
    line_height = font.size + 15

    for line in lines:
        draw_centered(draw, line, y, font, color)
        y += line_height

    return y


# ==================================================
# CREAR FOTOGRAMA
# ==================================================

def make_frame(photo_path, joke, progress):
    image = fit_background(photo_path)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (25, 35, WIDTH - 25, 105),
        radius=20,
        fill="black",
    )
    draw_centered(
        draw, "😂 ¡RÍE UN MOMENTO!", 48,
        get_font(29, True)
    )

    draw_wrapped(
        draw,
        joke["title"],
        205,
        get_font(39, True),
        max_chars=22,
        color="#FFE66D",
    )

    caption = joke["text"] if progress < 0.58 else joke["punch"]

    draw.rounded_rectangle(
        (30, 590, WIDTH - 30, 925),
        radius=25,
        fill="black",
    )
    draw_wrapped(
        draw,
        caption,
        680,
        get_font(32, True),
        max_chars=27,
    )

    draw_centered(
        draw, WATERMARK, 1090,
        get_font(23, True)
    )
    draw_centered(
        draw, SIGNATURE, 1132,
        get_font(28, True),
        "#FFE66D",
    )

    # Barra de progreso de cada escena
    x1, y1 = 45, 1205
    bar_width = WIDTH - 90

    draw.rounded_rectangle(
        (x1, y1, x1 + bar_width, y1 + 12),
        radius=6,
        fill="#666666",
    )
    draw.rounded_rectangle(
        (x1, y1, x1 + int(bar_width * progress), y1 + 12),
        radius=6,
        fill="#FFE66D",
    )

    return image


# ==================================================
# CREAR NARRACION
# ==================================================

async def create_voice(jokes, audio_path):
    intro = (
        "¡Bienvenidos a Nelson Lucha Reels Graciosos! "
        "Prepárate para reír un rato. "
    )

    outro = (
        "Si te sacamos una sonrisa, deja tu me gusta, "
        "comenta tu chiste favorito y comparte este video. "
        "¡Soy Nelson Lucha! Nos vemos en el próximo Reel."
    )

    narration = intro + " Pausa breve. ".join(
        joke["voice"] for joke in jokes
    ) + outro

    speech = edge_tts.Communicate(
        narration,
        VOICE,
        rate="-5%",
        volume="+0%",
    )
    await speech.save(str(audio_path))


def get_audio_duration(audio_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return float(result.stdout.strip())


# ==================================================
# PROCESO PRINCIPAL
# ==================================================

def main():
    selected = random.sample(JOKES, 4)
    photos = []

    print("=== BUSQUEDA DE FOTOGRAFIAS ===")

    for index, joke in enumerate(selected):
        photo = search_photo(joke["query"], index)

        if photo is None:
            raise RuntimeError(
                f"No se encontró una fotografía válida para la escena "
                f"{index + 1} ({joke['query']}). "
                "Revisa los mensajes de búsqueda anteriores."
            )

        photos.append(photo)

    print("Se descargaron las cuatro fotografías.")

    audio_path = WORK / "narracion.mp3"
    asyncio.run(create_voice(selected, audio_path))

    audio_duration = get_audio_duration(audio_path)
    duration = max(MIN_DURATION, math.ceil(audio_duration + 1))

    print(f"Duración de la voz: {audio_duration:.1f} segundos")
    print(f"Duración del Reel: {duration} segundos")

    frames_dir = WORK / "frames"
    frames_dir.mkdir(exist_ok=True)

    total_frames = duration * FPS
    frames_per_scene = total_frames // len(selected)
    frame_number = 0

    for scene_index, (joke, photo) in enumerate(
        zip(selected, photos)
    ):
        for local_frame in range(frames_per_scene):
            progress = local_frame / max(1, frames_per_scene - 1)

            frame = make_frame(photo, joke, progress)
            filename = frames_dir / f"frame_{frame_number:05d}.jpg"

            frame.save(filename, quality=92)
            frame_number += 1

        print(f"Escena {scene_index + 1} terminada.")

    # Completar cualquier fotograma restante.
    while frame_number < total_frames:
        frame = make_frame(photos[-1], selected[-1], 1.0)
        filename = frames_dir / f"frame_{frame_number:05d}.jpg"
        frame.save(filename, quality=92)
        frame_number += 1

    command = [
        "ffmpeg",
        "-y",
        "-framerate", str(FPS),
        "-i", str(frames_dir / "frame_%05d.jpg"),
        "-i", str(audio_path),
        "-af", "apad",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT,
    ]

    print("=== GENERANDO VIDEO ===")
    subprocess.run(command, check=True)

    if not os.path.exists(OUTPUT):
        raise RuntimeError("No se creó el archivo de video.")

    size = os.path.getsize(OUTPUT)

    if size < 100_000:
        raise RuntimeError("El archivo de video es demasiado pequeño.")

    print("===================================")
    print("¡REEL CREADO CORRECTAMENTE!")
    print(f"Archivo: {OUTPUT}")
    print(f"Duración: {duration} segundos")
    print(f"Tamaño: {size / 1024 / 1024:.2f} MB")
    print("===================================")


if __name__ == "__main__":
    main()
