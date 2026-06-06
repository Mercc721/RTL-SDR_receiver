import queue
import traceback
from rtlsdr import RtlSdr
from config import SDR_RATE, CHUNK_DURATION


class RadioEngine:
    """
    Moteur 1 : Capture USB (thread dédié).
    Lit les échantillons IQ depuis la clé RTL-SDR et les pousse
    dans une queue partagée avec AudioWorker.
    """

    def __init__(self, freq_mhz: float, audio_queue: queue.Queue,
                 power_flag: list, lcd_error_cb):
        """
        freq_mhz     : fréquence initiale en MHz
        audio_queue  : queue.Queue partagée avec AudioWorker
        power_flag   : liste à un élément [bool] — mutable, partagée entre threads
        lcd_error_cb : callable(text, color) pour afficher une erreur sur le LCD
        """
        self.freq_mhz     = freq_mhz
        self.audio_queue  = audio_queue
        self.power_flag   = power_flag   # [True] / [False]
        self.lcd_error_cb = lcd_error_cb
        self.sdr          = None

    # ── Propriété publique pour changer de fréquence à chaud ──
    def set_freq(self, freq_mhz: float):
        self.freq_mhz = freq_mhz
        if self.sdr:
            self.sdr.center_freq = int(freq_mhz * 1e6)

    def stop(self):
        if self.sdr:
            try:
                self.sdr.cancel_read_async()
            except Exception:
                pass

    # ── Point d'entrée du thread ──
    def run(self):
        try:
            self.sdr = RtlSdr()
            print("SDR INIT OK")
        except Exception as e:
            print("SDR INIT FAILED:", repr(e))
            traceback.print_exc()
            self.lcd_error_cb(f"SDR INIT ERROR\n{str(e)[:40]}", "red")
            self.power_flag[0] = False
            return

        try:
            self.sdr.sample_rate = SDR_RATE
            self.sdr.center_freq = int(self.freq_mhz * 1e6)
            self.sdr.gain        = 'auto'

            n = int(SDR_RATE * CHUNK_DURATION)

            def _cb(samples, _):
                if not self.power_flag[0]:
                    return
                try:
                    self.audio_queue.put_nowait(samples)
                except queue.Full:
                    pass   # on sacrifie ce bloc plutôt que de bloquer l'USB

            self.sdr.read_samples_async(_cb, n)   # bloque jusqu'à cancel_read_async

        except Exception as e:
            print("SDR ERROR:", e)
            self.lcd_error_cb("SDR ERROR", "red")
            self.power_flag[0] = False
        finally:
            try:
                self.sdr.close()
            except Exception:
                pass
