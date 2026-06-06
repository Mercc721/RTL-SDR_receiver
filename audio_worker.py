import queue
import numpy as np
import scipy.signal as signal
import sounddevice as sd
from config import SDR_RATE, AUDIO_RATE, CHUNK_DURATION, VOLUME


class AudioWorker:
    """
    Moteur 2 : DSP + carte son (thread dédié).
    Récupère les blocs IQ dans la queue, démodule FM et joue l'audio.
    """

    SQUELCH_THRESHOLD = 0.02

    def __init__(self, audio_queue: queue.Queue, power_flag: list, lcd_error_cb):
        """
        audio_queue  : queue.Queue partagée avec RadioEngine
        power_flag   : liste à un élément [bool]
        lcd_error_cb : callable(text, color) pour afficher une erreur sur le LCD
        """
        self.audio_queue  = audio_queue
        self.power_flag   = power_flag
        self.lcd_error_cb = lcd_error_cb
        self.stream       = None

    # ── Préparation des filtres ──────────────────────────────────────────────
    @staticmethod
    def _build_filters():
        b_audio, a_audio = signal.butter(5, 12_000 / (AUDIO_RATE / 2), 'low')
        b_de,    a_de    = signal.butter(1,  3_000 / (AUDIO_RATE / 2), 'low')
        b_hp,    a_hp    = signal.butter(2,     50 / (AUDIO_RATE / 2), 'high')
        return (b_audio, a_audio), (b_de, a_de), (b_hp, a_hp)

    # ── Démodulation FM ──────────────────────────────────────────────────────
    @staticmethod
    def _demodulate(samples):
        samples = samples - np.mean(samples)
        fm = np.angle(samples[1:] * np.conj(samples[:-1]))
        return fm - np.mean(fm)

    # ── Point d'entrée du thread ─────────────────────────────────────────────
    def run(self):
        try:
            (b_audio, a_audio), (b_de, a_de), (b_hp, a_hp) = self._build_filters()

            self.stream = sd.OutputStream(
                samplerate=AUDIO_RATE,
                channels=1,
                dtype='float32'
            )
            self.stream.start()

            while self.power_flag[0]:
                try:
                    samples = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Squelch — silence si pas de station
                if np.mean(np.abs(samples)) < self.SQUELCH_THRESHOLD:
                    silence = np.zeros(int(AUDIO_RATE * CHUNK_DURATION), dtype=np.float32)
                    self.stream.write(silence)
                    continue

                # DSP
                fm    = self._demodulate(samples)
                audio = signal.resample_poly(fm, AUDIO_RATE, SDR_RATE)
                audio = signal.lfilter(b_audio, a_audio, audio)
                audio = signal.lfilter(b_de,    a_de,    audio)
                audio = signal.lfilter(b_hp,    a_hp,    audio)
                audio = np.clip(audio * 2.0, -1.0, 1.0)

                self.stream.write(np.float32(audio * VOLUME))

        except Exception as e:
            print("AUDIO ERROR:", e)
            self.lcd_error_cb("AUDIO ERROR", "red")
            self.power_flag[0] = False
        finally:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
