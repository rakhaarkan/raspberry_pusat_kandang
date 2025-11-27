from BlynkLib import Blynk

BLYNK_AUTH = "Wl380IhMybLGDKPaG88Cg5Lvva7ylU7j"

blynk = Blynk(BLYNK_AUTH)

while True:
    blynk.run()

import time
import threading

# ======================================================
# KONFIGURASI BLYNK
# ======================================================

BLYNK_TEMPLATE_ID = "TMPL6FMUyY7XQ"
BLYNK_TEMPLATE_NAME = "Kipas Kandang Ayam"
BLYNK_AUTH = "Wl380IhMybLGDKPaG88Cg5Lvva7ylU7j"

# Inisialisasi Blynk
blynk = blynklib.Blynk(BLYNK_AUTH)


# ======================================================
# CALLBACK UNTUK MENERIMA DATA DARI BLYNK
# ======================================================

# Contoh V0 menerima mode kandang
@blynk.on("V0")
def v0_write(value):
    print("Mode kandang dari Blynk:", value[0])
    # tinggal masukkan ke variabel global kamu
    # gl.mode_kandang = int(value[0])

# Contoh V1-V5 untuk 5 kipas
@blynk.on("V1")
def v1_write(value):
    print("Kipas 1:", value[0])

@blynk.on("V2")
def v2_write(value):
    print("Kipas 2:", value[0])

@blynk.on("V3")
def v3_write(value):
    print("Kipas 3:", value[0])

@blynk.on("V4")
def v4_write(value):
    print("Kipas 4:", value[0])

@blynk.on("V5")
def v5_write(value):
    print("Kipas 5:", value[0])

# ======================================================
# FUNGSI UNTUK MENGIRIM DATA KE BLYNK
# ======================================================

def update_kipas_status(kipas_list):
    """kirim status kipas [0,1,0,1,0]"""
    for i, state in enumerate(kipas_list):
        blynk.virtual_write(i + 1, state)

def update_mode(mode):
    """kirim mode (manual/otomatis/timer)"""
    blynk.virtual_write(0, mode)

def send_temperature(temp):
    """Contoh kirim suhu ke V10"""
    blynk.virtual_write(10, temp)

# ======================================================
# PROSES BLYNK LOOP (HARUS JALAN TERUS)
# ======================================================

def _run_blynk():
    while True:
        blynk.run()
        time.sleep(0.01)

# Start thread Blynk
threading.Thread(target=_run_blynk, daemon=True).start()

print("Blynk sudah berjalan di background...")
