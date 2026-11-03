# Descargador

Interfaz gráfica sencilla (GTK3) para **yt-dlp**, pensada para Linux Mint XFCE y otras distros basadas en Ubuntu/Debian.
Pegas el link, eliges video o solo audio, eliges el formato y listo.

## Características

- Pega el link (o lo toma solo del portapapeles al abrir).
- Video (mp4, mkv, webm) o solo audio (mp3, m4a, opus, flac, wav), con elección de calidad.
- Barra de progreso con velocidad y tiempo restante.
- **Pensado para conexiones inestables:** si se corta el internet, reintenta solo y retoma lo ya descargado.
- Descarga e instala por su cuenta `yt-dlp` y `Deno` en `~/.local/bin` (no hay que tocar el PATH).
- Notificación de escritorio al terminar y botón para actualizar yt-dlp.

## Requisitos

- Python 3 y GTK3 (ya vienen en Linux Mint). Si falta algo:
  ```bash
  sudo apt install python3-gi gir1.2-gtk-3.0
  ```
- `ffmpeg` (para unir video y audio y convertir formatos):
  ```bash
  sudo apt install ffmpeg
  ```

## Uso

```bash
python3 descargador.py
```

Para agregarlo al menú de aplicaciones:

```bash
python3 descargador.py --instalar
```

Luego búscalo como **Descargador** en el menú.

## Limitaciones

Descargador solo es una interfaz; hereda las limitaciones de yt-dlp:

- No funciona con contenido protegido con DRM (Netflix, Disney+, Prime Video, Spotify, etc.).
- Contenido de pago, privado o que exige iniciar sesión no está soportado desde esta interfaz.
- Algunos videos están restringidos por región o edad.
- YouTube cambia seguido y a veces la descarga falla hasta que sale una actualización de yt-dlp (usa el botón "Actualizar yt-dlp").
- Lista de sitios soportados: [supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Créditos

Este proyecto no incluye ni redistribuye estos programas; los descarga o usa desde sus fuentes oficiales en el equipo de cada persona:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp): el motor que hace todo el trabajo de descarga (licencia Unlicense).
- [Deno](https://github.com/denoland/deno): entorno de JavaScript que yt-dlp usa para YouTube (licencia MIT).
- [FFmpeg](https://ffmpeg.org/): unión y conversión de audio y video.

Este proyecto no está afiliado a ninguno de los anteriores ni a YouTube.

## Aviso legal

Sos responsable de cumplir las leyes de tu país y los términos de uso de cada plataforma. El software se entrega "tal cual", sin garantías.

## Licencia

[MIT](LICENSE)
