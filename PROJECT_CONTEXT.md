# Project Context — Project Kandang

> Dokumen konteks teknis untuk developer dan AI coding assistant.
>
> Tujuan dokumen ini adalah memberikan gambaran sistem sebelum seseorang membaca,
> menganalisis, atau mengubah source code. Informasi yang belum diverifikasi secara
> langsung ditandai sebagai catatan atau hal yang perlu ditelusuri.

**Project:** Project Kandang
**Platform utama:** Raspberry Pi + ESP32
**Backend:** Python, FastAPI, Uvicorn
**Database utama:** SQLite
**Status:** Active Development

---

## 1. Tujuan Sistem

Project Kandang adalah sistem terintegrasi untuk mendukung monitoring, pengelolaan
data, komunikasi perangkat, dan otomasi operasional kandang ayam.

Raspberry Pi berperan sebagai pusat pemrosesan dan koordinasi. Perangkat ESP32
mengirimkan data dan menerima perintah dari sistem pusat. Backend menyediakan
layanan aplikasi dan API, sedangkan database menyimpan data operasional dan data
yang digunakan oleh fitur analisis.

Pengembangan dilakukan secara bertahap. Stabilitas operasional kandang harus tetap
menjadi prioritas ketika menambah fitur atau merapikan arsitektur.

## 2. Prinsip Penting untuk Developer

Sebelum mengubah sistem:

1. Pahami alur program dan hubungan antarmodul yang terdampak.
2. Periksa pemanggil dan pengguna suatu fungsi sebelum mengubah nama, parameter,
   tipe data, atau perilakunya.
3. Hindari perubahan besar sekaligus. Pilih perubahan kecil yang dapat diuji.
4. Jangan menghapus, mengosongkan, atau mengganti database operasional tanpa
   persetujuan eksplisit.
5. Jangan mengubah konfigurasi perangkat, alamat jaringan, pin, atau protokol
   berdasarkan asumsi.
6. Pertahankan kompatibilitas dengan perangkat ESP32 yang sudah terpasang.
7. Jangan memasukkan kredensial, token, API key, atau connection string ke source
   code, dokumentasi, commit, maupun output log.
8. Jangan melakukan restart service produksi kecuali diperlukan dan disetujui.
9. Setelah perubahan Python, lakukan pemeriksaan sintaks dan pengujian yang sesuai.
10. Dokumentasikan perubahan perilaku sistem dan langkah pemulihannya.

## 3. Lingkungan Runtime

### 3.1 Perangkat dan sistem operasi

| Komponen | Informasi |
|---|---|
| Komputer utama | Raspberry Pi |
| Arsitektur | ARM64 / aarch64 |
| Sistem operasi | Debian Linux |
| Kernel yang pernah diverifikasi | `6.12.47+rpt-rpi-v8` |
| User aplikasi | `rakha` |
| Direktori proyek | `/home/rakha/Documents/Project_Kandang` |

Versi kernel di atas adalah hasil pemeriksaan pada saat dokumentasi dibuat dan
dapat berubah setelah pembaruan sistem.

### 3.2 Python environment

Virtual environment berada di:

```text
/home/rakha/Documents/Project_Kandang/venv/
```

Executable Python yang digunakan service:

```text
/home/rakha/Documents/Project_Kandang/venv/bin/python3
```

Beberapa dependency yang terdeteksi pada environment:

| Package | Versi terdeteksi |
|---|---:|
| FastAPI | 0.121.2 |
| Uvicorn | 0.38.0 |
| aiohttp | 3.13.2 |
| httpx | 0.28.1 |
| requests | 2.32.5 |
| websockets | 16.0 |
| NumPy | 2.3.5 |
| OpenCV | 4.13.0.92 |
| pandas | 2.3.3 |
| joblib | 1.5.2 |
| scikit-learn | 1.7.2 |
| psycopg2-binary | 2.9.11 |
| pyserial | 3.5 |
| pytz | 2025.2 |

Daftar ini adalah snapshot environment, bukan file dependency resmi. Periksa
environment aktual sebelum memasang, menghapus, atau memperbarui package.

## 4. Cara Aplikasi Dijalankan

### 4.1 Entry point produksi

Aplikasi produksi dijalankan melalui `main.py`, bukan `webserver.py`.

Service systemd yang digunakan adalah:

```text
kandang.service
```

Konfigurasi penting yang pernah diverifikasi:

| Parameter | Nilai |
|---|---|
| Working directory | `/home/rakha/Documents/Project_Kandang` |
| User | `rakha` |
| Program | `venv/bin/python3 main.py` |
| Host Uvicorn | `0.0.0.0` |
| Port | `8080` |
| ASGI application | `main:app` |
| Restart policy | `always` |

`main.py` mengimpor objek `app` dari `webserver.py`. Pada saat import, fungsi
`setup_awal()` dijalankan. Startup event aplikasi digunakan untuk memulai sejumlah
background task.

### 4.2 Perintah operasional

Periksa status:

```bash
sudo systemctl status kandang.service
```

Lihat log:

```bash
sudo journalctl -u kandang.service -n 100 --no-pager
```

Ikuti log secara langsung:

```bash
sudo journalctl -u kandang.service -f
```

Restart hanya jika memang diperlukan:

```bash
sudo systemctl restart kandang.service
```

Catatan: konfigurasi service yang pernah diperiksa membuang stdout dan stderr
(`StandardOutput=null` dan `StandardError=null`). Karena itu, journal mungkin tidak
menampilkan seluruh output aplikasi.

## 5. Arsitektur Tingkat Tinggi

Gambaran konseptual sistem:

```text
             ESP32 DEVICES / FIELD HARDWARE
                         |
                HTTP / WebSocket / Serial
                         |
                         v
                 RASPBERRY PI SERVER
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          FastAPI     Automation   Data Layer
          Backend      Engine      / SQLite
             |           |           |
             +-----------+-----------+
                         |
                         v
                  WEB DASHBOARD
```

Diagram ini menggambarkan kelompok komponen, bukan seluruh detail alur data.
Hubungan aktual harus ditelusuri melalui implementasi fungsi dan endpoint.

## 6. Peta Modul Python

Source code Python saat ini berada di direktori utama repository. Belum dilakukan
migrasi ke direktori `src/`.

### 6.1 Orkestrasi aplikasi

| Modul | Peran yang diketahui |
|---|---|
| `main.py` | Entry point produksi, membuat aplikasi berjalan, dan mengatur background task. |
| `state_manager.py` | Mengelola state; saat ini mengimpor `main.py`, sehingga perlu diperiksa terhadap potensi circular import. |
| `variabel_global.py` | Menyediakan variabel atau state global yang digunakan banyak modul. |

### 6.2 Monitoring dan otomasi kipas

| Modul | Peran yang diketahui |
|---|---|
| `kontrol_kipas.py` | Logika kontrol kipas. |
| `aktuator_kipas.py` | Pengelolaan aktuator kipas. |
| `sensor.py` | Pengelolaan atau pembacaan data sensor. |
| `status_esp32.py` | Status perangkat ESP32. |
| `fungsi_umum.py` | Fungsi pendukung yang dipakai beberapa modul. |

### 6.3 Database dan penyimpanan

| Modul | Peran yang diketahui |
|---|---|
| `database_sqlite.py` | Operasi database SQLite. |
| `penyimpanan_data.py` | Fungsi penyimpanan dan pengelolaan data. |

### 6.4 Web backend dan antarmuka

| Modul / direktori | Peran yang diketahui |
|---|---|
| `webserver.py` | Definisi aplikasi FastAPI, endpoint, dan integrasi backend. |
| `local_server.py` | Server atau layanan lokal pendukung. |
| `templates/` | Template halaman web. |
| `static/` | Aset frontend seperti CSS, JavaScript, dan file statis. |

`webserver.py` berukuran besar dan memuat banyak tanggung jawab. Refactor dapat
dipertimbangkan di masa depan, tetapi harus dilakukan bertahap setelah dependency
dan route dipetakan.

### 6.5 Integrasi eksternal dan jaringan

| Modul | Peran yang diketahui |
|---|---|
| `thingspeak.py` | Integrasi ThingSpeak. |
| `koneksi_blynk.py` | Integrasi Blynk. |
| `konfigurasi_n8n.py` | Dukungan konfigurasi n8n. |
| `web_scraping.py` | Pengambilan data dari sumber web. |
| `backup_upload.py` | Fitur backup atau upload. |

### 6.6 PLC / Modbus

| Modul | Peran yang diketahui |
|---|---|
| `plc_client.py` | Komunikasi client PLC. |
| `plc_network.py` | Lapisan jaringan PLC. |
| `plc_manager.py` | Pengelolaan PLC. |
| `register_map.py` | Pemetaan register. |
| `modbus.py` | Modul Modbus; status penggunaan aktifnya perlu diverifikasi. |

Pemeriksaan sebelumnya menunjukkan task PLC/Modbus di `main.py` dalam keadaan
dikomentari/nonaktif. Jangan menganggap integrasi PLC sedang berjalan hanya karena
modulnya tersedia.

### 6.7 Pengolahan gambar dan eksperimen

| Modul | Peran yang diketahui |
|---|---|
| `proses_gambar.py` | Pengolahan gambar. |
| `zona_testing.py` | Area pengujian atau eksperimen. |

Jangan menganggap modul eksperimen sebagai bagian dari jalur produksi tanpa
memeriksa pemanggilnya.

## 7. Hubungan Import Antarmodul

Peta berikut berasal dari pemeriksaan import statis. Ini membantu menemukan
ketergantungan, tetapi tidak menjamin seluruh dependency runtime karena import
dinamis atau pemanggilan tidak langsung mungkin tidak tercakup.

```text
main.py
  ├── aktuator_kipas.py
  ├── database_sqlite.py
  ├── fungsi_umum.py
  ├── kontrol_kipas.py
  ├── local_server.py
  ├── penyimpanan_data.py
  ├── sensor.py
  ├── thingspeak.py
  ├── variabel_global.py
  ├── web_scraping.py
  └── webserver.py

webserver.py
  ├── database_sqlite.py
  ├── fungsi_umum.py
  ├── kontrol_kipas.py
  ├── penyimpanan_data.py
  ├── proses_gambar.py
  ├── thingspeak.py
  └── variabel_global.py

kontrol_kipas.py
  ├── aktuator_kipas.py
  ├── database_sqlite.py
  ├── fungsi_umum.py
  ├── penyimpanan_data.py
  ├── thingspeak.py
  └── variabel_global.py

fungsi_umum.py
  ├── database_sqlite.py
  ├── penyimpanan_data.py
  ├── status_esp32.py
  └── variabel_global.py

plc_manager.py
  ├── plc_network.py
  ├── register_map.py
  └── variabel_global.py

plc_network.py
  └── plc_client.py
```

Perhatian khusus: `state_manager.py` mengimpor `main.py`. Periksa kemungkinan
circular import sebelum mengubah urutan import atau memindahkan inisialisasi.

## 8. Background Task

Pemeriksaan `main.py` sebelumnya menemukan task periodik berikut. Interval di bawah
adalah interval yang teridentifikasi saat pemeriksaan; verifikasi kembali di source
code sebelum mengubah perilakunya.

| Proses | Interval yang teridentifikasi |
|---|---:|
| Pengambilan/pengiriman data perangkat 151 | 10 detik |
| Pengambilan/pengiriman data perangkat 152 | 5 detik |
| Pengambilan/pengiriman data perangkat 154 | 1 detik |
| Pengambilan/pengiriman data perangkat 1552 | 1 detik |
| Pengambilan/pengiriman data perangkat 157 | 10 detik |
| Pengambilan/pengiriman data perangkat 158 | 10 detik |
| Pembaruan data sensor database | 60 detik |
| Pembaruan umur ayam | 10 detik |
| Pengambilan data cuaca | 60 detik |
| Pemeriksaan serial | 0,1 detik |
| Broadcast | 1 detik |
| Pengiriman ThingSpeak | 15 dan 60 detik |
| Sinkronisasi data bakul | 3600 detik |
| Penulisan dataset AI | 300 detik |
| Pembaruan tren sensor | 10 detik |
| Kontrol kipas utama | 1 detik |
| Pengiriman aktuator | 1 detik |
| Pemeriksaan ambang suhu kipas | 300 detik |
| Heartbeat | 5 detik |
| Scraping harga ayam lokal | 3600 detik |
| Penulisan data performa | 600 detik |

Angka device ID dan interval adalah catatan hasil inventarisasi, bukan kontrak API.
Jangan mengubahnya tanpa memeriksa fungsi terkait dan kebutuhan perangkat lapangan.

## 9. API dan Web Application

Informasi yang pernah diverifikasi:

| Item | Nilai |
|---|---|
| Framework | FastAPI |
| Judul aplikasi | `Kandang Controller` |
| Versi aplikasi | `1.0` |
| Prefix router API | `/api` |
| Port aplikasi | `8080` |
| Zona waktu aplikasi | `Asia/Jakarta` |
| Direktori template | `templates/` |
| Direktori static | `static/` |

Endpoint yang pernah teridentifikasi antara lain:

- `/api/dataweb`
- `/api/health`
- `/api/ws/kipas`

Daftar ini bukan daftar endpoint lengkap. Periksa route di `webserver.py` sebelum
mengandalkan nama, metode HTTP, payload, atau format respons endpoint.

## 10. Database dan Data

Database operasional utama yang pernah diperiksa:

```text
kandang_ayam.db
```

Tabel yang teridentifikasi:

| Tabel | Jumlah baris saat pemeriksaan |
|---|---:|
| `data_auto` | 42 |
| `data_bakul` | 0 |
| `data_performa` | 32.747 |
| `data_sensor` | 24 |
| `dataset_training_AI` | 53.184 |
| `konfigurasi` | 1 |
| `timbangan` | 18.769 |

Jumlah baris adalah snapshot saat pemeriksaan, bukan jumlah tetap. Data akan berubah
seiring aplikasi berjalan.

Database lain yang pernah ditemukan antara lain `backup_kandang.db` dan beberapa
file database lama atau rusak. Jangan menghapus file database hanya berdasarkan
nama atau ukuran.

### Aturan keselamatan database

- Jangan menjalankan `DROP TABLE`, `DELETE`, `VACUUM`, migrasi destruktif, atau
  penggantian database tanpa backup dan persetujuan.
- Sebelum perubahan skema, identifikasi seluruh query yang menggunakan tabel dan
  kolom terkait.
- Backup database sebelum perubahan yang berisiko.
- Perhatikan file SQLite `-wal` dan `-shm`; jangan menghapusnya ketika database
  sedang aktif.
- Jangan menyalin data operasional sensitif ke repository publik.

## 11. File Data dan Direktori

Direktori yang pernah teridentifikasi:

| Path | Kegunaan yang diketahui |
|---|---|
| `dataset_csv/` | Dataset CSV untuk pengolahan/pelatihan AI. |
| `static/` | Aset frontend. |
| `templates/` | Template web. |
| `n8n/` | Integrasi dan runtime n8n. |
| `state/` | File state atau informasi proses lokal. |
| `uploads/` | File hasil upload. |
| `docs/` | Lokasi dokumentasi teknis yang direncanakan. |

File JSON seperti `data_sensor.json` dan `data_state.json` merupakan file runtime.
Jangan menganggap isinya sebagai konfigurasi statis atau mengeditnya tanpa
memahami siapa yang menulis dan membaca file tersebut.

## 12. Git dan Repository

Repository GitHub:

```text
https://github.com/rakhaarkan/raspberry_pusat_kandang
```

Branch utama yang pernah diperiksa:

```text
main
```

Aturan kerja Git:

1. Periksa `git status` sebelum melakukan perubahan.
2. Periksa diff sebelum staging dan commit.
3. Stage hanya file yang memang dimaksud.
4. Hindari `git add .` jika terdapat database, file runtime, konfigurasi, atau
   perubahan lain yang belum ditinjau.
5. Jangan commit file kredensial, database operasional, cache, virtual environment,
   atau file runtime.
6. Sebelum push ke repository publik, pastikan tidak ada secret atau data privat
   di dalam file yang akan dikirim.

`.gitignore` telah mencakup antara lain virtual environment, file secret tertentu,
database SQLite, cache, file IDE, dan runtime privat n8n. Namun, aturan ignore tidak
otomatis menghapus file yang sudah terlanjur dilacak Git. Periksa tracked files
secara khusus sebelum commit.

## 13. Cara Pemeriksaan Setelah Perubahan

Untuk pemeriksaan sintaks beberapa file Python:

```bash
cd /home/rakha/Documents/Project_Kandang
./venv/bin/python -m py_compile main.py webserver.py database_sqlite.py
```

Perintah di atas hanya memeriksa sintaks file yang disebutkan; ia bukan pengganti
pengujian integrasi atau pengujian perangkat.

Setelah perubahan, pertimbangkan urutan berikut:

1. Periksa diff.
2. Jalankan pemeriksaan sintaks pada file terdampak.
3. Jalankan unit test jika tersedia.
4. Uji endpoint atau fungsi terkait.
5. Pastikan komunikasi ESP32 dan kontrol perangkat tidak terganggu.
6. Periksa log aplikasi.
7. Restart service hanya jika perubahan memang memerlukan reload proses.

## 14. Hal yang Perlu Ditelusuri

Bagian berikut belum boleh dianggap selesai atau pasti:

- Daftar lengkap endpoint, metode HTTP, payload, dan skema WebSocket.
- Skema lengkap tabel database beserta relasi dan indeks.
- Kontrak komunikasi setiap ESP32: ID, alamat, payload, timeout, dan retry.
- Alur lengkap kontrol kipas dari sensor sampai aktuator.
- Mekanisme sinkronisasi waktu dan penanganan koneksi terputus.
- Status pemakaian aktual modul PLC/Modbus.
- Fungsi dan status modul `local_server.py`.
- Hubungan runtime `state_manager.py` dengan `main.py`.
- Prosedur backup dan pemulihan database yang benar.
- Dependency yang benar-benar wajib dibandingkan dependency opsional.
- Test suite dan standar pengujian otomatis.

Ketika menelusuri salah satu topik tersebut, perbarui dokumen ini dengan referensi
file dan fungsi yang benar-benar ditemukan.

## 15. Peta Dokumentasi

Dokumentasi proyek direncanakan sebagai berikut:

```text
README.md
PROJECT_CONTEXT.md
CHANGELOG.md
docs/
├── architecture/
├── software/
└── operations/
```

Peran dokumen:

| Dokumen | Isi |
|---|---|
| `README.md` | Ringkasan proyek dan cara menjalankan aplikasi. |
| `PROJECT_CONTEXT.md` | Konteks teknis menyeluruh untuk developer dan AI assistant. |
| `CHANGELOG.md` | Riwayat perubahan yang berarti. |
| `docs/architecture/` | Diagram sistem, alur data, dan hubungan modul. |
| `docs/software/` | Dokumentasi backend, API, database, dan otomasi. |
| `docs/operations/` | Instalasi, deployment, backup, pemulihan, dan troubleshooting. |

---

**Prinsip utama:** pahami sistem sebelum mengubahnya, jaga operasional kandang tetap
stabil, dan lakukan pengembangan secara bertahap serta terukur.
