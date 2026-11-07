from variabel_global import gl, lock_data
import asyncio, threading, time
from local_server import ambil_kirim_data_http
import penyimpanan_data as pd
import json
import fungsi_umum as fu
from fastapi import FastAPI
import kontrol_kipas as kk
import aktuator_kipas as ak
from web_scraping import ambil_harga_jogja
from webserver import app
import webserver as ws
import thingspeak as thg
import sensor as sn
import database_sqlite as db
# import plc_manager as plc  # Modbus dimatikan total (lihat aktuator_kipas.py) -
                              # file plc_manager.py/plc_client.py/register_map.py
                              # sengaja dipertahankan utuh untuk kemungkinan
                              # dipakai lagi kalau ada PLC Modbus sungguhan nanti.
#import proses_gambar as pg
#import koneksi_blynk as kb
#import konfigurasi_n8n as nn
import os
import faulthandler

faulthandler.enable()


if "RUN_MAIN" in os.environ:  # mencegah eksekusi dua kali
    pass
else:
    print("FASTAPI STARTING FOR THE FIRST TIME")

    
async def tugas_periodik(fungsi, interval, *args, **kwargs):
    while True:
        start = asyncio.get_event_loop().time()

        try:
            if asyncio.iscoroutinefunction(fungsi):
                await fungsi(*args, **kwargs)
            else:
                await asyncio.to_thread(fungsi, *args, **kwargs)

        except Exception as e:
            print(f"[ERROR] {fungsi.__name__}: {e}")

        # Tunggu sisa waktunya
        elapsed = asyncio.get_event_loop().time() - start
        wait_time = max(0, interval - elapsed)
        await asyncio.sleep(wait_time)


def tugas_periodik_threading(fungsi, interval, *args, **kwargs):
    """
    Menjalankan fungsi sync secara periodik menggunakan threading.
    Aman untuk fungsi yang blocking.
    """
    def loop():
        while True:
            try:
                fungsi(*args, **kwargs)
            except Exception as e:
                print(f"[ERROR THREAD] Fungsi {fungsi.__name__} gagal: {e}")
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()

def setup_awal():
    db.init_db()
    db.muat_data()
    fu.tanggal_waktu_usia()
    pd.load_data() #data sensor
    #kb.start_blynk()
    sn.kelola_suhu_acuan()
    fu.send_heartbeat()
    sn.update_trend_dan_selisih()
    sn.update_trend_dan_selisih()
    sn.update_trend_dan_selisih()
    db.hitung_statistik_bobot()
    ambil_harga_jogja()
    #nn.run_n8n()
    #kk.setting_kipas_auto()
    #db.sync_data_bakul()
    #thg.pengolah_json_2()
    #sn.cuaca()
    #asyncio.create_task(sn.cuaca())
    #pd.simpan_sensor()
    gl.usia_ui = gl.usia_ayam

setup_awal()

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    fu.register_broadcast_callback(ws.update_and_broadcast, loop)
    # await plc.init()  # Modbus dimatikan total, lihat catatan import di atas

    print("Menjalankan semua task async...")

    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 10, 151))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 5, 152))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 1, 154))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 1, 1552))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 10, 157))
    asyncio.create_task(tugas_periodik(ambil_kirim_data_http, 10, 158))
    asyncio.create_task(tugas_periodik(db.update_db_sensor_24, 60))
    asyncio.create_task(tugas_periodik(fu.tanggal_waktu_usia, 10))
    asyncio.create_task(tugas_periodik(sn.cuaca, 60))
    asyncio.create_task(tugas_periodik(fu.cek_serial, 0.1))
    asyncio.create_task(tugas_periodik(fu.broadcastkan, 1))
    asyncio.create_task(tugas_periodik(thg.kirim_thingspeak, 15))
    asyncio.create_task(tugas_periodik(thg.kirim_thingspeak_2, 60))
    asyncio.create_task(tugas_periodik(db.sync_data_bakul, 3600))
    asyncio.create_task(tugas_periodik(db.tulis_dataset_AI, 300))
    asyncio.create_task(tugas_periodik(sn.update_trend_dan_selisih, 10))
    asyncio.create_task(tugas_periodik(kk.kontrol_kipas_utama, 1))
    asyncio.create_task(tugas_periodik(ak.kirim_periodik, 1))
    #asyncio.create_task(tugas_periodik(kk.jalankan_model, 10))
    asyncio.create_task(tugas_periodik(sn.kelola_suhu_acuan, 300))
    asyncio.create_task(tugas_periodik(fu.send_heartbeat, 5))
    #asyncio.create_task(tugas_periodik(nn.check_status, 30))
    #asyncio.create_task(tugas_periodik(db.hitung_statistik_bobot, 60))
    asyncio.create_task(tugas_periodik(ambil_harga_jogja, 3600))
    asyncio.create_task(tugas_periodik(db.simpan_data_performa_sqlite, 600))
    # Modbus dimatikan total (lihat catatan import plc_manager di atas) -
    # tinggal un-comment 5 baris ini kalau suatu hari dipakai lagi:
    # asyncio.create_task(tugas_periodik(plc.monitor_koneksi, 30))
    # asyncio.create_task(tugas_periodik(plc.watchdog, 10))
    # asyncio.create_task(tugas_periodik(plc.scan_plc, 1))
    # asyncio.create_task(tugas_periodik(plc.sinkronisasi_kipas, 1))
    # asyncio.create_task(tugas_periodik(plc.update_statistik, 60))
    print("Semua task async sudah dimulai.")

# jalankan server hanya jika file ini dipanggil langsung
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
    
#dependensi:
#pip install fastapi uvicorn opencv-python numpy
#sudo apt install python3-rpi.gpio
#sudo apt update
#sudo apt install rclone
#sudo apt install python3-pip -y
#sudo apt install python3-serial
#sudo apt install python3-psycopg2
#sudo apt install libatlas-base-dev
#sudo apt install python3-opencv
#pip install psycopg2-binary
#pip install requests joblib pandas websocket
#pip install scikit-learn
#pip install beautifulsoup4
#pip install adafruit-circuitpython-dht
#pip install board
#pip install RPi.GPIO
#pip install httpx
#pip install pytz

#curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
#sudo apt install -y nodejs
#NODE_OPTIONS="--max-old-space-size=512" sudo npm install -g n8n

#venv
#source /home/rakha/Documents/Project_Kandang/virtual_env/bin/activate
#source /home/rakha/Documents/Project_Kandang/venv/bin/activate
#sudo chown -R rakha:rakha /home/rakha/Documents/Project_Kandang
    
#lain lain:
#ssh rakha@192.168.0.156
#sudo systemctl stop kandang.service
#sudo systemctl disable kandang.service
#sudo systemctl enable kandang.service
#sudo systemctl start kandang.service
#sudo nano /etc/systemd/system/kandang.service   # ubah konfigurasi
#sudo systemctl daemon-reload                    # muat ulang konfigurasi
#sudo systemctl restart kandang.service          # jalankan ulang servicenya
#sudo systemctl status kandang.service           # cek apakah berhasil

#htop #cek ram
#nmtui #atur wifi lan
#