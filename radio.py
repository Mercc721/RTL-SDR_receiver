import tkinter as tk
import threading
import socket
import struct
import numpy as np
import scipy.signal as signal
import sounddevice as sd

# --- CONFIGURATION VISUELLE ---
C = {
    "bg": "#1E222A", "body": "#282C34", "screen_bg": "#0D1117",
    "lcd_off": "#1B221E", "lcd_on": "#39FF14", "btn": "#3E4451",
    "btn_active": "#528BFF", "btn_red": "#E06C75", "text": "#ABB2BF",
    "dark_text": "#282C34"
}

# --- PARAMÈTRES TECHNIQUES ---
HOST = '127.0.0.1'
PORT = 1234
SDR_RATE = 1152000     # Fréquence d'échantillonnage de la clé
AUDIO_RATE = 48000     # Fréquence de la carte son
DECIMATION = SDR_RATE // AUDIO_RATE
DUREE_CHUNK = 0.25     # Blocs de 250ms pour la fluidité

class RadioMedi1Pro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SDR Receiver - Medi1 Edition")
        self.geometry("900x550")
        self.configure(bg=C["bg"])
        self.resizable(False, False)

        # État interne
        self.power = False
        self.socket_radio = None
        self.freq_mhz = 100.0
        self.saisie_clavier = ""

        self.cv = tk.Canvas(self, width=900, height=550, bg=C["bg"], highlightthickness=0)
        self.cv.pack(pady=20)
        self._build_ui()

    def _build_ui(self):
        # Design du boîtier
        self._round_rect(20, 10, 880, 500, radius=60, fill=C["body"])
        self._round_rect(50, 40, 420, 220, radius=80, fill=C["screen_bg"])
        self.lcd_text = self.cv.create_text(235, 130, text="OFF", font=("Courier", 42, "bold"), fill=C["lcd_off"], justify=tk.CENTER)

        # Boutons de contrôle
        self._make_circle_btn(130, 310, 45, "16", C["btn"], C["text"], lambda: self._changer_freq(156.8))
        self._make_circle_btn(280, 310, 45, "PWR", C["btn_red"], "white", self._toggle_power)

        # Colonne centrale (Tuning fin)
        self._round_rect(460, 50, 540, 450, radius=40, fill="#343A46")
        self._make_circle_btn(500, 100, 25, "+1", "#21252B", C["text"], lambda: self._changer_freq(self.freq_mhz + 1.0))
        self._make_circle_btn(500, 180, 25, "+.1", "#21252B", C["text"], lambda: self._changer_freq(self.freq_mhz + 0.1))
        self._make_circle_btn(500, 260, 25, "-.1", "#21252B", C["text"], lambda: self._changer_freq(self.freq_mhz - 0.1))
        self._make_circle_btn(500, 340, 25, "-1", "#21252B", C["text"], lambda: self._changer_freq(self.freq_mhz - 1.0))

        # Pavé numérique
        self._round_rect(580, 180, 740, 450, radius=20, fill="#ABB2BF")
        touches = [('1', 615, 220), ('2', 660, 220), ('3', 705, 220), ('4', 615, 280), ('5', 660, 280), ('6', 705, 280),
                   ('7', 615, 340), ('8', 660, 340), ('9', 705, 340), ('C', 615, 400), ('0', 660, 400), ('E', 705, 400)]
        for txt, x, y in touches:
            self._make_text_btn(x, y, txt, lambda t=txt: self._action_numpad(t))

    # --- LOGIQUE D'INTERFACE ---
    def _action_numpad(self, touche):
        if not self.power: return
        if touche == 'C':
            self.saisie_clavier = ""
            self._maj_ecran()
        elif touche == 'E':
            if self.saisie_clavier:
                try:
                    f = float(self.saisie_clavier)
                    # Si on tape 975 -> 97.5 | Si on tape 97.5 -> 97.5
                    if 870 <= f <= 1080: f /= 10.0
                    self._changer_freq(f)
                except: pass
            self.saisie_clavier = ""
        else:
            self.saisie_clavier += touche
            self._maj_ecran(f"Freq?\n{self.saisie_clavier}")

    def _changer_freq(self, f):
        if not self.power: return
        self.freq_mhz = round(f, 3)
        self._maj_ecran()
        if self.socket_radio:
            freq_hz = int(self.freq_mhz * 1e6)
            try:
                self.socket_radio.sendall(struct.pack('>BI', 0x01, freq_hz))
            except: pass

    def _maj_ecran(self, msg=None):
        if not self.power: return
        txt = msg if msg else f"{self.freq_mhz:.3f} MHz\nFM"
        self.cv.itemconfig(self.lcd_text, text=txt)

    def _toggle_power(self):
        self.power = not self.power
        if self.power:
            self.cv.itemconfig(self.lcd_text, text="LOAD...", fill=C["lcd_on"])
            threading.Thread(target=self._moteur_radio, daemon=True).start()
        else:
            self.cv.itemconfig(self.lcd_text, text="OFF", fill=C["lcd_off"])
            if self.socket_radio: self.socket_radio.close()

    # --- MOTEUR DE TRAITEMENT DU SIGNAL ---
    def _moteur_radio(self):
        try:
            self.socket_radio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_radio.connect((HOST, PORT))
            self.socket_radio.recv(12) 
            self._changer_freq(self.freq_mhz)
            
            # Filtre Passe-Bas Audio à 15kHz (Anti-souffle)
            b, a = signal.butter(4, 15000/(AUDIO_RATE/2), btype='low')
            
            # Flux audio temps réel
            stream = sd.OutputStream(samplerate=AUDIO_RATE, channels=1, dtype='float32')
            stream.start()
            
            size = int(SDR_RATE * 2 * DUREE_CHUNK)
            self._maj_ecran()

            while self.power:
                raw = b''
                while len(raw) < size and self.power:
                    chunk = self.socket_radio.recv(size - len(raw))
                    if not chunk: break
                    raw += chunk
                
                if not self.power: break
                
                # Conversion & Démodulation
                data = np.frombuffer(raw, dtype=np.uint8) - 127.5
                iq = data[0::2] + 1j * data[1::2]
                
                # Démodulateur FM
                angle = np.angle(iq[1:] * np.conj(iq[:-1]))
                
                # Réduction de vitesse & Filtrage
                audio = signal.decimate(angle, DECIMATION, zero_phase=False)
                audio_clean = signal.lfilter(b, a, audio)
                
                # Amplification finale (x4 pour bien entendre Medi1)
                stream.write(np.float32(audio_clean * 4.0))

            stream.stop(); stream.close(); self.socket_radio.close()
        except Exception as e:
            self.power = False
            self.cv.itemconfig(self.lcd_text, text="SDR ERR", fill="red")

    # --- HELPERS DESSIN ---
    def _round_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        p = [x1+radius,y1, x2-radius,y1, x2,y1, x2,y1+radius, x2,y2-radius, x2,y2, x2-radius,y2, x1+radius,y2, x1,y2, x1,y2-radius, x1,y1+radius, x1,y1]
        return self.cv.create_polygon(p, smooth=True, **kwargs)

    def _make_circle_btn(self, x, y, r, txt, bg, fg, cmd):
        tag = f"b{x}{y}"
        ov = self.cv.create_oval(x-r, y-r, x+r, y+r, fill=bg, outline="", tags=tag)
        self.cv.create_text(x, y, text=txt, fill=fg, font=("Arial", 12, "bold"), tags=tag)
        self.cv.tag_bind(tag, "<ButtonPress-1>", lambda e: self.cv.itemconfig(ov, fill=C["btn_active"]))
        self.cv.tag_bind(tag, "<ButtonRelease-1>", lambda e: [self.cv.itemconfig(ov, fill=bg), cmd()])

    def _make_text_btn(self, x, y, txt, cmd):
        tag = f"n{x}{y}"
        t = self.cv.create_text(x, y, text=txt, fill=C["dark_text"], font=("Arial", 22, "bold"), tags=tag)
        self.cv.tag_bind(tag, "<ButtonPress-1>", lambda e: self.cv.itemconfig(t, fill=C["btn_active"]))
        self.cv.tag_bind(tag, "<ButtonRelease-1>", lambda e: [self.cv.itemconfig(t, fill=C["dark_text"]), cmd()])

if __name__ == "__main__":
    RadioMedi1Pro().mainloop()