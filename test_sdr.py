from rtlsdr import RtlSdr

sdr = RtlSdr()

print(" SDR détecté ")
print("Fréquence par défaut:", sdr.center_freq)
print("Taux d'échantillonnage:", sdr.sample_rate)

sdr.close()