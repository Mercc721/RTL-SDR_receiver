import tkinter as tk
import threading
import numpy as np
import scipy.signal as signal
import sounddevice as sd
from rtlsdr import RtlSdr

# ================== CONFIG ==================
SDR_RATE = 1_152_000      # RTL-SDR sample rate
AUDIO_RATE = 48_000       # Sound card rate
DECIMATION = SDR_RATE // AUDIO_RATE
CHUNK_DURATION = 0.25     # seconds

FM_MIN = 87.5
FM_MAX = 170.0      # allow marine/VHF tuning like 156.800 MHz
VOLUME = 2.5

# ================== COLORS ==================
C = {
    "bg": "#1E222A",
    "body": "#282C34",
    "screen_bg": "#0D1117",
    "lcd_off": "#1B221E",
    "lcd_on": "#39FF14",
    "btn": "#3E4451",
    "btn_active": "#528BFF",
    "btn_red": "#E06C75",
    "text": "#ABB2BF",
    "dark_text": "#282C34"
}

# ============================================================
class SDR_FM_Radio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SDR FM Radio (Direct RTL-SDR)")
        self.geometry("900x550")
        self.configure(bg=C["bg"])
        self.resizable(False, False)

        self.power = False
        self.freq_mhz = 100.0
        self.key_input = ""

        self.sdr = None
        self.stream = None

        self.cv = tk.Canvas(self, width=900, height=550, bg=C["bg"], highlightthickness=0)
        self.cv.pack()
        self._build_ui()

    # ================= UI =================
    def _build_ui(self):
        self._round_rect(20, 10, 880, 500, 60, fill=C["body"])
        self._round_rect(50, 40, 420, 220, 80, fill=C["screen_bg"])

        self.lcd = self.cv.create_text(
            235, 130, text="OFF",
            font=("Courier", 42, "bold"),
            fill=C["lcd_off"],
            justify=tk.CENTER
        )

        self._make_circle_btn(130, 310, 45, "FM", C["btn"], C["text"],
                              lambda: self._set_freq(100.0))
        self._make_circle_btn(280, 310, 45, "PWR", C["btn_red"], "white",
                              self._toggle_power)

        self._round_rect(460, 50, 540, 450, 40, fill="#343A46")
        self._make_circle_btn(500, 100, 25, "+1", "#21252B", C["text"],
                              lambda: self._set_freq(self.freq_mhz + 1))
        self._make_circle_btn(500, 180, 25, "+.1", "#21252B", C["text"],
                              lambda: self._set_freq(self.freq_mhz + 0.1))
        self._make_circle_btn(500, 260, 25, "-.1", "#21252B", C["text"],
                              lambda: self._set_freq(self.freq_mhz - 0.1))
        self._make_circle_btn(500, 340, 25, "-1", "#21252B", C["text"],
                              lambda: self._set_freq(self.freq_mhz - 1))

        self._round_rect(580, 180, 740, 450, 20, fill="#ABB2BF")
        keys = [
            ('1',615,220), ('2',660,220), ('3',705,220),
            ('4',615,280), ('5',660,280), ('6',705,280),
            ('7',615,340), ('8',660,340), ('9',705,340),
            ('C',615,400), ('0',660,400), ('E',705,400)
        ]
        for t,x,y in keys:
            self._make_text_btn(x,y,t,lambda k=t:self._keypad(k))

    # ================= LOGIC =================
    def _keypad(self, k):
        if not self.power:
            return
        if k == 'C':
            self.key_input = ""
            self._update_screen()
        elif k == 'E':
            try:
                raw = self.key_input.strip()
                if not raw:
                    raise ValueError
                if raw.isdigit():
                    if len(raw) in (3, 4):
                        f = float(raw) / 10
                    elif len(raw) == 6:
                        f = float(raw) / 1000
                    else:
                        f = float(raw)
                else:
                    f = float(raw)
                self._set_freq(f)
            except Exception:
                pass
            self.key_input = ""
        else:
            self.key_input += k
            self._update_screen(f"SET FREQ\n{self.key_input}")

    def _set_freq(self, f):
        if not self.power:
            return
        if not (FM_MIN <= f <= FM_MAX):
            return

        self.freq_mhz = round(f, 3)
        self._update_screen()

        if self.sdr:
            self.sdr.center_freq = self.freq_mhz * 1e6

    def _update_screen(self, txt=None):
        if not self.power:
            return
        self.cv.itemconfig(
            self.lcd,
            text=txt if txt else f"{self.freq_mhz:.3f} MHz\nFM RADIO",
            fill=C["lcd_on"]
        )

    def _toggle_power(self):
        self.power = not self.power
        if self.power:
            self.cv.itemconfig(self.lcd, text="SDR CONNECT...", fill=C["lcd_on"])
            threading.Thread(target=self._radio_engine, daemon=True).start()
        else:
            self.power = False
            if self.sdr:
                self.sdr.close()
            if self.stream:
                self.stream.stop()
                self.stream.close()
            self.cv.itemconfig(self.lcd, text="OFF", fill=C["lcd_off"])

    # ================= SDR ENGINE =================
    def _radio_engine(self):
        try:
            self.sdr = RtlSdr()
            self.sdr.sample_rate = SDR_RATE
            self.sdr.center_freq = self.freq_mhz * 1e6
            self.sdr.gain = 'auto'

            b,a = signal.butter(4, 15000/(AUDIO_RATE/2), 'low')
            self.stream = sd.OutputStream(
                samplerate=AUDIO_RATE,
                channels=1,
                dtype='float32'
            )
            self.stream.start()
            self._update_screen()

            n = int(SDR_RATE * CHUNK_DURATION)

            while self.power:
                samples = self.sdr.read_samples(n)
                fm = np.angle(samples[1:] * np.conj(samples[:-1]))
                audio = signal.decimate(fm, DECIMATION, zero_phase=False)
                audio = signal.lfilter(b,a,audio)
                self.stream.write(np.float32(audio * VOLUME))

        except Exception as e:
            self.cv.itemconfig(self.lcd, text="SDR ERROR", fill="red")
            self.power = False

    # ================= DRAW HELPERS =================
    def _round_rect(self, x1,y1,x2,y2,r, **kw):
        p=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
           x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        return self.cv.create_polygon(p,smooth=True,**kw)

    def _make_circle_btn(self,x,y,r,t,bg,fg,cmd):
        tag=f"b{x}{y}"
        o=self.cv.create_oval(x-r,y-r,x+r,y+r,fill=bg,outline="",tags=tag)
        self.cv.create_text(x,y,text=t,fill=fg,font=("Arial",12,"bold"),tags=tag)
        self.cv.tag_bind(tag,"<ButtonPress-1>",
                         lambda e:self.cv.itemconfig(o,fill=C["btn_active"]))
        self.cv.tag_bind(tag,"<ButtonRelease-1>",
                         lambda e:(self.cv.itemconfig(o,fill=bg),cmd()))

    def _make_text_btn(self,x,y,t,cmd):
        tag=f"n{x}{y}"
        txt=self.cv.create_text(x,y,text=t,fill=C["dark_text"],
                                font=("Arial",22,"bold"),tags=tag)
        self.cv.tag_bind(tag,"<ButtonPress-1>",
                         lambda e:self.cv.itemconfig(txt,fill=C["btn_active"]))
        self.cv.tag_bind(tag,"<ButtonRelease-1>",
                         lambda e:(self.cv.itemconfig(txt,fill=C["dark_text"]),cmd()))

# ============================================================
if __name__ == "__main__":
    SDR_FM_Radio().mainloop()