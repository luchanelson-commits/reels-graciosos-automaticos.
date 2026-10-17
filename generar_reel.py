import os
import re
import math
import random
import subprocess
import requests
import asyncio
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import edge_tts

# ==========================================
# CONFIGURACION
# ==========================================

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

HEADERS = {
    "User-Agent": "NelsonLuchaReels/1.0 (motivational and humor video project)"
}

# ==========================================
# CHISTES CON NARRACION COMPLETA
# ==========================================

JOKES = [
    {
        "query": "funny dog pet",
        "title": "MI PERRO ES INTELIGENTE",
        "text": "Mi perro es tan inteligente que ya sabe cuándo voy a salir de casa.",
        "punch": "¡Se esconde para que no lo deje cuidando la casa!",
        "voice": (
            "Mi perro es tan inteligente que ya sabe cuándo voy a salir de casa. "
            "Apenas me ve buscando las llaves, comienza a mirarme con tristeza. "
            "Yo pensé que era porque me quería mucho. "
            "Pero un día descubrí la verdad: ¡se esconde para que no lo deje cuidando la casa!"
        ),
    },
    {
        "query": "funny cat",
        "title": "EL GATO Y LA COMIDA",
        "text": "Mi gato se comporta como si fuera el dueño de toda la casa.",
        "punch": "¡Y yo soy el empleado que paga la comida!",
        "voice": (
            "Mi gato se comporta como si fuera el dueño de toda la casa. "
            "Duerme donde quiere, se sube a los muebles y me mira como si yo le debiera dinero. "
            "Cuando tiene hambre, maúlla como si llevara tres días sin comer. "
            "¡Y yo soy el empleado que paga la comida!"
        ),
    },
    {
        "query": "man sleeping on sofa funny",
        "title": "EL LUNES POR LA MAÑANA",
        "text": "El lunes pongo cinco alarmas para levantarme temprano.",
        "punch": "¡Y las cinco se levantan menos yo!",
        "voice": (
            "El lunes pongo cinco alarmas para levantarme temprano. "
            "La primera suena y digo: cinco minutos más. "
            "La segunda suena y digo: ahora sí me levanto. "
            "La tercera ya me encuentra negociando con la vida. "
            "¡Y cuando suenan las cinco, las alarmas se levantan menos yo!"
        ),
    },
    {
        "query": "funny surprised man",
        "title": "CUANDO LLEGA EL RECIBO",
        "text": "Yo juraba que este mes iba a ahorrar bastante dinero.",
        "punch": "¡Hasta que llegaron los recibos a recordarme mis sueños!",
        "voice": (
            "Yo juraba que este mes iba a ahorrar bastante dinero. "
            "Me dije: voy a gastar menos, voy a comprar solo lo necesario y voy a ser responsable. "
            "Todo iba perfecto hasta que abrí el buzón. "
            "¡Los recibos llegaron juntos a recordarme que mis sueños también tienen gastos!"
        ),
    },
    {
        "query": "funny man cooking kitchen",
        "title": "SOY CHEF PROFESIONAL",
        "text": "Hoy decidí cocinar algo especial para sorprender a mi familia.",
        "punch": "¡Y terminé sorprendiendo hasta a los bomberos!",
        "voice": (
            "Hoy decidí cocinar algo especial para sorprender a mi familia. "
            "Busqué una receta en internet y pensé que sería facilísimo. "
            "Agregué los ingredientes, encendí la estufa y esperé el milagro. "
            "A los diez minutos, toda la cocina estaba llena de humo. "
            "¡Terminé sorprendiendo hasta a los bomberos!"
        ),
    },
    {
        "query": "funny man looking at phone",
        "title": "EL MENSAJE SIN RESPUESTA",
        "text": "Le mandé un mensaje y me dejó en visto.",
        "punch": "¡Ahora hasta mi orgullo está conectado pero no responde!",
        "voice": (
            "Le mandé un mensaje y me dejó en visto. "
            "Esperé cinco minutos, después diez y luego media hora. "
            "Revisé si tenía internet, si el teléfono funcionaba y si el mundo seguía girando. "
            "Todo estaba bien, menos mi tranquilidad. "
            "¡Ahora hasta mi orgullo está conectado, pero tampoco responde!"
        ),
    },
    {
        "query": "funny man exercising gym",
        "title": "MI NUEVA VIDA SALUDABLE",
        "text": "Hoy me inscribí al gimnasio para cambiar mi vida.",
        "punch": "¡Ya pagué un mes y estoy cansado de pensarlo!",
        "voice": (
            "Hoy me inscribí al gimnasio para cambiar mi vida. "
            "Compré ropa deportiva, preparé mi botella de agua y hasta puse música motivadora. "
            "Después me senté a descansar antes de ir. "
            "Ya pasó una semana y sigo preparándome mentalmente. "
            "¡Ya pagué un mes y estoy cansado de pensarlo!"
        ),
    },
    {
        "query": "funny man sleeping bed",
        "title": "SOLO CINCO MINUTITOS",
        "text": "Me acosté diciendo que solo iba a cerrar los ojos un momento.",
        "punch": "¡Desperté al día siguiente con la ropa puesta!",
        "voice": (
            "Anoche me acosté diciendo que solo iba a cerrar los ojos un momentito. "
            "No iba a dormir, solo quería descansar la vista. "
            "Cuando abrí los ojos, ya era de mañana y tenía el teléfono en la mano. "
            "¡Desperté al día siguiente con la ropa puesta y sin saber en qué momento terminó el día!"
        ),
    },
    {
        "query": "funny man shopping supermarket",
        "title": "SOLO IBA POR UN PAN",
        "text": "Entré al supermercado por un solo pan.",
        "punch": "¡Salí con diez bolsas y sin el pan!",
        "voice": (
            "Entré al supermercado por un solo pan. "
            "Me repetí que no necesitaba nada más y que iba a salir rapidito. "
            "Vi una oferta, después otra y luego recordé que necesitaba algunas cositas. "
            "Cuando llegué a casa, revisé las bolsas. "
            "¡Había comprado de todo menos el pan!"
        ),
    },
    {
        "query": "funny man talking phone",
        "title": "LA LLAMADA CORTITA",
        "text": "Mi amigo me llamó y me dijo que tenía algo rápido que contarme.",
        "punch": "¡Dos horas después ya conocía hasta sus antepasados!",
        "voice": (
            "Mi amigo me llamó y me dijo: te cuento algo rapidito. "
            "Yo estaba tranquilo porque tenía unos minutos libres. "
            "Me contó el problema, la solución, lo que dijo el vecino y lo que respondió la prima. "
            "Cuando miré el reloj, ya había pasado muchísimo tiempo. "
            "¡Dos horas después ya conocía hasta sus antepasados!"
        ),
    },
]

# ==========================================
# DESCARGAR FOTOGRAFIAS CON LICENCIA
# ==========================================

def search_photo(query, index):
    api = "https://commons.wikimedia.org/w/api.php"

    try:
        response = requests.get(
            api,
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srnamespace": 6,
                "srlimit": 30,
            },
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])

        titles = [item["title"] for item in results if "title" in item]
        if not titles:
            print(f"No se encontraron resultados para: {query}")
            return None

        random.shuffle(titles)

        for start in range(0, len(titles), 10):
            batch = titles[start:start + 10]

            details = requests.get(
                api,
                params={
                    "action": "query",
                    "format": "json",
                    "titles": "|".join(batch),
                    "prop": "imageinfo",
                    "iiprop": "url|mime|extmetadata|size",
                },
                headers=HEADERS,
                timeout=30,
            )
            details.raise_for_status()

            pages = details.json().get("query", {}).get("pages", {})

            for page in pages.values():
                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue

                info = info_list[0]
                mime = info.get("mime", "")
                if not mime.startswith("image/"):
                    continue
                if mime in ("image/svg+xml", "image/gif"):
                    continue

                metadata = info.get("extmetadata", {})
                license_name = (
                    metadata.get("LicenseShortName", {}).get("value", "")
                    .lower()
                )
                if not any(term in license_name for term in (
                    "cc0", "public domain", "cc by", "cc-by"
                )):
                    continue

                image_url = info.get("url")
                if not image_url:
                    continue

                image_response = requests.get(
                    image_url, headers=HEADERS, timeout=45
                )
                image_response.raise_for_status()

                path = WORK / f"foto_{index}.jpg"
                with open(path, "wb") as file:
                    file.write(image_response.content)

                try:
                    with Image.open(path) as im:
                        im.verify()
                except Exception:
                    path.unlink(missing_ok=True)
                    continue

                print(f"Fotografía descargada: {page.get('title')}")
                print(f"Licencia indicada: {license_name}")
                return path

    except Exception as exc:
        print(f"Error buscando foto para '{query}': {exc}")

    return None


# ==========================================
# FUENTES Y DISENO
# ==========================================

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

    for font_path in candidates:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


def fit_background(photo_path):
    with Image.open(photo_path).convert("RGB") as original:
        image = original.copy()

    target_ratio = WIDTH / HEIGHT
    ratio = image.width / image.height

    if ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = int(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    image = ImageEnhance.Brightness(image).enhance(0.52)
    return image


def draw_centered(draw, text, y, font, fill, stroke_width=2):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    x = (WIDTH - (box[2] - box[0])) // 2
    draw.text(
        (x, y), text, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill="black"
    )


def draw_wrapped(draw, text, y, font, max_chars=24, fill="white"):
    lines = textwrap.wrap(text, width=max_chars)
    line_height = font.size + 14

    for line in lines:
        draw_centered(draw, line, y, font, fill, stroke_width=3)
        y += line_height

    return y


def make_frame(photo_path, joke, scene_index, scene_progress):
    image = fit_background(photo_path)
    draw = ImageDraw.Draw(image)

    # Encabezado
    draw.rounded_rectangle(
        (25, 35, WIDTH - 25, 105),
        radius=20, fill=(0, 0, 0)
    )
    draw_centered(
        draw, "😂 ¡RÍE UN MOMENTO!", 48,
        get_font(29, True), "white", 1
    )

    # Titulo
    title_font = get_font(40, True)
    draw_wrapped(
        draw, joke["title"], 210, title_font, max_chars=22,
        fill="#FFE66D"
    )

    # Texto de la escena
    body_font = get_font(32, True)
    if scene_progress < 0.58:
        caption = joke["text"]
    else:
        caption = joke["punch"]

    draw.rounded_rectangle(
        (35, 610, WIDTH - 35, 900),
        radius=28, fill=(0, 0, 0)
    )
    draw_wrapped(
        draw, caption, 680, body_font, max_chars=27, fill="white"
    )

    # Marca de agua
    draw_centered(
        draw, WATERMARK, 1090, get_font(23, True), "#FFFFFF", 2
    )
    draw_centered(
        draw, SIGNATURE, 1130, get_font(28, True), "#FFE66D", 2
    )

    # Indicador de escena
    bar_x, bar_y = 45, 1205
    bar_width = WIDTH - 90
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + 12),
        radius=6, fill=(110, 110, 110)
    )
    draw.rounded_rectangle(
        (
            bar_x, bar_y,
            bar_x + int(bar_width * scene_progress), bar_y + 12
        ),
        radius=6, fill="#FFE66D"
    )

    return image


# ==========================================
# NARRACION
# ==========================================

async def create_voice(jokes, audio_path):
    intro = (
        "¡Bienvenidos a Nelson Lucha Reels Graciosos! "
        "Prepárate para reír un rato. ¡Comparte este video con tus amigos!"
    )
    outro = (
        "Si te sacamos una sonrisa, deja tu me gusta, comenta tu chiste favorito "
        "y comparte este video. ¡Soy Nelson Lucha, nos vemos en el próximo Reel!"
    )

    narration = intro + " "
    narration += " Pausa breve. ".join(joke["voice"] for joke in jokes)
    narration += " " + outro

    communicate = edge_tts.Communicate(
        narration, VOICE, rate="-5%", volume="+0%"
    )
    await communicate.save(str(audio_path))


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


# ==========================================
# CREAR VIDEO
# ==========================================

def main():
    selected = random.sample(JOKES, 4)
    photos = []

    print("Buscando cuatro fotografías con licencia apropiada...")

    for index, joke in enumerate(selected):
        photo = search_photo(joke["query"], index)
        if photo is None:
            raise RuntimeError(
                f"No se pudo descargar una fotografía válida para la escena "
                f"{index + 1}: '{joke['query']}'. "
                "Revisa los mensajes anteriores de esta ejecución."
            )
        photos.append(photo)

    audio_path = WORK / "narracion.mp3"
    asyncio.run(create_voice(selected, audio_path))

    audio_duration = get_audio_duration(audio_path)
    duration = max(MIN_DURATION, math.ceil(audio_duration + 1))
    scene_seconds = duration / len(selected)

    print(f"Duración de narración: {audio_duration:.1f} segundos")
    print(f"Duración final del Reel: {duration} segundos")

    frames_dir = WORK / "frames"
    frames_dir.mkdir(exist_ok=True)

    frame_number = 0
    total_frames = duration * FPS

    for scene_index, (joke, photo) in enumerate(zip(selected, photos)):
        scene_frames = round(scene_seconds * FPS)

        for local_frame in range(scene_frames):
            progress = local_frame / max(1, scene_frames - 1)
            frame = make_frame(photo, joke, scene_index, progress)

            frame_path = frames_dir / f"frame_{frame_number:05d}.jpg"
            frame.save(frame_path, quality=92)
            frame_number += 1

        print(f"Escena {scene_index + 1}/{len(selected)} preparada.")

    # Ajustar a la cantidad exacta de fotogramas necesaria.
    while frame_number < total_frames:
        frame = make_frame(photos[-1], selected[-1], len(selected) - 1, 1.0)
        frame.save(frames_dir / f"frame_{frame_number:05d}.jpg", quality=92)
        frame_number += 1

    # El video se extiende hasta el final de la narración.
    # La pista de audio se rellena con silencio si hace falta.
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

    print("Generando archivo MP4...")
    subprocess.run(command, check=True)

    if not os.path.exists(OUTPUT) or os.path.getsize(OUTPUT) < 100_000:
        raise RuntimeError("El archivo MP4 no se creó correctamente.")

    print("=" * 45)
    print(f"¡REEL CREADO CORRECTAMENTE!: {OUTPUT}")
    print(f"Duración aproximada: {duration} segundos")
    print(f"Tamaño: {os.path.getsize(OUTPUT) / 1024 / 1024:.2f} MB")
    print("=" * 45)


if __name__ == "__main__":
    main()
