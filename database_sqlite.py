from variabel_global import gl
import sqlite3, json
from pathlib import Path
import datetime, time, statistics
import psycopg2
from decimal import Decimal
import warnings
import fungsi_umum as fu
from fastapi.responses import FileResponse

warnings.filterwarnings("ignore", category=UserWarning)


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = "/home/rakha/Documents/Project_Kandang/kandang_ayam.db"

NEON_CONN = "postgresql://kandangrakha_owner:5Psm3KGwHfdO@ep-winter-cloud-a1b56pb2.ap-southeast-1.aws.neon.tech/kandangrakha?sslmode=require"
FILE_PATH = Path("/home/rakha/Documents/Project_Kandang/data_state.json")

db = sqlite3.connect("/home/rakha/Documents/Project_Kandang/kandang_ayam.db")
cur = db.cursor()
def _get_conn():
    return sqlite3.connect(DB_PATH)

def _to_int_no_decimal(value):
    """Ubah float ke integer tanpa koma (x10)."""
    if value is None:
        return 0
    try:
        return int(round(value * 10))  # 33.7 -> 337
    except:
        return 0
    
import sqlite3

def init_db():
    """Inisialisasi semua tabel SQLite. Jalankan sekali saat startup."""

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA temp_store=MEMORY")
        cur.execute("PRAGMA cache_size=10000")
        cur.execute("PRAGMA wal_autocheckpoint=1000")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS data_sensor (
                jam INTEGER PRIMARY KEY,
                timestamp TEXT,
                suhu_atas REAL,
                suhu_bawah REAL,    
                suhu_luar REAL,
                kelembapan_atas REAL,
                kelembapan_bawah REAL,
                kelembapan_luar REAL,
                kwh_jam REAL
            )
        """)
        for jam in range(24):
            cur.execute("""
                INSERT OR IGNORE INTO data_sensor (jam)
                VALUES (?)
            """, (jam,))

        cur.execute("""
            CREATE TABLE IF NOT EXISTS data_auto (
                usia_ayam INTEGER PRIMARY KEY,
                d1 TEXT NOT NULL,
                d2 TEXT NOT NULL,
                d3 TEXT NOT NULL,
                d4 TEXT NOT NULL,
                d5 TEXT NOT NULL,
                d6 TEXT NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS data_bakul (
                id INTEGER PRIMARY KEY,
                tanggal TEXT,
                nama_do TEXT,
                nama_bakul TEXT,
                plat_nomor TEXT,
                jumlah_ekor_ambil INTEGER,
                jumlah_kg_ambil REAL
            );
        """)
            
        cur.execute("""
        CREATE TABLE IF NOT EXISTS konfigurasi (
            id INTEGER PRIMARY KEY CHECK (id = 1),

            mode_kandang INTEGER,
            usia_ayam INTEGER,
            tanggal_masuk_ayam TEXT,

            jumlah_kipas_timer INTEGER,
            waktu_hidup INTEGER,
            waktu_mati INTEGER,

            jumlah_ayam_awal INTEGER,
            jumlah_ayam_mati INTEGER,
            jumlah_pakan_sak INTEGER,
            bobot_rata_rata REAL,

            harga_kontrak_ayam INTEGER,
            harga_bibit_ayam INTEGER,
            harga_obat_ayam INTEGER,
            harga_pakan_kg INTEGER,

            jumlah_ayam_dipanen INTEGER,

            cek_proteksi_listrik INTEGER,
            flag_database_AI INTEGER,
            flag_alarm_siaga INTEGER
        )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS timbangan (
                device_id INTEGER,
                timestamp INTEGER,
                weight REAL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS dataset_training_AI (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp INTEGER NOT NULL,
                mode_kandang INTEGER NOT NULL,
                usia_ayam INTEGER NOT NULL,
                hari_ke REAL NOT NULL,
                jam INTEGER NOT NULL,
                menit INTEGER NOT NULL,
                is_malam INTEGER NOT NULL,
                jam_mandatori_kipas INTEGER NOT NULL,
                suhu_dalam REAL NOT NULL,
                suhu_luar REAL NOT NULL,
                kelembapan_dalam REAL NOT NULL,
                kelembapan_luar REAL NOT NULL,
                target_suhu REAL NOT NULL,
                trend_suhu_dalam_10m REAL NOT NULL,
                trend_suhu_luar_10m REAL NOT NULL,
                trend_kelembapan_dalam_10m REAL NOT NULL,
                trend_kelembapan_luar_10m REAL NOT NULL,
                selisih_suhu_luar_dalam REAL NOT NULL,
                selisih_kelembapan_luar_dalam REAL NOT NULL,
                is_heater INTEGER NOT NULL,
                is_celldeck INTEGER NOT NULL,
                kecepatan_angin REAL NOT NULL,
                kode_cuaca INTEGER NOT NULL,
                bobot_rata_rata REAL NOT NULL,
                daya_listrik REAL NOT NULL,
                energy REAL NOT NULL,
                kipas_prev_1 INTEGER NOT NULL,
                kipas_prev_2 INTEGER NOT NULL,
                kipas_prev_3 INTEGER NOT NULL,
                kipas_prev_4 INTEGER NOT NULL,
                kipas_prev_5 INTEGER NOT NULL,

                kipas_1 INTEGER NOT NULL,
                kipas_2 INTEGER NOT NULL,
                kipas_3 INTEGER NOT NULL,
                kipas_4 INTEGER NOT NULL,
                kipas_5 INTEGER NOT NULL,
                mode_operasi INTEGER NOT NULL,
                waktu_hidup_timer INTEGER NOT NULL,
                waktu_mati_timer INTEGER NOT NULL,
                skala_kipas INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS data_performa (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                usia_ayam INTEGER,
                tanggal_masuk_ayam TEXT,

                jumlah_ayam_awal INTEGER,
                jumlah_ayam_mati INTEGER,
                jumlah_pakan_sak INTEGER,

                bobot_rata_rata_timbang INTEGER,

                harga_kontrak_ayam INTEGER,
                harga_bibit_ayam INTEGER,
                harga_obat_ayam INTEGER,
                harga_pakan_kg INTEGER,

                jumlah_ayam_dipanen INTEGER,

                harga_pasar TEXT,

                waktu_simpan TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )

        """)

        conn.commit()
        print("[init_db] Semua tabel siap digunakan.")

    except Exception as e:
        print("[init_db] ERROR:", e)

    finally:
        conn.close()

def update_database_many(data_dict):
    jam = datetime.datetime.now().hour
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build SQL SET clause dynamically
    set_parts = [f"{key} = ?" for key in data_dict.keys()]
    set_clause = ", ".join(set_parts) + ", timestamp = ?"

    # Build value tuple
    values = list(data_dict.values())
    values.append(timestamp)  # add timestamp at the end
    values.append(jam)        # last param for WHERE jam = ?

    query = f"""
        UPDATE data_sensor
        SET {set_clause}
        WHERE jam = ?
    """

    # Single connection only
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()

    print(f"Updated jam {jam}: {data_dict}")

def update_db_sensor_24():
    update_database_many({
        "suhu_atas": gl.suhu_atas,
        "suhu_bawah": gl.suhu_bawah,
        "suhu_luar": gl.suhu_luar,
        "kelembapan_atas": gl.kelembapan_atas,
        "kelembapan_bawah": gl.kelembapan_bawah,
        "kelembapan_luar": gl.kelembapan_luar,
        "kwh_jam": gl.kwh_jam
    })
    
def baca_sql_sensor():
    """Baca data dari SQLite dan isi grafik gl.* mirip baca_json_sensor()."""

    # Jika database tidak ada ? kosongkan grafik
    if not Path(DB_PATH).exists():
        for i in range(1, 25):
            gl.grafik_suhu_atas[i]       = None
            gl.grafik_kelembapan_luar[i] = None
            gl.grafik_suhu_luar[i]       = None
            #gl.grafik_kwh_listrik[i]     = None

        print("[baca_sql_sensor] DB tidak ditemukan, grafik dikosongkan.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Ambil semua 24 jam sekaligus
        cur.execute("SELECT jam, suhu_atas, suhu_luar, kelembapan_luar, kwh_jam FROM data_sensor")
        rows = cur.fetchall()

    except Exception as e:
        print("[baca_sql_sensor] ERROR membaca SQLite:", e)
        return
    finally:
        conn.close()

    # Isi grafik
    # Pastikan di-set None dulu
    for i in range(1, 24):
        gl.grafik_suhu_atas[i]       = None
        gl.grafik_kelembapan_luar[i] = None
        gl.grafik_suhu_luar[i]       = None
#         gl.grafik_kwh_listrik[i]     = None

    current_hour = gl.jam

    for row in rows:
        jam, suhu_atas, suhu_luar, kelembapan_luar, kwh_jam = row

        # hitung index grafik berdasarkan offset dari current_hour
        offset = (int(jam) - current_hour) % 24  # wrap around
        idx = offset  # langsung dipakai sebagai index 0..23

        gl.grafik_suhu_atas[idx]       = _to_int_no_decimal(suhu_atas)
        gl.grafik_kelembapan_luar[idx] = _to_int_no_decimal(kelembapan_luar)
        gl.grafik_suhu_luar[idx]       = _to_int_no_decimal(suhu_luar)
        # gl.grafik_kwh_listrik[idx]   = _to_int_no_decimal(kwh_jam)

    print("[baca_sql_sensor] Grafik diperbarui dari SQLite.")

def fetch_from_neon():
    pg_conn = None
    try:
        pg_conn = psycopg2.connect(NEON_CONN)
        pg_cur = pg_conn.cursor()

        pg_cur.execute("SELECT id, tanggal, nama_do, nama_bakul, plat_nomor, jumlah_ekor_ambil, jumlah_kg_ambil FROM data_bakul")
        rows = pg_cur.fetchall()
        return rows

    except Exception as e:
        print("Gagal membaca dari Neon PostgreSQL:", e)
        return None

    finally:
        if pg_conn:
            pg_conn.close()



# -------------------------------
# FUNGSI SYNC KE SQLITE
# -------------------------------
def sync_data_bakul():
    rows = fetch_from_neon()
    if rows is None:
        print("Sync gagal: tidak bisa baca dari Neon.")
        return

    # Koneksi SQLite
    sqlite_db = sqlite3.connect(DB_PATH)
    sqlite_cur = sqlite_db.cursor()

    # Bersihkan Decimal -> float
    cleaned_rows = []
    for row in rows:
        cleaned = [(float(v) if isinstance(v, Decimal) else v) for v in row]
        cleaned_rows.append(tuple(cleaned))
        
    sqlite_cur.execute("DELETE FROM data_bakul")
    # Insert OR replace
    insert_query = """
        INSERT INTO data_bakul 
        (id, tanggal, nama_do, nama_bakul, plat_nomor, jumlah_ekor_ambil, jumlah_kg_ambil)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    sqlite_cur.executemany(insert_query, cleaned_rows)
    sqlite_db.commit()
    sqlite_db.close()

    print("Sinkronisasi data_bakul berhasil.")

def load_data_bakul():

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Ambil maksimal 25 baris terbaru
        cur.execute("SELECT * FROM data_bakul ORDER BY id DESC LIMIT 25")
        rows = cur.fetchall()

        # Reset isi array
        gl.db_id = [0] * 25
        gl.db_tanggal = [""] * 25
        gl.db_nama_do = [""] * 25
        gl.db_nama_bakul = [""] * 25
        gl.db_plat_nomor = [""] * 25
        gl.db_jumlah_ekor_ambil = [0] * 25
        gl.db_jumlah_kg_ambil = [0.0] * 25
        gl.db_total_bakul = 0
        gl.db_total_ekor_panen = 0
        gl.db_total_kg_panen = 0.0

        # Masukkan data hasil query
        for i, row in enumerate(rows):
            # Row order: (id, tanggal, nama_do, nama_bakul, plat_nomor, ekor, kg)
            gl.db_id[i] = row[0]
            gl.db_tanggal[i] = row[1]
            gl.db_nama_do[i] = row[2]
            gl.db_nama_bakul[i] = row[3]
            gl.db_plat_nomor[i] = row[4]
            gl.db_jumlah_ekor_ambil[i] = int(row[5])
            gl.db_jumlah_kg_ambil[i] = float(row[6])
            gl.db_total_bakul += 1
            gl.db_total_ekor_panen += int(row[5])
            gl.db_total_kg_panen += float(row[6])

        print("Data bakul berhasil dimuat ke variabel global.")

    except Exception as e:
        print("Gagal membaca SQLite:", e)

    finally:
        conn.close()
        
def hitung_jam_mandatori_kipas():
    # Gunakan jam saat ini jika gl.jam tidak ada
    try:
        jam = int(gl.jam)
    except:
        jam = localtime().tm_hour

    # --- Kategori 1: malam - pagi ---
    if jam >= 19 or jam <= 8:
        gl.jam_mandatori_kipas = 1

    # --- Kategori 2: pagi & sore ---
    elif (9 <= jam <= 11) or (16 <= jam <= 18):
        gl.jam_mandatori_kipas = 2

    # --- Kategori 3: siang ---
    elif 12 <= jam <= 15:
        gl.jam_mandatori_kipas = 3


def hitung_skala_kipas():
    gl.skala_kipas = gl.kipas[0]*33 + gl.kipas[1]*11 + gl.kipas[2]*11 + gl.kipas[3]*11 + gl.kipas[4]*33
    

def pengisi_db_kosong(var_name):
    """
    Jika variabel global gl.var_name = 0 atau None,
    maka ambil nilai terakhir dari database (dataset_training_AI).
    """
    if not hasattr(gl, var_name):
        print(f"[WARNING] gl.{var_name} tidak ditemukan.")
        return

    val = getattr(gl, var_name)
    
    if val not in (0, None):
        # Sudah terisi, tidak perlu update
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Ambil baris terakhir untuk kolom tersebut
        c.execute(f"""
            SELECT {var_name} 
            FROM dataset_training_AI
            ORDER BY id DESC
            LIMIT 1
        """)
        row = c.fetchone()
        conn.close()
        
        if row is not None and row[0] is not None:
            setattr(gl, var_name, row[0])
            print(f"[INFO] gl.{var_name} diisi dari database: {row[0]}")
        else:
            print(f"[INFO] Tidak ada data sebelumnya untuk gl.{var_name}, tetap 0/None.")
        
    except Exception as e:
        print(f"[ERROR] pengisi_db_kosong gagal: {e}")

last_insert_ms = 0

def tulis_dataset_AI():
    if (gl.flag_database_AI == 0):
        gl.debug_str[1] = "tulis database SQLite ditolak"
        print("tulis database SQLite ditolak")
        return
            
    global last_insert_ms

    now_ms = int(time.time() * 1000)
    if now_ms - last_insert_ms < 10000:  # 1.5 detik
        print("[SKIP] Insert dibatalkan untuk mencegah duplikasi.")
        return

    if(gl.usia_ayam>40):
        print("penulisan database AI dibatalkan, tidak memenuhi kriteria")
    # --- Semua kolom fitur dan target ---
    kolom = [
        # Fitur
        "timestamp", "mode_kandang", "usia_ayam", "hari_ke", "jam", "menit",
        "is_malam", "jam_mandatori_kipas", "suhu_dalam", "suhu_luar",
        "kelembapan_dalam", "kelembapan_luar", "target_suhu",
        "trend_suhu_dalam_10m", "trend_suhu_luar_10m",
        "trend_kelembapan_dalam_10m", "trend_kelembapan_luar_10m",
        "selisih_suhu_luar_dalam", "selisih_kelembapan_luar_dalam",
        "is_heater", "is_celldeck", "kecepatan_angin", "kode_cuaca",
        "bobot_rata_rata", "daya_listrik", "energy",
        "kipas_prev_1", "kipas_prev_2", "kipas_prev_3", "kipas_prev_4", "kipas_prev_5",

        # Target
        "kipas_1", "kipas_2", "kipas_3", "kipas_4", "kipas_5",
        "mode_operasi", "waktu_hidup_timer", "waktu_mati_timer", "skala_kipas"
    ]
    kolom_2 = [
        # Fitur
        "timestamp", "mode_kandang", "jam_mandatori_kipas", "suhu_dalam", "suhu_luar",
        "kelembapan_dalam", "kelembapan_luar", "target_suhu",
        "kode_cuaca","bobot_rata_rata", "daya_listrik", "energy",
        "mode_operasi", "skala_kipas"
    ]
    
    # Timestamp milidetik
    gl.timestamp = int(time.time() * 1000)
    #gl.hari_ke = float(gl.usia_ayam)
    now = time.localtime()
    gl.jam = now.tm_hour
    gl.menit = now.tm_min
    gl.is_malam = 1 if gl.jam >= 18 or gl.jam < 6 else 0
    hitung_jam_mandatori_kipas()
    hitung_skala_kipas()
    #fu.tanggal_waktu_usia()
    gl.kipas_1 = gl.kipas[0]
    gl.kipas_2 = gl.kipas[1]
    gl.kipas_3 = gl.kipas[2]
    gl.kipas_4 = gl.kipas[3]
    gl.kipas_5 = gl.kipas[4]
    gl.kipas_prev_1 = gl.kipas[0]
    gl.kipas_prev_2 = gl.kipas[1]
    gl.kipas_prev_3 = gl.kipas[2]
    gl.kipas_prev_4 = gl.kipas[3]
    gl.kipas_prev_5 = gl.kipas[4]
    if gl.bobot_rata_rata == 0:
        gl.bobot_rata_rata = 1000
    # --- Ambil semua nilai dari modul global gl ---
    # Daftar variabel yang ingin dicek
    variabel_yang_bisa_kosong = [
        "suhu_luar", "kelembapan_luar",
        "bobot_rata_rata", "daya_listrik", "energy",
        "kode_cuaca"
    ]

    # Isi variabel 0 dengan data terakhir dari DB
    for var in variabel_yang_bisa_kosong:
        pengisi_db_kosong(var)


    for z in kolom_2:
        if not hasattr(gl, z):
            print(f"[ERROR] Variabel gl.{z} tidak ditemukan.")
            gl.debug_str[1] = f"[ERROR] Variabel gl.{z} tidak ditemukan."
            return
        
        val = getattr(gl, z)

        # Jika ada yang None/NULL ? keluar
        if val is None:
            print(f"[WARNING] Data NULL pada '{z}', cancel insert.")
            gl.debug_str[1] = f"[WARNING] Data NULL pada '{z}', cancel insert."
            return
        
        if val == 0:
            print(f"[WARNING] Data NULL pada '{z}', cancel insert.")
            gl.debug_str[1] = f"[WARNING] Data NULL pada '{z}', insert.dilanjutkan"
        
    data = {}
    for k in kolom:
        if not hasattr(gl, k):
            print(f"[ERROR] Variabel gl.{k} tidak ditemukan.")
            gl.debug_str[1] = f"[ERROR] Variabel gl.{k} tidak ditemukan."
            return
        
        val = getattr(gl, k)

        data[k] = val

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # --- Query insert ---
        placeholder = ",".join(["?"] * len(kolom))
        query = f"""
            INSERT INTO dataset_training_AI ({",".join(kolom)})
            VALUES ({placeholder})
        """

        # --- Eksekusi insert ---
        c.execute(query, tuple(data[k] for k in kolom))
        conn.commit()
        conn.close()

        print("[OK] Data berhasil ditulis ke SQLite.")
        gl.debug_str[1] = f"[OK] Data berhasil ditulis ke SQLite."
        last_insert_ms = now_ms


    except Exception as e:
        print(f"[ERROR] Gagal insert dataset: {e}")
        gl.debug_str[1] = f"[ERROR] Gagal insert dataset: {e}"
            
        return

def simpan_konfigurasi_default(data: dict):
    """
    Menyimpan seluruh konfigurasi default ke tabel data_auto.
    Akan menimpa data lama jika usia_ayam sama.
    """
    conn = _get_conn()
    cur = conn.cursor()
    
    query = """
        INSERT OR REPLACE INTO data_auto
        (usia_ayam, d1, d2, d3, d4, d5, d6)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    rows = []
    for usia, cfg in data.items():
        # pastikan panjang cfg = 6
        d1, d2, d3, d4, d5, d6 = cfg
        rows.append((usia, d1, d2, d3, d4, d5, d6))

    try:
        cur.executemany(query, rows)
        conn.commit()
        print(f"[simpan_konfigurasi_default] {len(rows)} baris disimpan")
    except Exception as e:
        print("[simpan_konfigurasi_default] ERROR:", e)
    finally:
        conn.close()

def edit_baris_konf_auto(
    usia_ayam: int,
    d1: str,
    d2: str,
    d3: str,
    d4: str,
    d5: str,
    d6: str
):
    """
    Mengedit / menimpa 1 baris konfigurasi auto berdasarkan usia_ayam
    """
    conn = _get_conn()
    cur = conn.cursor()
    
    query = """
        INSERT OR REPLACE INTO data_auto
        (usia_ayam, d1, d2, d3, d4, d5, d6)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    try:
        cur.execute(query, (usia_ayam, d1, d2, d3, d4, d5, d6))
        conn.commit()
        print(f"[edit_baris_konf_auto] usia {usia_ayam} diperbarui")
    except Exception as e:
        print("[edit_baris_konf_auto] ERROR:", e)
    finally:
        conn.close()

def baca_baris_auto(usia_ayam: int):
    """
    Membaca konfigurasi auto berdasarkan usia_ayam
    Return: list [d1, d2, d3, d4, d5, d6] atau None
    """
    conn = _get_conn()
    cur = conn.cursor()

    query = """
        SELECT d1, d2, d3, d4, d5, d6
        FROM data_auto
        WHERE usia_ayam = ?
    """

    try:
        cur.execute(query, (usia_ayam,))
        row = cur.fetchone()
        if row is None:
            return None
        return list(row)
    except Exception as e:
        print("[baca_baris_auto] ERROR:", e)
        return None
    finally:
        conn.close()


def simpan_data_sqlite():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    cur = conn.cursor()

    # 1. Pastikan tabel ada

    # 2. Konversi tanggal ke string
    tanggal_str = fu._serialize_dt(gl.tanggal_masuk_ayam)

    # 3. Simpan / update data
    cur.execute("""
    INSERT INTO konfigurasi (
        id,
        mode_kandang,
        usia_ayam,
        tanggal_masuk_ayam,
        jumlah_kipas_timer,
        waktu_hidup,
        waktu_mati,
        jumlah_ayam_awal,
        jumlah_ayam_mati,
        jumlah_pakan_sak,
        bobot_rata_rata,
        harga_kontrak_ayam,
        harga_bibit_ayam,
        harga_obat_ayam,
        harga_pakan_kg,
        jumlah_ayam_dipanen,
        cek_proteksi_listrik,
        flag_database_AI,
        flag_alarm_siaga
    )
    VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(id) DO UPDATE SET
        mode_kandang=excluded.mode_kandang,
        usia_ayam=excluded.usia_ayam,
        tanggal_masuk_ayam=excluded.tanggal_masuk_ayam,
        jumlah_kipas_timer=excluded.jumlah_kipas_timer,
        waktu_hidup=excluded.waktu_hidup,
        waktu_mati=excluded.waktu_mati,
        jumlah_ayam_awal=excluded.jumlah_ayam_awal,
        jumlah_ayam_mati=excluded.jumlah_ayam_mati,
        jumlah_pakan_sak=excluded.jumlah_pakan_sak,
        bobot_rata_rata=excluded.bobot_rata_rata,
        harga_kontrak_ayam=excluded.harga_kontrak_ayam,
        harga_bibit_ayam=excluded.harga_bibit_ayam,
        harga_obat_ayam=excluded.harga_obat_ayam,
        harga_pakan_kg=excluded.harga_pakan_kg,
        jumlah_ayam_dipanen=excluded.jumlah_ayam_dipanen,
        cek_proteksi_listrik=excluded.cek_proteksi_listrik,
        flag_database_AI=excluded.flag_database_AI,
        flag_alarm_siaga=excluded.flag_alarm_siaga
    """, (
        gl.mode_kandang,
        gl.usia_ayam,
        tanggal_str,

        gl.jumlah_kipas_timer,
        gl.waktu_hidup,
        gl.waktu_mati,

        gl.jumlah_ayam_awal,
        gl.jumlah_ayam_mati,
        gl.jumlah_pakan_sak,
        gl.bobot_rata_rata,

        gl.harga_kontrak_ayam,
        gl.harga_bibit_ayam,
        gl.harga_obat_ayam,
        gl.harga_pakan_kg,

        gl.jumlah_ayam_dipanen,

        gl.cek_proteksi_listrik,
        gl.flag_database_AI,
        gl.flag_alarm_siaga
    ))

    conn.commit()
    conn.close()

def muat_konfigurasi_sqlite():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cur = conn.cursor()

        cur.execute("""
        SELECT
            mode_kandang,
            usia_ayam,
            tanggal_masuk_ayam,
            jumlah_kipas_timer,
            waktu_hidup,
            waktu_mati,
            jumlah_ayam_awal,
            jumlah_ayam_mati,
            jumlah_pakan_sak,
            bobot_rata_rata,
            harga_kontrak_ayam,
            harga_bibit_ayam,
            harga_obat_ayam,
            harga_pakan_kg,
            jumlah_ayam_dipanen,
            cek_proteksi_listrik,
            flag_database_AI,
            flag_alarm_siaga
        FROM konfigurasi
        WHERE id = 1
        """)

        row = cur.fetchone()
        conn.close()

        if not row:
            print("[muat_konfigurasi] Data kosong, pakai default")
            return

        (
            gl.mode_kandang,
            gl.usia_ayam,
            tanggal_str,
            gl.jumlah_kipas_timer,
            gl.waktu_hidup,
            gl.waktu_mati,
            gl.jumlah_ayam_awal,
            gl.jumlah_ayam_mati,
            gl.jumlah_pakan_sak,
            gl.bobot_rata_rata,
            gl.harga_kontrak_ayam,
            gl.harga_bibit_ayam,
            gl.harga_obat_ayam,
            gl.harga_pakan_kg,
            gl.jumlah_ayam_dipanen,
            gl.cek_proteksi_listrik,
            gl.flag_database_AI,
            gl.flag_alarm_siaga
        ) = row

        # konversi string → datetime
        try:
            gl.tanggal_masuk_ayam = datetime.datetime.strptime(
                tanggal_str,
                "%Y-%m-%d %H:%M:%S.%f"
            )
        except ValueError:
            gl.tanggal_masuk_ayam = datetime.datetime.strptime(
                tanggal_str,
                "%Y-%m-%d %H:%M:%S"
            )

        #print("[muat_konfigurasi] Konfigurasi dimuat dari SQLite")

    except Exception as e:
        print("[muat_konfigurasi] ERROR:", e)

def simpan_data_performa_sqlite():

    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cur = conn.cursor()

        # datetime -> string
        tanggal_str = fu._serialize_dt(gl.tanggal_masuk_ayam)

        # list -> json string
        harga_pasar_json = json.dumps(gl.harga_pasar)

        # INSERT histori baru
        cur.execute("""

        INSERT INTO data_performa (

            usia_ayam,
            tanggal_masuk_ayam,

            jumlah_ayam_awal,
            jumlah_ayam_mati,
            jumlah_pakan_sak,

            bobot_rata_rata_timbang,

            harga_kontrak_ayam,
            harga_bibit_ayam,
            harga_obat_ayam,
            harga_pakan_kg,

            jumlah_ayam_dipanen,

            harga_pasar

        )

        VALUES (

            ?,?,
            ?,?,?,
            ?,
            ?,?,?,?,
            ?,
            ?

        )

        """, (

            gl.usia_ayam,
            tanggal_str,

            gl.jumlah_ayam_awal,
            gl.jumlah_ayam_mati,
            gl.jumlah_pakan_sak,

            gl.bobot_rata_rata_timbang,

            gl.harga_kontrak_ayam,
            gl.harga_bibit_ayam,
            gl.harga_obat_ayam,
            gl.harga_pakan_kg,

            gl.jumlah_ayam_dipanen,

            harga_pasar_json

        ))

        conn.commit()
        conn.close()

        #print("[SQLite] Histori performa tersimpan")

    except Exception as e:

        print("[simpan_data_sqlite] ERROR:", e)

def muat_kipas_dari_json():
    if not FILE_PATH.exists():
        print("[muat_kipas] File tidak ditemukan, pakai default")
        return

    try:
        with open(FILE_PATH, "r") as f:
            data = json.load(f)

        kipas = data.get("kipas")
        if isinstance(kipas, list) and len(kipas) == 5:
            gl.kipas = kipas
            print("[muat_kipas] Kipas dimuat:", gl.kipas)
        else:
            print("[muat_kipas] Format kipas invalid, pakai default")

    except Exception as e:
        print("[muat_kipas] ERROR parsing JSON:", e)

def muat_data():
    muat_kipas_dari_json()
    muat_konfigurasi_sqlite()

import sqlite3
import time

def simpan_timbangan(data: dict):

    print("Menerima data timbangan:", data)

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cur = conn.cursor()

        # timestamp dari Raspberry Pi
        timestamp = int(time.time())

        device_id = int(data.get("device_id"))
        weight = float(data.get("weight"))

        cur.execute(
            "INSERT INTO timbangan (device_id, timestamp, weight) VALUES (?,?,?)",
            (device_id, timestamp, weight)
        )

        conn.commit()
        print("Data timbangan disimpan ke SQLite.")

    except Exception as e:
        print("DB Error:", e)

    finally:
        conn.close()

def ambil_data_db_timbangan(limit=200):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT weight FROM timbangan ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()

    # 🔥 ambil list & urutkan dari lama → baru
    data = [r[0] for r in rows]
    data.reverse()

    # 🔥 kalau data sedikit, langsung pakai
    if len(data) <= 10:
        gl.list_bobot_timbang = data
        return data

    # 🔥 10 data terakhir (paling relevan dengan kondisi sekarang)
    last_10 = data[-10:]

    # 🔥 baseline rata-rata
    avg_last_10 = sum(last_10) / len(last_10)

    # 🔥 threshold (10x lipat dari baseline)
    threshold = avg_last_10 * 10

    # 🔥 filter data lama (190 data awal)
    filtered = []

    for x in data[:-10]:
        if x <= threshold:
            filtered.append(x)

    # 🔥 gabungkan kembali dengan 10 data terbaru (selalu dipakai)
    hasil = filtered + last_10
    gl.list_bobot_timbang = hasil
    return hasil

from datetime import timedelta

def ambil_sample_hari_ini():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now = datetime.datetime.now()
    awal_hari = datetime.datetime(now.year, now.month, now.day)

    awal_ts = int(awal_hari.timestamp())

    cur.execute("""
        SELECT COUNT(*) FROM timbangan
        WHERE timestamp >= ?
    """, (awal_ts,))

    jumlah = cur.fetchone()[0]
    conn.close()

    return jumlah

def ambil_sample_kemarin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now = datetime.datetime.now()

    awal_hari_ini = datetime.datetime(now.year, now.month, now.day)
    awal_kemarin = awal_hari_ini - timedelta(days=1)
    akhir_kemarin = awal_hari_ini

    awal_ts = int(awal_kemarin.timestamp())
    akhir_ts = int(akhir_kemarin.timestamp())

    cur.execute("""
        SELECT COUNT(*) FROM timbangan
        WHERE timestamp >= ? AND timestamp < ?
    """, (awal_ts, akhir_ts))

    jumlah = cur.fetchone()[0]
    conn.close()

    return jumlah

import statistics
import time

def hitung_statistik_bobot():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT weight FROM timbangan ORDER BY timestamp DESC LIMIT ?", (200,))
    rows = cur.fetchall()

    conn.close()

    data = ambil_data_db_timbangan()

    gl.list_bobot_timbang = data

    # =====================
    # BASIC STATISTIK
    # =====================
    jumlah = len(data)
    rata = sum(data) / jumlah
    dev = statistics.pstdev(data) if jumlah > 1 else 0

    bawah = rata - dev
    atas = rata + dev

    # =====================
    # ISI GLOBAL
    # =====================
    gl.bobot_timbang = int(data[-1])  # data terakhir
    gl.bobot_rata_rata_timbang = int(rata)
    gl.jumlah_sample_timbang = ambil_sample_hari_ini()
    gl.jumlah_sample_timbang_kemarin = ambil_sample_kemarin()

    gl.standar_bobot = int(rata)
    gl.standar_deviasi_bobot = int(dev)
    gl.standar_deviasi_atas = int(atas)
    gl.standar_deviasi_bawah = int(bawah)

    # =====================
    # PERSENTASE SEBARAN
    # =====================
    dalam_range = [x for x in data if bawah <= x <= atas]
    persen_dalam = (len(dalam_range) / jumlah) * 100

    gl.persentase_dalam_standar = int(persen_dalam)
    gl.persentase_standar_deviasi = int((dev / rata) * 100) if rata != 0 else 0

    # =====================
    # ADG (Average Daily Gain)
    # =====================
    hitung_adg_rolling()


def hitung_adg_rolling(
    min_sample=30,
    min_unique_weight=5,
    max_days_back=7
):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now_ts = int(datetime.datetime.now().timestamp())

    # =====================================================
    # Window sekarang (24 jam terakhir)
    # =====================================================

    w_now_start = now_ts - (24 * 3600)

    cur.execute("""
        SELECT
            AVG(weight),
            COUNT(*),
            COUNT(DISTINCT weight)
        FROM timbangan
        WHERE timestamp >= ?
        AND timestamp < ?
    """, (w_now_start, now_ts))

    avg_now, sample_now, unique_now = cur.fetchone()

    if avg_now is None:

        conn.close()

        return {
            "success": False,
            "error": "Tidak ada data 24 jam terakhir"
        }

    # =====================================================
    # PRIORITAS WINDOW
    # =====================================================
    # Prioritas:
    # 3 → 4 → 5 → 6 → 7 → 2 → 1
    # =====================================================

    priority_days = []

    # mulai dari 3 hari dulu
    for d in range(3, max_days_back + 1):
        priority_days.append(d)

    # lalu fallback ke 2 dan 1
    if max_days_back >= 2:
        priority_days.append(2)

    priority_days.append(1)

    # =====================================================
    # Cari historical window valid
    # =====================================================

    historical_found = False

    for day_back in priority_days:

        end_ts = w_now_start - ((day_back - 1) * 24 * 3600)
        start_ts = end_ts - (24 * 3600)

        cur.execute("""
            SELECT
                AVG(weight),
                COUNT(*),
                COUNT(DISTINCT weight)
            FROM timbangan
            WHERE timestamp >= ?
            AND timestamp < ?
        """, (start_ts, end_ts))

        avg_hist, sample_hist, unique_hist = cur.fetchone()

        # ================================================
        # Debug info
        # ================================================

        print(
            f"[CHECK] H-{day_back} | "
            f"AVG={avg_hist} | "
            f"SAMPLE={sample_hist} | "
            f"UNIQUE={unique_hist}"
        )

        # ================================================
        # Validasi historical window
        # ================================================

        if avg_hist is None:
            continue

        if sample_hist < min_sample:
            continue

        if unique_hist < min_unique_weight:
            continue

        # ================================================
        # Historical valid ditemukan
        # ================================================

        historical_found = True

        print(f"[SELECTED] Menggunakan H-{day_back}")

        break

    conn.close()

    # =====================================================
    # Tidak ada historical valid
    # =====================================================

    if not historical_found:

        return {
            "success": False,
            "error": (
                f"Tidak ditemukan historical window valid "
                f"dalam {max_days_back} hari"
            ),
            "confidence": "LOW"
        }

    # =====================================================
    # Hitung ADG
    # =====================================================

    days_interval = day_back

    adg = (avg_now - avg_hist) / days_interval

    # =====================================================
    # Confidence score
    # =====================================================

    confidence_score = sample_hist * unique_hist

    gl.average_daily_gain = round(adg, 2)

    print(
        f"[ADG] {adg:.2f} | "
        f"Confidence Score: {confidence_score} | "
        f"Samples: {sample_now} vs {sample_hist} | "
        f"Unique: {unique_now} vs {unique_hist} | "
        f"Interval: {days_interval} hari"
    )

    return {

        "success": True,

        "adg": round(adg, 2),

        "days_interval": days_interval,

        "avg_now": round(avg_now, 2),

        "avg_historical": round(avg_hist, 2),

        "sample_now": sample_now,

        "sample_historical": sample_hist,

        "unique_now": unique_now,

        "unique_historical": unique_hist,

        "confidence_score": confidence_score,

        "confidence": "HIGH"
    }

def download_db(DB_PATH):
    backup_path = "backup_kandang.db"

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(backup_path)

    with dst:
        src.backup(dst)

    src.close()
    dst.close()

    return FileResponse(
        backup_path,
        filename="kandang_ayam_backup.db",
        media_type="application/octet-stream"
    )

def ekstrak_kwh_24():
    import sqlite3, time

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now_sec = int(time.time())
    now_ms = now_sec * 1000
    batas_24_jam_ms = (now_sec - 24 * 3600) * 1000

    # 🔹 Ambil timestamp terakhir tiap jam (24 jam terakhir)
    cur.execute("""
        SELECT MAX(timestamp)
        FROM dataset_training_AI
        WHERE timestamp >= ?
        GROUP BY strftime('%Y-%m-%d %H', timestamp/1000, 'unixepoch', 'localtime')
        ORDER BY MAX(timestamp) ASC
    """, (batas_24_jam_ms,))

    ts_list = [row[0] for row in cur.fetchall()]
    print("Jumlah jam terdeteksi:", len(ts_list))

    hasil = []

    # 🔥 Hitung KWH per jam
    if len(ts_list) >= 2:
        for i in range(1, len(ts_list)):
            cur.execute("SELECT energy FROM dataset_training_AI WHERE timestamp = ?", (ts_list[i],))
            e_now = cur.fetchone()

            cur.execute("SELECT energy FROM dataset_training_AI WHERE timestamp = ?", (ts_list[i-1],))
            e_prev = cur.fetchone()

            if e_now and e_prev:
                diff = e_now[0] - e_prev[0]
                hasil.append(max(0, int(diff)))
            else:
                hasil.append(0)
    else:
        print("[kwh] Data per jam tidak cukup")

    # 🔹 Pastikan panjang 24
    hasil = ([0] * (24 - len(hasil))) + hasil

    for i in range(24):
        gl.grafik_kwh_listrik[i] = hasil[i]

    # =====================================================
    # 🔥 HITUNG TOTAL KWH 24 JAM (langsung dari meter)
    # =====================================================

    # energy sekarang
    cur.execute("""
        SELECT energy FROM dataset_training_AI
        WHERE timestamp <= ?
        ORDER BY timestamp DESC LIMIT 1
    """, (now_ms,))
    e_now = cur.fetchone()

    # energy 24 jam lalu
    cur.execute("""
        SELECT energy FROM dataset_training_AI
        WHERE timestamp <= ?
        ORDER BY timestamp DESC LIMIT 1
    """, (batas_24_jam_ms,))
    e_prev = cur.fetchone()

    if e_now and e_prev:
        total = e_now[0] - e_prev[0]
        total = max(0, int(total))
        gl.kwh_harian = total
    else:
        print("[kwh] Data total tidak cukup")
        gl.kwh_harian = 0

    conn.close()

    #print("[kwh] OK | Total:", gl.kwh_harian)

print("database_sqlite.py dimuat.")