import asyncio
import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import edge_tts
import imageio_ffmpeg

# CONFIGURACIÓN
WIDTH, HEIGHT = 720, 1280
FPS = 12
SCENE_SECONDS = 5
VOICE = "es-MX-DaliaNeural"

OUT = Path("salida")
FRAMES = OUT / "frames"
VIDEO = OUT / "reel_gracioso.mp4"
AUDIO = OUT / "narracion.mp3"

SCENES = [
    {
        "title": "CUANDO COBRO",
        "text": "ESTA VEZ SÍ VOY A AHORRAR",
        "punch": "¿QUIÉN SE LLEVÓ MI DINERO?",
        "voice": "Cuando cobro digo: esta vez sí voy a ahorrar. Diez minutos después: ¿quién se llevó mi dinero?"
    },
    {
        "title": "EL LUNES EMPIEZO",
        "text": "DIETA, EJERCICIO Y DISCIPLINA",
        "punch": "PERO HOY HAY PUPUSAS",
        "voice": "El lunes empiezo la dieta, el ejercicio y la disciplina. Pero hoy hay pupusas, y uno tiene prioridades."
    },
    {
        "title": "SOLO UN VIDEO MÁS",
        "text": "YA ME VOY A DORMIR",
        "punch": "¡SON LAS TRES DE LA MAÑANA!",
        "voice": "Yo diciendo que ya me voy a dormir. Solo un video más. De repente, ¡son las tres de la mañana!"
    },
    {
        "title": "CUANDO ME ESCRIBE MI EX",
        "text": "YA LO SUPERÉ",
        "punch": "¿Y SI LE DIGO HOLA?",
        "voice": "Cuando me escribe mi ex, digo que ya lo superé. Pero mi dedo pregunta: ¿y si le digo hola?"
    },
    {
        "title": "HACIENDO PLANES",
        "text": "MAÑANA SERÉ PRODUCTIVO",
        "punch": "MEJOR EMPIEZO EL LUNES",
        "voice": "Mañana seré productivo, ordenado y puntual. Bueno, mejor empiezo el lunes. ¡Este lunes sí!"
    },
    {
        "title": "CUANDO DICEN: TRANQUILO",
        "text": "YO ESTOY MUY TRANQUILO",
        "punch": "PERO POR DENTRO: ¡AAAAH!",
        "voice": "Cuando me dicen tranquilo, yo respondo que estoy tranquilo. Pero por dentro estoy gritando como loco."
    },
    {
        "title": "MI CUENTA BANCARIA",
        "text": "YO: SOY MILLONARIO",
        "punch": "MI SALDO: JA, JA, JA",
        "voice": "Yo me siento millonario hasta que reviso mi cuenta bancaria. Mi saldo se ríe de mí."
    },
    {
        "title": "CUANDO LIMPIO LA CASA",
        "text": "HOY SÍ TERMINO TODO",
        "punch": "ENCUENTRO EL CELULAR Y ADIÓS",
        "voice": "Hoy sí voy a limpiar toda la casa. Encuentro mi celular, reviso un mensaje y se acabó la jornada."
    },
]


def get_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_centered(draw, text, y, font, color, max_width=630):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    for line in lines:
        box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text(
            (x, y), line, font=font, fill=color,
            stroke_width=2, stroke_fill="#171717"
        )
        y += font.size + 12

    return y


def draw_character(draw, cx, cy, index, motion):
    skin_colors = ["#FFD166", "#F4B183", "#FFADAD", "#C9A0FF"]
    shirt_colors = ["#EF476F", "#118AB2", "#06D6A0", "#F59E0B"]

    skin = skin_colors[index % len(skin_colors)]
    shirt = shirt_colors[index % len(shirt_colors)]

    # Brazos y cuerpo
    draw.line(
        (cx - 45, cy + 105, cx - 115, cy + 145 + motion),
        fill=skin, width=25
    )
    draw.line(
        (cx + 45, cy + 105, cx + 115, cy + 145 - motion),
        fill=skin, width=25
    )
    draw.rounded_rectangle(
        (cx - 65, cy + 65, cx + 65, cy + 235),
        radius=30, fill=shirt
    )

    # Cabeza
    r = 82
    draw.ellipse(
        (cx-r, cy-r, cx+r, cy+r),
        fill=skin, outline="#202033", width=5
    )

    # Ojos
    draw.ellipse((cx-40, cy-25, cx-15, cy+8), fill="#202033")
    draw.ellipse((cx+15, cy-25, cx+40, cy+8), fill="#202033")

    # Boca cómica
    if index % 2 == 0:
        draw.ellipse((cx-28, cy+22, cx+28, cy+62), fill="#7A284B")
    else:
        draw.arc(
            (cx-38, cy+15, cx+38, cy+60),
            start=5, end=175, fill="#202033", width=6
        )


def make_scene(scene, index, frame_number):
    backgrounds = [
        "#172554", "#3B0764", "#064E3B", "#7C2D12",
        "#164E63", "#831843", "#312E81", "#14532D"
    ]
    img = Image.new("RGB", (WIDTH, HEIGHT), backgrounds[index % len(backgrounds)])
    draw = ImageDraw.Draw(img)

    # Decoración aleatoria pero estable por escena
    random.seed(index + 123)
    for _ in range(24):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        r = random.randint(7, 18)
        color = random.choice(
            ["#FFD166", "#FF70A6", "#70D6FF", "#E9FF70"]
        )
        draw.ellipse((x-r, y-r, x+r, y+r), fill=color)

    # Título
    draw.rounded_rectangle(
        (25, 35, WIDTH-25, 210), radius=28, fill="#FFF8E7"
    )
    draw_centered(
        draw, scene["title"], 80, get_font(34), "#202033"
    )

    # Personaje con pequeño movimiento
    seconds = frame_number / FPS
    motion = int(12 * math.sin(seconds * 5))
    draw_character(draw, WIDTH // 2, 440, index, motion)

    # Texto principal
    draw.rounded_rectangle(
        (25, 770, WIDTH-25, 1100), radius=30, fill="#FFF8E7"
    )
    draw_centered(
        draw, scene["text"], 815, get_font(36), "#C0265C"
    )
    draw_centered(
        draw, scene["punch"], 965, get_font(30), "#202033"
    )

    draw.text(
        (WIDTH // 2, 1180),
        "😂 COMPARTE Y ETIQUETA A TUS AMIGOS",
        font=get_font(19), fill="white", anchor="mm"
    )

    return img


async def create_voice():
    narration = " ".join(scene["voice"] for scene in SCENES)
    speaker = edge_tts.Communicate(
        narration, VOICE, rate="+8%", volume="+0%"
    )
    await speaker.save(str(AUDIO))


def run_command(command):
    result = subprocess.run(
        command, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-4000:])


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)

    print("Creando narración en español...")
    asyncio.run(create_voice())

    print("Creando escenas...")
    frames_per_scene = FPS * SCENE_SECONDS
    frame_number = 0

    for scene_index, scene in enumerate(SCENES):
        for _ in range(frames_per_scene):
            img = make_scene(scene, scene_index, frame_number)
            img.save(FRAMES / f"frame_{frame_number:05d}.png")
            frame_number += 1

    print("Generando archivo MP4...")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    duration = len(SCENES) * SCENE_SECONDS

    run_command([
        ffmpeg, "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame_%05d.png"),
        "-i", str(AUDIO),
        "-vf", "scale=720:1280,format=yuv420p",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "96k",
        "-af", "apad",
        "-t", str(duration),
        "-movflags", "+faststart",
        str(VIDEO),
    ])

    shutil.rmtree(FRAMES, ignore_errors=True)

    if not VIDEO.exists() or VIDEO.stat().st_size == 0:
        raise RuntimeError("No se encontró el video MP4 generado.")

    print(f"¡REEL CREADO! Archivo: {VIDEO}")
    print(f"Tamaño: {VIDEO.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
