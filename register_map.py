"""
register_map.py
===============
Python mirror of ModbusRegisterMap.h (firmware ESP32 - kandang kipas).

Alamat di sini adalah ALAMAT 0-based INTERNAL, sama seperti yang
dipakai langsung oleh ModbusTcpServer di firmware (getCoil/getHolding/dst).
Penomoran "Modbus klasik" 1-based (00001, 40001, dst) = alamat internal + 1.

PENTING - encoding register (harus sama persis dengan firmware):
    - Coil FAN_1..FAN_5   : 1 coil per kipas, ON/OFF langsung (bukan float!)
    - Holding MODE_KANDANG..JUMLAH_KIPAS_TIMER : SEMUA single-register
      uint16 (bukan float 2-register!). Suhu disimpan sebagai nilai x10
      integer (mis. 275 = 27.5°C) - pakai read_holding()/write_holding()
      lalu bagi/kali 10 manual, JANGAN pakai read_float()/write_float()
      (itu untuk IEEE-754 2-register, formatnya beda & TIDAK dipakai
      firmware kandang kipas ini).
    - Input Register IReg.* juga single-register uint16 x10, sama polanya.

Kalau menambah register baru di firmware (ModbusRegisterMap.h),
update juga file ini supaya tetap sinkron. Sumber kebenaran = firmware.
"""

from __future__ import annotations


class Coil:
    """Read/Write coil (digital output) - 00001-00xxx."""
    FAN_1   = 0   # 00001
    FAN_2   = 1   # 00002
    FAN_3   = 2   # 00003
    FAN_4   = 3   # 00004
    FAN_5   = 4   # 00005
    RELAY_6 = 5   # 00006 (reserved, belum ada controller di firmware)
    RELAY_7 = 6   # 00007 (reserved)
    RELAY_8 = 7   # 00008 (reserved)

    FAN_COUNT = 5


class DInput:
    """Discrete input (read-only digital input) - 10001-10xxx.

    Sumber: state.fan.inspeksi[] (pembacaan arus motor via PCF8574).
    Ini BUKAN status saklar fisik manual (saklar[] tidak diekspos
    lewat Modbus sama sekali di firmware saat ini).
    """
    INSPEKSI_KIPAS_1 = 0   # 10001
    INSPEKSI_KIPAS_2 = 1   # 10002
    INSPEKSI_KIPAS_3 = 2   # 10003
    INSPEKSI_KIPAS_4 = 3   # 10004
    INSPEKSI_KIPAS_5 = 4   # 10005

    COUNT = 5


class Holding:
    """Holding register (read/write 16-bit) - 40001-40xxx.

    Suhu/target disimpan x10 (1 register, bukan float 2-register).
    """
    MODE_KANDANG       = 0  # 40001 - 1=Auto,2=Manual,3=Timer,4=Selesai Panen
    USIA_AYAM          = 1  # 40002 - hari
    TARGET_SUHU_X10    = 2  # 40003 - target_suhu * 10
    SUHU_MIN_X10       = 3  # 40004 - suhu_minimal * 10
    SUHU_MAX_X10       = 4  # 40005 - suhu_maksimal * 10
    WAKTU_HIDUP        = 5  # 40006 - detik
    WAKTU_MATI         = 6  # 40007 - menit
    JUMLAH_KIPAS_TIMER = 7  # 40008 - 1..3

    COUNT = 8


class IReg:
    """Input register (read-only 16-bit) - 30001-30xxx.

    Nilai suhu x10, sumber: state.sensor (dibaca via SensorManager).
    """
    SUHU_ATAS_X10        = 0  # 30001
    SUHU_LUAR_X10        = 1  # 30002
    SUHU_OUTLET_ATAS_X10 = 2  # 30003
    SUHU_ACUAN_X10       = 3  # 30004

    COUNT = 4


def x10_ke_float(reg_value: int) -> float:
    """Konversi nilai register x10 (int) -> float asli. Sama pola dengan x10ToFloat() firmware."""
    return reg_value / 10.0


def float_ke_x10(value: float) -> int:
    """Konversi float -> nilai register x10 (int, clamp >=0). Sama pola dengan floatToX10() firmware."""
    if value < 0:
        value = 0
    return int(round(value * 10))


print("register_map.py dimuat.")