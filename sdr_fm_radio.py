import queue
import tkinter as tk
import threading

from config import FM_MIN, FM_MAX, C
from radio_engine import RadioEngine
from audio_worker import AudioWorker


class SDR_FM_Radio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SDR FM Radio")
        self.geometry("900x550")
        self.configure(bg=C["bg"])
        self.resizable(False, False)

        self.freq_mhz  = 88.0
        self.key_input = ""

        # power_flag : liste à un élément pour être mutable et partageable entre threads
        self._power_flag   = [False]
        self._radio_engine = None

        self.cv = tk.Canvas(self, width=900, height=550,
                            bg=C["bg"], highlightthickness=0)
        self.cv.pack()
        self._build_ui()

    # ─────────────────────── PROPRIÉTÉ POWER ───────────────────────
    @property
    def power(self):
        return self._power_flag[0]

    @power.setter
    def power(self, value):
        self._power_flag[0] = value

    # ─────────────────────── UI ───────────────────────
    def _build_ui(self):
        self._round_rect(20, 10, 880, 500, 60, fill=C["body"])
        self._round_rect(50, 40, 420, 220, 80, fill=C["screen_bg"])

        self.lcd = self.cv.create_text(
            235, 130, text="OFF",
            font=("Courier", 42, "bold"),
            fill=C["lcd_off"], justify=tk.CENTER
        )

        self._make_circle_btn(130, 310, 45, "FM",  C["btn"],     C["text"], lambda: self._set_freq(100.0))
        self._make_circle_btn(280, 310, 45, "PWR", C["btn_red"], "white",   self._toggle_power)

        self._round_rect(460, 50, 540, 450, 40, fill="#343A46")
        self._make_circle_btn(500, 100, 25, "+1",  "#21252B", C["text"], lambda: self._set_freq(self.freq_mhz + 1))
        self._make_circle_btn(500, 180, 25, "+.1", "#21252B", C["text"], lambda: self._set_freq(self.freq_mhz + 0.1))
        self._make_circle_btn(500, 260, 25, "-.1", "#21252B", C["text"], lambda: self._set_freq(self.freq_mhz - 0.1))
        self._make_circle_btn(500, 340, 25, "-1",  "#21252B", C["text"], lambda: self._set_freq(self.freq_mhz - 1))

        self._round_rect(580, 180, 740, 450, 20, fill="#ABB2BF")
        keys = [
            ('1',615,220), ('2',660,220), ('3',705,220),
            ('4',615,280), ('5',660,280), ('6',705,280),
            ('7',615,340), ('8',660,340), ('9',705,340),
            ('C',615,400), ('0',660,400), ('E',705,400)
        ]
        for t, x, y in keys:
            self._make_text_btn(x, y, t, lambda k=t: self._keypad(k))

    # ─────────────────────── LOGIQUE ───────────────────────
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
                    if len(raw) in (3, 4): f = float(raw) / 10
                    elif len(raw) == 6:    f = float(raw) / 1000
                    else:                  f = float(raw)
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
        f = round(f, 3)
        if not (FM_MIN <= f <= FM_MAX):
            return
        self.freq_mhz = f
        self._update_screen()
        if self._radio_engine:
            self._radio_engine.set_freq(f)

    def _update_screen(self, txt=None):
        if not self.power:
            return
        self.cv.itemconfig(
            self.lcd,
            text=txt if txt else f"{self.freq_mhz:.3f} MHz\nFM RADIO",
            fill=C["lcd_on"]
        )

    def _lcd_error(self, text, color="red"):
        """Callback passé aux moteurs pour afficher les erreurs."""
        self.cv.itemconfig(self.lcd, text=text, fill=color)

    def _toggle_power(self):
        if not self.power:
            self.power = True
            audio_queue = queue.Queue(maxsize=10)

            self.cv.itemconfig(self.lcd, text="SDR CONNECT...", fill=C["lcd_on"])

            self._radio_engine = RadioEngine(
                freq_mhz   = self.freq_mhz,
                audio_queue= audio_queue,
                power_flag = self._power_flag,
                lcd_error_cb = self._lcd_error
            )
            audio_engine = AudioWorker(
                audio_queue  = audio_queue,
                power_flag   = self._power_flag,
                lcd_error_cb = self._lcd_error
            )

            threading.Thread(target=self._radio_engine.run, daemon=True).start()
            threading.Thread(target=audio_engine.run,       daemon=True).start()
        else:
            self.power = False
            if self._radio_engine:
                self._radio_engine.stop()
            self.cv.itemconfig(self.lcd, text="OFF", fill=C["lcd_off"])

    # ─────────────────────── DRAW HELPERS ───────────────────────
    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        p = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
             x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        return self.cv.create_polygon(p, smooth=True, **kw)

    def _make_circle_btn(self, x, y, r, t, bg, fg, cmd):
        tag = f"b{x}{y}"
        o = self.cv.create_oval(x-r, y-r, x+r, y+r, fill=bg, outline="", tags=tag)
        self.cv.create_text(x, y, text=t, fill=fg, font=("Arial", 12, "bold"), tags=tag)
        self.cv.tag_bind(tag, "<ButtonPress-1>",
                         lambda e: self.cv.itemconfig(o, fill=C["btn_active"]))
        self.cv.tag_bind(tag, "<ButtonRelease-1>",
                         lambda e: (self.cv.itemconfig(o, fill=bg), cmd()))

    def _make_text_btn(self, x, y, t, cmd):
        tag = f"n{x}{y}"
        txt = self.cv.create_text(x, y, text=t, fill=C["dark_text"],
                                  font=("Arial", 22, "bold"), tags=tag)
        self.cv.tag_bind(tag, "<ButtonPress-1>",
                         lambda e: self.cv.itemconfig(txt, fill=C["btn_active"]))
        self.cv.tag_bind(tag, "<ButtonRelease-1>",
                         lambda e: (self.cv.itemconfig(txt, fill=C["dark_text"]), cmd()))
