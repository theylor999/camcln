"""
CamMic - Server (rode no notebook com a webcam)
Captura a webcam e transmite pela rede WiFi via MJPEG.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import socket
import cv2
from PIL import Image, ImageTk
from flask import Flask, Response
import queue

# ─── Flask MJPEG server ───────────────────────────────────────────────────────

app = Flask(__name__)
frame_queue = queue.Queue(maxsize=2)  # buffer mínimo para baixa latência


def generate_frames():
    while True:
        frame = frame_queue.get()
        if frame is None:
            break
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            continue
        data = buffer.tobytes()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + str(len(data)).encode() + b'\r\n\r\n'
            + data + b'\r\n'
        )


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ─── GUI ──────────────────────────────────────────────────────────────────────

class CamMicServer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CamMic — Servidor")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.cap = None
        self.streaming = False
        self.capture_thread = None
        self.flask_thread = None
        self.preview_active = True

        self._build_ui()
        self._detect_cameras()
        self._start_preview()
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
            header, text="CamMic — Servidor", font=("Segoe UI", 11),
            fg="#a6adc8", bg="#313244"
        ).pack(side="right", **pad)

        # Preview da webcam
        preview_frame = tk.Frame(self.root, bg="#1e1e2e")
        preview_frame.pack(padx=12, pady=(10, 4))
        self.preview_label = tk.Label(
            preview_frame, bg="#11111b", width=640, height=480
        )
        self.preview_label.pack()

        # Controles
        ctrl = tk.Frame(self.root, bg="#1e1e2e")
        ctrl.pack(fill="x", padx=12, pady=6)

        # Câmera selector
        tk.Label(ctrl, text="Câmera:", fg="#cdd6f4", bg="#1e1e2e",
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=4)
        self.cam_var = tk.StringVar()
        self.cam_combo = ttk.Combobox(ctrl, textvariable=self.cam_var,
                                      state="readonly", width=30)
        self.cam_combo.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="w")
        self.cam_combo.bind("<<ComboboxSelected>>", self._on_camera_change)

        # IP info
        ip = get_local_ip()
        self.port = 5000
        tk.Label(ctrl, text="Endereço:", fg="#cdd6f4", bg="#1e1e2e",
                 font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=4)
        self.ip_label = tk.Label(
            ctrl,
            text=f"http://{ip}:{self.port}/video_feed",
            fg="#a6e3a1", bg="#1e1e2e", font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        self.ip_label.grid(row=1, column=1, padx=(6, 0), pady=4, sticky="w")

        # Botão copiar IP
        copy_btn = tk.Button(
            ctrl, text="Copiar", bg="#45475a", fg="#cdd6f4",
            relief="flat", font=("Segoe UI", 9),
            command=lambda: self._copy_to_clipboard(f"{ip}:{self.port}")
        )
        copy_btn.grid(row=1, column=2, padx=(6, 0))

        # Status
        self.status_var = tk.StringVar(value="Aguardando...")
        tk.Label(ctrl, textvariable=self.status_var, fg="#f38ba8",
                 bg="#1e1e2e", font=("Segoe UI", 9)).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=4)

        # Botão Iniciar/Parar
        btn_frame = tk.Frame(self.root, bg="#1e1e2e")
        btn_frame.pack(pady=(0, 12))
        self.toggle_btn = tk.Button(
            btn_frame, text="▶  Iniciar Stream",
            font=("Segoe UI", 11, "bold"),
            bg="#a6e3a1", fg="#1e1e2e", relief="flat",
            padx=20, pady=8,
            command=self._toggle_stream
        )
        self.toggle_btn.pack()

    # ── Câmeras ───────────────────────────────────────────────────────────────

    def _detect_cameras(self):
        cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                cameras.append(f"Câmera {i}")
                cap.release()
        if not cameras:
            cameras = ["Câmera 0"]
        self.cam_combo["values"] = cameras
        self.cam_combo.current(0)
        self._open_camera(0)

    def _open_camera(self, idx):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    def _on_camera_change(self, _event=None):
        idx = self.cam_combo.current()
        self._open_camera(idx)

    # ── Preview ───────────────────────────────────────────────────────────────

    def _start_preview(self):
        self._update_preview()

    def _update_preview(self):
        if not self.preview_active:
            return
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Alimenta o stream MJPEG se estiver ativo
                if self.streaming:
                    try:
                        frame_queue.put_nowait(frame.copy())
                    except queue.Full:
                        try:
                            frame_queue.get_nowait()
                            frame_queue.put_nowait(frame.copy())
                        except Exception:
                            pass

                # Exibe no preview GUI
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                img = img.resize((640, 480), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=photo)
                self.preview_label.image = photo

        self.root.after(33, self._update_preview)  # ~30fps

    # ── Stream ────────────────────────────────────────────────────────────────

    def _toggle_stream(self):
        if not self.streaming:
            self._start_stream()
        else:
            self._stop_stream()

    def _start_stream(self):
        if self.flask_thread is None or not self.flask_thread.is_alive():
            self.flask_thread = threading.Thread(
                target=lambda: app.run(host="0.0.0.0", port=self.port,
                                       debug=False, use_reloader=False),
                daemon=True
            )
            self.flask_thread.start()

        self.streaming = True
        self.status_var.set("Transmitindo — aguardando conexão do cliente...")
        self.toggle_btn.configure(
            text="■  Parar Stream", bg="#f38ba8", fg="#1e1e2e"
        )

    def _stop_stream(self):
        self.streaming = False
        # Drena a fila
        while not frame_queue.empty():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                break
        self.status_var.set("Stream parado.")
        self.toggle_btn.configure(
            text="▶  Iniciar Stream", bg="#a6e3a1", fg="#1e1e2e"
        )

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("IP copiado!")
        self.root.after(2000, lambda: self.status_var.set(
            "Transmitindo..." if self.streaming else "Aguardando..."))

    def _on_close(self):
        self.preview_active = False
        self.streaming = False
        if self.cap:
            self.cap.release()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    CamMicServer().run()
