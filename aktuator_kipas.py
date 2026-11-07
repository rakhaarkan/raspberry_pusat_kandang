# aktuator_kipas.py
"""
aktuator_kipas.py
==================
Satu pintu masuk untuk mengirim perintah + config ke ESP32, dengan rantai
prioritas:

    1. HTTP POST   (PRIMER    - aiohttp, non-blocking)
    2. Serial UART (sekunder  - fu.send_serial, fallback kalau HTTP gagal)

Alasan HTTP jadi primer (per diskusi): LAN/WiFi historisnya stabil di
jaringan ini, dan rencana ke depan RPi bakal dipindah ke ruangan terpisah
dari ESP32 - itu cuma mungkin lewat jaringan (LAN gak terbatas jarak kabel
kayak Serial). Serial tetap dipertahankan sebagai fallback selama RPi &
ESP32 masih satu ruangan.

PAYLOAD GABUNGAN: kipas + tanaman (field "stn") + config buat TIMER darurat
(waktu_hidup/waktu_mati/jumlah_kipas_timer) dikirim BARENG di setiap
pengiriman - bukan cuma pas ada perubahan kipas. Ini dikirim di 2 pemicu
yang boleh tumpang tindih (idempotent, aman):
    1. Instan   - kirim_perintah_kipas() dipanggil dari saklar_kipas()
    2. Periodik - kirim_periodik() dijadwalkan tiap 1 detik dari main.py,
                  terlepas ada perubahan kipas atau nggak. Ini yang bikin
                  config & heartbeat watchdog ESP32 selalu segar, gak
                  numpang nunggu kipas kebetulan berubah.

WATCHDOG ESP32 (lihat watchdog.cpp firmware): kalau putus kontak lebih
dari 30 detik SAAT mode TIMER -> ESP32 jalankan siklus timer sendiri
pakai waktu_hidup/waktu_mati/jumlah_kipas_timer terakhir yang disinkron.
SAAT mode AUTO -> dikunci diam total (freeze, setara MANUAL), BUKAN coba
jalankan logika auto RPi yang kompleks (tabel usia ayam, faktor populasi,
aturan suhu bertingkat) - keputusan sadar demi keamanan.

CATATAN KOPLING FIRMWARE: field waktu_hidup/waktu_mati/jumlah_kipas_timer
di payload ini BARU BERGUNA kalau firmware (handleKipasBulk() di
web_server.cpp DAN SerialProtocol::handle() di serial_protocol.cpp) sudah
diupdate buat baca & terapkan field itu ke state.kandang.*. Sampai firmware
itu diupdate, field ini terkirim tapi diam-diam diabaikan (JSON field asing
tidak bikin error, cuma gak dipakai).

STATUS: Modbus DIMATIKAN TOTAL (lihat plc_manager.py untuk detail - file
itu sengaja dipertahankan utuh sebagai infrastruktur dorman).
"""

import asyncio
import json
import aiohttp

from variabel_global import gl
import fungsi_umum as fu
import status_esp32

HTTP_TIMEOUT_DETIK = 1.5  # primer & dipanggil sesering 1x/detik - harus cepat
                          # gagal supaya fallback Serial gak nunggu lama

# Cegah pemicu instan & periodik kirim bersamaan dan saling tabrakan
# (mis. kirim_periodik() lagi nunggu respons HTTP, barengan ada perubahan
# kipas yang manggil kirim_perintah_kipas() juga).
_lock_kirim = asyncio.Lock()


def _bangun_payload(kipas_state, tanaman_state=None):
    """Payload gabungan: kipas + tanaman/stn + config buat TIMER darurat.

    Catatan: target_suhu/suhu_minimal/suhu_maksimal SENGAJA tidak dikirim
    lagi di sini - mode AUTO di watchdog ESP32 dikunci diam total (freeze,
    setara MANUAL) begitu putus kontak, bukan coba jalankan logika auto
    RPi yang kompleks (tabel usia, faktor populasi, aturan suhu
    bertingkat). Yang dibutuhkan watchdog cuma waktu_hidup/waktu_mati/
    jumlah_kipas_timer, buat mode TIMER darurat.
    """
    if tanaman_state is None:
        tanaman_state = gl.state_tanaman[:5]
    return {
        "kipas": list(kipas_state),
        "stn": list(tanaman_state),
        "waktu_hidup": gl.waktu_hidup,
        "waktu_mati": gl.waktu_mati,
        "jumlah_kipas_timer": gl.jumlah_kipas_timer,
    }


async def _kirim_via_http(payload):
    """Primer: HTTP POST /kipasstr ke ESP32 kipas (non-blocking, aiohttp)."""
    url = gl.server_pusat_kipas_atas.rstrip("/") + "/kipasstr"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_DETIK),
            ) as resp:
                if resp.status != 200:
                    print(f"[aktuator_kipas] HTTP status {resp.status}, bukan 200")
                    return False
                # /kipasstr sekarang echo balik state yang beneran diterapkan
                # (lihat web_server.cpp) - dipakai buat update generasi
                # terkonfirmasi (lihat status_esp32.py), bukan cuma dicek
                # valid-JSON doang.
                data = await resp.json()
                status_esp32.terapkan_status_kipas(data)
                return True
    except Exception as e:
        print("[aktuator_kipas] HTTP gagal:", e)
        return False


def _kirim_via_serial(payload):
    """Sekunder/fallback: Serial UART."""
    return fu.send_serial(json.dumps(payload))


def kirim_tanaman_serial(kipas_state=None, tanaman_state=None):
    """
    Kirim state kipas+tanaman lewat Serial secara EKSPLISIT, di luar rantai
    prioritas HTTP->Serial normal.

    Dipakai khusus untuk update data tanaman/pompa (mis. pompa_sendang) dari
    webserver.py: field ini HANYA dibaca firmware lewat payload Serial
    ("stn") - belum ada rute HTTP khusus buat update ini secara instan.
    """
    if kipas_state is None:
        kipas_state = gl.kipas
    payload = _bangun_payload(kipas_state, tanaman_state)
    return _kirim_via_serial(payload)


async def kirim_perintah_kipas(kipas_state, tanaman_state=None):
    """
    Kirim status 5 kipas + config ke ESP32 lewat rantai prioritas
    HTTP -> Serial.

    Args:
        kipas_state   : list/tuple 5 elemen (0/1) status tiap kipas.
        tanaman_state : list 5 elemen untuk field "stn" (pompa/tanaman).
                        Default gl.state_tanaman[:5].

    Returns:
        dict {"berhasil": bool, "channel": "http"|"serial"|None}
    """
    payload = _bangun_payload(kipas_state, tanaman_state)

    async with _lock_kirim:
        # 1) HTTP - primer
        if await _kirim_via_http(payload):
            gl.kipas_channel_aktif = "http"
            return {"berhasil": True, "channel": "http"}

        print("[aktuator_kipas] HTTP gagal, fallback ke Serial")

        # 2) SERIAL - fallback
        if _kirim_via_serial(payload):
            gl.kipas_channel_aktif = "serial"
            return {"berhasil": True, "channel": "serial"}

        # Semua channel gagal
        gl.kipas_channel_aktif = "gagal"
        gl.kipas_gagal_total += 1
        print("[aktuator_kipas] SEMUA channel gagal! Kipas tidak berubah status.")
        return {"berhasil": False, "channel": None}


async def kirim_periodik():
    """
    Dipanggil tiap 1 detik dari main.py (terlepas ada perubahan kipas atau
    nggak) - jadwalkan lewat main.py:
        asyncio.create_task(tugas_periodik(ak.kirim_periodik, 1))

    Ini yang menjamin config (target_suhu dkk) & heartbeat watchdog ESP32
    selalu segar, gak numpang nunggu kipas kebetulan berubah.
    """
    await kirim_perintah_kipas(gl.kipas)


print("aktuator_kipas.py dimuat.")