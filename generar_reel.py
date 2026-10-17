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
# CONFIGURACION
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

HEADERS = {"User-Agent": "NelsonLuchaReels/2.0"}

BACKUP_PHOTOS = [
    "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=900",
    "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=900",
    "https://images.unsplash.com/photo-1552053831-71594a27632d?w=900",
    "https://images.unsplash.com/photo-1517849845537-4d257902454a?w=900",
]

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
            "Pero descubrí la verdad: ¡se esconde para no cuidar la casa!"
        ),
    },
    {
        "query": "funny cat",
        "title": "EL GATO Y LA COMIDA",
        "text": "Mi gato se cree el dueño de toda la casa.",
        "punch": "¡Yo soy el empleado que paga la comida!",
        "voice": (
            "Mi gato se comporta como si fuera el dueño de toda la casa. "
            "Duerme donde quiere y me mira como si yo le debiera dinero. "
            "Cuando tiene hambre, maúlla como si llevara tres días sin comer. "
            "¡Y yo soy el empleado que paga la comida!"
        ),
    },
    {
        "query": "funny man sleeping",
        "title": "EL LUNES POR LA MAÑANA",
        "text": "El lunes pongo cinco alarmas para levantarme temprano.",
        "punch": "¡Las cinco se levantan menos yo!",
        "voice": (
            "El lunes pongo cinco alarmas para levantarme temprano. "
            "La primera suena y digo: cinco minutos más. La segunda suena "
            "y digo: ahora sí me levanto. Cuando suena la tercera, comienzo "
            "a negociar con la vida. ¡Al final, las cinco alarmas se "
            "levantan menos yo!"
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
            "¡Terminé sorprendiendo hasta a los bomberos!"
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
            "tranquilidad. ¡Hasta mi orgullo dejó de responder!"
        ),
    },
    {
        "query": "funny man exercising",
        "title": "MI VIDA SALUDABLE",
        "text": "Hoy me inscribí al gimnasio para cambiar mi vida.",
        "punch": "¡Estoy cansado de pensarlo!",
        "voice": (
            "Hoy me inscribí al gimnasio para cambiar mi vida. Compré ropa "
            "deportiva, preparé mi botella de agua y puse música motivadora. "
            "Después me senté a descansar antes de ir. Ya pasó una semana "
            "y sigo preparándome mentalmente. ¡Ya pagué un mes y estoy "
            "cansado de pensarlo!"
        ),
    },
    {
        "query": "funny man shopping",
        "title": "SOLO IBA POR UN PAN",
        "text": "Entré al supermercado por un solo pan.",
        "punch": "¡Compré de todo menos el pan!",
        "voice": (
            "Entré al supermercado por un solo pan. Me repetí que no "
            "necesitaba nada más. Vi una oferta, después otra y recordé "
            "que necesitaba algunas cositas. Cuando llegué a casa, revisé "
            "las bolsas. ¡Había comprado de todo menos el pan!"
        ),
    },
    {
        "query": "funny man talking",
        "title": "LA LLAMADA CORTITA",
        "text": "Mi amigo dijo que tenía algo rápido que contarme.",
        "punch": "¡Ya conocía a toda su familia!",
        "voice": (
            "Mi amigo me llamó y me dijo: te cuento algo rapidito. "
            "Yo tenía unos minutos libres, así que acepté. Me contó el "
            "problema, la solución, lo que dijo el vecino y lo que respondió "
            "la prima. Cuando miré el reloj, habían pasado dos horas y "
            "¡ya conocía a toda su familia!"
        ),
    },
    {
        "query": "funny person laughing",
        "title": "EL AHORRADOR",
        "text": "Este mes decidí ahorrar todo mi dinero.",
        "punch": "¡Tuve que pedir prestado para comprar la alcancía!",
        "voice": (
            "Este mes decidí ahorrar todo mi dinero. No iba a comprar "
            "nada innecesario. Caminé por el centro y vi una alcancía "
            "preciosa para comenzar mi nuevo hábito. La compré de inmediato. "
            "¡Después tuve que pedir prestado para comprar la alcancía!"
        ),
    },
    {
        "query": "funny friends laughing",
        "title": "EL EXPERTO EN CONSEJOS",
        "text": "Mi amigo siempre tiene consejos para todo.",
        "punch": "¡Pero su propia vida sigue en construcción!",
        "voice": (
            "Tengo un amigo que siempre tiene consejos para todo. "
            "Si tienes problemas de amor, él sabe qué hacer. Si tienes "
            "problemas de dinero, también tiene una solución. Si necesitas "
            "organizar tu vida, te da una conferencia. ¡Pero su propia "
            "vida sigue en construcción!"
        ),
    },
]

# ==================================================
# DESCARGAR FOTOGRAFIAS
# ==================================================

def valid_image(path):
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def download_image(url, path):
    response = requests.get(url, headers=HEADERS, timeout=35)
    response.raise_for_status()

    if not response.headers.get("Content-Type", "").lower().startswith("image/"):
        raise ValueError("La dirección no devolvió una imagen.")

    path.write_bytes(response.content)

    if not valid_image(path):
        path.unlink(missing_ok=True)
        raise ValueError("La imagen descargada no es válida.")

    return path


def search_photo(query, index):
    api = "https://commons.wikimedia.org/w/api.php"
    terms = [query, "people laughing", "funny animals"]

    for term in terms:
        try:
            response = requests.get(
                api,
                params={
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrsearch": term,
                    "gsrnamespace": 6,
                    "gsrlimit": 20,
                    "prop": "imageinfo",
                    "iiprop": "url|mime|extmetadata",
                },
                headers=HEADERS,
                timeout=25,
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
                if info.get("mime") not in (
                    "image/jpeg", "image/png", "image/webp"
                ):
                    continue

                metadata = info.get("extmetadata", {})
                license_name = metadata.get(
                    "LicenseShortName", {}
                ).get("value", "").lower().replace("-", " ")

                if not any(term in license_name for term in (
                    "public domain", "cc0", "cc by"
                )):
                    continue

                url = info.get("url")
                if not url:
                    continue

                try:
                    path = download_image(
                        url, WORK / f"foto_{index}.jpg"
                    )
                    print("Fotografía Wikimedia:", page.get("title"))
                    print("Licencia:", license_name)
                    return path
                except Exception as exc:
                    print("No se pudo usar esa foto:", exc)

        except Exception as exc:
            print(f"Error buscando {term}: {exc}")

    print("Probando fotografías de respaldo de Unsplash...")

    for offset in range(len(BACKUP_PHOTOS)):
        url = BACKUP_PHOTOS[
            (index + offset) % len(BACKUP_PHOTOS)
        ]
        try:
            path = download_image(url, WORK / f"foto_{index}.jpg")
            print("Fotografía de respaldo descargada.")
            return path
        except Exception as exc:
            print("Error descargando respaldo:", exc)

    raise RuntimeError(
        f"No se pudo descargar una imagen para la escena {index + 1}."
    )


# ==================================================
# FUENTES Y DISEÑO
# ==================================================

def get_font(size, bold=False):
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
        if bold else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    )

    for filename in candidates:
        if os.path.exists(filename):
            return ImageFont.truetype(filename, size)

    return ImageFont.load_default()


def fit_background(photo_path, progress=0.0):
    with Image.open(photo_path) as source:
        image = source.convert("RGB")

    ratio = WIDTH / HEIGHT
    if image.width / image.height > ratio:
        new_width = int(image.height * ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = int(image.width / ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    # Movimiento suave de acercamiento para dar dinamismo.
    zoom = 1.0 + 0.045 * progress
    zoomed = image.resize(
        (int(WIDTH * zoom), int(HEIGHT * zoom)),
        Image.Resampling.LANCZOS,
    )
    left = (zoomed.width - WIDTH) // 2
    top = (zoomed.height - HEIGHT) // 2
    image = zoomed.crop((left, top, left + WIDTH, top + HEIGHT))

    return ImageEnhance.Brightness(image).enhance(0.48)


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
    for line in textwrap.wrap(text, width=max_chars):
        draw_centered(draw, line, y, font, color)
        y += font.size + 14
    return y


def draw_caption(draw, text):
    if not text.strip():
        return

    font = get_font(38, True)
    lines = textwrap.wrap(text.upper(), width=25)[:3]
    line_height = 48
    box_height = len(lines) * line_height + 34
    top = 790

    draw.rounded_rectangle(
        (24, top, WIDTH - 24, top + box_height),
        radius=22,
        fill="#111111",
        outline="#FFE66D",
        width=4,
    )

    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=1)
        x = (WIDTH - (box[2] - box[0])) // 2
        y = top + 15 + index * line_height
        draw.text(
            (x, y),
            line,
            font=font,
            fill="#FFFFFF",
            stroke_width=1,
            stroke_fill="#111111",
        )


def make_frame(photo_path, joke, progress, caption=""):
    image = fit_background(photo_path, progress)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (22, 30, WIDTH - 22, 105),
        radius=20,
        fill="#111111",
        outline="#FFE66D",
        width=3,
    )
    draw_centered(
        draw, "¡RÍE UN MOMENTO!", 48, get_font(29, True), "#FFE66D"
    )

    draw_wrapped(
        draw, joke["title"], 185, get_font(39, True),
        max_chars=22, color="#FFE66D"
    )

    draw.rounded_rectangle(
        (28, 530, WIDTH - 28, 720),
        radius=24,
        fill="#111111",
        outline="#FFFFFF",
        width=2,
    )
    draw_wrapped(
        draw, joke["punch"] if progress > 0.72 else joke["text"],
        580, get_font(31, True), max_chars=27
    )

    draw_caption(draw, caption)

    draw_centered(draw, WATERMARK, 1090, get_font(22, True))
    draw_centered(draw, SIGNATURE, 1130, get_font(28, True), "#FFE66D")

    x1, y1 = 45, 1205
    bar_width = WIDTH - 90
    draw.rounded_rectangle(
        (x1, y1, x1 + bar_width, y1 + 12),
        radius=6,
        fill="#555555",
    )
    draw.rounded_rectangle(
        (x1, y1, x1 + int(bar_width * progress), y1 + 12),
        radius=6,
        fill="#FFE66D",
    )

    return image


# ==================================================
# NARRACION Y SUBTITULOS CON TIEMPOS REALES
# ==================================================

async def create_voice(jokes, audio_path):
    intro = (
        "¡Bienvenidos a Nelson Lucha Reels Graciosos! "
        "Prepárate para reír un rato. "
    )
    outro = (
        "Si te sacamos una sonrisa, deja tu me gusta, comenta tu chiste "
        "favorito y comparte este video. ¡Soy Nelson Lucha! "
        "Nos vemos en el próximo Reel."
    )

    narration = intro + " Pausa breve. ".join(
        joke["voice"] for joke in jokes
    ) + outro

    communicate = edge_tts.Communicate(
        narration,
        VOICE,
        rate="-5%",
        volume="+0%",
    )

    words = []

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])

            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                end = (
                    chunk["offset"] + chunk["duration"]
                ) / 10_000_000

                words.append({
                    "text": chunk["text"],
                    "start": start,
                    "end": end,
                })

    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError("No se pudo generar el audio.")

    return words


def make_caption_groups(words):
    groups = []
    current = []

    for word in words:
        current.append(word)

        text = word["text"]
        punctuation = any(mark in text for mark in ".!?;:")

        if len(current) >= 5 or punctuation:
            groups.append({
                "start": current[0]["start"],
                "end": current[-1]["end"] + 0.20,
                "text": " ".join(item["text"] for item in current),
            })
            current = []

    if current:
        groups.append({
            "start": current[0]["start"],
            "end": current[-1]["end"] + 0.20,
            "text": " ".join(item["text"] for item in current),
        })

    return groups


def caption_at_time(groups, current_time):
    for group in groups:
        if group["start"] <= current_time <= group["end"]:
            return group["text"]
    return ""


def get_audio_duration(audio_path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
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
# CREAR EL REEL
# ==================================================

def main():
    selected = random.sample(JOKES, 4)
    photos = []

    print("Descargando fotografías...")
    for index, joke in enumerate(selected):
        photos.append(search_photo(joke["query"], index))

    audio_path = WORK / "narracion.mp3"
    print("Generando narración y tiempos de subtítulos...")
    words = asyncio.run(create_voice(selected, audio_path))
    groups = make_caption_groups(words)

    audio_duration = get_audio_duration(audio_path)
    duration = max(MIN_DURATION, math.ceil(audio_duration + 1))

    print(f"Duración del audio: {audio_duration:.1f} segundos")
    print(f"Duración del Reel: {duration} segundos")

    frames_dir = WORK / "frames"
    frames_dir.mkdir(exist_ok=True)

    # Eliminar fotogramas antiguos para evitar mezclarlos.
    for old_frame in frames_dir.glob("frame_*.jpg"):
        old_frame.unlink()

    total_frames = duration * FPS
    frames_per_scene = total_frames // len(selected)
    frame_number = 0

    for scene_index, (joke, photo) in enumerate(zip(selected, photos)):
        for local_frame in range(frames_per_scene):
            progress = local_frame / max(1, frames_per_scene - 1)
            current_time = frame_number / FPS
            caption = caption_at_time(groups, current_time)

            frame = make_frame(photo, joke, progress, caption)
            filename = frames_dir / f"frame_{frame_number:05d}.jpg"
            frame.save(filename, quality=88)
            frame_number += 1

        print(f"Escena {scene_index + 1} lista.")

    while frame_number < total_frames:
        current_time = frame_number / FPS
        caption = caption_at_time(groups, current_time)
        frame = make_frame(photos[-1], selected[-1], 1.0, caption)
        frame.save(
            frames_dir / f"frame_{frame_number:05d}.jpg",
            quality=88,
        )
        frame_number += 1

    command = [
        "ffmpeg", "-y",
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

    print("Creando video MP4...")
    subprocess.run(command, check=True)

    if not os.path.exists(OUTPUT) or os.path.getsize(OUTPUT) < 100_000:
        raise RuntimeError("El archivo MP4 no se creó correctamente.")

    size = os.path.getsize(OUTPUT) / (1024 * 1024)

    print("====================================")
    print("¡REEL CREADO CORRECTAMENTE!")
    print(f"Archivo: {OUTPUT}")
    print(f"Duración: {duration} segundos")
    print(f"Tamaño: {size:.2f} MB")
    print("Subtítulos sincronizados: preparados")
    print("Marca de agua: Nelson Lucha")
    print("====================================")


if __name__ == "__main__":
    main()
