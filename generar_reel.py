import asyncio
import random
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
import edge_tts
import imageio_ffmpeg

WIDTH, HEIGHT = 720, 1280
FPS = 12
SCENE_SECONDS = 7
VOICE = "es-MX-DaliaNeural"

OUT = Path("salida")
FRAMES = OUT / "frames"
PHOTOS = OUT / "fotos"
VIDEO = OUT / "reel_gracioso.mp4"
AUDIO = OUT / "narracion.mp3"
CREDITS = OUT / "creditos_imagenes.txt"

SCENES = [
    {
        "search": "funny dog",
        "title": "CUANDO DIGO QUE VOY A MADURAR",
        "text": "HOY SÍ SERÉ RESPONSABLE",
        "punch": "PERO MI PERRO TIENE OTROS PLANES 😂",
        "voice": "Hoy sí voy a ser una persona responsable. Pero mi perro me mira como diciendo: primero juega conmigo, jefe."
    },
    {
        "search": "funny cat",
        "title": "YO CUANDO ESCUCHO UN RUIDO",
        "text": "NO TENGO MIEDO",
        "punch": "PERO YA ESTOY DETRÁS DE LA PUERTA",
        "voice": "Yo diciendo que no tengo miedo. Pero escucho un ruido en la noche y ya estoy escondido detrás de la puerta."
    },
    {
        "search": "funny surprised face",
        "title": "CUANDO VEO MI SALDO",
        "text": "YO ME SENTÍA MILLONARIO",
        "punch": "MI CUENTA NO ESTÁ DE ACUERDO",
        "voice": "Yo me sentía millonario hasta que revisé mi saldo. Mi cuenta bancaria me aterrizó más rápido que un avión."
    },
    {
        "search": "funny person sleeping",
        "title": "SOLO CINCO MINUTITOS MÁS",
        "text": "YA ME LEVANTO",
        "punch": "TRES HORAS DESPUÉS...",
        "voice": "La alarma suena y digo: cinco minutitos más. Cuando abro los ojos, ya casi tengo que preparar la cena."
    },
    {
        "search": "funny monkey",
        "title": "CUANDO INTENTO HACER EJERCICIO",
        "text": "HOY SÍ VOY AL GIMNASIO",
        "punch": "ME CANSÉ BUSCANDO LOS ZAPATOS",
        "voice": "Hoy sí voy al gimnasio. Pero me cansé buscando los zapatos deportivos. Creo que ya hice suficiente calentamiento."
    },
    {
        "search": "funny baby expression",
        "title": "CUANDO ME PIDEN UN FAVOR",
        "text": "CLARO, YO TE AYUDO",
        "punch": "¿Y QUIÉN ME AYUDA A MÍ? 😂",
        "voice": "Claro que te ayudo, digo con una sonrisa. Por dentro estoy calculando cómo voy a resolver todo lo que ya tengo pendiente."
    },
    {
        "search": "funny goat",
        "title": "YO DANDO CONSEJOS",
        "text": "HAY QUE ORGANIZAR LA VIDA",
        "punch": "YO: NO SÉ NI DÓNDE DEJÉ LAS LLAVES",
        "voice": "Yo dando consejos sobre cómo organizar la vida. Mientras tanto, llevo veinte minutos buscando las llaves que tengo en la mano."
    },
    {
        "search": "funny person reaction",
        "title": "CUANDO DICEN: ES RÁPIDO",
        "text": "SON SOLO CINCO MINUTOS",
        "punch": "NOS VEMOS EL PRÓXIMO AÑO",
        "voice": "Cuando alguien dice que solo serán cinco minutos, yo ya sé que debo llevar agua, comida y paciencia para toda la tarde."
    },
]


def font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def centered_text(draw, text, y, fnt, color, max_width=630):
    lines = []
    current = ""

    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    for line in lines:
        box = draw.textbbox((0, 0), line, font=fnt, stroke_width=2)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text(
            (x, y), line, font=fnt, fill=color,
            stroke_width=2, stroke_fill="#111111"
        )
        y += fnt.size + 10

    return y


def search_commons(query):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 15,
        "gsrwhat": "text",
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 900,
        "format": "json",
    }
    headers = {
        "User-Agent": "ReelsGraciososCreator/1.0 (personal creative project)"
    }

    response = requests.get(
        url, params=params, headers=headers, timeout=25
    )
    response.raise_for_status()
    data = response.json()

    pages = list(data.get("query", {}).get("pages", {}).values())
    random.shuffle(pages)

    for page in pages:
        infos = page.get("imageinfo", [])
        if not infos:
            continue

        info = infos[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            continue

        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "")
        license_url = meta.get("LicenseUrl", {}).get("value", "")
        artist = meta.get("Artist", {}).get("value", "")
        description_url = info.get("descriptionurl", "")

        # Solo licencias abiertas conocidas o dominio público.
        allowed = (
            "CC BY" in license_name
            or "CC0" in license_name
            or "Public domain" in license_name.lower()
            or "Public Domain" in license_name
        )
        if not allowed:
            continue

        image_url = info.get("thumburl") or info.get("url")
        if not image_url:
            continue

        return {
            "url": image_url,
            "title": page.get("title", "Imagen"),
            "artist": artist,
            "license": license_name,
            "license_url": license_url,
            "page_url": description_url,
        }

    return None


def download_photo(scene, index):
    headers = {
        "User-Agent": "ReelsGraciososCreator/1.0 (personal creative project)"
    }

    try:
        result = search_commons(scene["search"])
        if not result:
            print(f"No se encontró foto reutilizable: {scene['search']}")
            return None

        response = requests.get(
            result["url"], headers=headers, timeout=30
        )
        response.raise_for_status()

        path = PHOTOS / f"foto_{index:02d}.jpg"
        path.write_bytes(response.content)

        with Image.open(path) as img:
            img.verify()

        return path, result

    except Exception as exc:
        print(f"Foto no disponible para escena {index + 1}: {exc}")
        return None


def make_background(photo_path, index, frame_index):
    if photo_path and photo_path.exists():
        with Image.open(photo_path) as original:
            image = ImageOps.fit(
                original.convert("RGB"),
                (WIDTH, HEIGHT),
                method=Image.Resampling.LANCZOS
            )
    else:
        colors = [
            "#172554", "#3B0764", "#064E3B", "#7C2D12",
            "#164E63", "#831843", "#312E81", "#14532D"
        ]
        image = Image.new(
            "RGB", (WIDTH, HEIGHT), colors[index % len(colors)]
        )
        draw = ImageDraw.Draw(image)
        draw.ellipse((180, 340, 540, 700), fill="#FFD166")
        draw.ellipse((260, 440, 305, 490), fill="#202033")
        draw.ellipse((410, 440, 455, 490), fill="#202033")
        draw.ellipse((310, 520, 410, 590), fill="#C0265C")

    # Oscurecer ligeramente para que los subtítulos contrasten.
    shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 65))
    image = Image.alpha_composite(image.convert("RGBA"), shade)
    return image.convert("RGB")


def render_frame(scene, photo_path, index, frame_index):
    image = make_background(photo_path, index, frame_index)
    draw = ImageDraw.Draw(image)

    # Título superior
    draw.rounded_rectangle(
        (20, 30, WIDTH - 20, 225),
        radius=28, fill="#FFF8E7"
    )
    centered_text(
        draw, scene["title"], 65, font(32), "#202033"
    )

    # Panel principal
    draw.rounded_rectangle(
        (20, 800, WIDTH - 20, 1115),
        radius=30, fill="#FFF8E7"
    )
    centered_text(
        draw, scene["text"], 840, font(37), "#C0265C"
    )
    centered_text(
        draw, scene["punch"], 985, font(29), "#202033"
    )

    draw.text(
        (WIDTH // 2, 1180),
        "😂 COMPARTE CON TUS AMIGOS",
        font=font(20), fill="white", anchor="mm",
        stroke_width=2, stroke_fill="#111111"
    )

    return image


async def create_narration():
    text = " ".join(scene["voice"] for scene in SCENES)
    communicator = edge_tts.Communicate(
        text, VOICE, rate="+8%", volume="+0%"
    )
    await communicator.save(str(AUDIO))


def run_command(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-3500:])


def main():
    OUT.mkdir(exist_ok=True)
    PHOTOS.mkdir(exist_ok=True)

    if FRAMES.exists():
        import shutil
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)

    credits = []
    photos = []

    print("Buscando fotografías con licencias reutilizables...")
    for i, scene in enumerate(SCENES):
        found = download_photo(scene, i)
        if found:
            photo_path, info = found
            photos.append(photo_path)
            credits.append(
                f"Escena {i + 1}: {info['title']}\n"
                f"Autor: {info['artist']}\n"
                f"Licencia: {info['license']} {info['license_url']}\n"
                f"Fuente: {info['page_url']}\n"
            )
        else:
            photos.append(None)
            credits.append(
                f"Escena {i + 1}: imagen gráfica de respaldo creada por el script.\n"
            )

    CREDITS.write_text("\n".join(credits), encoding="utf-8")

    print("Generando narración en español...")
    asyncio.run(create_narration())

    print("Creando escenas verticales...")
    number = 0

    for scene_index, scene in enumerate(SCENES):
        for _ in range(FPS * SCENE_SECONDS):
            image = render_frame(
                scene, photos[scene_index], scene_index, number
            )
            image.save(FRAMES / f"frame_{number:05d}.jpg", quality=85)
            number += 1

    print("Montando MP4...")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    duration = len(SCENES) * SCENE_SECONDS

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
        "-t", str(duration),
        "-movflags", "+faststart",
        str(VIDEO)
    ])

    import shutil
    shutil.rmtree(FRAMES, ignore_errors=True)

    print(f"REEL CREADO: {VIDEO}")
    print(f"CRÉDITOS DE IMÁGENES: {CREDITS}")


if __name__ == "__main__":
    main()
