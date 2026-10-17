import asyncio
import os
import random
import subprocess
from pathlib import Path

import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance


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

MARCA = "Nelson Lucha Reels Graciosos"

FRASES = [
    "Yo diciendo: hoy sí me duermo temprano... 😂",
    "Mi cartera cuando llega el fin de mes: ¡auxilio! 🤣",
    "Yo haciendo ejercicio: levantando el control remoto. 😂",
    "Cuando dicen que el lunes comienzo la dieta... 🍕",
    "La vida es corta: ríete antes de que llegue la factura. 🤣",
    "Yo esperando que llegue el dinero sin salir a trabajar. 😂",
    "Mi motivación los lunes todavía está dormida. 😴",
    "Cuando abres la refrigeradora esperando algo nuevo. 😂",
    "Sonríe, que preocuparse no paga las cuentas. 🤣",
    "Yo haciendo planes y mi bolsillo haciendo otros. 😂",
]

FOTOS = [
    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=1000",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=1000",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=1000",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1000",
    "https://images.unsplash.com/photo-1504593811423-6dd665756598?w=1000",
]


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


def cargar_fuente(tamano):
    rutas = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for ruta in rutas:
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default()


def descargar_foto(url, destino):
    respuesta = requests.get(
        url,
        timeout=35,
        headers={"User-Agent": "NelsonLuchaReels/1.0"}
    )
    respuesta.raise_for_status()
    destino.write_bytes(respuesta.content)

    with Image.open(destino) as imagen:
        imagen.verify()


def obtener_foto(destino):
    urls = FOTOS[:]
    random.shuffle(urls)

    for url in urls:
        try:
            descargar_foto(url, destino)
            return
        except Exception as error:
            print(f"No se pudo descargar una foto: {error}")

    raise RuntimeError("No se pudo descargar ninguna fotografía.")


def ajustar_fondo(imagen):
    imagen = imagen.convert("RGB")
    escala = max(ANCHO / imagen.width, ALTO / imagen.height)
    ancho = int(imagen.width * escala)
    alto = int(imagen.height * escala)

    imagen = imagen.resize((ancho, alto), Image.Resampling.LANCZOS)
    izquierda = (ancho - ANCHO) // 2
    arriba = (alto - ALTO) // 2

    imagen = imagen.crop((
        izquierda, arriba,
        izquierda + ANCHO, arriba + ALTO
    ))

    return ImageEnhance.Brightness(imagen).enhance(0.65)


def dividir_lineas(dibujo, texto, fuente, max_ancho):
    lineas = []
    actual = ""

    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        caja = dibujo.textbbox((0, 0), prueba, font=fuente)

        if caja[2] - caja[0] <= max_ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra

    if actual:
        lineas.append(actual)

    return lineas


def crear_escena(foto, frase, destino):
    with Image.open(foto) as original:
        fondo = ajustar_fondo(original)

    dibujo = ImageDraw.Draw(fondo)
    fuente = cargar_fuente(49)
    fuente_marca = cargar_fuente(23)

    lineas = dividir_lineas(
        dibujo, frase, fuente, ANCHO - 90
    )

    alturas = []
    for linea in lineas:
        caja = dibujo.textbbox(
            (0, 0), linea, font=fuente, stroke_width=2
        )
        alturas.append(caja[3] - caja[1] + 20)

    y = (ALTO - sum(alturas)) // 2

    for linea, altura in zip(lineas, alturas):
        caja = dibujo.textbbox(
            (0, 0), linea, font=fuente, stroke_width=2
        )
        x = (ANCHO - (caja[2] - caja[0])) // 2

        dibujo.text(
            (x, y),
            linea,
            font=fuente,
            fill="white",
            stroke_width=3,
            stroke_fill="black"
        )
        y += altura

    dibujo.text(
        (25, 28),
        MARCA,
        font=fuente_marca,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    fondo.save(destino, quality=94)


async def generar_narracion(texto, destino):
    voz = os.getenv("EDGE_TTS_VOICE", "es-MX-DaliaNeural")
    comunicacion = edge_tts.Communicate(
        texto,
        voice=voz,
        rate="+8%"
    )
    await comunicacion.save(destino)


def crear_video():
    CARPETA.mkdir(parents=True, exist_ok=True)
    frases = random.sample(FRASES, k=TOTAL_ESCENAS)
    clips = []

    for i, frase in enumerate(frases):
        foto = CARPETA / f"foto_{i}.jpg"
        imagen = CARPETA / f"escena_{i}.jpg"
        clip = CARPETA / f"clip_{i}.mp4"

        print(f"Preparando escena {i + 1}/{TOTAL_ESCENAS}...")
        obtener_foto(foto)
        crear_escena(foto, frase, imagen)

        cuadros = FPS * SEGUNDOS_ESCENA
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
            "-i", str(imagen),
            "-t", str(SEGUNDOS_ESCENA),
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
            archivo.write(f"file '{clip.resolve().as_posix()}'\n")

    video_sin_voz = CARPETA / "video_sin_voz.mp4"
    ejecutar([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(lista),
        "-c", "copy",
        str(video_sin_voz)
    ])

    audio = CARPETA / "narracion.mp3"
    asyncio.run(generar_narracion(" ".join(frases), str(audio)))

    ejecutar([
        "ffmpeg", "-y",
        "-i", str(video_sin_voz),
        "-i", str(audio),
        "-filter_complex", "[1:a]apad[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-t", str(TOTAL_ESCENAS * SEGUNDOS_ESCENA),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT
    ])

    print(f"Video creado: {OUTPUT}")


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

    print(f"Subiendo video con preset: {UPLOAD_PRESET}")

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
        # Diagnóstico adicional; no mostrar claves ni secretos.
        detalle = respuesta.headers.get(
            "X-Cld-Error", "No disponible"
        )
        try:
            cuerpo = respuesta.json()
            mensaje = cuerpo.get("error", {}).get(
                "message", respuesta.text[:1500]
            )
        except ValueError:
            mensaje = respuesta.text[:1500]

        raise RuntimeError(
            f"Cloudinary rechazó la subida: {respuesta.status_code}\n"
            f"X-Cld-Error: {detalle}\n"
            f"Respuesta: {mensaje}"
        )

    datos = respuesta.json()
    url = datos.get("secure_url")

    if not url or not url.startswith("https://"):
        raise RuntimeError(
            "Cloudinary no devolvió una URL HTTPS válida."
        )

    Path(VIDEO_URL_FILE).write_text(url, encoding="utf-8")
    print("Video subido correctamente.")
    print("URL guardada en video_url.txt")


def main():
    print("=== GENERADOR DE REELS GRACIOSOS ===")
    crear_video()
    subir_a_cloudinary(OUTPUT)
    print("=== GENERACIÓN Y SUBIDA TERMINADAS ===")


if __name__ == "__main__":
    main()
