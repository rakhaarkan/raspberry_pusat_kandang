import asyncio
import aiohttp
import json

from variabel_global import gl, lock_data
import status_esp32
from parser_esp import parse_json_esp


# ============================================================
# KONFIGURASI ROUTING DAN STATUS
# ============================================================

SERVER_MAP = {
    150: gl.server_pusat_data,
    151: gl.server_sensor_dalam,
    152: gl.server_sensor_tangki_air,
    153: gl.server_sensor_kipas,
    154: gl.server_sensor_listrik,
    155: gl.server_pusat_kipas_atas,
    1551: gl.server_pusat_kipas_atas_wkt,
    1552: gl.server_pusat_kipas_atas_kps,
    1553: gl.server_pusat_kipas_atas_shu,
    1554: gl.server_pusat_kipas_atas_epr,
    156: gl.server_kebun_kandang,
    157: gl.server_saklar_cuaca_relay,
    158: gl.server_timbangan_auto,
    1581: gl.server_timbangan_auto_raw,
}

DEBUG_ERR_INDEX = {
    150: 0,
    151: 1,
    152: 2,
    153: 3,
    154: 4,
    155: 5,
    156: 6,
    157: 7,
    158: 8,
}

PROTOCOL_METADATA_KEYS = {"device_id", "protocol_version"}


# ============================================================
# PENGIRIMAN DATA KE ESP
# ============================================================

async def kirim_data_ke_esp(url_tujuan: str, data_akan_dikirim: str):
    """Mengirim data ke ESP lain menggunakan HTTP POST."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url_tujuan,
                data=data_akan_dikirim,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                if resp.status == 200:
                    response_text = await resp.text()
                    print(f"Response dari ESP tujuan: {response_text}")
                    async with lock_data:
                        gl.http_sukses = True
                else:
                    print(f"Gagal kirim. Error code: {resp.status}")
                    async with lock_data:
                        gl.http_sukses = False
    except Exception as e:
        print(f"WiFi tidak terhubung / error: {e}")
        async with lock_data:
            gl.http_sukses = False


# ============================================================
# UTILITAS STATUS
# ============================================================

async def _set_http_status(sukses: bool, debug_index=None, debug_value=None):
    async with lock_data:
        gl.http_sukses = sukses
        if debug_index is not None and debug_value is not None:
            gl.debug_err[debug_index] = str(debug_value)


async def _catat_gagal(kode_server: int):
    """Mempertahankan pemetaan debug_err dari implementasi lama."""
    index = DEBUG_ERR_INDEX.get(kode_server)
    if index is not None:
        await _set_http_status(False, index, 0 if kode_server in (150, 153, 155, 156) else kode_server)
    else:
        await _set_http_status(False)


def _punya_metadata_protokol_baru(data: dict) -> bool:
    """
    Jika salah satu metadata muncul, payload harus diproses sebagai
    protokol baru. Payload metadata yang tidak lengkap tidak boleh
    jatuh diam-diam ke parser lama.
    """
    return any(key in data for key in PROTOCOL_METADATA_KEYS)


# ============================================================
# HANDLER PROTOKOL BARU
# ============================================================

async def _terapkan_special_baru(special: dict, kode_server: int):
    """
    Terapkan field khusus yang tidak boleh di-set secara generik.

    Status kipas utama tetap melewati status_esp32 agar perlindungan
    generation + boot_id terhadap data basi tidak hilang.
    """
    if not special:
        return

    # Jangan menahan lock_data ketika memanggil parser:
    # parser sudah mengambil lock_data untuk field biasa.
    async with lock_data:
        # Field khusus selain status kipas utama.
        for key in (
            "kipas_1", "kipas_2", "kipas_3", "kipas_4", "kipas_5",
            "kipas_6", "kipas_7", "kipas_8", "kipas_9", "kipas_10",
            "kipas_inspeksi", "kipas_saklar",
            "kipas_channel_aktif", "kipas_gagal_total", "rpm_kipas",
        ):
            if key in special:
                value = special[key]
                # Salin list agar object payload tidak menjadi referensi
                # langsung ke state global.
                setattr(gl, key, list(value) if isinstance(value, list) else value)

    # Status gl.kipas hanya boleh diperbarui melalui mekanisme generasi.
    # status_esp32 mengharuskan ketiga informasi ini tersedia.
    if kode_server == 1552:
        required = (
            "kipas",
            "kipas_generasi_terkonfirmasi",
            "esp32_boot_id_terakhir",
        )
        if all(key in special for key in required):
            async with lock_data:
                status_esp32.terapkan_status_kipas({
                    "kps": special["kipas"],
                    "gen": special["kipas_generasi_terkonfirmasi"],
                    "boot_id": special["esp32_boot_id_terakhir"],
                })
        elif "kipas" in special:
            print(
                "[local_server] Status kipas protokol baru diabaikan: "
                "kipas, generation, dan boot_id harus tersedia bersama."
            )

    # Field tracking generation/boot tidak boleh ditulis langsung.
    # Keduanya hanya diperbarui oleh terapkan_status_kipas() setelah
    # validasi kelengkapan dan pemeriksaan generation.
    #
    # Jika payload modern mengirim field tracking tanpa status kipas
    # lengkap, field tersebut sengaja tidak diterapkan.


async def _proses_protokol_baru(data: dict, kode_server: int) -> bool:
    """
    Jalur protokol baru: metadata device_id + protocol_version.
    Parser melakukan validasi field dan update field biasa.
    Return True jika payload lolos validasi protokol.
    """
    hasil = await parse_json_esp(data, gl, lock_data)

    if not hasil.get("ok"):
        print(
            f"[local_server] JSON protokol baru ditolak "
            f"(server={kode_server}): {hasil.get('error')}"
        )
        await _set_http_status(False)
        return False

    device_id = hasil.get("device_id")

    # Catat identitas perangkat dari metadata protokol baru.
    async with lock_data:
        if device_id is not None:
            gl.nomor_perangkat = device_id

    await _terapkan_special_baru(hasil.get("special", {}), kode_server)

    if hasil.get("rejected"):
        print(
            f"[local_server] Sebagian field ditolak dari device "
            f"{device_id}: {list(hasil['rejected'].keys())}"
        )

    if hasil.get("unknown"):
        print(
            f"[local_server] Field tidak dikenal dari device "
            f"{device_id} diabaikan: {hasil['unknown']}"
        )

    # Payload valid meskipun ada field individual yang tidak dikenal
    # atau ditolak; parser memang dirancang menerima field valid lainnya.
    print(f"[local_server] Payload protokol baru diterima dari device {device_id}") 
    await _set_http_status(True)
    return True


# ============================================================
# HANDLER PROTOKOL LAMA (FALLBACK KOMPATIBILITAS)
# ============================================================

async def _proses_protokol_lama(data: dict) -> bool:
    """
    Handler format lama berbasis dta/mtd/shu/klb/dhi/dll.
    Logika konversi dan mapping lama dipertahankan.
    """
    try:
        nomor_perangkat = data["dta"][0]
        if isinstance(nomor_perangkat, bool) or not isinstance(nomor_perangkat, int):
            raise ValueError("dta[0] harus integer")
    except (KeyError, IndexError, TypeError, ValueError):
        print("JSON lama tidak memiliki 'dta[0]' yang valid")
        await _set_http_status(False)
        return False

    try:
        async with lock_data:
            gl.nomor_perangkat = nomor_perangkat

            if nomor_perangkat == 150:
                gl.harga_pakan_kg = data["mtd"][0]
                gl.jumlah_ayam_awal = data["mtd"][1]
                gl.harga_obat_ayam = data["mtd"][2]
                gl.jumlah_ayam_mati = data["mtd"][3]
                gl.harga_bibit_ayam = data["mtd"][4]
                gl.jumlah_pakan_sak = data["mtd"][5]
                gl.harga_kontrak_ayam = data["mtd"][6]
                gl.bobot_rata_rata = data["mtd"][7]
                gl.jumlah_ayam_dipanen = data["mtd"][9]
                gl.debug_err[0] = "OK"
                gl.http_sukses = True

            elif nomor_perangkat == 151:
                gl.suhu_atas = data["shu"][0] / 10.0
                gl.suhu_bawah = data["shu"][1] / 10.0
                gl.kelembapan_atas = data["klb"][0] / 10.0
                gl.kelembapan_bawah = data["klb"][1] / 10.0
                gl.data_HI_atas = data["dhi"][0] / 100.0
                gl.data_HI_bawah = data["dhi"][1] / 100.0
                gl.suhu_dalam = gl.suhu_atas
                gl.kelembapan_dalam = gl.kelembapan_atas
                gl.debug_err[1] = "OK"
                gl.http_sukses = True

            elif nomor_perangkat == 152:
                gl.liter_tong_atas = data["air"][0]
                gl.persen_air_atas = data["air"][1]
                gl.liter_tong_bawah = data["air"][2]
                gl.persen_air_bawah = data["air"][3]
                gl.kecepatan_minum_atas = data["air"][4]
                gl.kecepatan_minum_bawah = data["air"][5]
                gl.debug_err[2] = "OK"
                gl.http_sukses = True

            elif nomor_perangkat == 153:
                for i in range(5):
                    setattr(gl, f"kipas_{i + 1}", data["kps"][i])
                gl.debug_err[3] = "OK"
                gl.http_sukses = True

            elif nomor_perangkat == 154:
                lst = data["lst"]
                if lst[0] != 0:
                    gl.voltage = lst[0]
                gl.current = lst[1]
                gl.power = lst[2]
                if lst[3] != 0:
                    gl.energy = lst[3]
                gl.frequency = lst[4]
                gl.pf = lst[5]
                gl.kecepatan_listrik_atas = lst[6]
                gl.kwh_jam = lst[7]
                gl.daya_listrik = gl.power
                gl.debug_err[4] = "OK"
                gl.http_sukses = True

            elif nomor_perangkat == 1552:
                # Format legacy tetap menggunakan adapter lama.
                # Fungsi ini aman dipanggil saat lock_data dipegang karena
                # terapkan_status_kipas() sendiri tidak mengambil lock.
                status_esp32.terapkan_status_kipas(data)

                for i in range(5):
                    gl.kipas_inspeksi[i] = data["kpi"][i]
                    gl.kipas_saklar[i] = data["kcs"][i]
                gl.http_sukses = True

            elif nomor_perangkat == 157:
                gl.suhu_inlet_atas = data["shu"][0] / 10.0
                gl.suhu_inlet_bawah = data["shu"][1] / 10.0
                gl.suhu_luar = data["shu"][2] / 10.0
                gl.kelembapan_inlet_atas = data["klb"][0] / 10.0
                gl.kelembapan_inlet_bawah = data["klb"][1] / 10.0
                gl.kelembapan_luar = data["klb"][2] / 10.0
                gl.data_HI_inlet_atas = data["dhi"][0] / 100.0
                gl.data_HI_inlet_bawah = data["dhi"][1] / 100.0
                gl.data_HI_luar = data["dhi"][2] / 100.0
                gl.indikator_cuaca = data["cry"][0]
                gl.kode_cuaca = data["cry"][1]
                gl.teks_cuaca = data["cry"][2]
                gl.http_sukses = True

            else:
                gl.http_sukses = False
                return False

        return True

    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError) as e:
        print(
            f"[local_server] Payload legacy perangkat "
            f"{nomor_perangkat} tidak lengkap/tidak valid: {e}"
        )
        await _set_http_status(False)
        return False


# ============================================================
# ENTRY POINT HTTP
# ============================================================

async def ambil_kirim_data_http(
    kode_server: int,
    address: str = "",
    data_kiriman: str = "",
):
    """Mengambil data dari server lokal atau mengirim data ke ESP."""
    gl.debug_str[2] = str(gl.debug_err[:8])

    await _set_http_status(False)

    # Tentukan URL tujuan.
    if kode_server == 0:
        url = address
    elif kode_server == 1:
        await kirim_data_ke_esp(address, data_kiriman)
        return
    else:
        url = SERVER_MAP.get(kode_server)
        if not url:
            print(f"Kode server tidak dikenal: {kode_server}")
            return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"Error code: {resp.status}, Server: {kode_server}")
                    await _catat_gagal(kode_server)
                    return
                payload = await resp.text()

        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Root JSON harus berupa object")

    except Exception as e:
        print(f"Gagal mengambil data server {kode_server}: {e}")
        await _catat_gagal(kode_server)
        return

    # Fallback deterministik:
    # - Ada salah satu metadata baru -> wajib parser protokol baru.
    # - Tidak ada keduanya -> handler legacy.
    # Metadata parsial atau versi salah tidak boleh turun ke legacy.
    if _punya_metadata_protokol_baru(data):
        await _proses_protokol_baru(data, kode_server)
    else:
        await _proses_protokol_lama(data)


print("local_server.py dimuat.")
