import asyncio
import aiohttp
import json
from variabel_global import gl, lock_data


async def kirim_data_ke_esp(url_tujuan: str, data_akan_dikirim: str):
    """Mengirim data ke ESP lain menggunakan HTTP POST"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url_tujuan,
                data=data_akan_dikirim,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
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


async def ambil_kirim_data_http(kode_server: int, address: str = "", data_kiriman: str = ""):
    """Mengambil atau mengirim data ke server lokal sesuai kode_server"""
    server_map = {
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

    async with lock_data:
        gl.http_sukses = False

    # Tentukan URL tujuan
    if kode_server == 0:
        url = address
    elif kode_server == 1:
        url = address
        await kirim_data_ke_esp(url, data_kiriman)
        return
    else:
        url = server_map.get(kode_server)
        if not url:
            print(f"Kode server tidak dikenal: {kode_server}")
            return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"Error code: {resp.status}, Server: {kode_server}")
                    return
                payload = await resp.text()

        data = json.loads(payload)
        print(f"Ambil data server {kode_server} berhasil")
        
    except Exception as e:
        print(f"Gagal mengambil data server {kode_server}")
        return

    async with lock_data:
        try:
            nomor_perangkat = data["dta"][0]
            gl.nomor_perangkat = nomor_perangkat
        except Exception:
            print("JSON tidak memiliki key 'dta'")
            return

        # Parsing data sesuai nomor_perangkat
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
            gl.http_sukses = True

        elif nomor_perangkat == 151:
            gl.suhu_atas = data["shu"][0] / 10.0
            gl.suhu_bawah = data["shu"][1] / 10.0
            gl.kelembapan_atas = data["klb"][0] / 10.0
            gl.kelembapan_bawah = data["klb"][1] / 10.0
            gl.data_HI_atas = data["dhi"][0] / 100.0
            gl.data_HI_bawah = data["dhi"][1] / 100.0
            gl.http_sukses = True

        elif nomor_perangkat == 153:
            for i in range(5):
                setattr(gl, f"kipas_{i+1}", data["kps"][i])
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
            gl.kwh_harian = lst[8]
            gl.http_sukses = True

        elif nomor_perangkat == 157:
            gl.lampu_luar = data["cry"][0]
            gl.indikator_cuaca = data["cry"][1]
            gl.kode_cuaca = data["cry"][2]
            gl.suhu_luar = data["shu"][0] / 10.0
            gl.kelembapan_luar = data["klb"][0] / 10.0
            gl.data_HI_luar = data["dhi"][0] / 100.0
            gl.http_sukses = True

        else:
            gl.http_sukses = False

print("local server ok")

# Contoh pemakaian
#if __name__ == "__main__":
 #   import asyncio
  #  asyncio.run(ambil_kirim_data_http(151))
