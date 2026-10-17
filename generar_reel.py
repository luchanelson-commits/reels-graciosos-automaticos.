import asyncio
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import edge_tts
import imageio_ffmpeg


# ---------------- CONFIGURACIÓN ----------------

ANCHO = 720
ALTO = 1280
FPS = 15
SEGUNDOS_ESCENA = 5
TOTAL_ESCENAS = 5

SALIDA = Path("salida")
FRAMES = SALIDA / "frames"
SALIDA.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)

VIDEO = SALIDA / "reel_gracioso.mp4"
AUDIO = SALIDA / "narracion.mp3"

VOZ = "es-MX-DaliaNeural"

ESCENAS = [
    {
        "titulo": "YO, COBRANDO EL SUELDO",
        "texto": "ESTA VEZ SÍ VOY A AHORRAR",
        "remate": "A LOS 10 MINUTOS: ¿Y MI DINERO?",
        "voz": "Yo cuando cobro: esta vez sí voy a ahorrar. Diez minutos después... ¿y mi dinero?"
    },
    {
        "titulo": "EL LUNES EMPIEZO",
        "texto": "DIETA, EJERCICIO Y DISCIPLINA",
        "remate": "PERO HOY HAY PUPUSAS",
        "voz": "El lunes empiezo la dieta, el ejercicio y la disciplina. Pero hoy hay pupusas... y uno tiene prioridades."
    },
    {
        "titulo": "YO DICIENDO: YA ME DUERMO",
        "texto": "SOLO VOY A VER UN VIDEO",
        "remate": "SON LAS 3 DE LA MAÑANA",
        "voz": "Yo diciendo que ya me voy a dormir. Solo un video más... y de repente son las tres de la mañana."
    },
    {
        "titulo": "CUANDO ME ESCRIBE MI EX",
        "texto": "YA LO SUPERÉ",
        "remate": "¿Y SI SOLO LE CONTESTO HOLA?",
        "voz": "Cuando me escribe mi ex, digo que ya lo superé. Pero mi dedo pregunta... ¿y si solo le contesto hola?"
    },
    {
        "titulo": "YO HACIENDO PLANES",
        "texto": "MAÑANA SERÉ PRODUCTIVO",
        "remate": "MAÑANA TAMBIÉN ES DÍA",
        "voz": "Yo haciendo planes para mañana: seré productivo, ordenado y puntual. Bueno... mañana también es día."
    },
]


def fuente(tamano, negrita=True):
    rutas = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if negrita else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
    ]
    for ruta in rutas:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default()


def texto_centrado(draw, texto, y, font, fill, ancho_max=660):
    palabras = texto.split()
    lineas = []
    actual = ""

    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if draw.textbbox((0, 0), prueba, font=font)[2] <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra

    if actual:
        lineas.append(actual)

    alto_linea = font.size + 12
    for linea in lineas:
        caja = draw.textbbox((0, 0), linea, font=font, stroke_width=2)
        x = (ANCHO - (caja[2] - caja[0])) // 2
        draw.text(
            (x, y), linea, font=font, fill=fill,
            stroke_width=2, stroke_fill="#202033"
        )
        y += alto_linea

    return y


def dibujar_personaje(draw, cx, cy, tipo, movimiento):
    # Personaje cómico original dibujado con formas.
    radio = 92
    colores = ["#FFD166", "#FFADAD", "#BDB2FF", "#9BF6FF", "#CAFFBF"]
    piel = colores[tipo % len(colores)]

    # Cuerpo
    draw.rounded_rectangle(
        (cx - 70, cy + 70, cx + 70, cy + 235),
        radius=35, fill=["#EF476F", "#118AB2", "#06D6A0"][tipo % 3]
    )

    # Brazos
    draw.line((cx - 50, cy + 100, cx - 115, cy + 155 + movimiento),
              fill=piel, width=28)
    draw.line((cx + 50, cy + 100, cx + 115, cy + 140 - movimiento),
              fill=piel, width=28)

    # Cabeza
    draw.ellipse((cx-radio, cy-radio, cx+radio, cy+radio), fill=piel,
                 outline="#202033", width=5)

    # Ojos
    draw.ellipse((cx-42, cy-25, cx-15, cy+10), fill="#202033")
    draw.ellipse((cx+15, cy-25, cx+42, cy+10), fill="#202033")

    # Boca exagerada
    if tipo % 2 == 0:
        draw.ellipse((cx-35, cy+22, cx+35, cy+65), fill="#7A284B")
    else:
        draw.arc((cx-42, cy+10, cx+42, cy+62),
                 start=10, end=170, fill="#202033", width=7)


def crear_imagen_escena(escena, indice, movimiento):
    fondo = ["#172554", "#3B0764", "#064E3B", "#7C2D12", "#164E63"][indice]
    img = Image.new("RGB", (ANCHO, ALTO), fondo)
    draw = ImageDraw.Draw(img)

    # Confeti y círculos decorativos
    random.seed(indice + 20)
    for _ in range(28):
        x = random.randint(0, ANCHO)
        y = random.randint(0, ALTO)
        r = random.randint(8, 25)
        color = random.choice(
            ["#FFD166", "#FF70A6", "#70D6FF", "#E9FF70"]
        )
        draw.ellipse((x-r, y-r, x+r, y+r), fill=color)

    # Panel superior
    draw.rounded_rectangle(
        (25, 35, ANCHO-25, 225), radius=32, fill="#FFF8E7"
    )
    texto_centrado(
        draw, escena["titulo"], 65, fuente(36),
        "#202033", ancho_max=620
    )

    # Ilustración central
    dibujar_personaje(draw, ANCHO // 2, 440, indice, movimiento)

    # Panel de texto
    draw.rounded_rectangle(
        (28, 770, ANCHO-28, 1110), radius=35, fill="#FFF8E7"
    )
    texto_centrado(
        draw, escena["texto"], 815, fuente(39),
        "#C0265C", ancho_max=620
    )
    texto_centrado(
        draw, escena["remate"], 970, fuente(32),
        "#202033", ancho_max=620
    )

    draw.text(
        (ANCHO // 2, 1180), "😂 ¡COMPÁRTELO CON TUS AMIGOS!",
        font=fuente(22), fill="white", anchor="mm"
    )
    return img


async def generar_narracion():
    texto = " ".join(escena["voz"] for escena in ESCENAS)
    comunicador = edge_tts.Communicate(texto, VOZ, rate="+8%")
    await comunicador.save(str(AUDIO))


def ejecutar(comando):
    resultado = subprocess.run(
        comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr[-3000:])


def main():
    print("Generando narración en español...")
    try:
        asyncio.run(generar_narracion())
    except Exception as error:
        raise RuntimeError(
            "No se pudo crear la narración. Revisa la conexión del servicio "
            "de voz e inténtalo de nuevo."
        ) from error

    print("Dibujando las escenas...")
    total_frames = FPS * SEGUNDOS_ESCENA * TOTAL_ESCENAS
    numero = 0

    for indice, escena in enumerate(ESCENAS):
        for local in range(FPS * SEGUNDOS_ESCENA):
            tiempo = local / FPS
            movimiento = int(10 * math.sin(tiempo * 5))
            imagen = crear_imagen_escena(escena, indice, movimiento)
            imagen.save(FRAMES / f"frame_{numero:05d}.png")
            numero += 1

    print("Montando el video vertical...")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    ejecutar([
        ffmpeg, "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame_%05d.png"),
        "-i", str(AUDIO),
        "-vf", "scale=720:1280,format=yuv420p",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "27",
        "-c:a", "aac",
        "-b:a", "96k",
        "-af", "apad",
        "-t", str(SEGUNDOS_ESCENA * TOTAL_ESCENAS),
        "-movflags", "+faststart",
        str(VIDEO)
    ])

    # Limpia los cuadros intermedios para reducir el tamaño del artefacto.
    for archivo in FRAMES.glob("*.png"):
        archivo.unlink()
    FRAMES.rmdir()

    print(f"Reel creado correctamente: {VIDEO}")
    print(f"Duración prevista: {SEGUNDOS_ESCENA * TOTAL_ESCENAS} segundos")


if __name__ == "__main__":
    main()
