from variabel_global import gl
import asyncio,time,serial,json
from penyimpanan_data import simpan_data, muat_data, LOCK_FILE
import thingspeak as thg
import fungsi_umum as fu
import database_sqlite as ds
import time
import joblib # Change import from pickle to joblib
import pandas as pd
import aktuator_kipas as ak


# Muat model
model = joblib.load("model_kandang.pkl") # Use joblib.load to load the model

#from util_math import map_range, constrain

wkt_kps = 0
LOCK_TIMER = asyncio.Lock()

def map_range(x, in_min, in_max, out_min, out_max):
   return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def constrain(val, min_val, max_val):
    return max(min_val, min(max_val, val))

# kirim_json_kipas() dan kirim_http_kipas_backup() sudah dipindah ke
# aktuator_kipas.py (sebagai _kirim_via_serial / _kirim_via_http), sekalian
# dibetulkan: key JSON "tanaman" -> "stn" (cocok firmware) dan IP HTTP
# fallback yang tadinya salah ketik (.150 -> .155, device kipas yang benar).

async def wajib_hidup(*args):
    """Menerima 5 argumen boolean (1 kipas = 1 argumen)"""
    async with gl.lock_kipas:
        for i, wajib in enumerate(args):
            if wajib:
                gl.kipas[i] = True
    print(f"Wajib hidup: {args}")
    await asyncio.sleep(0)

async def saklar_kipas(k1, k2, k3, k4, k5):
    """Atur status 5 kipas (1=ON, 0=OFF)"""

    new_state = [k1, k2, k3, k4, k5]

    # Proteksi listrik dulu sebelum commit
    if gl.cek_proteksi_listrik == 1:
        if all(new_state):
            new_state[2] = 0

    # Cek perubahan
    if gl.kipas == new_state:
        return  # Tidak ada perubahan → tidak perlu apa-apa

    # Commit state
    gl.kipas = new_state
    gl.status_relay = new_state.copy()

    # Kirim ke device lewat rantai prioritas: Modbus (primer) -> Serial -> HTTP
    hasil = await ak.kirim_perintah_kipas(new_state)
    if not hasil["berhasil"]:
        print("[saklar_kipas] PERINGATAN: semua channel gagal, kipas fisik mungkin tidak berubah!")

    # Simpan
    simpan_data()

    # Broadcast
    fu.broadcastkan()

def getWaktuSetelahDetik(detik):
    t = time.localtime(time.time() + detik)
    return f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

async def timer_kipas():
    """Kontrol kipas otomatis (mode timer), berhenti otomatis jika mode kandang berubah."""
    if gl.mode_kandang not in (1, 3, 4):
        return
    print("Mode TIMER aktif")
    gl.status_timer = 1
    sekarang = time.monotonic()

    durasi_hidup = gl.waktu_hidup          # detik
    durasi_mati = gl.waktu_mati * 60       # menit → detik

    if gl.status_on_timer == 1:
        print("a")
        print(sekarang - gl.waktuTerakhir)
        if sekarang - gl.waktuTerakhir >= durasi_hidup:
            gl.status_on_timer = False
            await saklar_kipas(0, 0, 0, 0, 0)
            gl.waktuTerakhir = sekarang
            gl.detail_timer_kipas = (
                f"Hidup pada : {getWaktuSetelahDetik(gl.waktu_mati*60)} --- "
                f"{gl.suhu_atas},{gl.suhu_outlet_atas},{gl.suhu_luar},{gl.suhu_acuan}"
            )
            simpan_data()
            ds.simpan_data_sqlite()
    else:
        print("b")
        print(sekarang - gl.waktuTerakhir)
        print(gl.jumlah_kipas_timer)
        if sekarang - gl.waktuTerakhir >= durasi_mati:
            gl.status_on_timer = True
            pola_kipas = {
                1: (0, 0, 0, 1, 0),
                2: (0, 1, 0, 1, 0),
                3: (0, 1, 1, 1, 0),
            }
            await saklar_kipas(*pola_kipas.get(gl.jumlah_kipas_timer, (0, 0, 0, 0, 0)))
            gl.waktuTerakhir = sekarang
            gl.detail_timer_kipas = f"Mati pada : {getWaktuSetelahDetik(gl.waktu_hidup)}"
            simpan_data()
            ds.simpan_data_sqlite()

# --- Fungsi utama kontrol kipas ---
async def kontrol_kipas_utama():
    # Debug / log status suhu
    gl.suhu_atas = gl.suhu_tengah_atas
    gl.suhu_dalam = gl.suhu_atas
    gl.kelembapan_atas = gl.kelembapan_tengah_atas
    gl.debug_str[0] = f"{gl.suhu_atas},{gl.suhu_outlet_atas},{gl.suhu_luar},{gl.suhu_acuan}"

    gl.keterangan_web = (
        f"Timer kipas : Hidup {gl.waktu_hidup} detik, "
        f"Mati {gl.waktu_mati} menit (diatur otomatis)"
    )

    # Logika mode kandang
    if gl.mode_kandang == 1:  # AUTO
        await setting_kipas_auto()

    elif gl.mode_kandang == 2:  # MANUAL
        #wajib_list = [0, 0, 0, 0, 0]
        gl.status_timer = 0
        await saklar_kipas(*gl.kipas)
        print("Mode MANUAL - kontrol kipas di web")

    elif gl.mode_kandang == 3:  # TIMER
        gl.status_timer = 1     
        await timer_kipas()

    elif gl.mode_kandang == 4:  # Auto A1
        gl.status_timer = 1
        await pengatur_kipas_auto_AI()

    else:  # DEFAULT fallback
        gl.status_timer = 0
        await saklar_kipas(*gl.kipas)
        
# Use joblib.load to load the model

def jalankan_model():
    # Susun input sebagai DataFrame
    data = pd.DataFrame([{
        "mode_kandang": gl.mode_kandang,
        "usia_ayam": gl.usia_ayam,
        "hari_ke": gl.hari_ke,
        "jam": gl.jam,
        "is_malam": gl.is_malam,
        "jam_mandatori_kipas": gl.jam_mandatori_kipas,
        "suhu_dalam": gl.suhu_dalam,
        "suhu_luar": gl.suhu_luar,
        "kelembapan_dalam": gl.kelembapan_dalam,
        "kelembapan_luar": gl.kelembapan_luar,
        "target_suhu": gl.target_suhu,
        "kode_cuaca": gl.kode_cuaca
    }])

    # Prediksi
    pred = model.predict(data)[0]

    # Mapping hasil menjadi dictionary
    output = {
        "kipas_1": pred[0],
        "kipas_2": pred[1],
        "kipas_3": pred[2],
        "kipas_4": pred[3],
        "kipas_5": pred[4],
        "mode_operasi": pred[5],
        "waktu_hidup_timer": pred[6],
        "waktu_mati_timer": pred[7],
        "skala_kipas": pred[8],
        "is_heater": pred[9],
        "is_celldeck": pred[10]
        
    }
    pred_2 = [1 if x >= 0.7 else 0 for x in pred[:5]]
    gl.debug_str[0] = str(pred[:10]) + " ==> " +  str(pred_2)
    output_2 = str(pred[:5]) + " ==> " + str(pred_2)
    #print(output)
    #print(output_2)
    return output

async def pengatur_kipas_auto_AI():
    await saklar_kipas(*gl.kipas)

async def pengatur_kipas_auto(wjb_hidup, *data_kipas):
    print("Pengatur kipas auto dengan data:", wjb_hidup, data_kipas)
    
    kipas_target = [0, 0, 0, 0, 0]
    detail_kipas = []
    
    # Batasi jumlah ayam antara 3000-8000, default pop_factor = 1 jika di luar range
    jumlah_ayam = constrain(gl.jumlah_ayam_awal, 3000, 8000)
    pop_factor = jumlah_ayam / 5000 if 3000 <= gl.jumlah_ayam_awal <= 8000 else 1

    if len(wjb_hidup) == 5:
        wajib_list = [int(c) for c in wjb_hidup]
        for i, v in enumerate(wajib_list):
            if v:
                kipas_target[i] = 1

        aktif = [i+1 for i, v in enumerate(wajib_list) if v]
        detail_kipas.append(f"0:{','.join(map(str, aktif)) if aktif else 0}")
    else:
        detail_kipas.append("0:0")

    ambang_tertinggi = -999
    kipas_mode_s = None

    for item in data_kipas:
        if not item or item == "N":
            continue

        bagian = item.split("-")

        if bagian[0] != "S":
            continue

        ambang = int(bagian[1]) / 10.0

        # === ADAPTIVE POPULATION ADJUSTMENT ===
        adjustment = (pop_factor - 1) * 0.8  # max ±0.5°C kalau 0-10000 ayam
        ambang -= adjustment
        
        kipas_list = [int(c) for c in bagian[2]]
 
        detail_kipas.append(
            f"1:{int(ambang*10)},{','.join(str(i+1) for i,v in enumerate(kipas_list) if v)}"
        )

        if gl.suhu_acuan > ambang and ambang > ambang_tertinggi:
            ambang_tertinggi = ambang
            kipas_mode_s = kipas_list

    if kipas_mode_s is not None:
        gl.status_timer = 0
        print(f"eksekusi: {data_kipas[1]}, kipas: {gl.kipas}, suhu : {gl.suhu_acuan}")  # Print data_kipas yang dipilih
        kipas_target = kipas_mode_s[:]   # overwrite total
        mode_dijalankan = True
    else:
        mode_dijalankan = False

    # ===============================
    # 3. MODE TIMER (FALLBACK)
    # ===============================
    if not mode_dijalankan:
        for item in data_kipas:
            if not item or item == "N":
                continue

            bagian = item.split("-")
            if bagian[0] != "T":
                continue

            ambang = int(bagian[1]) / 10.0
            if gl.suhu_acuan <= ambang:
                continue

            jml_kipas = int(bagian[2])
            suhu_min, suhu_max = int(bagian[3]), int(bagian[4])
            on_min, on_max = int(bagian[5]), int(bagian[6])
            off_min, off_max = int(bagian[7]), int(bagian[8])

            sh = int(gl.suhu_acuan * 10)

            # semakin banyak ayam → ON lebih lama, OFF lebih cepat
            gl.waktu_hidup = constrain(
                int(round(map_range(sh, suhu_min, suhu_max, on_min, on_max) * pop_factor)),
                on_min, int(on_max * 1.3)
            )

            gl.waktu_mati = constrain(
                int(round(map_range(sh, suhu_min, suhu_max, off_max, off_min) / pop_factor)),
                int(off_min * 0.7), off_max
            )

            gl.jumlah_kipas_timer = jml_kipas
            #print(f"Timer kipas diatur:{item} waktu hidup {gl.waktu_hidup} detik ON, {gl.waktu_mati} menit OFF, {jml_kipas} kipas")   
            gl.status_timer = 1
            await timer_kipas()
            break

    # ===============================
    # 4. EKSEKUSI (SATU TITIK)
    # ===============================
    if mode_dijalankan:
        await saklar_kipas(*kipas_target)
        gl.kipas = kipas_target[:]   # commit state

    # ===============================
    # 5. LOG & SIMPAN
    # ===============================
    gl.detail_kipas = "|".join(detail_kipas)
    gl.debug_str[3] = gl.detail_kipas
    simpan_data()
    ds.simpan_data_sqlite()

async def setting_kipas_auto():
    """Menentukan pengaturan kipas otomatis berdasarkan usia ayam."""
    usia = gl.usia_ayam

    # === KONFIGURASI DEFAULT (FALLBACK) ===
    daftar_konfigurasi = {
        0:  ("00000", "T-290-1-290-350-10-60-10-40", "S-360-00010", "N", "N", "N"),
        1:  ("00000", "T-290-1-290-345-10-80-5-30",  "S-345-00010", "N", "N", "N"),
        2:  ("00000", "T-280-2-285-340-10-90-5-25",  "S-340-00010", "N", "N", "N"),
        3:  ("00000", "T-280-2-280-340-15-100-4-20", "S-340-00010", "N", "N", "N"),
        4:  ("00000", "T-280-2-280-340-20-110-3-15", "S-340-00010", "N", "N", "N"),
        5:  ("00000", "T-270-2-280-330-25-120-2-10", "S-330-00010", "S-340-01010", "N", "N"),
        6:  ("00000", "T-260-2-280-320-30-130-1-6",  "S-320-00010", "S-330-01010", "N", "N"),
        7:  ("00000", "T-260-2-280-310-35-140-1-4",  "S-310-00010", "S-315-01010", "N", "N"),
        8:  ("00000", "T-255-2-270-305-40-150-1-3",  "S-294-00010", "S-310-01010", "N", "N"),
        9:  ("00000", "T-250-2-260-300-50-150-1-3",  "S-290-00010", "S-305-01010", "N", "N"),
        10: ("00000", "T-245-2-255-290-55-150-1-3",  "S-284-00010", "S-300-01010", "S-320-01110", "N"),
        11: ("00000", "T-240-2-250-287-60-150-1-2",  "S-278-00010", "S-295-01010", "S-315-01110", "N"),
        12: ("00010", "S-293-01010", "S-313-01110", "N", "N", "N"),
        13: ("00010", "S-290-01010", "S-310-01110", "N", "N", "N"),
        14: ("00010", "S-285-01010", "S-300-01110", "N", "N", "N"),
        15: ("01010", "S-287-01110", "S-305-01011", "N", "N", "N"),
        16: ("01010", "S-280-01110", "S-300-11010", "N", "N", "N"),
        17: ("01010", "S-275-01110", "S-296-01011", "N", "N", "N"),
        18: ("01010", "S-270-01110", "S-293-11010", "N", "N", "N"),
        19: ("01010", "S-265-01110", "S-289-01011", "N", "N", "N"),
        20: ("01010", "S-260-01110", "S-285-11010", "N", "N", "N"),
        21: ("01010", "S-255-01110", "S-284-01011", "N", "N", "N"),
        22: ("01010", "S-250-01110", "S-283-11010", "N", "N", "N"),
        23: ("01010", "S-245-01110", "S-282-01011", "N", "N", "N"),
        24: ("01010", "S-240-01110", "S-281-11010", "N", "N", "N"),
        25: ("01010", "S-240-01110", "S-280-01011", "N", "N", "N"),
        26: ("01010", "S-240-01110", "S-285-11010", "N", "N", "N"),
        27: ("01010", "S-240-01011", "S-300-01111", "N", "N", "N"),
        28: ("01010", "S-240-11010", "S-285-11110", "N", "N", "N"),
        29: ("01010", "S-240-01011", "S-285-01111", "N", "N", "N"),
        30: ("01010", "S-240-11010", "S-285-11110", "N", "N", "N"),
        31: ("01010", "S-240-01011", "S-285-01111", "N", "N", "N"),
        32: ("01010", "S-240-11010", "S-285-11110", "N", "N", "N"),
        33: ("01010", "S-240-01011", "S-285-01111", "N", "N", "N"),
        34: ("01010", "S-240-11010", "S-285-11110", "N", "N", "N"),
        35: ("01010", "S-240-01011", "S-285-01111", "N", "N", "N"),
        36: ("01010", "S-240-11010", "S-285-11110", "N", "N", "N"),
        37: ("01010", "S-240-01011", "S-285-01111", "N", "N", "N"),
        38: ("01010", "S-260-01110", "S-285-11010", "N", "N", "N"),
        39: ("01010", "S-260-01110", "S-285-01011", "N", "N", "N"),
        40: ("01010", "S-260-01110", "S-285-11010", "N", "N", "N"),
    }

    # === 1. COBA AMBIL DARI DATABASE ===
    data_db = ds.baca_baris_auto(usia)

    if data_db:
        # data_db = [d1, d2, d3, d4, d5, d6]
        wjb_hidup = data_db[0]
        aturan = [x for x in data_db[1:] if x and x != "N"]

        print(f"[AUTO] Pakai konfigurasi dari DATABASE (usia {usia})")

    else:
        # === 2. FALLBACK KE DEFAULT ===
        konfigurasi = daftar_konfigurasi.get(usia)

        if not konfigurasi:
            print(f"[AUTO] Tidak ada konfigurasi untuk usia {usia}")
            return

        wjb_hidup = konfigurasi[0]
        aturan = [x for x in konfigurasi[1:] if x != "N"]

        print(f"[AUTO] Pakai konfigurasi DEFAULT (usia {usia})")

    # === 3. EKSEKUSI ===
    await pengatur_kipas_auto(wjb_hidup, *aturan)

    print(f"Pengaturan kipas AUTO untuk usia {usia} hari diterapkan.")


print("kontrol_kipas.py dimuat.")