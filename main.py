from variabel_global import gl, lock_data
import asyncio
from local_server import ambil_kirim_data_http
import penyimpanan_data as pd
import json
import fungsi_umum as fu
from fastapi import FastAPI
from kontrol_kipas import saklar_kipas
from webserver import app
import thingspeak as thg
import sensor as sn
import database_sqlite as db


async def cek_serial():

    if gl.ser is None:
        fu.connect_serial()
        return

    data = fu.baca_serial_nonblocking()
    if data:
        print("[ESP32]", data)

    
async def tugas_periodik(fungsi, interval, *args, **kwargs):
    """
    Jalankan fungsi apa pun secara periodik dengan interval tertentu.

    Parameters:
    - fungsi: nama fungsi (async atau sync)
    - interval: jeda waktu antar eksekusi (detik)
    - *args, **kwargs: parameter tambahan untuk fungsi
    """
    while True:
        try:
            if asyncio.iscoroutinefunction(fungsi):
                await fungsi(*args, **kwargs)
            else:
                # kalau fungsi biasa (blocking), jalankan di thread terpisah agar tidak ganggu loop
                await asyncio.to_thread(fungsi, *args, **kwargs)
        except Exception as e:
            print(f"[ERROR] Fungsi {fungsi.__name__} gagal dijalankan: {e}")

        await asyncio.sleep(interval)

def setup_awal():
    pd.muat_data()
    fu.tanggal_waktu_usia()
    pd.load_data() #data sensor
    #thg.pengolah_json_2()
    #sn.cuaca()
    #asyncio.create_task(sn.cuaca())
    #pd.simpan_sensor()
    

setup_awal()

@app.on_event("startup")
async def startup_event():
    print("Menjalankan semua task async...")

    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 10, 151))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 5, 152))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 1, 154))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 10, 157))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 10, 158))
    asyncio.create_task(tugas_periodik(db.update_db_sensor_24, 60))
    asyncio.create_task(tugas_periodik(fu.tanggal_waktu_usia, 10))
    asyncio.create_task(tugas_periodik(sn.cuaca, 60))
    asyncio.create_task(tugas_periodik(cek_serial, 0.05))
    asyncio.create_task(tugas_periodik(thg.kirim_thingspeak, 15))

    print("Semua task async sudah dimulai.")

# jalankan server hanya jika file ini dipanggil langsung
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)

#dependensi:
#pip install fastapi uvicorn
#sudo apt install python3-rpi.gpio
#sudo apt update
#sudo apt install python3-pip -y
#sudo apt install python3-serial
#pip3 install fastapi uvicorn



#lain lain:
#sudo systemctl stop kandang.service
#sudo systemctl disable kandang.service
#sudo systemctl enable kandang.service
#sudo systemctl start kandang.service
#sudo nano /etc/systemd/system/kandang.service   # ubah konfigurasi
#sudo systemctl daemon-reload                    # muat ulang konfigurasi
#sudo systemctl restart kandang.service          # jalankan ulang servicenya
#sudo systemctl status kandang.service           # cek apakah berhasil