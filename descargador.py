#!/usr/bin/env python3
"""Descargador: interfaz gráfica sencilla para yt-dlp (Linux Mint XFCE).

Uso:   python3 descargador.py            -> abre la ventana
       python3 descargador.py --instalar -> lo agrega al menú de aplicaciones
Solo usa Python 3 + GTK3 (ya vienen en Mint). Instala yt-dlp y Deno por su cuenta
en ~/.local/bin, así que no tienes que tocar el PATH.
"""
import os, re, shutil, subprocess, sys, threading, time, urllib.request, zipfile
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

BIN = os.path.expanduser("~/.local/bin")
ENV = dict(os.environ, PATH=BIN + os.pathsep + os.environ.get("PATH", ""))  # ~/.local/bin primero
URL_YTDLP = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
URL_DENO = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip"
ERRORES_RED = ("timed out", "Name or service", "Temporary failure", "Connection", "Network",
               "Errno", "HTTP Error 5", "IncompleteRead", "SSL", "Unable to download")
CALIDADES = {"Mejor disponible": None, "1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
FORMATOS = {"video": ["mp4", "mkv", "webm"], "audio": ["mp3", "m4a", "opus", "flac", "wav"]}

CSS = b"""
window { background: #1e2127; }
label, checkbutton, radiobutton { color: #e6e6e6; }
entry, combobox button { background: #2b2f38; color: #fff; border-radius: 8px; padding: 6px; }
button { border-radius: 8px; padding: 6px 14px; }
button.go { background: #3fb27f; color: #fff; font-weight: bold; }
button.stop { background: #d9534f; color: #fff; }
progressbar trough { min-height: 22px; border-radius: 11px; background: #2b2f38; }
progressbar progress { min-height: 22px; border-radius: 11px; background: #3fb27f; }
progressbar text { color: #fff; font-weight: bold; }
textview, textview text { background: #14161a; color: #9fd8b8; font-family: monospace; }
"""


def bajar(url, destino):
    with urllib.request.urlopen(url, timeout=60) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def asegurar_herramientas(log):
    """Descarga yt-dlp y Deno si faltan. Devuelve True si ffmpeg existe."""
    os.makedirs(BIN, exist_ok=True)
    if not shutil.which("yt-dlp", path=ENV["PATH"]):
        log("Descargando yt-dlp...")
        bajar(URL_YTDLP, os.path.join(BIN, "yt-dlp"))
        os.chmod(os.path.join(BIN, "yt-dlp"), 0o755)
    if not shutil.which("deno", path=ENV["PATH"]):
        try:
            log("Instalando Deno (necesario para YouTube)...")
            bajar(URL_DENO, "/tmp/deno.zip")
            with zipfile.ZipFile("/tmp/deno.zip") as z:
                z.extract("deno", BIN)
            os.chmod(os.path.join(BIN, "deno"), 0o755)
        except Exception as e:
            log(f"(Deno no se pudo instalar, se intentará sin él: {e})")
    return shutil.which("ffmpeg") is not None


def armar_comando(url, modo, fmt, calidad, carpeta, lista):
    c = [shutil.which("yt-dlp", path=ENV["PATH"]), "--newline", "--embed-metadata",
         "--retries", "infinite", "--fragment-retries", "infinite",
         "--retry-sleep", "3", "--socket-timeout", "30",
         "-o", os.path.join(carpeta, "%(title)s [%(id)s].%(ext)s"),
         "--yes-playlist" if lista else "--no-playlist"]
    if modo == "audio":
        c += ["-x", "--audio-format", fmt, "--audio-quality", "0"]
    else:
        h = CALIDADES[calidad]
        c += ["-f", f"bv*[height<={h}]+ba/b[height<={h}]" if h else "bv*+ba/b",
              "--merge-output-format", fmt]
        orden = {"mp4": "res,ext:mp4:m4a", "webm": "res,vcodec:vp9,acodec:opus"}.get(fmt)
        if orden:
            c += ["-S", orden]
    return c + [url]


class App(Gtk.Window):
    def __init__(self):
        super().__init__(title="Descargador")
        self.set_default_size(560, 560)
        self.set_border_width(16)
        self.cancelado, self.proc = False, None
        css = Gtk.CssProvider(); css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10); self.add(caja)

        fila = Gtk.Box(spacing=6); caja.pack_start(fila, False, False, 0)
        self.url = Gtk.Entry(placeholder_text="Pega aquí el link..."); fila.pack_start(self.url, True, True, 0)
        b = Gtk.Button(label="Pegar"); b.connect("clicked", lambda *_: self.pegar()); fila.pack_start(b, False, False, 0)

        fila = Gtk.Box(spacing=12); caja.pack_start(fila, False, False, 0)
        self.r_video = Gtk.RadioButton.new_with_label(None, "Video")
        self.r_audio = Gtk.RadioButton.new_with_label_from_widget(self.r_video, "Solo audio")
        self.r_video.connect("toggled", self.cambiar_modo)
        fila.pack_start(self.r_video, False, False, 0); fila.pack_start(self.r_audio, False, False, 0)
        self.fmt = Gtk.ComboBoxText(); fila.pack_start(self.fmt, False, False, 0)
        self.cal = Gtk.ComboBoxText()
        for k in CALIDADES: self.cal.append_text(k)
        self.cal.set_active(0); fila.pack_start(self.cal, False, False, 0)
        self.cambiar_modo()

        self.lista = Gtk.CheckButton(label="Si es una lista de reproducción, descargarla completa")
        caja.pack_start(self.lista, False, False, 0)

        fila = Gtk.Box(spacing=6); caja.pack_start(fila, False, False, 0)
        fila.pack_start(Gtk.Label(label="Guardar en:"), False, False, 0)
        self.carpeta = Gtk.FileChooserButton(title="Carpeta", action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.carpeta.set_filename(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
                                  or os.path.expanduser("~"))
        fila.pack_start(self.carpeta, True, True, 0)

        fila = Gtk.Box(spacing=6); caja.pack_start(fila, False, False, 0)
        self.b_go = Gtk.Button(label="Descargar"); self.b_go.get_style_context().add_class("go")
        self.b_go.connect("clicked", self.iniciar); fila.pack_start(self.b_go, True, True, 0)
        self.b_stop = Gtk.Button(label="Cancelar"); self.b_stop.get_style_context().add_class("stop")
        self.b_stop.set_sensitive(False); self.b_stop.connect("clicked", self.cancelar)
        fila.pack_start(self.b_stop, False, False, 0)

        self.barra = Gtk.ProgressBar(show_text=True, text="Listo para descargar")
        caja.pack_start(self.barra, False, False, 4)
        self.estado = Gtk.Label(label="", xalign=0); caja.pack_start(self.estado, False, False, 0)

        exp = Gtk.Expander(label="Detalles"); caja.pack_start(exp, True, True, 0)
        sw = Gtk.ScrolledWindow(); self.txt = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        sw.add(self.txt); exp.add(sw)

        fila = Gtk.Box(spacing=6); caja.pack_start(fila, False, False, 0)
        b = Gtk.Button(label="Abrir carpeta")
        b.connect("clicked", lambda *_: subprocess.Popen(["xdg-open", self.carpeta.get_filename()]))
        fila.pack_start(b, False, False, 0)
        b = Gtk.Button(label="Actualizar yt-dlp"); b.connect("clicked", self.actualizar)
        fila.pack_start(b, False, False, 0)
        self.pegar()

    # ---------- utilidades de interfaz ----------
    def ui(self, f, *a): GLib.idle_add(lambda: f(*a) and False)

    def log(self, t):
        def _():
            self.txt.get_buffer().insert(self.txt.get_buffer().get_end_iter(), t + "\n")
            self.txt.scroll_to_iter(self.txt.get_buffer().get_end_iter(), 0, False, 0, 0)
        self.ui(_)

    def poner(self, frac=None, texto=None, estado=None):
        def _():
            if frac is not None: self.barra.set_fraction(frac)
            if texto is not None: self.barra.set_text(texto)
            if estado is not None: self.estado.set_text(estado)
        self.ui(_)

    def pegar(self, *_):
        t = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
        if t and t.strip().startswith("http"): self.url.set_text(t.strip())

    def cambiar_modo(self, *_):
        modo = "video" if self.r_video.get_active() else "audio"
        self.fmt.remove_all()
        for f in FORMATOS[modo]: self.fmt.append_text(f)
        self.fmt.set_active(0)
        if hasattr(self, "cal"): self.cal.set_visible(modo == "video")

    def activar(self, descargando):
        self.ui(self.b_go.set_sensitive, not descargando)
        self.ui(self.b_stop.set_sensitive, descargando)

    # ---------- acciones ----------
    def iniciar(self, *_):
        url = self.url.get_text().strip()
        if not url.startswith("http"):
            self.poner(texto="Pega un link válido (empieza con http)"); return
        modo = "video" if self.r_video.get_active() else "audio"
        args = (url, modo, self.fmt.get_active_text(), self.cal.get_active_text(),
                self.carpeta.get_filename(), self.lista.get_active())
        self.cancelado = False; self.activar(True); self.barra.set_fraction(0)
        threading.Thread(target=self.trabajo, args=args, daemon=True).start()

    def cancelar(self, *_):
        self.cancelado = True
        if self.proc: self.proc.terminate()

    def trabajo(self, *args):
        try:
            self.poner(texto="Preparando...", estado="Comprobando herramientas")
            if not asegurar_herramientas(self.log):
                self.poner(texto="Falta ffmpeg", estado="Instálalo con: sudo apt install ffmpeg"); return
            ok = self.correr(armar_comando(*args))
            if ok:
                self.poner(1.0, "¡Listo!", "Descarga terminada")
                subprocess.run(["notify-send", "Descargador", "Descarga terminada"], check=False)
            elif self.cancelado:
                self.poner(texto="Cancelado", estado="")
            else:
                self.poner(texto="Falló", estado="Revisa 'Detalles' para ver el motivo")
        except Exception as e:
            self.log(f"Error: {e}"); self.poner(texto="Error", estado=str(e))
        finally:
            self.activar(False)

    def correr(self, cmd):
        for intento in range(1, 31):  # reintenta si se cae el internet; yt-dlp reanuda lo ya bajado
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, env=ENV, bufsize=1)
            falla_red = False
            for linea in self.proc.stdout:
                linea = linea.rstrip(); self.log(linea)
                m = re.search(r"\[download\]\s+([\d.]+)%", linea)
                if m:
                    v = re.search(r"at\s+(\S+)", linea); e = re.search(r"ETA\s+(\S+)", linea)
                    self.poner(float(m.group(1)) / 100, f"{m.group(1)}%",
                               f"Velocidad: {v.group(1) if v else '-'}   Quedan: {e.group(1) if e else '-'}")
                elif "[Merger]" in linea or "[ExtractAudio]" in linea:
                    self.poner(texto="Procesando archivo...", estado="Uniendo / convirtiendo")
                if any(k in linea for k in ERRORES_RED) and linea.startswith(("ERROR", "WARNING")):
                    falla_red = True
            self.proc.wait()
            if self.proc.returncode == 0: return True
            if self.cancelado or not falla_red: return False
            for s in range(8, 0, -1):  # espera 8 s y reintenta
                if self.cancelado: return False
                self.poner(estado=f"Sin conexión. Reintentando en {s}s (intento {intento})...")
                time.sleep(1)
        return False

    def actualizar(self, *_):
        def _():
            try:
                asegurar_herramientas(self.log)
                r = subprocess.run([shutil.which("yt-dlp", path=ENV["PATH"]), "-U"], env=ENV,
                                   capture_output=True, text=True)
                self.log(r.stdout + r.stderr); self.poner(estado="yt-dlp actualizado (ver Detalles)")
            except Exception as e:
                self.log(str(e))
        threading.Thread(target=_, daemon=True).start()


def instalar_en_menu():
    destino = os.path.expanduser("~/.local/share/descargador/descargador.py")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    try: shutil.copy(os.path.abspath(__file__), destino)
    except shutil.SameFileError: pass
    os.chmod(destino, 0o755)
    apps = os.path.expanduser("~/.local/share/applications"); os.makedirs(apps, exist_ok=True)
    with open(os.path.join(apps, "descargador.desktop"), "w") as f:
        f.write("[Desktop Entry]\nType=Application\nName=Descargador\n"
                "Comment=Descarga video y audio con yt-dlp\n"
                f'Exec=python3 "{destino}"\nIcon=folder-download\nTerminal=false\n'
                "Categories=AudioVideo;Network;\n")
    print("Listo: busca 'Descargador' en el menú de aplicaciones.")


if __name__ == "__main__":
    if "--instalar" in sys.argv:
        instalar_en_menu()
    else:
        w = App(); w.connect("destroy", Gtk.main_quit); w.show_all()
        w.cal.set_visible(w.r_video.get_active()); Gtk.main()
