# status_esp32.py
"""
status_esp32.py
================
Satu fungsi: evaluasi apakah data status kipas yang datang dari ESP32
(lewat respons HTTP /kipasstr, poll /kps, atau ACK Serial) boleh dipercaya
buat menimpa gl.kipas.

LATAR BELAKANG: gl.kipas sempat kena race condition - poll /kps (jalan
periodik, independen dari command) bisa nimpa gl.kipas dengan status LAMA
kalau kebetulan nyampe ke ESP32 sebelum command terbaru dari RPi sempat
diproses. kirim_periodik() (aktuator_kipas.py) yang jalan tiap detik lalu
ikut menyebarkan status basi itu balik ke relay fisik - kelihatan kayak
kipas "kembali sendiri" beberapa saat setelah dinyalakan.

SOLUSI: bukan nebak pakai jeda waktu (network delay itu gak bisa
diprediksi), tapi pakai NOMOR GENERASI eksplisit dari firmware. Firmware
naikkan fan_generasi cuma kalau status kipas BENERAN berubah (dari jalur
mana pun: command RPi, tombol web lokal ESP32, autopilot darurat). RPi
cuma percaya laporan status yang generasinya LEBIH BESAR dari generasi
terakhir yang sudah dikonfirmasi - laporan dengan generasi sama/lebih
kecil pasti gema/basi, diabaikan.

KASUS REBOOT: fan_generasi di firmware itu RAM-only, reset ke 0 kalau
ESP32 reboot. boot_id (acak, sekali per boot) dipakai buat bedain "device
baru nyala ulang, ini genuinely baseline baru" vs "ini cuma data basi".
RPi restart juga otomatis tertangani: gl.esp32_boot_id_terakhir mulai
dari None, jadi kontak pertama SELALU dianggap "boot baru", baseline
langsung dipercaya.
"""

from variabel_global import gl


def terapkan_status_kipas(data):
    """
    Terima dict hasil parse JSON dari ESP32 (field 'kps' wajib ada;
    'gen'/'boot_id' opsional - kalau gak ada, gak bisa dipastikan, jadi
    gak disinkronkan sama sekali, lebih aman diam daripada salah timpa).

    Return True kalau gl.kipas disinkronkan (ada perubahan diterima),
    False kalau diabaikan (basi/gema, atau data gak lengkap).
    """
    kps = data.get("kps")
    if not kps or len(kps) != 5:
        return False

    gen = data.get("gen")
    boot_id = data.get("boot_id")

    if gen is None or boot_id is None:
        # Firmware lama / respons tanpa info generasi - gak bisa
        # dipastikan basi atau nggak, jadi jangan disinkronkan.
        return False

    if boot_id != gl.esp32_boot_id_terakhir:
        # ESP32 baru boot (fan_generasi ikut reset ke 0 di sisi firmware),
        # atau ini kontak pertama RPi ke device ini - percaya baseline
        # barunya, reset titik referensi generasi.
        gl.esp32_boot_id_terakhir = boot_id
        gl.kipas_generasi_terkonfirmasi = gen
        gl.kipas = list(kps)
        print(f"[status_esp32] Boot ESP32 baru terdeteksi (boot_id={boot_id}), baseline kipas direset")
        return True

    if gen > gl.kipas_generasi_terkonfirmasi:
        # Perubahan genuinely baru (bukan command RPi sendiri yang lagi
        # digemakan balik) - sinkronkan.
        gl.kipas_generasi_terkonfirmasi = gen
        gl.kipas = list(kps)
        print(f"[status_esp32] Perubahan kipas dari ESP32 terdeteksi (gen={gen})")
        return True

    # gen <= gl.kipas_generasi_terkonfirmasi -> basi/gema, abaikan diam-diam
    return False


print("status_esp32.py dimuat.")