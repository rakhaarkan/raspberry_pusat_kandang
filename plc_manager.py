# plc_manager.py

from variabel_global import gl

import asyncio
from plc_network import PLCNetwork
import register_map as rm

# ============================================================
# Konfigurasi PLC
# ============================================================

network = PLCNetwork()

network.add("plc_kipas", "192.168.0.155")
network.add("kebun_kandang", "192.168.0.157")
network.add("kebun_rumah", "192.168.0.159")


# ============================================================
# Koneksi
# ============================================================

async def init():
    """
    Percobaan awal connect ke semua PLC saat startup FastAPI, dengan
    retry+backoff singkat (sebelumnya cuma coba sekali lalu pasrah nunggu
    watchdog() yang jalan tiap 10 detik).

    DIBATASI ke beberapa kali percobaan supaya startup FastAPI gak
    tertahan lama kalau ESP32 kebetulan masih booting bersamaan dengan
    RPi (mis. abis mati listrik). Kalau masih gagal setelah percobaan
    awal ini, tetap lanjut (non-fatal) - watchdog() yang akan terus
    mencoba reconnect di background selama aplikasi berjalan.
    """
    max_percobaan_awal = 3
    delay = 1.0

    for percobaan in range(1, max_percobaan_awal + 1):
        try:
            hasil = await network.connect_all(ignore_errors=True)
            print(f"PLC CONNECT (percobaan {percobaan}/{max_percobaan_awal}):", hasil)
            if hasil and all(hasil.values()):
                return  # semua PLC berhasil connect
        except Exception as e:
            print("PLC INIT ERROR:", e)

        if percobaan < max_percobaan_awal:
            await asyncio.sleep(delay)
            delay = min(delay * 2, 10.0)

    print("PLC INIT: sebagian/semua PLC belum connect setelah percobaan awal, "
          "akan terus dicoba di background oleh plc_manager.watchdog()")

async def shutdown():
    try:
        await network.disconnect_all()
    except Exception as e:
        print("PLC SHUTDOWN ERROR:", e)

# ============================================================
# Monitoring
# ============================================================

def plc_connected():
    try:
        return network["plc_kipas"].connected
    except:
        return False
    
async def monitor_koneksi():
    try:
        status = await network.ping_all()
        gl.plc_status = status
    except Exception as e:
        print("PLC MONITOR ERROR:", e)

async def watchdog():
    try:
        status = await network.ping_all()
        for nama, online in status.items():
            if not online:
                print(f"[PLC OFFLINE] {nama}")
                await network.reconnect_all()
                break
    except Exception as e:
        print("PLC WATCHDOG ERROR:", e)

# ============================================================
# Sensor
# ============================================================

async def baca_sensor():
    """
    Baca 4 input register suhu dari ESP32 (IReg, semua x10 uint16 single-register).

    CATATAN: sebelumnya fungsi ini memanggil plc.read_float(100) yang salah
    total - alamat 100 tidak ada di ModbusRegisterMap.h firmware (holding
    register cuma sampai alamat 7, input register cuma sampai 3), dan
    read_float() decode IEEE-754 2-register sedangkan firmware simpan
    suhu sebagai 1 register x10 integer. Sekarang dibetulkan pakai
    read_input_register() + konversi x10 manual, sesuai x10ToFloat()
    di modbus_tcp.cpp firmware.
    """
    try:
        plc = network["plc_kipas"]
        gl.suhu_atas_plc = rm.x10_ke_float(await plc.read_input_register(rm.IReg.SUHU_ATAS_X10))
        gl.suhu_luar_plc = rm.x10_ke_float(await plc.read_input_register(rm.IReg.SUHU_LUAR_X10))
        gl.suhu_outlet_atas_plc = rm.x10_ke_float(await plc.read_input_register(rm.IReg.SUHU_OUTLET_ATAS_X10))
        gl.suhu_acuan_plc = rm.x10_ke_float(await plc.read_input_register(rm.IReg.SUHU_ACUAN_X10))
    except Exception as e:
        print("PLC SENSOR ERROR:", e)

# ============================================================
# Output
# ============================================================

async def tulis_kipas_modbus(status_list):
    """
    Tulis status 5 kipas ke coil Modbus secara paralel.
    Dipanggil oleh aktuator_kipas.kirim_perintah_kipas() sebagai jalur PRIMER
    pengiriman perintah kipas.

    Return True kalau semua coil berhasil ditulis & PLC terkoneksi,
    False kalau PLC offline atau salah satu write gagal (caller lalu
    fallback ke Serial/HTTP).
    """
    if not plc_connected():
        return False
    try:
        plc = network["plc_kipas"]
        await asyncio.gather(*[
            plc.write_coil(rm.Coil.FAN_1 + i, bool(v))
            for i, v in enumerate(status_list[:rm.Coil.FAN_COUNT])
        ])
        return True
    except Exception as e:
        print("PLC KIPAS WRITE ERROR:", e)
        return False


async def sinkronisasi_kipas():
    if not plc_connected():
        return
    try:
        plc = network["plc_kipas"]
        status_kipas = [bool(v) for v in gl.kipas[:rm.Coil.FAN_COUNT]]
        for i, nilai in enumerate(status_kipas):
            await plc.write_coil(rm.Coil.FAN_1 + i, nilai)
    except Exception as e:
        print("PLC KIPAS ERROR:", e)

# ============================================================
# Feedback
# ============================================================

async def baca_feedback_kipas():
    try:
        plc = network["plc_kipas"]
        gl.fb_kipas = [
            await plc.read_coil(0),
            await plc.read_coil(1),
            await plc.read_coil(2),
            await plc.read_coil(3),
            await plc.read_coil(4),

        ]
    except Exception as e:
        print("PLC FEEDBACK ERROR:", e)


# ============================================================
# Statistik
# ============================================================

async def update_statistik():
    try:
        gl.plc_stats = network.get_stats()
    except Exception as e:
        print("PLC STATS ERROR:", e)

# ============================================================
# Scan Cycle
# ============================================================

async def scan_plc():
    if not plc_connected():
        return
    try:
        await baca_sensor()
        await sinkronisasi_kipas()
        await baca_feedback_kipas()
    except Exception as e:
        print("PLC SCAN ERROR:", e)