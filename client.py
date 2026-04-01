"""
CamMic - Client (rode no PC do Discord)
Recebe o stream do notebook e disponibiliza como câmera virtual.

Pré-requisito: OBS Studio instalado (cria o driver de câmera virtual).
  → https://obsproject.com/
"""

import tkinter as tk
from tkinter import messagebox
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import requests

try:
    import pyvirtualcam
    VIRTUALCAM_AVAILABLE = True
except ImportError:
    VIRTUALCAM_AVAILABLE = False


# ─── Constantes ───────────────────────────────────────────────────────────────

DEFAULT_PORT = 5000
FRAME_W, FRAME_H = 640, 480


# ─── GUI ──────────────────────────────────────────────────────────────────────

class CamMicClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CamMic — Cliente")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.connected = False
        self.stream_thread = None
        self._stop_event = threading.Event()
        self._virtualcam = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # Cabeçalho
        header = tk.Frame(self.root, bg="#313244")
        header.pack(fill="x")
        tk.Label(
            header, text="Olá Theylor,", font=("Segoe UI", 13, "bold"),
            fg="#cdd6f4", bg="#313244"
        ).pack(side="left", **pad)
        tk.Label(
            header, text="CamMic — Cliente", font=("Segoe UI", 11),
            fg="#a6adc8", bg="#313244"
        ).pack(side="right", **pad)

        # Preview pequeno
        preview_frame = tk.Frame(self.root, bg="#1e1e2e")
        preview_frame.pack(padx=12, pady=(10, 4))
        self.preview_label = tk.Label(
            preview_frame, bg="#11111b",
            text="Sem sinal", fg="#585b70", font=("Segoe UI", 10)
        )
        self.preview_label.pack()
        # força tamanho em pixels via place trick
        self.preview_label.config(width=1, height=1)
        preview_frame.config(width=320, height=180)
        preview_frame.pack_propagate(False)

        # Controles
        ctrl = tk.Frame(self.root, bg="#1e1e2e")
        ctrl.pack(fill="x", padx=12, pady=6)

        tk.Label(ctrl, text="IP do Notebook:", fg="#cdd6f4", bg="#1e1e2e",
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=4)
        self.ip_entry = tk.Entry(ctrl, font=("Segoe UI", 11), width=20,
                                 bg="#313244", fg="#cdd6f4",
                                 insertbackground="#cdd6f4", relief="flat")
        self.ip_entry.insert(0, "192.168.1.")
        self.ip_entry.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="w")

        tk.Label(ctrl, text="Porta:", fg="#cdd6f4", bg="#1e1e2e",
                 font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w",
                                              padx=(12, 0), pady=4)
        self.port_entry = tk.Entry(ctrl, font=("Segoe UI", 11), width=6,
                                   bg="#313244", fg="#cdd6f4",
                                   insertbackground="#cdd6f4", relief="flat")
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.grid(row=0, column=3, padx=(6, 0), pady=4, sticky="w")

        # Câmera virtual status
        vcam_ok = "✓ pyvirtualcam disponível" if VIRTUALCAM_AVAILABLE \
            else "✗ pyvirtualcam não instalado (instale OBS + pip install pyvirtualcam)"
        vcam_color = "#a6e3a1" if VIRTUALCAM_AVAILABLE else "#f38ba8"
        tk.Label(ctrl, text=vcam_ok, fg=vcam_color, bg="#1e1e2e",
                 font=("Segoe UI", 9)).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=2)

        # Status geral
        self.status_var = tk.StringVar(value="Desconectado.")
        tk.Label(ctrl, textvariable=self.status_var, fg="#89b4fa",
                 bg="#1e1e2e", font=("Segoe UI", 9)).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=4)

        # Câmera virtual label quando ativa
        self.vcam_status_var = tk.StringVar(value="")
        tk.Label(ctrl, textvariable=self.vcam_status_var, fg="#a6e3a1",
                 bg="#1e1e2e", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, columnspan=4, sticky="w")

        # Botão conectar
        btn_frame = tk.Frame(self.root, bg="#1e1e2e")
        btn_frame.pack(pady=(0, 12))
        self.toggle_btn = tk.Button(
            btn_frame, text="▶  Conectar",
            font=("Segoe UI", 11, "bold"),
            bg="#89b4fa", fg="#1e1e2e", relief="flat",
            padx=20, pady=8,
            command=self._toggle_connection
        )
        self.toggle_btn.pack()

    # ── Conexão ───────────────────────────────────────────────────────────────

    def _toggle_connection(self):
        if not self.connected:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        if not ip:
            messagebox.showwarning("CamMic", "Digite o IP do notebook.")
            return

        url = f"http://{ip}:{port}/video_feed"
        self._stop_event.clear()
        self.connected = True

        self.toggle_btn.configure(text="■  Desconectar", bg="#f38ba8", fg="#1e1e2e")
        self.status_var.set(f"Conectando em {url} ...")
        self.ip_entry.configure(state="disabled")
        self.port_entry.configure(state="disabled")

        self.stream_thread = threading.Thread(
            target=self._stream_loop, args=(url,), daemon=True
        )
        self.stream_thread.start()

    def _disconnect(self):
        self._stop_event.set()
        self.connected = False
        self.toggle_btn.configure(text="▶  Conectar", bg="#89b4fa", fg="#1e1e2e")
        self.status_var.set("Desconectado.")
        self.vcam_status_var.set("")
        self.ip_entry.configure(state="normal")
        self.port_entry.configure(state="normal")
        self.preview_label.configure(image="", text="Sem sinal",
                                     fg="#585b70", font=("Segoe UI", 14))

    # ── Loop de stream ────────────────────────────────────────────────────────

    def _stream_loop(self, url):
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
        except Exception as e:
            self._set_status(f"Erro ao conectar: {e}")
            self._schedule(self._disconnect)
            return

        self._set_status("Conectado! Recebendo frames...")

        vcam = None
        if VIRTUALCAM_AVAILABLE:
            try:
                vcam = pyvirtualcam.Camera(
                    width=FRAME_W, height=FRAME_H, fps=30,
                    fmt=pyvirtualcam.PixelFormat.RGB
                )
                self._set_vcam_status(f"Câmera virtual ativa: \"{vcam.device}\" — selecione no Discord!")
            except Exception as e:
                self._set_vcam_status(f"Câmera virtual indisponível: {e}")

        try:
            boundary = b'--frame'
            raw = response.raw
            buf = b""

            while not self._stop_event.is_set():
                chunk = raw.read(4096)
                if not chunk:
                    break
                buf += chunk

                # Procura pares de imagem JPEG dentro do buffer
                while True:
                    start = buf.find(b'\xff\xd8')  # SOI JPEG
                    end = buf.find(b'\xff\xd9')    # EOI JPEG
                    if start == -1 or end == -1 or end <= start:
                        break

                    jpeg_data = buf[start:end + 2]
                    buf = buf[end + 2:]

                    frame_array = np.frombuffer(jpeg_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Câmera virtual
                    if vcam is not None:
                        try:
                            vcam.send(rgb)
                            vcam.sleep_until_next_frame()
                        except Exception:
                            pass

                    # Preview GUI reduzido (via root.after para thread safety)
                    small = cv2.resize(frame, (320, 180))
                    small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                    self._schedule(lambda f=small_rgb: self._update_preview(f))

        except Exception as e:
            if not self._stop_event.is_set():
                self._set_status(f"Conexão perdida: {e}")
        finally:
            if vcam is not None:
                try:
                    vcam.close()
                except Exception:
                    pass
            self._set_vcam_status("")
            if not self._stop_event.is_set():
                self._schedule(self._disconnect)

    # ── Preview ───────────────────────────────────────────────────────────────

    def _update_preview(self, rgb_frame):
        img = Image.fromarray(rgb_frame)
        img = img.resize((320, 180), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=photo, text="")
        self.preview_label.image = photo  # evita garbage collection

    # ── Helpers thread-safe ───────────────────────────────────────────────────

    def _schedule(self, fn):
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def _set_status(self, msg):
        self._schedule(lambda: self.status_var.set(msg))

    def _set_vcam_status(self, msg):
        self._schedule(lambda: self.vcam_status_var.set(msg))

    # ── Fechar ────────────────────────────────────────────────────────────────

    def _on_close(self):
        self._stop_event.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    CamMicClient().run()
