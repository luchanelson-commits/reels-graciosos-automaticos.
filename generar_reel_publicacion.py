import os
import math
import time
import random
import asyncio
import subprocess
import hashlib
from pathlib import Path

import requests
import generar_reel as base


OUTPUT = "reel_gracioso_publicacion.mp4"
FPS_PUBLICACION = 24
MAX_DURATION = 59


def subir_a_cloudinary(video_path):
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

    if not cloud or not api_key or not api_secret:
        raise RuntimeError(
            "Faltan secretos de Cloudinary en GitHub Actions."
        )

    timestamp = int(time.time())
    public_id = f"nelson_lucha_reel_{timestamp}"

    params = {
        "public_id": public_id,
        "timestamp": str(timestamp),
    }

    signature_text = "&".join(
        f"{key}={params[key]}" for key in sorted(params)
    ) + api_secret

    signature = hashlib.sha1(
        signature_text.encode("utf-8")
    ).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{cloud}/video/upload"

    print("Subiendo video a Cloudinary...")

    with open(video_path, "rb") as video_file:
        response = requests.post(
            url,
            data={
                **params,
                "api_key": api_key,
                "signature": signature,
            },
            files={"file": video_file},
            timeout=300,
        )

    if not response.ok:
        raise RuntimeError(
            f"Cloudinary rechazó la subida: "
            f"{response.status_code} {response.text[:800]}"
        )

    result = response.json()
    video_url = result.get("secure_url")

    if not video_url:
        raise RuntimeError(
            "Cloudinary no devolvió la URL pública del video."
        )

    check = requests.get(
        video_url,
        headers={"Range": "bytes=0-1023"},
        timeout=45,
        stream=True,
    )

    try:
        if check.status_code not in (200, 206):
            raise RuntimeError(
                f"No se pudo comprobar la URL pública: "
                f"HTTP {check.status_code}"
            )
    finally:
        check.close()

    Path("video_url.txt").write_text(
        video_url + "\n", encoding="utf-8"
    )

    print("Video subido correctamente.")
    print("URL pública verificada.")
    print("La URL se guardó en video_url.txt")


def crear_video_corto():
    # Primero probamos con dos chistes para acercarnos a 45-59 s.
    selected = random.sample(base.JOKES, 2)
    audio_path = base.WORK / "narracion_publicacion.mp3"

    for intento in range(2):
        print(f"Preparando narración: intento {intento + 1}")

        words = asyncio.run(
            base.create_voice(selected, audio_path)
        )

        audio_duration = base.get_audio_duration(audio_path)
        duration = max(base.MIN_DURATION, math.ceil(audio_duration + 1))

        if duration <= MAX_DURATION:
            break

        if intento == 0:
            print(
                "Dos chistes superan los 59 segundos. "
                "Probando con uno."
            )
            selected = random.sample(selected, 1)
        else:
            raise RuntimeError(
                "La narración supera 59 segundos. "
                "No se publicará un video demasiado largo."
            )

    if duration > MAX_DURATION:
        raise RuntimeError("El video supera el límite de duración.")

    groups = base.make_caption_groups(words)
    photos = []

    print("Descargando fotografías...")
    for index, joke in enumerate(selected):
        photos.append(base.search_photo(joke["query"], index))

    frames_dir = base.WORK / "frames_publicacion"
    frames_dir.mkdir(exist_ok=True)

    for old_frame in frames_dir.glob("frame_*.jpg"):
        old_frame.unlink()

    total_frames = duration * FPS_PUBLICACION
    frames_per_scene = total_frames // len(selected)
    frame_number = 0

    for scene_index, (joke, photo) in enumerate(
        zip(selected, photos)
    ):
        for local_frame in range(frames_per_scene):
            progress = local_frame / max(1, frames_per_scene - 1)
            current_time = frame_number / FPS_PUBLICACION
            caption = base.caption_at_time(groups, current_time)

            frame = base.make_frame(
                photo, joke, progress, caption
            )

            frame.save(
                frames_dir / f"frame_{frame_number:05d}.jpg",
                quality=88,
            )
            frame_number += 1

        print(f"Escena {scene_index + 1} lista.")

    while frame_number < total_frames:
        current_time = frame_number / FPS_PUBLICACION
        caption = base.caption_at_time(groups, current_time)

        frame = base.make_frame(
            photos[-1], selected[-1], 1.0, caption
        )

        frame.save(
            frames_dir / f"frame_{frame_number:05d}.jpg",
            quality=88,
        )
        frame_number += 1

    command = [
        "ffmpeg", "-y",
        "-framerate", str(FPS_PUBLICACION),
        "-i", str(frames_dir / "frame_%05d.jpg"),
        "-i", str(audio_path),
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS_PUBLICACION),
        "-c:a", "aac",
        "-ar", "48000",
        "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT,
    ]

    print("Creando Reel corto...")
    subprocess.run(command, check=True)

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            OUTPUT,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    actual_duration = float(result.stdout.strip())

    if actual_duration > MAX_DURATION:
        raise RuntimeError(
            f"El MP4 dura {actual_duration:.1f} segundos. "
            "Se cancela la subida."
        )

    if not Path(OUTPUT).exists() or Path(OUTPUT).stat().st_size < 100_000:
        raise RuntimeError("El video no se creó correctamente.")

    print(f"Video listo: {actual_duration:.1f} segundos.")
    subir_a_cloudinary(OUTPUT)


def main():
    crear_video_corto()


if __name__ == "__main__":
    main()
