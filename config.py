# ================== CONFIG ==================
SDR_RATE       = 1_152_000   # RTL-SDR sample rate
AUDIO_RATE     = 48_000      # Sound card rate
DECIMATION     = SDR_RATE // AUDIO_RATE
CHUNK_DURATION = 0.05        # seconds

FM_MIN = 87.5
FM_MAX = 170.0               # allow marine/VHF tuning like 156.800 MHz
VOLUME = 0.8

# ================== COLORS ==================
C = {
    "bg":        "#1E222A",
    "body":      "#282C34",
    "screen_bg": "#0D1117",
    "lcd_off":   "#1B221E",
    "lcd_on":    "#39FF14",
    "btn":       "#3E4451",
    "btn_active":"#528BFF",
    "btn_red":   "#E06C75",
    "text":      "#ABB2BF",
    "dark_text": "#282C34"
}
