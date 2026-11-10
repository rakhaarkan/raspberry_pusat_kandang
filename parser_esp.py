import json
import math
import types
from functools import lru_cache
from typing import Any, Union, get_args, get_origin, get_type_hints


# ============================================================
# KONFIGURASI PROTOKOL
# ============================================================

PROTOCOL_VERSION = 1

# Hanya menentukan field yang perlu jalur pemrosesan khusus.
# Daftar key yang dikenali tetap berasal dari anotasi class gl.
SPECIAL_FIELDS = {
    *(f"kipas_{i}" for i in range(1, 11)),
    "kipas",
    "kipas_inspeksi",
    "kipas_saklar",
    "kipas_channel_aktif",
    "kipas_gagal_total",
    "kipas_generasi_terkonfirmasi",
    "esp32_boot_id_terakhir",
    "rpm_kipas",
}


# ============================================================
# SUMBER TIPE VARIABEL
# ============================================================

@lru_cache(maxsize=8)
def _get_variable_types(gl_class):
    """Ambil tipe variabel yang memiliki anotasi pada class gl."""
    return get_type_hints(gl_class)


def _is_valid_number(value: Any) -> bool:
    # bool merupakan subclass int di Python, jadi harus ditolak eksplisit.
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _matches_type(value: Any, expected_type: Any) -> bool:
    """Validasi berdasarkan anotasi: tipe dasar, Union/Optional, dan list[T]."""

    if expected_type is Any:
        return True

    if expected_type is type(None):
        return value is None

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    # Optional[T], Union[T1, T2], dan T1 | T2.
    if origin in (Union, types.UnionType):
        return any(_matches_type(value, item_type) for item_type in args)

    # list[T] atau typing.List[T].
    if origin is list:
        if not isinstance(value, list):
            return False
        if not args:
            return True
        return all(_matches_type(item, args[0]) for item in value)

    # Field float boleh menerima angka JSON integer maupun float.
    if expected_type is float:
        return _is_valid_number(value)

    if expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)

    if expected_type is bool:
        return isinstance(value, bool)

    try:
        return isinstance(value, expected_type)
    except TypeError:
        # Anotasi yang tidak didukung tidak boleh lolos tanpa validasi.
        return False


# ============================================================
# VALIDASI SEMANTIK FIELD KHUSUS
# ============================================================

def _validate_special_field(key: str, value: Any) -> bool:
    """
    Validasi tambahan setelah tipe dasarnya cocok dengan anotasi gl.
    """

    if key == "kipas":
        return len(value) == 5 and all(item in (0, 1) for item in value)

    if key in ("kipas_inspeksi", "kipas_saklar"):
        return len(value) == 5

    if key.startswith("kipas_") and key not in (
        "kipas_channel_aktif",
        "kipas_gagal_total",
        "kipas_generasi_terkonfirmasi",
    ):
        return value in (0, 1)

    if key in ("kipas_gagal_total", "kipas_generasi_terkonfirmasi"):
        return value >= 0

    if key == "rpm_kipas":
        return len(value) == 10 and all(item >= 0 for item in value)

    return True


def _reject_json_constant(value: str):
    """Tolak NaN dan Infinity yang bukan nilai numerik JSON standar."""
    raise ValueError(f"Nilai numerik tidak valid: {value}")


# ============================================================
# PARSER UNIVERSAL
# ============================================================

async def parse_json_esp(payload: str, gl, lock_data):
    """
    Parser universal JSON ESP32 -> Raspberry Pi.

    Aturan:
    - device_id dan protocol_version wajib ada dan divalidasi.
    - Key berawalan 'x_' selalu diabaikan.
    - Key tanpa anotasi pada class gl dianggap tidak dikenal.
    - Tipe setiap key diperiksa berdasarkan anotasi class gl.
    - Key invalid ditolak sendiri; key valid lainnya tetap diproses.
    - Key yang tidak dikirim tidak mengubah nilai sebelumnya.
    - Field khusus dikembalikan melalui result['special'].
    - Pembaruan langsung dilakukan di dalam lock_data.

    payload dapat berupa JSON string, bytes, atau dictionary.
    """

    result = {
        "ok": False,
        "device_id": None,
        "updated": [],
        "special": {},
        "rejected": {},
        "unknown": [],
        "ignored": [],
        "error": None,
    }

    # 1. Decode JSON.
    try:
        if isinstance(payload, dict):
            data = payload
        else:
            data = json.loads(payload, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        result["error"] = f"JSON tidak valid: {exc}"
        return result

    if not isinstance(data, dict):
        result["error"] = "Root JSON harus berupa object."
        return result

    # 2. Validasi metadata protokol.
    device_id = data.get("device_id")
    protocol_version = data.get("protocol_version")

    if not isinstance(device_id, int) or isinstance(device_id, bool):
        result["error"] = "device_id tidak valid."
        return result

    if (
        not isinstance(protocol_version, int)
        or isinstance(protocol_version, bool)
    ):
        result["error"] = "protocol_version tidak valid."
        return result

    if protocol_version != PROTOCOL_VERSION:
        result["error"] = f"Protocol tidak didukung: {protocol_version}"
        return result

    result["device_id"] = device_id

    # 3. Ambil anotasi tipe dari class instance gl.
    try:
        variable_types = _get_variable_types(type(gl))
    except Exception as exc:
        result["error"] = f"Gagal membaca anotasi variabel gl: {exc}"
        return result

    direct_updates = {}
    special_updates = {}

    # 4. Validasi setiap key secara independen.
    for key, value in data.items():

        if key in ("device_id", "protocol_version"):
            continue

        # Prefix x_ berarti jangan diproses sama sekali.
        if isinstance(key, str) and key.startswith("x_"):
            result["ignored"].append(key)
            continue

        # Hanya variabel dengan anotasi tipe yang dikenali.
        if not isinstance(key, str) or key not in variable_types:
            result["unknown"].append(key)
            continue

        expected_type = variable_types[key]

        if not _matches_type(value, expected_type):
            result["rejected"][key] = value
            continue

        if key in SPECIAL_FIELDS:
            if not _validate_special_field(key, value):
                result["rejected"][key] = value
                continue
            special_updates[key] = value
            continue

        direct_updates[key] = value

    # 5. Terapkan pembaruan langsung dengan lock_data.
    async with lock_data:
        for key, value in direct_updates.items():
            setattr(gl, key, value)
            result["updated"].append(key)

    # 6. Serahkan field khusus kepada pemanggil untuk diproses lanjut.
    result["special"] = special_updates
    result["ok"] = True
    return result


print("parser_esp.py dimuat.")
