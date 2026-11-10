# variabel_global.py
from dataclasses import dataclass, field
from typing import List
import asyncio
from collections import deque

lock_data = asyncio.Lock()

#"timestamp", "mode_kandang", "usia_ayam", "hari_ke", "jam", "menit",
#        "is_malam", "jam_mandatori_kipas", "suhu_dalam", "suhu_luar",
#        "kelembapan_dalam", "kelembapan_luar", "target_suhu",
#        "trend_suhu_dalam_10m", "trend_suhu_luar_10m",
#        "trend_kelembapan_dalam_10m", "trend_kelembapan_luar_10m",
#        "selisih_suhu_luar_dalam", "selisih_kelembapan_luar_dalam",
#        "is_heater", "is_celldeck", "kecepatan_angin", "kode_cuaca",
#        "bobot_rata_rata", "daya_listrik",
#        "kipas_prev_1", "kipas_prev_2", "kipas_prev_3", "kipas_prev_4", "kipas_prev_5",#

        # Target
#        "kipas_1", "kipas_2", "kipas_3", "kipas_4", "kipas_5",
#        "mode_operasi", "waktu_hidup_timer", "waktu_mati_timer", "skala_kipas"

@dataclass
class gl:
    ser = None
    last_saved_data: dict = None
    cek_proteksi_listrik: int = 0
    usia_ui: int = 0
    # Server
    server_pusat_data: str = "http://192.168.0.150/"
    server_sensor_dalam: str = "http://192.168.0.151/"
    server_sensor_tangki_air: str = "http://192.168.0.152/"
    server_sensor_kipas: str = "http://192.168.0.153/"
    server_sensor_listrik: str = "http://192.168.0.154/"
    server_pusat_kipas_atas: str = "http://192.168.0.155/"
    server_pusat_kipas_atas_wkt: str = "http://192.168.0.155/wkt"
    server_pusat_kipas_atas_kps: str = "http://192.168.0.155/kps"
    server_pusat_kipas_atas_shu: str = "http://192.168.0.155/shu"
    server_pusat_kipas_atas_epr: str = "http://192.168.0.155/epr"
    server_kebun_kandang: str = "http://192.168.0.156/"
    server_saklar_cuaca_relay: str = "http://192.168.0.157/"
    server_timbangan_auto: str = "http://192.168.0.158/"
    server_timbangan_auto_raw: str = "http://192.168.0.158/raw"

    # Variabel acak & sensor
    acak_p1: int = 0
    acak_p2: int = 0
    acak_p3: int = 0
    acak_p4: int = 0
    acak_p5: int = 0
    
    suhu_dalam: float = 0.0
    suhu_atas: float = 0.0
    suhu_tengah: float = 0.0
    suhu_bawah: float = 0.0
    suhu_luar: float = 0.0
    suhu_depan: float = 0.0
    suhu_belakang: float = 0.0
    suhu_greenhouse: float = 0.0
    suhu_inlet_atas: float = 0.0
    suhu_inlet_bawah: float = 0.0
    suhu_tengah_atas: float = 0.0
    suhu_tengah_bawah: float = 0.0
    suhu_outlet_atas: float = 0.0
    suhu_outlet_bawah: float = 0.0
    suhu_acuan: float = 0.0

    # Hasil baca IReg Modbus dari ESP32 kipas (lihat plc_manager.baca_sensor)
    suhu_atas_plc: float = 0.0
    suhu_luar_plc: float = 0.0
    suhu_outlet_atas_plc: float = 0.0
    suhu_acuan_plc: float = 0.0

    # Observability jalur pengiriman perintah kipas (lihat aktuator_kipas.py)
    kipas_channel_aktif: str = ""
    kipas_gagal_total: int = 0

    # Pelacak generasi status kipas ESP32 (lihat status_esp32.py) - cegah
    # race condition antara command RPi sendiri vs laporan status
    # independen (poll /kps, ACK Serial) yang bisa datang basi.
    kipas_generasi_terkonfirmasi: int = 0
    esp32_boot_id_terakhir = None  # None = belum pernah kontak sama sekali

    trend_suhu_dalam_10m = 0.0
    trend_suhu_luar_10m = 0.0
    trend_kelembapan_dalam_10m = 0.0
    trend_kelembapan_luar_10m = 0.0

    selisih_suhu_luar_dalam = 0.0
    selisih_kelembapan_luar_dalam = 0.0

    kelembapan_dalam: float = 0.0
    kelembapan_atas: float = 0.0
    kelembapan_tengah: float = 0.0
    kelembapan_bawah: float = 0.0
    kelembapan_luar: float = 0.0
    kelembapan_depan: float = 0.0
    kelembapan_belakang: float = 0.0
    kelembapan_greenhouse: float = 0.0
    kelembapan_inlet_atas: float = 0.0
    kelembapan_inlet_bawah: float = 0.0
    kelembapan_tengah_atas: float = 0.0
    kelembapan_tengah_bawah: float = 0.0
    kelembapan_outlet_atas: float = 0.0
    kelembapan_outlet_bawah: float = 0.0

    data_HI_atas: float = 0.0
    data_HI_tengah: float = 0.0
    data_HI_bawah: float = 0.0
    data_HI_luar: float = 0.0
    data_HI_depan: float = 0.0
    data_HI_belakang: float = 0.0
    data_HI_greenhouse: float = 0.0
    data_HI_inlet_atas: float = 0.0
    data_HI_inlet_bawah: float = 0.0
    data_HI_tengah_atas: float = 0.0    
    data_HI_tengah_bawah: float = 0.0
    data_HI_outlet_atas: float = 0.0
    data_HI_outlet_bawah: float = 0.0

    hist_suhu_dalam: deque = field(default_factory=lambda: deque(maxlen=10))
    hist_suhu_luar: deque = field(default_factory=lambda: deque(maxlen=10))
    hist_kelembapan_dalam: deque = field(default_factory=lambda: deque(maxlen=10))
    hist_kelembapan_luar: deque = field(default_factory=lambda: deque(maxlen=10))
    
    ppm_gas_atas: float = 0.0
    ppm_gas_tengah: float = 0.0
    ppm_gas_bawah: float = 0.0

    kecepatan_angin: float = 0.0
    kecepatan_angin_atas: float = 0.0
    kecepatan_angin_tengah: float = 0.0
    kecepatan_angin_bawah: float = 0.0

    intensitas_cahaya_atas: float = 0.0
    intensitas_cahaya_tengah: float = 0.0
    intensitas_cahaya_bawah: float = 0.0

    liter_tong_atas: int = 0
    liter_tong_bawah: int = 0
    persen_air_atas: int = 0
    persen_air_bawah: int = 0
    kecepatan_minum_atas: int = 0
    kecepatan_minum_bawah: int = 0

    nomor_perangkat: int = 0
    indikator_ultrasonik: int = 0
    intensitas_cahaya: int = 0
    jarak_ultrasonik: int = 0
    ult: int = 0
    tinggi_air_1: int = 0
    tinggi_air_2: int = 0

    indikator_p1: int = 0
    indikator_p2: int = 0
    indikator_p3: int = 0
    indikator_p4: int = 0
    indikator_p5: int = 0
    indikator_p6: int = 0

    target_heat_index: int = 155
    target_suhu_atas_maksimal: int = 33

    kipas_1: int = 0
    kipas_2: int = 0
    kipas_3: int = 0
    kipas_4: int = 0
    kipas_5: int = 0
    kipas_6: int = 0
    kipas_7: int = 0
    kipas_8: int = 0
    kipas_9: int = 0
    kipas_10: int = 0
    
    kipas_prev_1 = 0
    kipas_prev_2 = 0
    kipas_prev_3 = 0
    kipas_prev_4 = 0
    kipas_prev_5 = 0

    rpm_kipas: List[int] = field(default_factory=lambda: [0]*10)
    grafik_waktu: List[int] = field(default_factory=lambda: [0]*25)
    grafik_suhu_atas: List[int] = field(default_factory=lambda: [0]*25)
    grafik_suhu_luar: List[int] = field(default_factory=lambda: [0]*25)
    grafik_kelembapan_atas: List[int] = field(default_factory=lambda: [0]*25)
    grafik_kelembapan_luar: List[int] = field(default_factory=lambda: [0]*25)
    grafik_kwh_listrik: List[int] = field(default_factory=lambda: [0]*25)
    sebaran_bobot: List[int] = field(default_factory=lambda: [0]*11)

    voltage: float = 0.0
    current: float = 0.0
    power: float = 0.0
    energy: float = 0.0
    frequency: float = 0.0
    pf: float = 0.0
    kecepatan_listrik_atas: int = 0
    kwh_jam: int = 0
    kwh_harian: int = 0
    daya_listrik: float = 0.0
    lampu_luar: int = 0
    kode_cuaca: int = 0
    teks_cuaca: str = ""
    indikator_cuaca: int = 0

    list_bobot_timbang: list[int] = field(default_factory=list)
    bobot_timbang: int = 0
    bobot_rata_rata_timbang: int = 0
    jumlah_sample_timbang: int = 0
    jumlah_sample_timbang_kemarin: int = 0
    standar_bobot: int = 0
    standar_deviasi_bobot: int = 0
    standar_deviasi_atas: int = 0
    standar_deviasi_bawah: int = 0
    persentase_standar_deviasi: int = 0
    persentase_dalam_standar: int = 0
    average_daily_gain: int = 0
    average_daily_gain_jam: int = 0
    target_adg: int = 0

    raw_bobot_normal: List[int] = field(default_factory=lambda: [0]*400)
    raw_bobot_kecil: List[int] = field(default_factory=lambda: [0]*400)

    tanggal_masuk_ayam = None  # tipe datetime.datetime
    epoch_data_waktu = 0
    data_waktu = ""
    tanggal_masuk_ayam_hari: int = 0
    tanggal_masuk_ayam_bulan: int = 0
    tanggal_masuk_ayam_tahun: int = 0
    usia_ayam: int = 0
    hari_ke: int = 0
    target_suhu: int = 0
    suhu_minimal: int = 0
    suhu_maksimal: int = 0
    status_timer: int = 0
    waktu_hidup: int = 0
    waktu_mati: int = 0
    waktu_hidup_timer: int = 0
    waktu_mati_timer: int = 0
    timer_state = "on" 
    timer_end_timestamp = 1700000000 
    skala_kipas: int = 0
    status_on_timer: int = 0
    waktuTerakhir: int = 0
    
    detail_kipas: str = ""
    detail_timer_kipas: str = ""
    debug_155: str = ""
    mode_kandang: int = 1
    mode_operasi: int = 1
    blok_kandang: str = "1111111111111"
    jumlah_kipas_timer = 1
    keterangan_web = ""
    jumlah_http = 0
    internetConnected = 1
    json_thingspeak = ""
    json_thingspeak_2 = ""
    
    timestamp = 0
    hari: int = 0
    bulan: int = 0
    tahun: int = 0
    detik: int = 0
    menit: int = 0
    jam: int = 0
    is_malam = 0
    jam_mandatori_kipas = 0

    kipas: List[int] = field(default_factory=lambda: [0]*5)
    kipas_inspeksi: List[int] = field(default_factory=lambda: [0]*5)
    kipas_saklar: List[int] = field(default_factory=lambda: [0]*5)
    kipas_web: List[int] = field(default_factory=lambda: [0]*5)
    whk: List[int] = field(default_factory=lambda: [0]*5)
    state_tanaman: List[int] = field(default_factory=lambda: [0]*5)

    jumlah_ayam_awal: int = 0
    jumlah_ayam_mati: int = 0
    jumlah_pakan_sak: int = 0
    bobot_rata_rata: int = 0

    harga_kontrak_ayam: int = 0
    harga_bibit_ayam: int = 0
    harga_obat_ayam: int = 0
    harga_pakan_kg: int = 0
    jumlah_ayam_dipanen: int = 0
    harga_pasar: List[int] = field(default_factory=lambda: [0]*10)
    
    db_id: List[int] = field(default_factory=lambda: [0]*25)
    db_tanggal: List[str] = field(default_factory=lambda: [0]*25)
    db_nama_do: List[str] = field(default_factory=lambda: [0]*25)
    db_nama_bakul: List[str] = field(default_factory=lambda: [0]*25)
    db_plat_nomor: List[str] = field(default_factory=lambda: [0]*25)
    db_jumlah_ekor_ambil: List[int] = field(default_factory=lambda: [0]*25)
    db_jumlah_kg_ambil: List[float] = field(default_factory=lambda: [0]*25)
    db_total_bakul: int = 0
    db_total_ekor_panen: int = 0
    db_total_kg_panen: float = 0.0
    
    data_waktu: str = ""
    epoch_data_waktu: int = 0
    is_heater = 0
    is_celldeck = 0

    http_sukses: bool = False
    kode_wifi_pilihan: int = 0
    teks_i2c: str = ""
    jumlah_request_http: int = 0
    flag_database_AI: int = 0
    flag_alarm_siaga: int = 0

    tanaman: int = 0
    tanaman2: int = 0

    debug_int: List[int] = field(default_factory=lambda: [0]*10)
    debug_float: List[float] = field(default_factory=lambda: [0.0]*10)
    debug_bool: List[bool] = field(default_factory=lambda: [False]*10)
    debug_str: List[str] = field(default_factory=lambda: [""]*10)
    debug_err: List[str] = field(default_factory=lambda: [""]*10)

    penampung_json_1: str = ""
    penampung_json_2: str = ""
    penampung_json_3: str = ""
    penampung_json_4: str = ""
    penampung_json_5: str = ""
    penampung_json_server: str = ""
    penampung_json_epr: str = ""
    penampung_json_chip: str = ""
    penampung_json_kipas: str = ""
    penampung_json_waktu: str = ""
    penampung_json_debug: str = ""
    penampung_json_sensor_1: str = ""
    penampung_json_sersor_2: str = ""
    penampung_json_grafik_1: str = ""
    penampung_json_grafik_2: str = ""

    eeprom_sha: List[int] = field(default_factory=lambda: [0]*24)
    eeprom_shl: List[int] = field(default_factory=lambda: [0]*24)
    eeprom_kll: List[int] = field(default_factory=lambda: [0]*24)
    eeprom_lst: List[int] = field(default_factory=lambda: [0]*24)

    row_konfigurasi_kipas = ["00000", "N", "N", "N", "N", "N"]

# Buat instance global agar bisa diakses langsung dari modul lain
gl = gl()

print("variabel_global.py dimuat.")