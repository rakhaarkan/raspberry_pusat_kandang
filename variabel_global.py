# variabel_global.py
from dataclasses import dataclass, field
from typing import List
import asyncio

lock_data = asyncio.Lock()

@dataclass
class gl:
    ser = None
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

    suhu_atas: float = 0.0
    suhu_tengah: float = 0.0
    suhu_bawah: float = 0.0
    suhu_luar: float = 0.0
    suhu_depan: float = 0.0
    suhu_belakang: float = 0.0
    suhu_greenhouse: float = 0.0
    suhu_outlet_atas: float = 0.0
    suhu_acuan: float = 0.0

    kelembapan_atas: float = 0.0
    kelembapan_tengah: float = 0.0
    kelembapan_bawah: float = 0.0
    kelembapan_luar: float = 0.0
    kelembapan_depan: float = 0.0
    kelembapan_belakang: float = 0.0
    kelembapan_greenhouse: float = 0.0

    data_HI_atas: float = 0.0
    data_HI_tengah: float = 0.0
    data_HI_bawah: float = 0.0
    data_HI_luar: float = 0.0
    data_HI_depan: float = 0.0
    data_HI_belakang: float = 0.0
    data_HI_greenhouse: float = 0.0

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

    lampu_luar: int = 0
    kode_cuaca: int = 0
    teks_cuaca: str = ""
    indikator_cuaca: int = 0

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
    target_suhu: int = 0
    suhu_minimal: int = 0
    suhu_maksimal: int = 0
    status_timer: int = 0
    waktu_hidup: int = 0
    waktu_mati: int = 0

    detail_kipas: str = ""
    detail_timer_kipas: str = ""
    debug_155: str = ""
    mode_kandang: int = 1
    blok_kandang: str = "1111111111111"
    jumlah_kipas_timer = 1
    keterangan_web = ""
    jumlah_http = 0
    internetConnected = 1
    json_thingspeak = ""
    
    
    hari: int = 0
    bulan: int = 0
    tahun: int = 0
    detik: int = 0
    menit: int = 0
    jam: int = 0

    kipas: List[int] = field(default_factory=lambda: [0]*5)
    kipas_web: List[int] = field(default_factory=lambda: [0]*5)
    whk: List[int] = field(default_factory=lambda: [0]*5)

    jumlah_ayam_awal: int = 0
    jumlah_ayam_mati: int = 0
    jumlah_pakan_sak: int = 0
    bobot_rata_rata: int = 0

    harga_kontrak_ayam: int = 0
    harga_bibit_ayam: int = 0
    harga_obat_ayam: int = 0
    harga_pakan_kg: int = 0
    jumlah_ayam_dipanen: int = 0

    data_waktu: str = ""
    epoch_data_waktu: int = 0

    http_sukses: bool = False
    kode_wifi_pilihan: int = 0
    teks_i2c: str = ""
    jumlah_request_http: int = 0

    debug_int: List[int] = field(default_factory=lambda: [0]*10)
    debug_float: List[float] = field(default_factory=lambda: [0.0]*10)
    debug_bool: List[bool] = field(default_factory=lambda: [False]*10)
    debug_str: List[str] = field(default_factory=lambda: [""]*10)

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

# Buat instance global agar bisa diakses langsung dari modul lain
gl = gl()
