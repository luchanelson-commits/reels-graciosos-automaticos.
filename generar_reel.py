import asyncio
import random
import shutil
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
import edge_tts
import imageio_ffmpeg


# =====================================================
# NELSON LUCHA REELS GRACIOSOS
# Reels verticales de 15 segundos con narración
# =====================================================

WIDTH = 720
HEIGHT = 1280
FPS = 12
SCENE_SECONDS = 5
TOTAL_SCENES = 3

VOICE = "es-MX-DaliaNeural"
BRAND = "Nelson Lucha Reels Graciosos"
SIGNATURE = "Nelson Lucha"

OUT = Path("salida")
FRAMES = OUT / "frames"
PHOTOS = OUT / "fotos"
VIDEO = OUT / "reel_gracioso.mp4"
AUDIO = OUT / "narracion.mp3"
CREDITS = OUT / "creditos_imagenes.txt"

OUT.mkdir(parents=True, exist_ok=True)
PHOTOS.mkdir(parents=True, exist_ok=True)


# =====================================================
# CHISTES CORTOS: SE ELIGEN TRES DIFERENTES POR REEL
# =====================================================

JOKES = [
    {
        "search": "funny dog face",
        "title": "YO CUIDANDO LA DIETA",
        "text": "HOY SOLO ENSALADA",
        "punch": "¿QUIÉN PIDIÓ PIZZA? 😂",
        "voice": "Hoy solo voy a comer ensalada. ¿Quién pidió pizza? ¡Bueno, que no se desperdicie!"
    },
    {
        "search": "funny cat expression",
        "title": "CUANDO SUENA LA ALARMA",
        "text": "CINCO MINUTITOS MÁS",
        "punch": "¡YA ES MAÑANA OTRA VEZ!",
        "voice": "Cinco minutitos más, digo yo. Abro los ojos y ya es mañana otra vez."
    },
    {
        "search": "funny surprised person",
        "title": "CUANDO REVISO MI SALDO",
        "text": "YO ME SENTÍA RICO",
        "punch": "MI BANCO SE BURLA DE MÍ",
        "voice": "Yo me sentía millonario. Revisé mi saldo y se me quitó hasta la sonrisa."
    },
    {
        "search": "funny monkey face",
        "title": "HOY SÍ HARÉ EJERCICIO",
        "text": "PRIMERO UN DESCANSITO",
        "punch": "¡YA ME CANSÉ! 😂",
        "voice": "Hoy sí haré ejercicio. Me senté a descansar un momento y ya terminé la rutina."
    },
    {
        "search": "funny baby expression",
        "title": "CUANDO DICEN: ES FÁCIL",
        "text": "ESO LO HAGO RÁPIDO",
        "punch": "TRES HORAS DESPUÉS...",
        "voice": "Me dijeron que era fácil. Tres horas después, aquí sigo preguntándome quién me mandó."
    },
    {
        "search": "funny goat face",
        "title": "YO DANDO CONSEJOS",
        "text": "HAY QUE ORGANIZARSE",
        "punch": "¿DÓNDE DEJÉ LAS LLAVES?",
        "voice": "Yo dando consejos para organizarse. Y ni siquiera encuentro las llaves que tengo en la mano."
    },
    {
        "search": "funny person sleeping",
        "title": "SOLO UN VIDEO MÁS",
        "text": "YA ME VOY A DORMIR",
        "punch": "SON LAS TRES DE LA MAÑANA",
        "voice": "Solo un video más, dije. Ahora son las tres de la mañana y tengo sueño hasta en las pestañas."
    },
    {
        "search": "funny dog looking guilty",
        "title": "¿QUIÉN HIZO EL DESASTRE?",
        "text": "YO NO FUI",
        "punch": "EL PERRO NI PARPADEA 😂",
        "voice": "¿Quién hizo este desastre? Yo no fui, dice mi perro con una cara que no le cree ni su dueño."
    },
    {
        "search": "funny man reaction",
        "title": "CUANDO ME PAGAN",
        "text": "AHORA SÍ, A DISFRUTAR",
        "punch": "LAS DEUDAS LLEGAN PRIMERO",
        "voice": "Cuando me pagan, ya me siento rico. Después llegan las deudas y me recuerdan la realidad."
    },
    {
        "search": "funny cat looking surprised",
        "title": "CUANDO ABRO LA NEVERA",
        "text": "A VER QUÉ HAY",
        "punch": "LO MISMO QUE HACE DIEZ MINUTOS",
        "voice": "Abro la nevera para ver qué hay. La cierro, vuelvo a abrirla y aparece exactamente lo mismo."
    },
]


# =====================================================
# FUENTES
# =====================================================

def get_font(size, italic=False):
    if italic:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def draw_centered(draw, text, y, fnt, color, max_width=630):
    lines = []
    current = ""

    for word in text.split():
        test = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), test, font=fnt)[2]

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    for line in lines:
        box = draw.textbbox(
            (0, 0), line, font=fnt, stroke_width=2
        )
        x = (WIDTH - (box[2] - box[0])) // 2

        draw.text(
            (x, y),
            line,
            font=fnt,
            fill=color,
            stroke_width=2,
            stroke_fill="#151515",
        )

        y += fnt.size + 10

    return y


# =====================================================
# FOTOGRAFÍAS GRATUITAS DE WIKIMEDIA COMMONS
# =====================================================

def search_photo(query):
    endpoint = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 900,
        "format": "json",
    }

    headers = {
        "User-Agent": "NelsonLuchaReels/1.0"
    }

    response = requests.get(
        endpoint,
        params=params,
        headers=headers,
        timeout=25,
    )
    response.raise_for_status()

    data = response.json()
    pages = list(
        data.get("query", {}).get("pages", {}).values()
    )
    random.shuffle(pages)

    for page in pages:
        infos = page.get("imageinfo", [])
        if not infos:
            continue

        info = infos[0]
        mime = info.get("mime", "")

        if mime not in (
            "image/jpeg",
            "image/png",
            "image/webp",
        ):
            continue

        metadata = info.get("extmetadata", {})

        license_name = metadata.get(
            "LicenseShortName", {}
        ).get("value", "")

        license_lower = license_name.lower()

        # Aceptar licencias abiertas conocidas.
        allowed = (
            "cc by" in license_lower
            or "cc0" in license_lower
            or "public domain" in license_lower
        )

        if not allowed:
            continue

        image_url = info.get("thumburl") or info.get("url")

        if not image_url:
            continue

        return {
            "url": image_url,
            "title": page.get("title", "Fotografía"),
            "artist": metadata.get(
                "Artist", {}
            ).get("value", "No indicado"),
            "license": license_name,
            "license_url": metadata.get(
                "LicenseUrl", {}
            ).get("value", ""),
            "page_url": info.get("descriptionurl", ""),
        }

    return None


def download_photo(joke, index):
    try:
        info = search_photo(joke["search"])

        if not info:
            print(
                f"Escena {index + 1}: no se encontró "
                "fotografía reutilizable."
            )
            return None, None

        response = requests.get(
            info["url"],
            headers={"User-Agent": "NelsonLuchaReels/1.0"},
            timeout=30,
        )
        response.raise_for_status()

        path = PHOTOS / f"foto_{index + 1}.jpg"
        path.write_bytes(response.content)

        with Image.open(path) as im:
            im.verify()

        print(f"Fotografía descargada para escena {index + 1}")
        return path, info

    except Exception as error:
        print(
            f"Escena {index + 1}: se usará fondo alternativo. "
            f"Detalle: {error}"
        )
        return None, None


# =====================================================
# FONDO Y MARCA DE AGUA
# =====================================================

def make_background(photo_path, index):
    if photo_path and photo_path.exists():
        with Image.open(photo_path) as original:
            image = ImageOps.fit(
                original.convert("RGB"),
                (WIDTH, HEIGHT),
                method=Image.Resampling.LANCZOS,
            )
    else:
        colors = [
            "#172554", "#3B0764", "#064E3B",
            "#7C2D12", "#164E63",
        ]

        image = Image.new(
            "RGB",
            (WIDTH, HEIGHT),
            colors[index % len(colors)],
        )

        draw = ImageDraw.Draw(image)
        draw.ellipse((175, 350, 545, 720), fill="#FFD166")
        draw.ellipse((260, 445, 305, 490), fill="#202033")
        draw.ellipse((415, 445, 460, 490), fill="#202033")
        draw.ellipse((305, 530, 415, 605), fill="#C0265C")

    # Oscurecimiento suave para leer bien el texto.
    shade = Image.new(
        "RGBA", (WIDTH, HEIGHT), (0, 0, 0, 55)
    )

    return Image.alpha_composite(
        image.convert("RGBA"), shade
    ).convert("RGB")


def add_watermark(image):
    image = image.convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    fnt = get_font(17)
    box = draw.textbbox((0, 0), BRAND, font=fnt)

    text_width = box[2] - box[0]
    x = (WIDTH - text_width) // 2
    y = HEIGHT - 58

    draw.rounded_rectangle(
        (x - 12, y - 6, x + text_width + 12, y + 27),
        radius=10,
        fill=(0, 0, 0, 100),
    )

    draw.text(
        (x, y),
        BRAND,
        font=fnt,
        fill=(255, 255, 255, 190),
    )

    return Image.alpha_composite(image, layer).convert("RGB")


def add_signature_card(image, seconds_in_scene):
    """
    Firma elegante visible durante los últimos 1.5 segundos
    del Reel. Utiliza una fuente cursiva disponible en Ubuntu.
    """
    if seconds_in_scene < 3.5:
        return image

    image = image.convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Entrada gradual de la firma.
    opacity = int(
        230 * min(1.0, (seconds_in_scene - 3.5) / 0.6)
    )

    draw.rounded_rectangle(
        (95, 485, WIDTH - 95, 690),
        radius=32,
        fill=(12, 12, 18, min(opacity, 190)),
        outline=(255, 255, 255, opacity),
        width=2,
    )

    signature_font = get_font(48, italic=True)
    box = draw.textbbox(
        (0, 0), SIGNATURE, font=signature_font
    )

    text_width = box[2] - box[0]
    x = (WIDTH - text_width) // 2
    y = 525

    draw.text(
        (x + 2, y + 3),
        SIGNATURE,
        font=signature_font,
        fill=(0, 0, 0, opacity),
    )

    draw.text(
        (x, y),
        SIGNATURE,
        font=signature_font,
        fill=(255, 255, 255, opacity),
    )

    subtitle_font = get_font(18)
    subtitle = "REELS GRACIOSOS"

    subtitle_box = draw.textbbox(
        (0, 0), subtitle, font=subtitle_font
    )

    subtitle_x = (WIDTH - (subtitle_box[2] - subtitle_box[0])) // 2

    draw.text(
        (subtitle_x, 600),
        subtitle,
        font=subtitle_font,
        fill=(255, 209, 102, opacity),
    )

    return Image.alpha_composite(image, layer).convert("RGB")


# =====================================================
# COMPONER CADA ESCENA
# =====================================================

def render_frame(joke, photo_path, scene_index, frame_index):
    image = make_background(photo_path, scene_index)
    draw = ImageDraw.Draw(image)

    # Título
    draw.rounded_rectangle(
        (20, 35, WIDTH - 20, 220),
        radius=28,
        fill="#FFF8E7",
    )

    draw_centered(
        draw,
        joke["title"],
        75,
        get_font(30),
        "#202033",
    )

    # Texto principal y remate
    draw.rounded_rectangle(
        (20, 815, WIDTH - 20, 1110),
        radius=28,
        fill="#FFF8E7",
    )

    draw_centered(
        draw,
        joke["text"],
        850,
        get_font(35),
        "#C0265C",
    )

    draw_centered(
        draw,
        joke["punch"],
        980,
        get_font(27),
        "#202033",
    )

    # Marca de agua permanente.
    image = add_watermark(image)

    # Firma personal al final del tercer segmento.
    scene_frame = frame_index % (FPS * SCENE_SECONDS)
    seconds_in_scene = scene_frame / FPS

    if scene_index == TOTAL_SCENES - 1:
        image = add_signature_card(image, seconds_in_scene)

    return image


# =====================================================
# NARRACIÓN
# =====================================================

async def create_voice(selected_jokes):
    narration = " ".join(
        joke["voice"] for joke in selected_jokes
    )

    communicator = edge_tts.Communicate(
        narration,
        VOICE,
        rate="+20%",
        volume="+0%",
    )

    await communicator.save(str(AUDIO))


# =====================================================
# CREAR EL MP4 DE 15 SEGUNDOS
# =====================================================

def run_command(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3500:])


def main():
    if FRAMES.exists():
        shutil.rmtree(FRAMES)

    FRAMES.mkdir(parents=True, exist_ok=True)
    PHOTOS.mkdir(parents=True, exist_ok=True)

    # Evitar restos de una ejecución anterior.
    if VIDEO.exists():
        VIDEO.unlink()

    if AUDIO.exists():
        AUDIO.unlink()

    # Seleccionar tres chistes sin repetir dentro del Reel.
    selected = random.sample(JOKES, TOTAL_SCENES)

    print("Chistes seleccionados:")
    for item in selected:
        print("-", item["title"])

    print("Buscando fotografías...")
    photo_paths = []
    credits = []

    for index, joke in enumerate(selected):
        photo_path, info = download_photo(joke, index)
        photo_paths.append(photo_path)

        if info:
            credits.append(
                f"Escena {index + 1}: {info['title']}\n"
                f"Autor: {info['artist']}\n"
                f"Licencia: {info['license']}\n"
                f"Enlace de licencia: {info['license_url']}\n"
                f"Fuente: {info['page_url']}\n"
            )
        else:
            credits.append(
                f"Escena {index + 1}: fondo gráfico de respaldo.\n"
            )

    CREDITS.write_text(
        "\n".join(credits),
        encoding="utf-8",
    )

    print("Generando narración en español...")
    asyncio.run(create_voice(selected))

    print("Creando 180 cuadros...")
    frame_number = 0

    for scene_index, joke in enumerate(selected):
        for _ in range(FPS * SCENE_SECONDS):
            frame = render_frame(
                joke,
                photo_paths[scene_index],
                scene_index,
                frame_number,
            )

            frame.save(
                FRAMES / f"frame_{frame_number:05d}.jpg",
                quality=86,
            )

            frame_number += 1

    print("Montando el video vertical...")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    run_command([
        ffmpeg, "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame_%05d.jpg"),
        "-i", str(AUDIO),
        "-vf", "scale=720:1280,format=yuv420p",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "27",
        "-c:a", "aac",
        "-b:a", "96k",
        "-af", "apad",
        "-t", str(TOTAL_SCENES * SCENE_SECONDS),
        "-movflags", "+faststart",
        str(VIDEO),
    ])

    shutil.rmtree(FRAMES, ignore_errors=True)

    if not VIDEO.exists() or VIDEO.stat().st_size == 0:
        raise RuntimeError("No se generó correctamente el MP4.")

    print("=" * 45)
    print("REEL CREADO CORRECTAMENTE")
    print(f"Archivo: {VIDEO}")
    print("Duración prevista: 15 segundos")
    print(f"Firma: {SIGNATURE}")
    print(f"Marca de agua: {BRAND}")
    print(f"Créditos: {CREDITS}")
    print("=" * 45)


if __name__ == "__main__":
    main()
