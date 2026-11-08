import json
import math
from typing import Any


# ============================================================
# KONFIGURASI PROTOKOL
# ============================================================

PROTOCOL_VERSION = 1


# ============================================================
# VALIDASI DASAR
# ============================================================

def is_valid_number(value: Any) -> bool:
    """
    Integer dan float diperbolehkan.
    Boolean tidak dianggap angka.
    NaN dan Infinity ditolak.
    """

    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return math.isfinite(value)


def is_valid_integer(value: Any) -> bool:
    """
    Integer murni.
    Boolean tidak diperbolehkan.
    """

    return isinstance(value, int) and not isinstance(value, bool)


def is_valid_numeric_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False

    return all(is_valid_number(item) for item in value)


def is_valid_integer_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False

    return all(is_valid_integer(item) for item in value)


def is_valid_status_list(value: Any, expected_length: int) -> bool:
    """
    Validasi array status perangkat.
    Setiap elemen harus integer 0 atau 1.
    """

    if not isinstance(value, list):
        return False

    if len(value) != expected_length:
        return False

    return all(
        is_valid_integer(item) and item in (0, 1)
        for item in value
    )


# ============================================================
# REGISTRY: VARIABEL YANG BOLEH DIPERBARUI LANGSUNG
# ============================================================

NUMERIC_FIELDS = {
    # SUHU
    "suhu_dalam",
    "suhu_atas",
    "suhu_tengah",
    "suhu_bawah",
    "suhu_luar",
    "suhu_depan",
    "suhu_belakang",
    "suhu_greenhouse",
    "suhu_inlet_atas",
    "suhu_inlet_bawah",
    "suhu_outlet_atas",
    "suhu_outlet_bawah",
    "suhu_acuan",

    # KELEMBAPAN
    "kelembapan_dalam",
    "kelembapan_atas",
    "kelembapan_tengah",
    "kelembapan_bawah",
    "kelembapan_luar",
    "kelembapan_depan",
    "kelembapan_belakang",
    "kelembapan_greenhouse",
    "kelembapan_inlet_atas",
    "kelembapan_inlet_bawah",
    "kelembapan_outlet_atas",
    "kelembapan_outlet_bawah",

    # HEAT INDEX
    "data_HI_atas",
    "data_HI_tengah",
    "data_HI_bawah",
    "data_HI_luar",
    "data_HI_depan",
    "data_HI_belakang",
    "data_HI_greenhouse",
    "data_HI_inlet_atas",
    "data_HI_inlet_bawah",
    "data_HI_outlet_atas",
    "data_HI_outlet_bawah",

    # GAS
    "ppm_gas_atas",
    "ppm_gas_tengah",
    "ppm_gas_bawah",

    # ANGIN
    "kecepatan_angin",
    "kecepatan_angin_atas",
    "kecepatan_angin_tengah",
    "kecepatan_angin_bawah",

    # CAHAYA
    "intensitas_cahaya",
    "intensitas_cahaya_atas",
    "intensitas_cahaya_tengah",
    "intensitas_cahaya_bawah",

    # AIR
    "liter_tong_atas",
    "liter_tong_bawah",
    "persen_air_atas",
    "persen_air_bawah",
    "kecepatan_minum_atas",
    "kecepatan_minum_bawah",
    "jarak_ultrasonik",
    "tinggi_air_1",
    "tinggi_air_2",

    # INDIKATOR
    "indikator_ultrasonik",
    "ult",
    "indikator_p1",
    "indikator_p2",
    "indikator_p3",
    "indikator_p4",
    "indikator_p5",
    "indikator_p6",

    # KELISTRIKAN
    "voltage",
    "current",
    "power",
    "energy",
    "frequency",
    "pf",
    "kecepatan_listrik_atas",
    "kwh_jam",
    "kwh_harian",
    "daya_listrik",

    # CUACA
    "kode_cuaca",
    "indikator_cuaca",

    # LAMPU DAN PERANGKAT
    "lampu_luar",
    "is_heater",
    "is_celldeck",

    # TIMBANGAN
    "bobot_timbang",
}


STRING_FIELDS = {
    "teks_cuaca",
}


LIST_FIELDS = {
    "list_bobot_timbang",
    "raw_bobot_normal",
    "raw_bobot_kecil",
}


# ============================================================
# REGISTRY: VARIABEL YANG MEMERLUKAN UPDATE KHUSUS
# ============================================================

SPECIAL_FIELDS = {
    # Status kipas individual
    *(f"kipas_{i}" for i in range(1, 11)),

    # Array status kipas
    "kipas",
    "kipas_inspeksi",
    "kipas_saklar",

    # Informasi kontrol kipas
    "kipas_channel_aktif",
    "kipas_gagal_total",
    "kipas_generasi_terkonfirmasi",

    # Identitas boot perangkat
    "esp32_boot_id_terakhir",

    # Data RPM
    "rpm_kipas",
}


ALLOWED_FIELDS = (
    NUMERIC_FIELDS
    | STRING_FIELDS
    | LIST_FIELDS
    | SPECIAL_FIELDS
)


# ============================================================
# VALIDASI FIELD LANGSUNG
# ============================================================

def validate_field(key: str, value: Any) -> bool:

    if key in NUMERIC_FIELDS:
        return is_valid_number(value)

    if key in STRING_FIELDS:
        return isinstance(value, str)

    if key in LIST_FIELDS:
        return is_valid_numeric_list(value)

    return False


# ============================================================
# VALIDASI FIELD KHUSUS
# ============================================================

def validate_special_field(key: str, value: Any) -> bool:

    # Status lima kipas
    if key == "kipas":
        return is_valid_status_list(value, 5)

    # Status inspeksi dan saklar lima kipas
    if key in ("kipas_inspeksi", "kipas_saklar"):
        return is_valid_integer_list(value) and len(value) == 5

    # Status kipas individual
    if key.startswith("kipas_") and key not in (
        "kipas_inspeksi",
        "kipas_saklar",
        "kipas_channel_aktif",
        "kipas_gagal_total",
        "kipas_generasi_terkonfirmasi",
    ):
        return is_valid_integer(value) and value in (0, 1)

    # Kanal kipas aktif
    if key == "kipas_channel_aktif":
        return isinstance(value, str)

    # Jumlah kegagalan kipas
    if key == "kipas_gagal_total":
        return is_valid_integer(value) and value >= 0

    # Generasi status kipas
    if key == "kipas_generasi_terkonfirmasi":
        return is_valid_integer(value) and value >= 0

    # Identitas boot ESP
    if key == "esp32_boot_id_terakhir":
        return (
            isinstance(value, str)
            or is_valid_integer(value)
        )

    # RPM sepuluh kipas
    if key == "rpm_kipas":
        return is_valid_integer_list(value) and len(value) == 10

    return False


# ============================================================
# PARSER UNIVERSAL
# ============================================================

async def parse_json_esp(
    payload: str,
    gl,
    lock_data,
):
    """
    Parser universal JSON ESP -> Raspberry Pi.

    Format metadata:
        {
            "device_id": 151,
            "protocol_version": 1
        }

    Parameter:
        payload   : JSON string atau dictionary
        gl        : instance variabel_global.gl
        lock_data : asyncio.Lock sistem

    Return:
        {
            "ok": bool,
            "device_id": int,
            "updated": list,
            "special": dict,
            "rejected": dict,
            "unknown": list,
            "error": str atau None
        }

    Catatan:
        - Key tidak dikenal diabaikan.
        - Key tidak dikirim tidak mengubah nilai lama.
        - Data langsung diperbarui dengan lock_data.
        - Data khusus dikembalikan untuk diproses terpisah.
    """

    result = {
        "ok": False,
        "device_id": None,
        "updated": [],
        "special": {},
        "rejected": {},
        "unknown": [],
        "error": None,
    }

    # --------------------------------------------------------
    # 1. DECODE JSON
    # --------------------------------------------------------

    try:
        if isinstance(payload, dict):
            data = payload
        else:
            data = json.loads(payload)

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        result["error"] = f"JSON tidak valid: {e}"
        return result

    if not isinstance(data, dict):
        result["error"] = "Root JSON harus berupa object."
        return result

    # --------------------------------------------------------
    # 2. VALIDASI METADATA
    # --------------------------------------------------------

    device_id = data.get("device_id")
    protocol_version = data.get("protocol_version")

    if not is_valid_integer(device_id):
        result["error"] = "device_id tidak valid."
        return result

    if not is_valid_integer(protocol_version):
        result["error"] = "protocol_version tidak valid."
        return result

    if protocol_version != PROTOCOL_VERSION:
        result["error"] = (
            f"Protocol tidak didukung: {protocol_version}"
        )
        return result

    result["device_id"] = device_id

    # --------------------------------------------------------
    # 3. PISAHKAN DATA LANGSUNG DAN DATA KHUSUS
    # --------------------------------------------------------

    direct_updates = {}
    special_updates = {}

    for key, value in data.items():

        # Metadata tidak diproses sebagai variabel.
        if key in ("device_id", "protocol_version"):
            continue

        # Key tidak dikenal.
        if key not in ALLOWED_FIELDS:
            result["unknown"].append(key)
            continue

        # Field khusus.
        if key in SPECIAL_FIELDS:

            if not validate_special_field(key, value):
                result["rejected"][key] = value
                continue

            special_updates[key] = value
            continue

        # Field langsung.
        if not validate_field(key, value):
            result["rejected"][key] = value
            continue

        direct_updates[key] = value

    # --------------------------------------------------------
    # 4. UPDATE VARIABEL GLOBAL
    # --------------------------------------------------------

    async with lock_data:

        for key, value in direct_updates.items():

            setattr(gl, key, value)

            result["updated"].append(key)

    # --------------------------------------------------------
    # 5. KEMBALIKAN DATA KHUSUS
    # --------------------------------------------------------

    result["special"] = special_updates

    result["ok"] = True

    return result


print("parser_esp.py dimuat.")
