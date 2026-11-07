# Project Kandang

**Sistem monitoring, pengelolaan data, dan otomasi kandang ayam berbasis Raspberry Pi dan ESP32.**

---

## Deskripsi Proyek

Project Kandang merupakan sistem terintegrasi yang dikembangkan untuk mendukung operasional kandang ayam melalui teknologi monitoring, pengolahan data, komunikasi perangkat, dan otomasi.

Sistem menggunakan Raspberry Pi sebagai pusat pemrosesan dan koordinasi. Raspberry Pi menjalankan backend aplikasi, mengelola database, memproses data, serta berkomunikasi dengan perangkat ESP32 yang terpasang di lapangan.

Project ini dikembangkan secara bertahap dengan tujuan membangun infrastruktur peternakan yang lebih terukur, terintegrasi, dan dapat dikembangkan lebih lanjut.

## Fitur dan Kapabilitas

- **Monitoring:** pengumpulan dan pemantauan data kondisi kandang.
- **Otomasi:** pengendalian kipas berdasarkan logika kontrol sistem.
- **Komunikasi perangkat:** pertukaran data dan perintah antara Raspberry Pi dan ESP32.
- **Manajemen data:** penyimpanan serta pengolahan data operasional menggunakan SQLite.
- **Web application:** backend FastAPI dan antarmuka dashboard.
- **Integrasi eksternal:** dukungan integrasi layanan dan perangkat tambahan.

## Teknologi

| Komponen | Teknologi |
|---|---|
| Komputer utama | Raspberry Pi |
| Sistem operasi | Debian Linux ARM64 |
| Bahasa pemrograman | Python |
| Backend framework | FastAPI |
| Application server | Uvicorn |
| Database | SQLite |
| Mikrokontroler | ESP32 |
| Komunikasi | HTTP, WebSocket, Serial |
| Frontend | HTML, CSS, JavaScript |
| Version control | Git |
| Repository hosting | GitHub |

## Arsitektur Singkat

```text
                    ESP32 DEVICES
                         |
                 HTTP / WebSocket
                         |
                         v
                  RASPBERRY PI
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          FastAPI     Automation   Database
          Backend      Engine       SQLite
             |           |           |
             +-----------+-----------+
                         |
                         v
                   WEB DASHBOARD
```

Diagram di atas merupakan gambaran konseptual hubungan komponen utama, bukan diagram seluruh alur internal aplikasi.

## Struktur Repository

Source code Python saat ini berada di direktori utama repository.

| Direktori | Fungsi |
|---|---|
| `static/` | Aset frontend seperti CSS, JavaScript, dan file statis lainnya. |
| `templates/` | Template halaman web. |
| `dataset_csv/` | Dataset untuk pengolahan dan pelatihan model. |
| `docs/` | Dokumentasi teknis proyek. |
| `n8n/` | Integrasi dan konfigurasi n8n. |

### File Utama

| File | Fungsi |
|---|---|
| `main.py` | Entry point aplikasi dan koordinasi proses utama. |
| `webserver.py` | Backend FastAPI dan endpoint aplikasi. |
| `database_sqlite.py` | Pengelolaan database SQLite. |
| `kontrol_kipas.py` | Logika kontrol kipas. |
| `aktuator_kipas.py` | Pengelolaan aktuator kipas. |
| `variabel_global.py` | Variabel dan state global aplikasi. |

## Menjalankan Aplikasi

Aplikasi utama dijalankan melalui `main.py` menggunakan FastAPI dan Uvicorn.

### Konfigurasi Server

| Parameter | Nilai |
|---|---|
| Host | `0.0.0.0` |
| Port | `8080` |
| Entry point | `main.py` |
| ASGI application | `main:app` |

### Menjalankan melalui systemd

Aplikasi produksi dijalankan menggunakan service `kandang.service`.

Memeriksa status:

```bash
sudo systemctl status kandang.service
```

Melihat log:

```bash
sudo journalctl -u kandang.service -n 100 --no-pager
```

Restart aplikasi jika diperlukan:

```bash
sudo systemctl restart kandang.service
```

### Lingkungan Python

Aplikasi menggunakan virtual environment Python yang berada di direktori `venv/`.

## Dokumentasi

Dokumentasi teknis dikembangkan secara terpisah agar informasi proyek tetap terstruktur.

Dokumentasi yang direncanakan:

- `PROJECT_CONTEXT.md` — konteks menyeluruh proyek untuk developer dan AI coding assistant.
- `CHANGELOG.md` — riwayat perubahan dan pengembangan.
- `docs/architecture/` — dokumentasi arsitektur dan hubungan antarmodul.
- `docs/software/` — dokumentasi backend, database, dan otomasi.
- `docs/operations/` — panduan instalasi, operasional, dan troubleshooting.

## Prinsip Pengembangan

1. Menjaga kestabilan sistem yang sedang digunakan dalam operasional kandang.
2. Memahami hubungan antarmodul sebelum melakukan perubahan.
3. Mengutamakan perubahan kecil, terukur, dan dapat diuji.
4. Memisahkan source code, konfigurasi, data operasional, dan dokumentasi.
5. Mendokumentasikan perubahan arsitektur dan perilaku sistem.
6. Menjaga kompatibilitas dengan perangkat yang sudah terpasang.

---

**Project:** Project Kandang
**Platform:** Raspberry Pi + ESP32
**Status:** Active Development
