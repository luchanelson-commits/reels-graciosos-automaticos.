import asyncio
import os
import random
import subprocess
import textwrap
from pathlib import Path

import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter


# ============================================================
# CONFIGURACIÓN
# ============================================================

ANCHO = 720
ALTO = 1280
FPS = 12
SEGUNDOS_ESCENA = 7
TOTAL_ESCENAS = 5

OUTPUT = "reel_gracioso_publicacion.mp4"
VIDEO_URL_FILE = "video_url.txt"
CARPETA = Path("reel_temporal")

CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
UPLOAD_PRESET = os.getenv(
    "CLOUDINARY_UPLOAD_PRESET", "reels_automaticos"
).strip()

FIRMA = "Nelson Lucha"
MARCA = "Nelson Lucha Reels Graciosos"

FRASES = [
    "Yo diciendo: hoy sí me duermo temprano... 😂",
    "Mi cartera cuando llega el fin de mes: ¡auxilio! 🤣",
    "Yo haciendo ejercicio: levantando el control remoto. 😂",
    "Cuando dicen que el lunes comienzo la dieta... 🍕",
    "La vida es corta: ríete antes de que llegue la factura. 🤣",
    "Yo esperando que llegue el dinero sin salir a trabajar. 😂",
    "Mi motivación los lunes todavía está dormida. 😴",
    "Cuando abres la refrigeradora por quinta vez esperando algo nuevo. 😂",
    "Sonríe, que preocuparse no paga las cuentas. 🤣",
    "Yo haciendo planes y mi bolsillo haciendo otros. 😂",
]

# Fotografías públicas de Unsplash para los fondos.
FOTOS = [
    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=1000",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=1000",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=1000",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1000",
    "https://images.unsplash.com/photo-1504593811423-6dd665756598?w=1000",
]


# ============================================================
# HERRAMIENTAS
# ============================================================

def ejecutar(comando):
    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            "Falló un comando multimedia:\n"
            + resultado.stderr[-3000:]
        )


def cargar_fuente(tamano, negrita=True):
    posibles = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for ruta in posibles:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                pass

    return ImageFont.load_default()


def descargar_foto(url, destino):
    respuesta = requests.get(
        url,
        timeout=35,
        headers={"User-Agent": "NelsonLuchaReels/1.0"}
    )
    respuesta.raise_for_status()

    with open(destino, "wb") as archivo:
        archivo.write(respuesta.content)

    # Verificar que realmente sea una imagen.
    with Image.open(destino) as imagen:
        imagen.verify()


def obtener_foto(indice, destino):
    # Intentar las fotos en orden aleatorio, sin depender
    # de un único servidor.
    urls = FOTOS[:]
    random.shuffle(urls)

    for url in urls:
        try:
            descargar_foto(url, destino)
            return
        except Exception as error:
            print(f"No se pudo descargar una foto: {error}")

    raise RuntimeError(
        "No se pudo descargar ninguna fotografía. "
        "Comprueba el acceso a Internet."
    )


def ajustar_fondo(imagen):
    imagen = imagen.convert("RGB")

    escala = max(
        ANCHO / imagen.width,
        ALTO / imagen.height
    )

    nuevo_ancho = int(imagen.width * escala)
    nuevo_alto = int(imagen.height * escala)

    imagen = imagen.resize(
        (nuevo_ancho, nuevo_alto),
        Image.Resampling.LANCZOS
    )

    izquierda = (nuevo_ancho - ANCHO) // 2
    arriba = (nuevo_alto - ALTO) // 2

    imagen = imagen.crop(
        (izquierda, arriba, izquierda + ANCHO, arriba + ALTO)
    )

    imagen = ImageEnhance.Brightness(imagen).enhance(0.66)
    return imagen


def dibujar_texto_centrado(
    dibujo, texto, centro_y, fuente, ancho_maximo
):
    palabras = texto.split()
    lineas = []
    actual = ""

    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        caja = dibujo.textbbox(
            (0, 0), prueba, font=fuente, stroke_width=2
        )

        if caja[2] - caja[0] <= ancho_maximo:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra

    if actual:
        lineas.append(actual)

    alturas = []
    for linea in lineas:
        caja = dibujo.textbbox(
            (0, 0), linea, font=fuente, stroke_width=2
        )
        alturas.append(caja[3] - caja[1] + 18)

    y = centro_y - sum(alturas) // 2

    for linea, altura in zip(lineas, alturas):
        caja = dibujo.textbbox(
            (0, 0), linea, font=fuente, stroke_width=2
        )
        ancho_texto = caja[2] - caja[0]
        x = (ANCHO - ancho_texto) // 2

        dibujo.text(
            (x, y),
            linea,
            font=fuente,
            fill="white",
            stroke_width=3,
            stroke_fill="black"
        )
        y += altura


def crear_escena(foto, frase, destino, numero):
    with Image.open(foto) as original:
        fondo = ajustar_fondo(original)

    dibujo = ImageDraw.Draw(fondo)

    fuente_titulo = cargar_fuente(53)
    fuente_marca = cargar_fuente(25)
    fuente_firma = cargar_fuente(23)

    dibujar_texto_centrado(
        dibujo,
        frase,
        ALTO // 2,
        fuente_titulo,
        ANCHO - 90
    )

    dibujo.text(
        (35, 35),
        MARCA,
        font=fuente_marca,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    dibujo.text(
        (ANCHO - 35, ALTO - 65),
        FIRMA,
        font=fuente_firma,
        fill="white",
        anchor="ra",
        stroke_width=2,
        stroke_fill="black"
    )

    fondo.save(destino, quality=94)


# ============================================================
# NARRACIÓN EN ESPAÑOL
# ============================================================

async def generar_narracion(texto, destino):
    voz = os.getenv("EDGE_TTS_VOICE", "es-MX-DaliaNeural")

    comunicacion = edge_tts.Communicate(
        texto,
        voice=voz,
        rate="+8%",
        volume="+0%"
    )

    await comunicacion.save(destino)


# ============================================================
# GENERAR VIDEO VERTICAL
# ============================================================

def crear_video():
    CARPETA.mkdir(parents=True, exist_ok=True)

    frases = random.sample(FRASES, k=TOTAL_ESCENAS)
    escenas = []
    clips = []

    for i, frase in enumerate(frases):
        foto = CARPETA / f"foto_{i}.jpg"
        imagen_texto = CARPETA / f"escena_{i}.jpg"
        clip = CARPETA / f"clip_{i}.mp4"

        print(f"Preparando escena {i + 1}/{TOTAL_ESCENAS}...")

        obtener_foto(i, foto)
        crear_escena(foto, frase, imagen_texto, i)

        duracion = SEGUNDOS_ESCENA
        cuadros = FPS * duracion

        filtro = (
            f"scale={ANCHO}:{ALTO}:"
            "force_original_aspect_ratio=increase,"
            f"crop={ANCHO}:{ALTO},"
            f"zoompan=z='min(zoom+0.0007,1.05)':"
            f"d={cuadros}:s={ANCHO}x{ALTO}:fps={FPS},"
            "format=yuv420p"
        )

        ejecutar([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(imagen_texto),
            "-t", str(duracion),
            "-vf", filtro,
            "-r", str(FPS),
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            str(clip)
        ])

        clips.append(clip)

    lista = CARPETA / "clips.txt"

    with open(lista, "w", encoding="utf-8") as archivo:
        for clip in clips:
            ruta = clip.resolve().as_posix()
            archivo.write(f"file '{ruta}'\n")

    video_sin_voz = CARPETA / "video_sin_voz.mp4"

    ejecutar([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(lista),
        "-c", "copy",
        str(video_sin_voz)
    ])

    texto_narracion = " ".join(frases)
    audio = CARPETA / "narracion.mp3"

    print("Generando narración en español...")
    asyncio.run(generar_narracion(texto_narracion, str(audio)))

    duracion_total = TOTAL_ESCENAS * SEGUNDOS_ESCENA

    ejecutar([
        "ffmpeg", "-y",
        "-i", str(video_sin_voz),
        "-i", str(audio),
        "-filter_complex",
        "[1:a]apad,volume=1.0[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-t", str(duracion_total),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT
    ])

    print(f"Video creado: {OUTPUT}")
    return frases


# ============================================================
# SUBIR VIDEO A CLOUDINARY CON PRESET UNSIGNED
# ============================================================

def subir_a_cloudinary(video_path):
    if not CLOUD_NAME:
        raise RuntimeError(
            "Falta el secreto CLOUDINARY_CLOUD_NAME en GitHub."
        )

    if not UPLOAD_PRESET:
        raise RuntimeError(
            "Falta CLOUDINARY_UPLOAD_PRESET."
        )

    endpoint = (
        f"https://api.cloudinary.com/v1_1/"
        f"{CLOUD_NAME}/video/upload"
    )

    print("Subiendo video a Cloudinary con preset unsigned...")

    with open(video_path, "rb") as video_file:
        respuesta = requests.post(
            endpoint,
            data={
                "upload_preset": UPLOAD_PRESET,
                "folder": "reels_graciosos",
            },
            files={
                "file": (
                    os.path.basename(video_path),
                    video_file,
                    "video/mp4"
                )
            },
            timeout=240
        )

    if respuesta.status_code not in (200, 201):
        raise RuntimeError(
            "Cloudinary rechazó la subida: "
            f"{respuesta.status_code} {respuesta.text[:1500]}"
        )

    datos = respuesta.json()
    url = datos.get("secure_url")

    if not url or not url.startswith("https://"):
        raise RuntimeError(
            "Cloudinary no devolvió una URL HTTPS válida."
        )

    with open(VIDEO_URL_FILE, "w", encoding="utf-8") as archivo:
        archivo.write(url)

    print("Subida completada.")
    print("URL guardada en video_url.txt")
    return url


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    print("=== GENERADOR DE REELS GRACIOSOS ===")

    if not os.path.exists("ffmpeg") and not os.getenv("PATH"):
        print("Aviso: comprueba que FFmpeg esté instalado.")

    crear_video()
    url = subir_a_cloudinary(OUTPUT)

    print("=== PROCESO TERMINADO ===")
    print(f"Video: {OUTPUT}")
    print(f"URL: {url}")


if __name__ == "__main__":
    main()
