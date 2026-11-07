# webserver.py
from fastapi import FastAPI, APIRouter, Request, Query, WebSocket, UploadFile, File, HTTPException, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import numpy as np
import time, cv2, base64
import asyncio
import random
import json
import os
import pytz
import httpx

# === IMPORT MODUL INTERNAL ===
from variabel_global import gl
from fungsi_umum import tanggal_waktu_usia, atur_usia
from kontrol_kipas import saklar_kipas
import penyimpanan_data as pd
import database_sqlite as ds
import thingspeak as thg
from proses_gambar import process_image_to_json, DEFAULT_CONFIG, draw_detection_overlay
from pathlib import Path
from fastapi.staticfiles import StaticFiles

TIMEZONE = pytz.timezone("Asia/Jakarta")

VISION_CONFIG = DEFAULT_CONFIG

DB_PATH = "kandang_ayam.db"

def decode_jpeg(jpeg_bytes: bytes) -> np.ndarray:
    np_arr = np.frombuffer(jpeg_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
# ==========================================================
#  INIT APP
# ==========================================================
app = FastAPI(title="Kandang Controller", version="1.0")
api_router = APIRouter(prefix="/api")
origins = [
    "https://kandangayamrakha.netlify.app",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # ← harus False jika allow_origins="*"
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

KEYS = ["jumlah_ayam_awal", "jumlah_ayam_mati", "jumlah_ayam_dipanen",
        "jumlah_pakan_sak", "bobot_rata_rata", "harga_kontrak_ayam",
        "harga_bibit_ayam", "harga_obat_ayam", "harga_pakan_kg"]

@api_router.get("/set", response_class=HTMLResponse)
async def set_baru():
    init = {"kipas": gl.kipas, "mode": gl.mode_kandang, "usia": gl.usia_ayam,
            "channel": gl.kipas_channel_aktif, "jml": gl.jumlah_kipas_timer,
            "hidup": gl.waktu_hidup, "mati": gl.waktu_mati,
            "prt": gl.cek_proteksi_listrik, "alarm": gl.flag_alarm_siaga,
            "dbw": gl.flag_database_AI, "suhu": gl.suhu_acuan,
            "log": str(gl.debug_str),
            "data": {k: getattr(gl, k, 0) for k in KEYS},
            "ip": {"pompa": POMPA_SENDANG_IP, "kebun": KEBUN_BELAKANG_IP, "pupuk": PUPUK_IP},}
    html = (BASE_DIR / "templates" / "set.html").read_text(encoding="utf-8")
    return html.replace("__INIT__", json.dumps(init, default=float))

@api_router.get("/auto_konf")
async def auto_konf(usia: int = Query(..., ge=0, le=45)):
    row = ds.baca_baris_auto(usia)
    if row is None or len(row) != 6:
        row = DEFAULT_ROW
    konf = parse_konfigurasi_auto(usia, row)
    rules = []
    for idx, key in enumerate(["d2", "d3", "d4", "d5", "d6"]):
        m = dict(konf["mode"][key])
        if m.get("mode") in ("S", "T"):
            m["id"] = idx + 1
            rules.append(m)
    return {"usia": usia, "wajib": konf["kipas_wajib"]["array"], "rules": rules}
# ==========================================================
#  KONFIGURASI RELAY TANAMAN (scalable)
#  Tambah relay baru cukup tambah 1 baris dict di list ini.
#  Tidak perlu ubah kode lain (HTML, JS, WebSocket, dst).
#
#  Catatan: "Air Depan Kandang" (tanaman/.157) dan "Air Belakang Rumah"
#  (tanaman2/.159) sudah dihapus - device tidak dipakai lagi.
#  "Pompa Sendang" (tanaman3/.160) juga sudah dikeluarkan dari sini -
#  device itu sekarang punya widget sendiri di halaman /set yang connect
#  LANGSUNG dari browser ke WebSocket ESP32-nya (lihat POMPA_SENDANG_IP
#  di bawah), tidak lagi lewat backend Pi seperti relay generik ini.
# ==========================================================
RELAY_TANAMAN = []

POMPA_SENDANG_IP = "192.168.0.160"
KEBUN_BELAKANG_IP = "192.168.0.159"
PUPUK_IP = "192.168.0.161"

# ==========================================================
#  NAVIGASI SWIPE ANTAR DASHBOARD
#  Urutan melingkar: BASE(0) - kebun(1) - pompa(2) - pupuk(3) - balik ke BASE.
#  Konvensi standar: tiap node expose GET /health (BASE: /api/health) yang
#  balas cepat kalau hidup — dipakai buat cek hidup/mati sebelum pindah
#  halaman lewat swipe/tombol, supaya tidak pernah nyasar ke device mati.
#  Kalau IP salah satu device berubah, cukup ubah konstanta di atas —
#  otomatis kepakai di sini juga.
# ==========================================================
NAV_NODES_JS = f"""[
  {{ id:'base',  set:'http://192.168.0.150:8080/api/set', health:'http://192.168.0.150:8080/api/health' }},
  {{ id:'kebun', set:'http://{KEBUN_BELAKANG_IP}/set',     health:'http://{KEBUN_BELAKANG_IP}/health' }},
  {{ id:'pompa', set:'http://{POMPA_SENDANG_IP}/set',      health:'http://{POMPA_SENDANG_IP}/health' }},
  {{ id:'pupuk', set:'http://{PUPUK_IP}/set',              health:'http://{PUPUK_IP}/health' }}
]"""

# BASE (index 0) — cuma swipe, tanpa tombol back (BASE itu "pusat",
# tidak ada satu tujuan "kembali" yang jelas).
SWIPE_NAV_HTML = f"""
<script>
(function(){{
  var NODES = {NAV_NODES_JS};
  var MY_INDEX = 0;
  var CEK_TIMEOUT_MS = 800;
  var sedangCek = false;

  function cekHidup(url, timeoutMs){{
    return new Promise(function(resolve){{
      var ctl = new AbortController();
      var timer = setTimeout(function(){{ ctl.abort(); resolve(false); }}, timeoutMs);
      fetch(url, {{signal: ctl.signal, cache:'no-store'}})
        .then(function(r){{ clearTimeout(timer); resolve(r.ok); }})
        .catch(function(){{ clearTimeout(timer); resolve(false); }});
    }});
  }}

  async function cariDanPindah(arah){{
    if (sedangCek) return;
    sedangCek = true;
    document.body.style.cursor = 'wait';

    var n = NODES.length;
    for (var i = 1; i < n; i++) {{
      var idx = arah === 'next' ? (MY_INDEX + i) % n : (MY_INDEX - i + n) % n;
      var target = NODES[idx];
      if (await cekHidup(target.health, CEK_TIMEOUT_MS)) {{
        window.location.href = target.set;
        return;
      }}
    }}
    sedangCek = false;
    document.body.style.cursor = 'default';
  }}

  var mulaiX = 0, mulaiY = 0;
  var SWIPE_MIN_JARAK = 80, SWIPE_MAX_VERTIKAL = 60;

  document.addEventListener('touchstart', function(e){{
    if (e.touches.length !== 1) return;
    mulaiX = e.touches[0].clientX;
    mulaiY = e.touches[0].clientY;
  }}, {{passive:true}});

  document.addEventListener('touchend', function(e){{
    if (!e.changedTouches || e.changedTouches.length !== 1) return;
    var dx = e.changedTouches[0].clientX - mulaiX;
    var dy = e.changedTouches[0].clientY - mulaiY;
    if (Math.abs(dy) >= SWIPE_MAX_VERTIKAL) return;
    if (dx > SWIPE_MIN_JARAK) cariDanPindah('next');
    else if (dx < -SWIPE_MIN_JARAK) cariDanPindah('prev');
  }}, {{passive:true}});
}})();
</script>
"""

# ==========================================================
#  UTILITY RESPONSE
# ==========================================================
def json_response(data: dict):
    return JSONResponse(content=data)

def parse_konfigurasi_string(s: str) -> dict:
    if not s or s == "N":
        return {"mode": "N"}

    parts = s.split("-")
    mode = parts[0]

    if mode == "S":
        suhu_raw = int(parts[1])
        kipas_str = parts[2]

        return {
            "mode": "S",
            "suhu": suhu_raw / 10.0,
            "kipas": [int(k) for k in kipas_str]
        }

    elif mode == "T":
        keys = ["tA", "tB", "tC", "tD", "tE", "tF", "tG", "tH"]
        values = list(map(int, parts[1:]))

        data = {"mode": "T"}
        for k, v in zip(keys, values):
            if k in ("tA", "tC", "tD"):
                data[k] = v / 10.0
            else:
                data[k] = v

        return data

    else:
        raise ValueError(f"Mode tidak dikenal: {mode}")

def parse_konfigurasi_auto(usia_ayam: int, row: list):
    d1, d2, d3, d4, d5, d6 = row

    def parse_kipas_string(s):
        try:
            s = str(s).strip()
            return [int(c) for c in s.ljust(5, "0")[:5]]
        except:
            return [0, 0, 0, 0, 0]

    def parse_mode_string(s):
        try:
            if not s or s == "N":
                return {"mode": "N"}

            parts = s.split("-")

            # ================= S MODE =================
            if parts[0] == "S" and len(parts) >= 3:
                return {
                    "mode": "S",
                    "suhu": int(parts[1]) / 10,
                    "kipas": parse_kipas_string(parts[2])
                }

            # ================= T MODE =================
            if parts[0] == "T" and len(parts) >= 9:
                a, b, c, d, e, f, g, h = parts[1:9]
                return {
                    "mode": "T",
                    "suhu_batas": int(a) / 10,
                    "jumlah_kipas": int(b),
                    "map_min": int(c) / 10,
                    "map_max": int(d) / 10,
                    "on_min": int(e),
                    "on_max": int(f),
                    "off_min": int(g),
                    "off_max": int(h)
                }

            return {"mode": "INVALID", "raw": s}

        except Exception as e:
            return {"mode": "ERROR", "raw": s}

    return {
        "usia_ayam": usia_ayam,
        "kipas_wajib": {
            "raw": d1,
            "array": parse_kipas_string(d1)
        },
        "mode": {
            "d2": parse_mode_string(d2),
            "d3": parse_mode_string(d3),
            "d4": parse_mode_string(d4),
            "d5": parse_mode_string(d5),
            "d6": parse_mode_string(d6),
        }
    }

def kipas_checked(arr, idx):
    return "checked" if arr[idx] == 1 else ""

def render_pengaturan_html(konf):
    import json
    from variabel_global import gl

    

    return f"""
<style>
  
</style>



<script>

</script>
"""

# ==========================================================
#  ENDPOINT /
# ==========================================================
@api_router.get("/")
async def root():
    #gl.jumlah_http += 1
    data = {
        "dta": [155, random.randint(1, 9), gl.jumlah_http],
        "kpa": [
            gl.mode_kandang,
            gl.tanggal_masuk_ayam_hari,
            gl.tanggal_masuk_ayam_bulan,
            gl.tanggal_masuk_ayam_tahun,
            gl.usia_ayam,
            gl.target_suhu,
            gl.suhu_minimal,
            gl.suhu_maksimal,
            *gl.kipas,
            gl.status_timer,
            gl.waktu_hidup,
            gl.waktu_mati,
            gl.detail_kipas,
            gl.detail_timer_kipas,
            gl.suhu_outlet_atas,
            gl.suhu_acuan
        ],
    }
    return json_response(data)



# ==========================================================
#  ENDPOINT /set (HALAMAN HTML)
# ==========================================================
@api_router.get("/health")
def health():
    return {"status": "ok"}

@api_router.get("/set_lama", response_class=HTMLResponse)
async def halaman_pengatur_kipas(request: Request):
    kipas_html = "".join([
        f"<button class='btn {'on' if k else 'off'}' onclick='toggleKipas({i})'>Kipas {i+1}</button>"
        for i, k in enumerate(gl.kipas)
    ])

    usia_options = "".join([f"<option value='{i}' {'selected' if gl.usia_ayam==i else ''}>{i}</option>" for i in range(46)])
    
    mode_options = f"""
    <option value='1' {'selected' if gl.mode_kandang==1 else ''}>Auto</option>
    <option value='2' {'selected' if gl.mode_kandang==2 else ''}>Manual</option>
    <option value='3' {'selected' if gl.mode_kandang==3 else ''}>Timer</option>
    <option value='4' {'selected' if gl.mode_kandang==4 else ''}>Selesai Panen</option>
    """

    jumlah_kipas_opts = "".join([
        f"<option value='{i}' {'selected' if gl.jumlah_kipas_timer==i else ''}>{i}</option>"
        for i in range(1,4)
    ])

    opsi_hidup = [10, 15, 20, 30, 45, 60, 90, 120]
    custom_hidup = gl.waktu_hidup not in opsi_hidup

    hidup_opts = "".join([
        f"<option value='{v}' {'selected' if gl.waktu_hidup==v else ''}>{v} Detik</option>"
        for v in opsi_hidup
    ])
    hidup_opts += f"<option value='custom' {'selected' if custom_hidup else ''}>Custom</option>"

    opsi_mati = [1, 2, 3, 5, 10, 15, 20, 30, 45, 60]
    custom_mati = gl.waktu_mati not in opsi_mati

    mati_opts = "".join([
        f"<option value='{v}' {'selected' if gl.waktu_mati==v else ''}>{v} Menit</option>"
        for v in opsi_mati
    ])
    mati_opts += f"<option value='custom' {'selected' if custom_mati else ''}>Custom</option>"

    timer_section = f"""
        <div id="timerSection" style="display:{'block' if gl.mode_kandang==3 else 'none'}">

            <br><label>Jumlah Kipas:</label>
            <select id='jumlah_kipas' onchange='updateSetting("jumlah_kipas_timer", this.value)'>
                {jumlah_kipas_opts}
            </select>

            <br><br><label>Waktu Hidup:</label>
            <select id='waktu_hidup'
                onchange='handleSelectChange("waktu_hidup", "Detik")'>
                {hidup_opts}
            </select>

            <div id='waktu_hidup_custom'
                style='display:{"block" if custom_hidup else "none"}'>
                <input type='number'
                    id='input_waktu_hidup'
                    value='{gl.waktu_hidup if custom_hidup else ""}'
                    onblur='updateSetting("waktu_hidup", this.value)'>
                <span>Detik</span>
            </div>

            <br><br><label>Waktu Mati:</label>
            <select id='waktu_mati'
                onchange='handleSelectChange("waktu_mati", "Menit")'>
                {mati_opts}
            </select>

            <div id='waktu_mati_custom'
                style='display:{"block" if custom_mati else "none"}'>
                <input type='number'
                    id='input_waktu_mati'
                    value='{gl.waktu_mati if custom_mati else ""}'
                    onblur='updateSetting("waktu_mati", this.value)'>
                <span>Menit</span>
            </div>

            <br><br>
        </div>
    """

    mode_name = "AUTO" if gl.mode_kandang == 1 else "TIMER" if gl.mode_kandang == 3 else "UNKNOWN"

    card_timer_html = f"""
    <div id="timerCard" class="timer-card"
        style="display:none;">

        <div class="timer-title">
            MODE <span id="cardModeName">{mode_name}</span>
        </div><br>

        <div>Waktu hidup:
            <span id="cardWaktuHidup">{gl.waktu_hidup}</span> detik
        </div>

        <div>Waktu mati:
            <span id="cardWaktuMati">{gl.waktu_mati}</span> menit
        </div>

        <div>Jumlah kipas:
            <span id="cardJumlahKipas">{gl.jumlah_kipas_timer}</span>
        </div>

        <div id="timerStatus" class="timer-status"></div>
        <div id="timerCountdown" class="timer-countdown">00:00</div>

        <div class="progress-container">
            <div id="progressBar" class="progress-bar"></div>
        </div>
    </div>
    """

    ayam_vars = [
        ("jumlah_ayam_awal", "Jumlah Ayam Awal"),
        ("jumlah_ayam_mati", "Jumlah Ayam Mati"),
        ("jumlah_pakan_sak", "Jumlah Pakan Sak"),
        ("bobot_rata_rata", "Bobot Rata-Rata"),
        ("harga_kontrak_ayam", "Harga Kontrak Ayam"),
        ("harga_bibit_ayam", "Harga Bibit Ayam"),
        ("harga_obat_ayam", "Harga Obat Ayam"),
        ("harga_pakan_kg", "Harga Pakan/kg"),
        ("jumlah_ayam_dipanen", "Jumlah Ayam Dipanen")
    ]
    ayam_opts = "".join([f"<option value='{k}'>{v}</option>" for k, v in ayam_vars])

    usia_raw = request.query_params.get("usia")
    
    if usia_raw is not None and usia_raw.isdigit():
        gl.usia_ui = int(usia_raw)
    
    row = ds.baca_baris_auto(gl.usia_ui)
    
    if row is None or len(row) != 6:
        row = DEFAULT_ROW
    
    konf = parse_konfigurasi_auto(gl.usia_ui, row)
    kipas_wajib = konf["kipas_wajib"]["array"]

    usia_options_2 = "".join([f"<option value='{i}' {'selected' if gl.usia_ui == i else ''}>{i}</option>" for i in range(46)])
    kipas_options = "".join([
        f"<label><input type='checkbox' value='{i}' {'checked' if kipas_wajib[i] else ''}> Kipas {i+1}</label>"
        for i in range(5)
    ])

    # ================= AMBIL DATA ASLI =================
    # asumsi kamu sudah punya ini dari DB / API / ESP
    
    row = gl.row_konfigurasi_kipas   # contoh: ["11000", "S-305-11000", ...]
    usia = gl.usia_ayam

    # ================= PARSE =================
    # konf = parse_konfigurasi_auto(usia, row)

    mode_keys = ["d2", "d3", "d4", "d5", "d6"]
    initial_rules = []

    # ================= KONVERSI KE FORMAT UI =================
    for idx, key in enumerate(mode_keys):
        m = konf.get("mode", {}).get(key, {})
        mode = m.get("mode", "N")

        rule = {"id": idx + 1, "mode": mode}

        if mode == "S":
            rule["suhu"] = float(m.get("suhu", 30))
            rule["kipas"] = m.get("kipas", [0, 0, 0, 0, 0])

        elif mode == "T":
            rule["suhu_batas"] = float(m.get("suhu_batas", 30))
            rule["jumlah_kipas"] = int(m.get("jumlah_kipas", 1))
            rule["map_min"] = float(m.get("map_min", 25))
            rule["map_max"] = float(m.get("map_max", 35))
            rule["on_min"] = int(m.get("on_min", 10))
            rule["on_max"] = int(m.get("on_max", 60))
            rule["off_min"] = int(m.get("off_min", 5))
            rule["off_max"] = int(m.get("off_max", 30))

        if mode != "N":
            initial_rules.append(rule)

    # ================= JSON UNTUK FRONTEND =================
    rules_json = json.dumps(initial_rules, ensure_ascii=False)

    # ================= CHECKBOX KIPAS =================
    fan_cbs_html = " ".join(
        f'<label><input type="checkbox" class="popup-fan-cb" value="{i}"> K{i+1}</label>'
        for i in range(5)
    )

    rules_json = json.dumps(initial_rules, ensure_ascii=False)
    suhu_acuan = gl.suhu_acuan  # ← tambah ini

    # RELAY_TANAMAN sekarang kosong (lihat definisi di atas) - variabel ini
    # cuma dipakai JS generik toggleTanaman/updateTanamanButton yang tetap
    # dipertahankan sebagai infrastruktur kalau nanti ada relay tanaman baru
    # ditambahkan lewat RELAY_TANAMAN. Pompa Sendang sekarang pakai widget
    # sendiri (lihat bagian "Kebun" di HTML) yang connect langsung ke ESP32.
    tanaman_ids_json = json.dumps([r["id"] for r in RELAY_TANAMAN])

    if gl.mode_kandang in [1]:
        section_kipas_auto = f"""
    <section>
        <h2>Pengaturan Kipas Auto</h2>
        <div id="sliderContainer">
        <label>Pilih kipas yang wajib hidup:</label>
        <div class="checkbox-group" id="wajibGroup">
          {kipas_options}
        </div>
        <h2>Pengaturan Mode</h2>
        <div id="pengaturanContainer">
            <div id="sliderOuter">
            <div id="tempScale"></div>
            <div id="trackCol"><div id="trackLine"></div></div>
            <div id="infoCol"></div>
            </div>
            <button id="addRuleBtn" onclick="addNewRule()">+ Tambah Aturan</button>

            <!-- overlay + popup -->
            <div id="popupOverlay" onclick="closePopup()"></div>
            <div id="rulePopup">
            <h3>&#9881; Pengaturan Aturan</h3>

            <label class="pp-label">Mode:</label>
            <select class="pp-input" id="popupMode" onchange="onPopupModeChange()">
                <option value="S">Mode Suhu (S)</option>
                <option value="T">Mode Timer (T)</option>
            </select>

            <label class="pp-label">Jika suhu lebih dari (°C):</label>
            <input type="number" class="pp-input" id="popupSuhu" step="0.1" min="25" max="37">

            <!-- Mode S -->
            <div id="ppModeS">
                <div class="pp-section-title">Kipas yang hidup</div>
                <div class="fan-cb-group" id="popupFanGroup">{fan_cbs_html}</div>
            </div>

            <!-- Mode T -->
            <div id="ppModeT" style="display:none;">
                <div class="pp-section-title">Rentang suhu mapping</div>
                <div class="pp-row2">
                <div>
                    <label class="pp-label">Min (°C):</label>
                    <input type="number" class="pp-input" id="popupMapMin" step="0.1" min="25" max="37">
                </div>
                <div>
                    <label class="pp-label">Max (°C):</label>
                    <input type="number" class="pp-input" id="popupMapMax" step="0.1" min="25" max="37">
                </div>
                </div>
                <div class="pp-section-title">Jumlah kipas</div>
                <label class="pp-label">Kipas yang hidup (1–5):</label>
                <input type="number" class="pp-input" id="popupJumlah" step="1" min="1" max="5">
                <div class="pp-section-title">Siklus waktu</div>
                <div class="pp-row2">
                <div>
                    <label class="pp-label">Hidup min (dtk):</label>
                    <input type="number" class="pp-input" id="popupOnMin" min="1" max="300">
                </div>
                <div>
                    <label class="pp-label">Hidup max (dtk):</label>
                    <input type="number" class="pp-input" id="popupOnMax" min="1" max="300">
                </div>
                </div>
                <div class="pp-row2" style="margin-top:6px;">
                <div>
                    <label class="pp-label">Mati min (mnt):</label>
                    <input type="number" class="pp-input" id="popupOffMin" min="1" max="120">
                </div>
                <div>
                    <label class="pp-label">Mati max (mnt):</label>
                    <input type="number" class="pp-input" id="popupOffMax" min="1" max="120">
                </div>
                </div>
            </div>

            <div class="pp-actions">
                <button class="pp-save"   onclick="savePopup()">Simpan</button>
                <button class="pp-delete" onclick="deleteRule()">Hapus</button>
                <button class="pp-cancel" onclick="closePopup()">Batal</button>
            </div>
            </div>
        </div>
        </div><br><br>
        <button class="btnsimpan" onclick="generateSemua()">Simpan</button>
        <div class="output" id="outputSemua"></div>
      </section>"""
    else:
        section_kipas_auto = ''

    html = f"""<!DOCTYPE html>
    <html><head>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Pengatur Kipas</title>
    <style>
      body {{ font-family: Arial; padding: 20px; margin: 0; }}
      label {{ margin:7px; display:inline-block; }}
      .button-container {{ display: flex; width: 100%; padding: 0; margin: 0; }}
      .btn {{ flex: 1; aspect-ratio: 1 / 1; font-size: 16px; border: 1px solid #ccc; margin: 2px; cursor: pointer; transition: background-color 0.3s; }}
      .on {{ background-color: #25D366; color: white; }}
      .off {{ background-color: red; color: white; }}
      .btn.locked {{ opacity: 0.4; pointer-events: none; cursor: not-allowed; }}
      #statusBadge {{
        position: fixed; top: 8px; right: 8px; z-index: 10000;
        background: #fff; border: 1px solid #ccc; border-radius: 8px;
        padding: 6px 12px; font-size: 12px; font-family: Arial;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        text-align: right; line-height: 1.4;
      }}
      .loader {{ border: 8px solid #f3f3f3; border-top: 8px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; }}
      @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
      .info-icon {{ display: inline-block; width: 15px; height: 15px; background-color: #3498db; color: white; border-radius: 50%; text-align: center; line-height: 15px; font-size: 10px; cursor: pointer; margin-left: 6px; }}
      .tooltip-box {{ display: none; position: absolute; background: #fff; border: 1px solid #888; padding: 10px; border-radius: 8px; box-shadow: 0px 3px 10px rgba(0,0,0,0.2); max-width: 250px; z-index: 9999; }}
      .timer-card {{
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-top: 15px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
            text-align: center;
        }}

        .timer-title {{
            font-size: 14px;
            letter-spacing: 1px;
            opacity: 0.8;
        }}

        .timer-status {{
            font-size: 16px;
            margin-top: 5px;
        }}

        .timer-countdown {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}

        .progress-container {{
            width: 100%;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            overflow: hidden;
            height: 12px;
        }}

        .progress-bar {{
            height: 100%;
            width: 0%;
            background: #25D366;
            transition: width 1s linear;
        }}

        h2 {{ margin-top: 30px; }}
        section {{ background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
        .checkbox-group {{ display: flex; gap: 10px; margin-top: 10px; }}
        select, input[type="number"] {{ width: 100%; max-width: 200px; }}
        .output {{ margin-top: 15px; font-family: monospace; background: #e0e0e0; padding: 10px; border-radius: 5px; }}
        .baris-pengaturan {{ border-top: 1px solid #ccc; margin-top: 15px; padding-top: 10px; }}
        .form-grid {{
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 8px 12px;
        align-items: center;
        max-width: 500px;
        }}
        .form-row-3 {{
        display: grid;
        grid-template-columns: auto 1fr auto 1fr;
        gap: 8px 10px;
        align-items: center;
        }}
        .form-section {{
        margin-top: 12px;
        }}
        .form-title {{
        font-weight: bold;
        margin-top: 10px;
        }}
        #sliderOuter {{
            display: flex;
            align-items: flex-start;
            gap: 0;
            margin: 20px 0 10px 0;
            height: 450px;
        }}
        #tempScale {{
            position: relative;
            width: 40px;
            flex-shrink: 0;
            height: 450px;
        }}
        .temp-lbl {{
            position: absolute;
            right: 4px;
            font-size: 10px;
            color: #bbb;
            transform: translateY(-50%);
            white-space: nowrap;
        }}
        .temp-lbl.major {{
            font-size: 11px;
            font-weight: bold;
            color: #666;
        }}
        #trackCol {{
            position: relative;
            width: 30px;
            flex-shrink: 0;
            height: 450px;
        }}
        #trackLine {{
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            width: 4px;
            top: 10px;
            bottom: 10px;
            background: #222;
            border-radius: 2px;
        }}
        .sl-handle {{
            position: absolute;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 78px;
            height: 22px;
            background: #8B0000;
            border: 2px solid #5a0000;
            border-radius: 3px;
            cursor: grab;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.4);
            transition: background 0.1s;
            -webkit-tap-highlight-color: transparent;
            touch-action: none;       
            user-select: none;       
            -webkit-user-select: none;
        }}

        @media (pointer: coarse) {{
            .sl-handle {{
            width: 78px;
            height: 22px;
            }}
            .sl-handle-text {{
            font-size: 11px;
            }}
        }}

        .sl-handle:hover {{ background: #a80000; }}
        .sl-handle.dragging {{ cursor: grabbing !important; background: #c40000; }}
        .sl-handle-text {{
            color: white;
            font-size: 9px;
            font-weight: bold;
            pointer-events: none;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }}
        #infoCol {{
            position: relative;
            flex: 1;
            height: 450px;
        }}
        .handle-info {{
            position: absolute;
            transform: translateY(-50%);
            display: flex;
            align-items: center;
            gap: 6px;
            left: 30px;
            pointer-events: none;
        }}
        .temp-tag {{
            font-size: 11px;
            font-weight: bold;
            color: #333;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 3px;
            padding: 1px 5px;
            min-width: 44px;
            text-align: center;
        }}
        .mode-badge {{
            font-size: 8px;
            padding: 2px 5px;
            border-radius: 3px;
            font-weight: bold;
            color: white;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .badge-S {{ background: #007bff; }}
        .badge-T {{ background: #fd7e14; }}
        .fan-box {{
            display: flex;
            gap: 3px;
            border: 1px solid #bbb;
            border-radius: 3px;
            padding: 3px 5px;
            background: #fff;
            align-items: center;
        }}
        .fan-dot {{
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: #e0e0e0;
            border: 1px solid #bbb;
        }}
        .fan-dot.on {{ background: #28a745; border-color: #1c6e31; }}
        .tick-mark {{
            position: absolute;
            right: 0;
            height: 1px;
            background: #ddd;
            transform: translateY(-50%);
        }}
        .tick-mark.major {{
            height: 1px;
            background: #aaa;
        }}

        /* ── Popup ── */
        #rulePopup {{
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #fff;
            padding: 22px 24px 18px;
            border-radius: 12px;
            box-shadow: 0 10px 36px rgba(0,0,0,0.28);
            z-index: 2000;
            width: 340px;
            max-height: 85vh;
            overflow-y: auto;
            box-sizing: border-box;
        }}
        #popupOverlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.45);
            z-index: 1999;
        }}
        #rulePopup h3 {{
            margin: 0 0 14px;
            font-size: 14px;
            color: #222;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .pp-label {{
            display: block;
            font-size: 11px;
            color: #666;
            margin-top: 10px;
            margin-bottom: 3px;
        }}
        .pp-input {{
            width: 100%;
            padding: 6px 8px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 13px;
            box-sizing: border-box;
        }}
        .pp-row2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 4px;
        }}
        .fan-cb-group {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 6px;
        }}
        .fan-cb-group label {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
            cursor: pointer;
            margin: 0;
        }}
        .pp-section-title {{
            font-size: 11px;
            font-weight: bold;
            color: #888;
            margin-top: 14px;
            margin-bottom: 2px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .pp-actions {{
            display: flex;
            gap: 8px;
            margin-top: 18px;
        }}
        .pp-actions button {{
            flex: 1;
            padding: 9px 0;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
        }}
        .pp-save {{ background: #007bff; color: #fff; }}
        .pp-save:hover {{ background: #0056b3; }}
        .pp-delete {{ background: #dc3545; color: #fff; }}
        .pp-delete:hover {{ background: #b02a37; }}
        .pp-cancel {{ background: #e9ecef; color: #333; }}
        .pp-cancel:hover {{ background: #ced4da; }}
        #addRuleBtn {{
            margin-top: 6px;
            padding: 8px 18px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
        }}
        .btnsimpan{{
            margin-top: 6px;
            padding: 8px 18px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
        }}
        #addRuleBtn:hover {{ background: #1e7e34; }}

    </style>
    </head><body>
    <div id='statusBadge'>...</div>
    <div id='loading' style='display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.7);z-index:9999;text-align:center;'>
      <div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'><div class='loader'></div><br>Loading...</div>
    </div>

    <h2>Pengatur Kipas</h2>
    <label>Usia Ayam:</label>
    <select id='usia' onchange='updateSetting("usia", this.value)'>{usia_options}</select>
    <br><br>
    <label>Mode:</label>
    <select id='mode' onchange='setMode("mode", this.value)'>{mode_options}</select><br><br>
    <div style='margin-bottom:12px;padding:10px 14px;border:1px solid #ccc;border-radius:8px;display:inline-block;background:#f8f9fa;color:red;'>Suhu Saat Ini: {gl.suhu_acuan}</div><br><br>
    {timer_section}
    {section_kipas_auto}
    <br><br><h3>Kipas</h3>
    <div class='button-container'>{kipas_html}</div><br><br>
    {card_timer_html}

    <h3>Update Data Ayam</h3>
    <label>Pilih Variabel:</label><br>
    <select id="varSelect">{ayam_opts}</select><br><br>
    <label>Masukkan Nilai:</label><br>
    <input type="number" id="nilai"><br><br>
    <button onclick="kirimData()">Kirim ke Kandang</button><br><br>
    
    <h3>Kebun</h3>

    <style>
    .pompa-btn{{width:100px;height:100px;border-radius:12px;border:none;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:#fff;font-size:14px;font-weight:600;cursor:pointer}}
    .pompa-btn:active{{opacity:.85}}
    .pompa-on{{background:#22c55e}}
    .pompa-off{{background:#ef4444}}
    .pompa-connecting{{background:#9ca3af;cursor:default}}
    .pompa-dot{{width:10px;height:10px;border-radius:50%;background:rgba(255,255,255,.5)}}
    </style>
    <div style="display:flex; flex-direction:row; align-items:flex-start; justify-content:center; gap:24px; flex-wrap:wrap;">
        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
            <div style="font-size:13px; font-weight:bold; color:#333;">Pompa Sendang</div>
            <button class="pompa-btn pompa-connecting" id="pompaBtn" onclick="kirimPompa()">
                <div class="pompa-dot"></div>
                <span id="pompaLbl">...</span>
            </button>
            <div id="pompaWsInfo" style="font-size:11px;color:#9ca3af;">menghubungkan...</div>
        </div>

        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
            <div style="font-size:13px; font-weight:bold; color:#333;">Air Kebun Belakang</div>
            <button class="pompa-btn pompa-connecting" id="kebunBelakangBtn" onclick="kirimKebunBelakang()">
                <div class="pompa-dot"></div>
                <span id="kebunBelakangLbl">...</span>
            </button>
            <div id="kebunBelakangWsInfo" style="font-size:11px;color:#9ca3af;">menghubungkan...</div>
        </div>
    </div>

    <style>
    .pupuk-grid{{display:flex;gap:1rem;flex-wrap:wrap;justify-content:center}}
    .pupuk-card{{display:flex;flex-direction:column;align-items:center;gap:.5rem}}
    .pupuk-lbl{{font-size:11px;color:#888;font-weight:500;text-transform:uppercase;letter-spacing:.05em}}
    .pupuk-btn{{width:90px;height:90px;border-radius:12px;border:none;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;color:#fff;font-size:13px;font-weight:600;cursor:pointer}}
    .pupuk-btn.pupuk-wide{{width:120px;height:75px}}
    .pupuk-btn:active{{opacity:.8}}
    .pupuk-on{{background:#22c55e}}
    .pupuk-off{{background:#ef4444}}
    .pupuk-connecting{{background:#9ca3af;cursor:default}}
    .pupuk-dot{{width:9px;height:9px;border-radius:50%;background:rgba(255,255,255,.5)}}
    </style>
    <div style="margin-top:24px; text-align:center;">
        <div style="font-size:13px; font-weight:bold; color:#333; margin-bottom:10px;">Mesin Pupuk</div>

        <div style="font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Pompa Nutrisi</div>
        <div class="pupuk-grid" id="pupukGridPompa"></div>

        <div style="font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:.05em;margin:14px 0 6px;">Pengaduk &amp; Penyiram Benih</div>
        <div class="pupuk-grid" id="pupukGridAux"></div>

        <div id="pupukWsInfo" style="font-size:11px;color:#9ca3af;margin-top:8px;">menghubungkan...</div>
    </div>

    <br><br><br><br><br><br>

    <h3>Pengaturan Kandang</h3>
    <label><input id="check_0" type="checkbox" {'checked' if gl.cek_proteksi_listrik else ''} onclick="updateCeklist()"> Proteksi Listrik Overload</label>
    <span class="info-icon" onclick="toggleInfo('info1')">?</span>
    <div id="info1" class="tooltip-box">Fitur ini memastikan agar sistem menjaga kipas tidak hidup semua untuk melindungi kandang dari mati listrik akibat arus overload.</div><br>
    
    <label><input id="check_2" type="checkbox" {'checked' if gl.flag_alarm_siaga else ''} onclick="updateCeklist()"> Alarm Lampu Kipas Rumah</label>
    <span class="info-icon" onclick="toggleInfo('info3')">?</span>
    <div id="info3" class="tooltip-box">Lampu indikator kipas di rumah berkedip saat listrik mati</div><br>
    
    <br><br><br>

    <label><input id="check_1" type="checkbox" {'checked' if gl.flag_database_AI else ''} onclick="updateCeklist()"> Tulis database</label>
    <span class="info-icon" onclick="toggleInfo('info2')">?</span>
    <div id="info2" class="tooltip-box">Menulis data sensor dan kipas ke database training</div>

    <br><br>

    <h3>Log data</h3>
    <div>{gl.debug_str}</div>

    <br><br>

    <button onclick="downloadDB()">Download Database</button>

    <script>
      let mode = {gl.mode_kandang};
      let prtlst = {gl.cek_proteksi_listrik};
      let kipas = {gl.kipas};
      let usia = {gl.usia_ayam};
      let channelAktif = "{gl.kipas_channel_aktif}";  // "http" | "serial" | "gagal" | "" (belum pernah kirim)
      let ws = null;
      let currentVersion = 0;
      let waitingServer = false;
      let timerRemaining = 0;
      let timerState = null;
      let countdownInterval = null;

      // === STATE TANAMAN (scalable, generated dari RELAY_TANAMAN) ===
      let tanamanIds = {tanaman_ids_json};
      let tanamanState = {{}};
      tanamanIds.forEach(id => tanamanState[id] = 0);

      // === POMPA SENDANG - WebSocket LANGSUNG ke ESP32, TIDAK lewat backend Pi ===
      // Desain & protokol disalin dari handleSet() firmware ESP32-nya sendiri:
      // kirim teks "on"/"off", terima teks "1"/"0" sebagai state.
      const POMPA_SENDANG_IP = "{POMPA_SENDANG_IP}";
      var wsPompa = null, pompaState = null;

      function connectPompaSendang() {{
        wsPompa = new WebSocket('ws://' + POMPA_SENDANG_IP + '/ws');

        wsPompa.onopen = function() {{
          document.getElementById('pompaWsInfo').textContent = 'terhubung';
        }};

        wsPompa.onmessage = function(e) {{
          setPompaState(e.data === '1');
        }};

        wsPompa.onclose = function() {{
          document.getElementById('pompaWsInfo').textContent = 'terputus, menghubungkan ulang...';
          document.getElementById('pompaBtn').className = 'pompa-btn pompa-connecting';
          document.getElementById('pompaLbl').textContent = '...';
          pompaState = null;
          setTimeout(connectPompaSendang, 2000);
        }};

        wsPompa.onerror = function() {{
          wsPompa.close();
        }};
      }}

      function setPompaState(nyala) {{
        pompaState = nyala;
        document.getElementById('pompaBtn').className = 'pompa-btn ' + (nyala ? 'pompa-on' : 'pompa-off');
        document.getElementById('pompaLbl').textContent = nyala ? 'NYALA' : 'MATI';
      }}

      function kirimPompa() {{
        if (!wsPompa || wsPompa.readyState !== WebSocket.OPEN || pompaState === null) return;
        wsPompa.send(pompaState ? 'off' : 'on');
      }}

      // === AIR KEBUN BELAKANG - WebSocket LANGSUNG ke ESP32, TIDAK lewat backend Pi ===
      // Desain & protokol sama persis dengan Pompa Sendang di atas.
      const KEBUN_BELAKANG_IP = "{KEBUN_BELAKANG_IP}";
      var wsKebunBelakang = null, kebunBelakangState = null;

      function connectKebunBelakang() {{
        wsKebunBelakang = new WebSocket('ws://' + KEBUN_BELAKANG_IP + '/ws');

        wsKebunBelakang.onopen = function() {{
          document.getElementById('kebunBelakangWsInfo').textContent = 'terhubung';
        }};

        wsKebunBelakang.onmessage = function(e) {{
          setKebunBelakangState(e.data === '1');
        }};

        wsKebunBelakang.onclose = function() {{
          document.getElementById('kebunBelakangWsInfo').textContent = 'terputus, menghubungkan ulang...';
          document.getElementById('kebunBelakangBtn').className = 'pompa-btn pompa-connecting';
          document.getElementById('kebunBelakangLbl').textContent = '...';
          kebunBelakangState = null;
          setTimeout(connectKebunBelakang, 2000);
        }};

        wsKebunBelakang.onerror = function() {{
          wsKebunBelakang.close();
        }};
      }}

      function setKebunBelakangState(nyala) {{
        kebunBelakangState = nyala;
        document.getElementById('kebunBelakangBtn').className = 'pompa-btn ' + (nyala ? 'pompa-on' : 'pompa-off');
        document.getElementById('kebunBelakangLbl').textContent = nyala ? 'NYALA' : 'MATI';
      }}

      function kirimKebunBelakang() {{
        if (!wsKebunBelakang || wsKebunBelakang.readyState !== WebSocket.OPEN || kebunBelakangState === null) return;
        wsKebunBelakang.send(kebunBelakangState ? 'off' : 'on');
      }}

      // === MESIN PUPUK - WebSocket LANGSUNG ke ESP32, TIDAK lewat backend Pi ===
      // Desain & protokol disalin dari handleSet() firmware pupuk_esp12:
      // kirim teks "A:on"/"A:off"/"B:.../"C:.../"P:.../"S:...",
      // terima JSON {{pompa:[...], pengaduk:{{...}}, solenoid:{{...}}}}.
      const PUPUK_IP = "{PUPUK_IP}";
      var wsPupuk = null;
      var pupukState = {{ pompa: {{A:null,B:null,C:null}}, pengaduk:null, solenoid:null }};

      function renderPupukPompa() {{
        var g = document.getElementById('pupukGridPompa');
        g.innerHTML = '';
        ['A','B','C'].forEach(function(id) {{
          var on = pupukState.pompa[id];
          var cls = on===null ? 'pupuk-connecting' : (on ? 'pupuk-on' : 'pupuk-off');
          var teks = on===null ? '...' : (on ? 'NYALA' : 'MATI');
          g.innerHTML += '<div class="pupuk-card">'
            + '<span class="pupuk-lbl">Pupuk ' + id + '</span>'
            + '<button class="pupuk-btn ' + cls + '" onclick="kirimPupukPompa(\\'' + id + '\\')">'
            + '<div class="pupuk-dot"></div>' + teks + '</button>'
            + '</div>';
        }});
      }}

      function renderPupukAux() {{
        var g = document.getElementById('pupukGridAux');
        g.innerHTML = '';

        var onP = pupukState.pengaduk;
        var clsP = onP===null ? 'pupuk-connecting' : (onP ? 'pupuk-on' : 'pupuk-off');
        var teksP = onP===null ? '...' : (onP ? 'NYALA' : 'MATI');
        g.innerHTML += '<div class="pupuk-card">'
          + '<span class="pupuk-lbl">Pengaduk</span>'
          + '<button class="pupuk-btn pupuk-wide ' + clsP + '" onclick="kirimPupukAux(\\'P\\')">'
          + '<div class="pupuk-dot"></div>' + teksP + '</button>'
          + '</div>';

        var onS = pupukState.solenoid;
        var clsS = onS===null ? 'pupuk-connecting' : (onS ? 'pupuk-on' : 'pupuk-off');
        var teksS = onS===null ? '...' : (onS ? 'NYALA' : 'MATI');
        g.innerHTML += '<div class="pupuk-card">'
          + '<span class="pupuk-lbl">Siram Benih</span>'
          + '<button class="pupuk-btn pupuk-wide ' + clsS + '" onclick="kirimPupukAux(\\'S\\')">'
          + '<div class="pupuk-dot"></div>' + teksS + '</button>'
          + '</div>';
      }}

      function kirimPupukPompa(id) {{
        if (!wsPupuk || wsPupuk.readyState !== WebSocket.OPEN || pupukState.pompa[id] === null) return;
        wsPupuk.send(id + ':' + (pupukState.pompa[id] ? 'off' : 'on'));
      }}

      function kirimPupukAux(id) {{
        var on = id === 'P' ? pupukState.pengaduk : pupukState.solenoid;
        if (!wsPupuk || wsPupuk.readyState !== WebSocket.OPEN || on === null) return;
        wsPupuk.send(id + ':' + (on ? 'off' : 'on'));
      }}

      function connectPupuk() {{
        wsPupuk = new WebSocket('ws://' + PUPUK_IP + '/ws');

        wsPupuk.onopen = function() {{
          document.getElementById('pupukWsInfo').textContent = 'terhubung';
        }};

        wsPupuk.onmessage = function(e) {{
          var d = JSON.parse(e.data);
          d.pompa.forEach(function(p) {{ pupukState.pompa[p.id] = p.nyala; }});
          pupukState.pengaduk = d.pengaduk.nyala;
          pupukState.solenoid = d.solenoid.nyala;
          renderPupukPompa();
          renderPupukAux();
        }};

        wsPupuk.onclose = function() {{
          document.getElementById('pupukWsInfo').textContent = 'terputus, menghubungkan ulang...';
          pupukState = {{ pompa: {{A:null,B:null,C:null}}, pengaduk:null, solenoid:null }};
          renderPupukPompa();
          renderPupukAux();
          setTimeout(connectPupuk, 2000);
        }};

        wsPupuk.onerror = function() {{
          wsPupuk.close();
        }};
      }}

      renderPupukPompa();
      renderPupukAux();

      function toggleTanaman(id) {{
          if (!ws || ws.readyState !== WebSocket.OPEN) {{
              alert("WebSocket belum siap");
              return;
          }}

          tanamanState[id] = tanamanState[id] ? 0 : 1;

          ws.send(JSON.stringify({{
              type: "set_setting",
              param: id,
              value: tanamanState[id],
              version: currentVersion
          }}));

          updateTanamanButton(id);
      }}

      function updateTanamanButton(id) {{
          const btn = document.getElementById("btn_" + id);
          if (!btn) return;
          btn.innerText = tanamanState[id] ? "Matikan Air" : "Hidupkan Air";
          btn.className = "btn " + (tanamanState[id] ? "on" : "off");
      }}

      function connectWebSocket() {{
        ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/api/ws/kipas');
        ws.onopen = function(event) {{
          console.log('WebSocket connected');
          currentVersion = 0;
        }};

        ws.onmessage = function(event) {{
          const data = JSON.parse(event.data);

            if (data.type === "init" || data.type === "state_update" || data.type === "resync") {{
                kipas = data.kipas;
                usia = data.usia;
                currentVersion = data.version;
                mode = data.mode;
                document.getElementById("mode").value = data.mode;
                if ((data.mode === 1 || data.mode === 3) && data.timer_remaining !== undefined) {{
                    timerRemaining = data.timer_remaining;
                    timerState = data.timer_state;
                    startCountdown();
                }}
                updateKipasDisplay();
                updateUsiaDisplay();
                waitingServer = false;
            }}

            if (data.channel !== undefined) {{
                channelAktif = data.channel;
                updateStatusBadge();
                updateKipasDisplay();  // status lock (offline) ikut disegarkan
            }}

            if (data.mode !== undefined) {{
                document.getElementById("mode").value = data.mode;
                mode = data.mode;
                const timerSection = document.getElementById("timerSection");
                timerSection.style.display =
                    (data.mode == 3) ? "block" : "none";
                const card = document.getElementById("timerCard");

                
            }}

            // TIMER VALUE SYNC
            if (data.jumlah_kipas_timer !== undefined) {{
                document.getElementById("jumlah_kipas").value = data.jumlah_kipas_timer;
                document.getElementById("cardJumlahKipas").innerText = data.jumlah_kipas_timer;
            }}

            if (data.waktu_hidup !== undefined) {{
                syncTimerValue("waktu_hidup", data.waktu_hidup);
                document.getElementById("cardWaktuHidup").innerText = data.waktu_hidup;
            }}

            if (data.waktu_mati !== undefined) {{
                syncTimerValue("waktu_mati", data.waktu_mati);
                document.getElementById("cardWaktuMati").innerText = data.waktu_mati;
            }}

            // SYNC SEMUA TOMBOL TANAMAN (scalable)
            tanamanIds.forEach(id => {{
                if (data[id] !== undefined) {{
                    tanamanState[id] = data[id];
                    updateTanamanButton(id);
                }}
            }});

            if (data.relay_error) {{
                alert(`Gagal mengatur "${{data.relay_error.param}}": ${{data.relay_error.reason}}. Status dikembalikan ke semula.`);
            }}
        }};
        ws.onerror = function(event) {{
          console.error('WebSocket error:', event);
        }};
        ws.onclose = function(event) {{
          console.log('WebSocket disconnected, reconnecting...');
          setTimeout(connectWebSocket, 3000);
        }};
      }}

      function syncTimerValue(id, value) {{
        const select = document.getElementById(id);
        const customDiv = document.getElementById(id + "_custom");
        const input = document.getElementById("input_" + id);

        const optionExists =
            [...select.options].some(opt => opt.value == value);

        if (optionExists) {{
            select.value = value;
            customDiv.style.display = "none";
        }} else {{
            select.value = "custom";
            customDiv.style.display = "block";
            input.value = value;
        }}
    }}


      function updateKipasDisplay() {{
        const terkunci = (mode == 1 || mode == 3) || (channelAktif === "gagal");
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach((btn, i) => {{
          btn.className = 'btn ' + (kipas[i] ? 'on' : 'off') + (terkunci ? ' locked' : '');
        }});
      }}

      function updateStatusBadge() {{
        const badge = document.getElementById('statusBadge');
        let ikon, teks;
        if (channelAktif === "http") {{
          ikon = "\N{LARGE GREEN CIRCLE}"; teks = "Online - HTTP";
        }} else if (channelAktif === "serial") {{
          ikon = "\N{LARGE YELLOW CIRCLE}"; teks = "Online - Serial (fallback)";
        }} else if (channelAktif === "gagal") {{
          ikon = "\N{LARGE RED CIRCLE}"; teks = "Offline";
        }} else {{
          ikon = "\N{MEDIUM WHITE CIRCLE}"; teks = "Menghubungkan...";
        }}
        badge.innerHTML = ikon + " " + teks;
      }}

      function updateUsiaDisplay() {{
        const usiaSelect = document.getElementById('usia');
        for (let i = 0; i < usiaSelect.options.length; i++) {{
          if (usiaSelect.options[i].value == usia) {{
            usiaSelect.selectedIndex = i;
            break;
          }}
        }}
      }}

    function handleSelectChange(id, satuan) {{
        const select = document.getElementById(id);
        const customDiv = document.getElementById(id + "_custom");

        if (select.value === "custom") {{
            customDiv.style.display = "block";
        }} else {{
            customDiv.style.display = "none";
            updateSetting(id, select.value);
        }}
    }}
      
      function toggleKipas(i) {{
      if (waitingServer) return;
        if ((mode == 1)||(mode == 3)) {{
            alert('Ganti dulu ke mode manual atau selesai panen!');
            return;
        }}
        if (channelAktif === "gagal") {{
            alert('RPi sedang tidak terhubung ke ESP32 (HTTP maupun Serial gagal). Tombol dikunci sampai koneksi pulih.');
            return;
        }}

        const count = kipas.filter(k => k == 1).length;
        if (prtlst == 1 && count == 4 && kipas[i] == 0) {{
            alert('Tidak dapat menghidupkan 5 kipas karena proteksi listrik overload.');
            return;
        }}
        waitingServer = true;

        ws.send(JSON.stringify({{
            type: "set_kipas",
            index: i,
            value: kipas[i] ? 0 : 1,
            version: currentVersion
            }}));
        }}
      
      function toggleInfo(id) {{
        const box = document.getElementById(id);
        box.style.display = box.style.display === 'block' ? 'none' : 'block';
      }}

      function toggleCustomInput(field) {{
        const customDiv = document.getElementById(field + '_custom');
        customDiv.style.display = document.getElementById(field).value === 'custom' ? 'block' : 'none';
      }}

      function updateSetting(param, value) {{
            if (!ws || ws.readyState !== WebSocket.OPEN) {{
                console.error("WebSocket belum siap");
                return;
            }}

            ws.send(JSON.stringify({{
                type: "set_setting",
                param: param,
                value: value,
                version: currentVersion
            }}));

             if (param === "usia") {{
                fetch(`/api/slider_kipas_auto?usia=${{value}}`)
                    .then(r => r.text())
                    .then(html => {{
                        const container = document.getElementById('sliderContainer');
                        if (container) container.innerHTML = html;
                    }});
            }}
        }}

      function kirimData() {{
        const value = document.getElementById('nilai').value;
        if (!value) {{ alert("Isi nilai terlebih dahulu!"); return; }}
        updateSetting(document.getElementById('varSelect').value, value);
        alert("Berhasil memperbarui");
      }}
      
      function updateCeklist() {{
        fetch(`/api/ceklist?prt_lst=${{document.getElementById('check_0').checked ? 1 : 0}}&flg_dtbs=${{document.getElementById('check_1').checked ? 1 : 0}}&flg_alrml=${{document.getElementById('check_2').checked ? 1 : 0}}`)
          .then(r => r.json());
      }}

      function setMode() {{
        updateSetting("mode", document.getElementById('mode').value);
      }}

      function setUsia() {{
        updateSetting("usia", document.getElementById('usia').value);
      }}

    function startCountdown() {{
        if (countdownInterval) {{
            clearInterval(countdownInterval);
        }}

        updateTimerDisplay();

        countdownInterval = setInterval(() => {{
            if (timerRemaining > 0) {{
                timerRemaining--;
                updateTimerDisplay();
            }}
        }}, 1000);
    }}

    function updateTimerDisplay() {{
        const card = document.getElementById("timerCard");
        const statusEl = document.getElementById("timerStatus");
        const countdownEl = document.getElementById("timerCountdown");
        const progressBar = document.getElementById("progressBar");

        if ((mode !== 1 && mode !== 3) || timerState === null) {{
            card.style.display = "none";
            return;
        }}

        card.style.display = "block";

        const minutes = Math.floor(timerRemaining / 60);
        const seconds = timerRemaining % 60;

        const mm = String(minutes).padStart(2, '0');
        const ss = String(seconds).padStart(2, '0');

        countdownEl.innerHTML = mm + ":" + ss;

        let totalDuration = 0;

        if (timerState === "ON") {{
            statusEl.innerHTML = "Kipas akan <b>MATI</b> dalam:";
            totalDuration = {gl.waktu_hidup};
            progressBar.style.background = "#ff4d4d";
        }} else {{
            statusEl.innerHTML = "Kipas akan <b>HIDUP</b> dalam:";
            totalDuration = {gl.waktu_mati} * 60;
            progressBar.style.background = "#25D366";
        }}

        const percent = totalDuration > 0
            ? ((totalDuration - timerRemaining) / totalDuration) * 100
            : 0;

        progressBar.style.width = percent + "%";
    }}

    function downloadDB() {{
        window.location.href = "/api/download-db";
    }}

      updateStatusBadge();
      updateKipasDisplay();
      connectWebSocket();
      connectPompaSendang();
      connectKebunBelakang();
      connectPupuk();

    function getChecklistString(containerId) {{
          const checkboxes = document.querySelectorAll(`#${{containerId}} input[type="checkbox"]`);
          let str = '';
          for (let i = 0; i < 5; i++) {{
            const cb = [...checkboxes].find(c => c.value === i.toString());
            str += cb && cb.checked ? '1' : '0';
          }}
          return str;
        }}

        function onModeChange(select, index) {{
          const container = document.getElementById(`input${{index}}`);
          const modeInputs = {{
            'S': `<label>Jika Suhu Lebih dari:</label><input type="number" id="suhuMin${{index}}" step="0.1" min="25" max="37"><label>Kipas yang hidup:</label><div class="checkbox-group" id="kipasS${{index}}">{"".join([f'<label><input type="checkbox" value="{i}"> K{i+1}</label>' for i in range(5)])}</div>`,
            'T': `<label>Suhu Batas:</label><input type="number" id="tA${{index}}" step="0.1" min="25" max="37"><label>Jumlah Kipas:</label><input type="number" id="tB${{index}}" min="1" max="3"><label>Suhu Mapping Min:</label><input type="number" id="tC${{index}}" step="0.1" min="25" max="37"><label>Suhu Mapping Max:</label><input type="number" id="tD${{index}}" step="0.1" min="25" max="37"><label>Waktu Hidup Min (detik):</label><input type="number" id="tE${{index}}" min="1" max="300"><label>Waktu Hidup Max (detik):</label><input type="number" id="tF${{index}}" min="1" max="300"><label>Waktu Mati Min (menit):</label><input type="number" id="tG${{index}}" min="1" max="120"><label>Waktu Mati Max (menit):</label><input type="number" id="tH${{index}}" min="1" max="120">`,
            'N': ''
          }};
          container.innerHTML = modeInputs[select.value] || '';
        }}

        function getVal(id, defVal = 0) {{
            const el = document.getElementById(id);
            return el ? (el.value || defVal) : defVal;
        }}

        function getChecklistSafe(id) {{
            try {{
                return getChecklistString(id) || "00000";
            }} catch (e) {{
                return "00000";
            }}
        }}

        (function() {{
            const TEMP_MIN  = 25;
            const TEMP_MAX  = 37;
            const TRACK_H   = 450;
            const PAD       = 10;
            const RANGE_PX  = TRACK_H - PAD * 2;

            let rules   = {rules_json};
            let _nextId = 100;
            rules.forEach(r => {{ if (!r.id) r.id = _nextId++; }});

            let activeRuleId = null;
            let _dragId      = null;
            let _dragStartY  = 0;
            let _dragStartT  = 0;
            let _hasDragged  = false;

            // ── helpers ──────────────────────────────────────────────────────

            function tempToY(t) {{
                t = Math.max(TEMP_MIN, Math.min(TEMP_MAX, t));
                return PAD + (1 - (t - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)) * RANGE_PX;
            }}

            function getRuleTemp(r) {{
                return r.mode === 'T' ? (r.suhu_batas || 30) : (r.suhu || 30);
            }}

            function setRuleTemp(r, t) {{
                t = Math.round(Math.max(TEMP_MIN, Math.min(TEMP_MAX, t)) * 10) / 10;
                if (r.mode === 'T') r.suhu_batas = t;
                else r.suhu = t;
            }}

            function getFanDots(r) {{
                if (r.mode === 'S') {{
                return (r.kipas || [0,0,0,0,0]).map(v => !!v);
                }}
                if (r.mode === 'T') {{
                const n = r.jumlah_kipas || 1;
                return Array.from({{length: 5}}, (_, i) => i < n);
                }}
                return Array(5).fill(false);
            }}

            // ── render ───────────────────────────────────────────────────────

            function renderSlider() {{
                renderScale();
                renderHandles();
                renderInfo();
                renderSuhuAcuan();
            }}

            function renderSuhuAcuan() {{
                // hapus indikator lama
                const old = document.getElementById('suhuAcuanMarker');
                if (old) old.remove();

                const suhu = {suhu_acuan};
                const y = tempToY(suhu);

                // ── lingkaran di track ──
                const marker = document.createElement('div');
                marker.id = 'suhuAcuanMarker';
                marker.style.cssText = `
                    position: absolute;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    top: ${{y}}px;
                    width: 20px;
                    height: 20px;
                    background: #e00;
                    border: 2px solid #900;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 100;
                    pointer-events: none;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                `;
                marker.innerHTML = `<span style="color:white;font-size:7px;font-weight:bold;pointer-events:none;">${{suhu.toFixed(1)}}</span>`;
                document.getElementById('trackCol').appendChild(marker);

                // ── label di info col ──
                const label = document.createElement('div');
                label.style.cssText = `
                    position: absolute;
                    top: ${{y}}px;
                    left: 6px;
                    transform: translateY(-50%);
                    font-size: 10px;
                    color: #e00;
                    font-weight: bold;
                    pointer-events: none;
                    white-space: nowrap;
                    z-index: 1000;
                `;
                label.textContent = `▶ Suhu Saat Ini: ${{suhu.toFixed(1)}}°C`;
                document.getElementById('infoCol').appendChild(label);
            }}

            function renderScale() {{
                const el = document.getElementById('tempScale');
                el.innerHTML = '';
                for (let t = TEMP_MIN; t <= TEMP_MAX; t++) {{
                const y = tempToY(t);
                const isMajor = t % 5 === 0;
                const lbl = document.createElement('div');
                lbl.className = 'temp-lbl' + (isMajor ? ' major' : '');
                lbl.style.top = y + 'px';
                lbl.textContent = t + '°';
                el.appendChild(lbl);
                if (isMajor) {{
                    const tick = document.createElement('div');
                    tick.className = 'tick-mark major';
                    tick.style.cssText = `top:${{y}}px;width:5px;`;
                    el.appendChild(tick);
                }}
                }}
            }}

            // ── drag ─────────────────────────────────────────────────────────

            const DRAG_THRESHOLD = 6;  // px, cukup toleran untuk jari

            function startDrag(rid, clientY) {{
                _dragId     = rid;
                const r     = rules.find(x => x.id === rid);
                if (!r) return;
                _dragStartY = clientY;
                _dragStartT = getRuleTemp(r);
                _hasDragged = false;
            }}

            function applyDrag(clientY) {{
                const dy = clientY - _dragStartY;
                if (Math.abs(dy) > DRAG_THRESHOLD) _hasDragged = true;
                const dT = -(dy / RANGE_PX) * (TEMP_MAX - TEMP_MIN);
                const r = rules.find(x => x.id === _dragId);
                if (r) {{
                setRuleTemp(r, _dragStartT + dT);
                renderHandles();
                renderInfo();
                }}
            }}

            function endDrag() {{
                document.querySelectorAll('.sl-handle').forEach(el => {{
                el.classList.remove('dragging');
                el.releasePointerCapture && el._pointerId && el.releasePointerCapture(el._pointerId);
                }});
                if (!_hasDragged && _dragId !== null) openPopup(_dragId);
                _dragId = null;
            }}

            function onPointerDown(e) {{
                e.preventDefault();
                const rid = parseInt(e.currentTarget.dataset.rid);
                e.currentTarget.classList.add('dragging');
                e.currentTarget.setPointerCapture(e.pointerId);  // ← kunci drag ke elemen ini
                e.currentTarget._pointerId = e.pointerId;
                startDrag(rid, e.clientY);
            }}

            function onPointerMove(e) {{
                if (_dragId !== null) applyDrag(e.clientY);
            }}

            function onPointerUp(e) {{
                endDrag();
            }}

            function renderHandles() {{
                const col = document.getElementById('trackCol');
                col.querySelectorAll('.sl-handle').forEach(el => el.remove());
                rules.forEach(r => {{
                const y = tempToY(getRuleTemp(r));
                const h = document.createElement('div');
                h.className   = 'sl-handle';
                h.style.top   = y + 'px';
                h.dataset.rid = r.id;
                h.innerHTML   = `<span class="sl-handle-text">${{r.mode === 'T' ? 'TIMER' : 'SUHU'}}</span>`;

                // ← ganti semua mouse/touch event dengan pointer event
                h.addEventListener('pointerdown', onPointerDown);
                h.addEventListener('pointermove', onPointerMove);
                h.addEventListener('pointerup',   onPointerUp);
                h.addEventListener('pointercancel', onPointerUp);

                col.appendChild(h);
                }});
            }}

            function renderInfo() {{
                const col = document.getElementById('infoCol');
                col.innerHTML = '';
                rules.forEach(r => {{
                const y = tempToY(getRuleTemp(r));
                const info = document.createElement('div');
                info.className = 'handle-info';
                info.style.top = y + 'px';

                const tempTag = document.createElement('div');
                tempTag.className = 'temp-tag';
                tempTag.textContent = getRuleTemp(r).toFixed(1) + '°C';

                const badge = document.createElement('span');
                badge.className = `mode-badge badge-${{r.mode}}`;
                badge.textContent = r.mode;

                const fanBox = document.createElement('div');
                fanBox.className = 'fan-box';
                getFanDots(r).forEach(on => {{
                    const dot = document.createElement('div');
                    dot.className = 'fan-dot' + (on ? ' on' : '');
                    fanBox.appendChild(dot);
                }});

                info.appendChild(tempTag);
                info.appendChild(badge);
                info.appendChild(fanBox);
                col.appendChild(info);
                }});
            }}

            function openPopup(id) {{
                activeRuleId = id;
                const r = rules.find(x => x.id === id);
                if (!r) return;

                document.getElementById('popupMode').value = r.mode;
                document.getElementById('popupSuhu').value =
                r.mode === 'T' ? (r.suhu_batas ?? 30) : (r.suhu ?? 30);

                if (r.mode === 'S') {{
                document.querySelectorAll('.popup-fan-cb').forEach((cb, i) => {{
                    cb.checked = !!(r.kipas && r.kipas[i]);
                }});
                }} else {{
                document.getElementById('popupMapMin').value  = r.map_min  ?? 25;
                document.getElementById('popupMapMax').value  = r.map_max  ?? 35;
                document.getElementById('popupJumlah').value  = r.jumlah_kipas ?? 1;
                document.getElementById('popupOnMin').value   = r.on_min   ?? 10;
                document.getElementById('popupOnMax').value   = r.on_max   ?? 60;
                document.getElementById('popupOffMin').value  = r.off_min  ?? 5;
                document.getElementById('popupOffMax').value  = r.off_max  ?? 30;
                }}

                onPopupModeChange();
                document.getElementById('popupOverlay').style.display = 'block';
                document.getElementById('rulePopup').style.display    = 'block';
            }}

            window.onPopupModeChange = function() {{
                const m = document.getElementById('popupMode').value;
                document.getElementById('ppModeS').style.display = m === 'S' ? '' : 'none';
                document.getElementById('ppModeT').style.display = m === 'T' ? '' : 'none';
            }};

            window.savePopup = function() {{
                const mode = document.getElementById('popupMode').value;
                const suhu = parseFloat(document.getElementById('popupSuhu').value) || 30;
                const r = rules.find(x => x.id === activeRuleId);
                if (!r) return;

                r.mode = mode;
                if (mode === 'S') {{
                r.suhu  = suhu;
                r.kipas = Array.from(document.querySelectorAll('.popup-fan-cb')).map(cb => cb.checked ? 1 : 0);
                delete r.suhu_batas;
                }} else {{
                r.suhu_batas    = suhu;
                r.map_min       = parseFloat(document.getElementById('popupMapMin').value)  || 25;
                r.map_max       = parseFloat(document.getElementById('popupMapMax').value)  || 35;
                r.jumlah_kipas  = parseInt(document.getElementById('popupJumlah').value)    || 1;
                r.on_min        = parseInt(document.getElementById('popupOnMin').value)      || 10;
                r.on_max        = parseInt(document.getElementById('popupOnMax').value)      || 60;
                r.off_min       = parseInt(document.getElementById('popupOffMin').value)     || 5;
                r.off_max       = parseInt(document.getElementById('popupOffMax').value)     || 30;
                delete r.suhu; delete r.kipas;
                }}
                closePopup();
                renderSlider();
            }};

            window.deleteRule = function() {{
                rules = rules.filter(r => r.id !== activeRuleId);
                closePopup();
                renderSlider();
            }};

            window.closePopup = function() {{
                document.getElementById('popupOverlay').style.display = 'none';
                document.getElementById('rulePopup').style.display    = 'none';
                activeRuleId = null;
            }};

            window.addNewRule = function() {{
                if (rules.length >= 5) {{
                alert('Maksimal 5 aturan.');
                return;
                }}
                const nr = {{ id: _nextId++, mode: 'S', suhu: 32, kipas: [1,0,0,0,0] }};
                rules.push(nr);
                renderSlider();
                openPopup(nr.id);
            }};


            window.generateSemua = function() {{
                const usia       = {gl.usia_ui};
                const kipasWajib = (typeof getChecklistSafe === 'function')
                ? getChecklistSafe('wajibGroup') : '00000';

                // ── urutkan: T suhu terkecil dulu, lalu S dari kecil ke besar ──
                const sorted = [...rules].sort((a, b) => {{
                const tA = a.mode === 'T' ? (a.suhu_batas || 0) : (a.suhu || 0);
                const tB = b.mode === 'T' ? (b.suhu_batas || 0) : (b.suhu || 0);
                if (a.mode === b.mode) return tA - tB;        // sama mode → sort suhu
                if (a.mode === 'T') return -1;                // T selalu duluan
                return 1;
                }});

                const out = [usia, kipasWajib];
                for (let i = 0; i < 5; i++) {{
                const r = sorted[i];
                if (!r || r.mode === 'N') {{
                    out.push('N');
                }} else if (r.mode === 'S') {{
                    const suhu  = Math.round((r.suhu || 0) * 10);
                    const kipas = (r.kipas || [0,0,0,0,0]).map(v => v ? '1' : '0').join('');
                    out.push(`S-${{suhu}}-${{kipas}}`);
                }} else if (r.mode === 'T') {{
                    const vals = [
                    Math.round((r.suhu_batas   || 0) * 10),
                    Math.round( r.jumlah_kipas || 1),
                    Math.round((r.map_min      || 0) * 10),
                    Math.round((r.map_max      || 0) * 10),
                    Math.round( r.on_min       || 0),
                    Math.round( r.on_max       || 0),
                    Math.round( r.off_min      || 0),
                    Math.round( r.off_max      || 0),
                    ];
                    out.push(`T-${{vals.join('-')}}`);
                }}
                }}

                const outEl = document.getElementById('outputSemua');
                if (outEl) outEl.textContent = out.map(s => `"${{s}}"`).join(', ');
                fetch(`/api/atur_auto?tulis=${{encodeURIComponent(out.join(','))}}`)
                .catch(e => console.error('Error:', e));
            }};

            if (document.readyState === 'loading')
                document.addEventListener('DOMContentLoaded', renderSlider);
            else
                renderSlider();

            }})();
    </script>
    {SWIPE_NAV_HTML}
    </body></html>
    """
    return html

@api_router.get("/slider_kipas_auto", response_class=HTMLResponse)
async def slider_kipas_auto(request: Request):
    usia_raw = request.query_params.get("usia")
    if usia_raw is not None and usia_raw.isdigit():
        gl.usia_ui = int(usia_raw)
    
    row = ds.baca_baris_auto(gl.usia_ui)
    if row is None or len(row) != 6:
        row = DEFAULT_ROW
    
    konf = parse_konfigurasi_auto(gl.usia_ui, row)
    kipas_wajib = konf["kipas_wajib"]["array"]
    kipas_options = "".join([
        f"<label><input type='checkbox' value='{i}' {'checked' if kipas_wajib[i] else ''}> Kipas {i+1}</label>"
        for i in range(5)
    ])
    pengaturan_html = render_pengaturan_html(konf)
    
    return f"""
        <label>Pilih kipas yang wajib hidup:</label>
        <div class="checkbox-group" id="wajibGroup">{kipas_options}</div>
        <h2>Pengaturan Mode</h2>
        <div id="pengaturanContainer">
            {pengaturan_html}
        </div>
    """

clients = set()
state_lock = asyncio.Lock()
state_version = 0

def get_tanaman_state_dict():
    """Mengembalikan dict {relay_id: state} untuk semua relay tanaman.
    Scalable: otomatis mengikuti isi RELAY_TANAMAN."""
    return {r["id"]: getattr(gl, r["id"], 0) for r in RELAY_TANAMAN}

async def update_and_broadcast():
    global state_version
    remaining = 0
    timer_state = None

    if gl.mode_kandang in [1,3]:
        now = time.monotonic()

        if gl.status_on_timer:
            remaining = gl.waktu_hidup - (now - gl.waktuTerakhir)
            timer_state = "ON"
        else:
            remaining = (gl.waktu_mati * 60) - (now - gl.waktuTerakhir)
            timer_state = "OFF"

        if remaining < 0:
            remaining = 0

    async with state_lock:
        state_version += 1

        snapshot = {
            "type": "state_update",
            "kipas": gl.kipas.copy(),
            "mode": gl.mode_kandang,
            "usia": gl.usia_ayam,
            "version": state_version,
            "timer_remaining": int(remaining),
            "timer_state": timer_state,
            "channel": gl.kipas_channel_aktif,
            **get_tanaman_state_dict()
        }
        print("-1-")

    print("Broadcasting state update, version:", state_version)
    await broadcast(snapshot)


async def broadcast(message: dict):
    dead_clients = []

    for c in clients.copy():  # copy supaya aman kalau berubah
        try:
            await c.send_json(message)
        except:
            dead_clients.append(c)

    for dc in dead_clients:
        clients.discard(dc)

@api_router.websocket("/ws/kipas")
async def websocket_kipas(ws: WebSocket):
    global state_version
    remaining = 0
    timer_state = None

    if gl.mode_kandang in [1,3]:
        now = time.monotonic()

        if gl.status_on_timer:
            remaining = gl.waktu_hidup - (now - gl.waktuTerakhir)
            timer_state = "ON"
        else:
            remaining = (gl.waktu_mati * 60) - (now - gl.waktuTerakhir)
            timer_state = "OFF"

        if remaining < 0:
            remaining = 0

    await ws.accept()
    clients.add(ws)

    try:
        # === KIRIM SNAPSHOT AWAL ===
        async with state_lock:
            initial_state = gl.kipas.copy()
            mode = gl.mode_kandang
            usia = gl.usia_ayam
            version = state_version

        await ws.send_json({
            "type": "init",
            "kipas": initial_state,
            "mode": mode,
            "usia": usia,
            "version": version,
            "timer_remaining": int(remaining),
            "timer_state": timer_state,
            "jumlah_kipas_timer": gl.jumlah_kipas_timer,
            "waktu_hidup": gl.waktu_hidup,
            "waktu_mati": gl.waktu_mati,
            **get_tanaman_state_dict()
        })

        # === LOOP TERIMA PESAN ===
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)

            if data["type"] == "set_kipas":

                client_version = int(data.get("version", -1))

                async with state_lock:

                    # 🔴 Kalau versi client sudah lama → paksa resync
                    if client_version != state_version:
                        await ws.send_json({
                            "type": "resync",
                            "kipas": gl.kipas.copy(),
                            "mode": gl.mode_kandang,
                            "usia": gl.usia_ayam,
                            "version": state_version,
                            "timer_remaining": int(remaining),
                            "timer_state": timer_state,
                            "jumlah_kipas_timer": gl.jumlah_kipas_timer,
                            "waktu_hidup": gl.waktu_hidup,
                            "waktu_mati": gl.waktu_mati,
                            **get_tanaman_state_dict()
                        })
                        continue

                    # ✅ Update aman
                    i = int(data["index"])
                    value = int(data["value"])

                    current = gl.kipas.copy()
                    current[i] = value
                    await saklar_kipas(*current)

                    state_version += 1

                    current_state = gl.kipas.copy()
                    mode = gl.mode_kandang
                    usia = gl.usia_ayam
                    version = state_version
                
            elif data["type"] == "set_setting":
                print("Received setting update:", data)

                client_version = int(data.get("version", -1))

                async with state_lock:

                    # 🔴 Kalau versi client beda → paksa resync
                    if client_version != state_version:
                        await ws.send_json({
                            "type": "resync",
                            "kipas": gl.kipas.copy(),
                            "mode": gl.mode_kandang,
                            "usia": gl.usia_ayam,
                            "version": state_version,
                            "timer_remaining": int(remaining),
                            "timer_state": timer_state,
                            "jumlah_kipas_timer": gl.jumlah_kipas_timer,
                            "waktu_hidup": gl.waktu_hidup,
                            "waktu_mati": gl.waktu_mati,
                            **get_tanaman_state_dict()
                        })
                        continue

                    param = data.get("param")
                    value = data.get("value")

                    # === UPDATE STATE ===
                    if param == "usia":
                        atur_usia(int(value))
                        gl.usia_ayam = int(value)
                        print("Usia ayam diubah menjadi:", gl.usia_ayam)

                    elif param == "mode":
                        gl.mode_kandang = int(value)
                        print("Mode kandang diubah menjadi:", gl.mode_kandang)

                    elif param == "jumlah_kipas_timer":
                        gl.jumlah_kipas_timer = int(value)
                        print("Jumlah kipas timer diubah menjadi:", gl.jumlah_kipas_timer)
                        
                    elif param == "waktu_hidup":
                        gl.waktu_hidup = int(value)
                        print("Waktu hidup timer diubah menjadi:", gl.waktu_hidup)

                    elif param == "waktu_mati":
                        gl.waktu_mati = int(value)
                        print("Waktu mati timer diubah menjadi:", gl.waktu_mati)    

                    elif param == "jumlah_ayam_awal":
                        gl.jumlah_ayam_awal = int(value)
                        print("Jumlah ayam awal diubah menjadi:", gl.jumlah_ayam_awal)

                    elif param == "jumlah_ayam_mati":
                        gl.jumlah_ayam_mati = int(value)
                        print("Jumlah ayam mati diubah menjadi:", gl.jumlah_ayam_mati)

                    elif param == "jumlah_pakan_sak":
                        gl.jumlah_pakan_sak = int(value)
                        print("Jumlah pakan sak diubah menjadi:", gl.jumlah_pakan_sak)

                    elif param == "bobot_rata_rata":
                        gl.bobot_rata_rata = int(value)
                        print("Bobot rata-rata diubah menjadi:", gl.bobot_rata_rata)

                    elif param == "harga_kontrak_ayam":
                        gl.harga_kontrak_ayam = int(value)
                        print("Harga kontrak ayam diubah menjadi:", gl.harga_kontrak_ayam)

                    elif param == "harga_bibit_ayam":
                        gl.harga_bibit_ayam = int(value)
                        print("Harga bibit ayam diubah menjadi:", gl.harga_bibit_ayam)

                    elif param == "harga_obat_ayam":
                        gl.harga_obat_ayam = int(value)
                        print("Harga obat ayam diubah menjadi:", gl.harga_obat_ayam)

                    elif param == "harga_pakan_kg":
                        gl.harga_pakan_kg = int(value)
                        print("Harga pakan/kg diubah menjadi:", gl.harga_pakan_kg)

                    elif param == "jumlah_ayam_dipanen":
                        gl.jumlah_ayam_dipanen = int(value)
                        print("Jumlah ayam dipanen diubah menjadi:", gl.jumlah_ayam_dipanen)

                    elif param in RELAY_TANAMAN_IDS:
                        # === HANDLER GENERIK UNTUK SEMUA RELAY TANAMAN (scalable) ===
                        # Optimistic update: gl.{param} langsung di-set di sini,
                        # broadcast pertama (di luar lock, di bawah) langsung mengirim
                        # state baru ini. Konfirmasi ke ESP32 jalan di background;
                        # kalau gagal total setelah retry, terapkan_relay_optimistic
                        # akan mengoreksi balik dan mengirim broadcast susulan.
                        relay_cfg = get_relay_config(param)
                        val = int(value)
                        setattr(gl, param, val)
                        print(f"{param} diubah menjadi:", val)
                        if relay_cfg:
                            asyncio.create_task(
                                terapkan_relay_optimistic(param, relay_cfg["ip"], val)
                            )

                    # ⬆⬆⬆ Tambahkan param lain kalau perlu

                    ds.simpan_data_sqlite()
                    state_version += 1

                    current_state = gl.kipas.copy()
                    mode = gl.mode_kandang
                    usia = gl.usia_ayam
                    version = state_version

                # === BROADCAST DI LUAR LOCK ===
                await broadcast({
                    "type": "state_update",
                    "kipas": current_state,
                    "mode": mode,
                    "usia": usia,
                    "version": version,
                    "timer_remaining": int(remaining),
                    "timer_state": timer_state,
                    "jumlah_kipas_timer": gl.jumlah_kipas_timer,
                    "waktu_hidup": gl.waktu_hidup,
                    "waktu_mati": gl.waktu_mati,
                    **get_tanaman_state_dict()
                })
                print("-2-")


    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        print("WS error:", e)

    finally:
        clients.discard(ws)

@api_router.post("/timbangan")
async def terima_timbangan(data: dict):
    ds.simpan_timbangan(data)
    ds.hitung_statistik_bobot()
    return {"status": "ok"}

@api_router.get("/testpost")
def testpost():
    return HTMLResponse("""
    <h2>Test Kirim Data Timbangan</h2>
    <button onclick="kirim()">Kirim Sample</button>

    <script>
    function kirim(){
        fetch("/api/timbangan",{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                device_id:1,
                timestamp:Math.floor(Date.now()/1000),
                weight:1234
            })
        })
        .then(r=>r.json())
        .then(d=>alert(JSON.stringify(d)))
    }
    </script>
    """)

@api_router.get("/download-db")
def download_db():
    return ds.download_db(DB_PATH)

DEFAULT_ROW = [
    "00000",
    "N",
    "N",
    "N",
    "N",
    "N",
]

@api_router.get("/set_kps_auto", response_class=HTMLResponse)
async def halaman_pengatur_kipas_auto(request: Request):
    
    html = f"""<!DOCTYPE html>
    <html lang="id">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Pengatur Kipas Raspberry PI</title>
      <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f0f0f0; }}
        
      </style>
    </head>
    <body>
      
      <script>
        
      </script>
    </body>
    </html>
    """
    return html
# ==========================================================
#  ENDPOINT LAINNYA (disingkat tapi lengkap)
# ==========================================================

# ==========================================================
#  FUNGSI RELAY TANAMAN (generik, scalable berdasar IP)
#  Satu fungsi ini menggantikan set_relay_air/set_relay_air_2/dst.
#  Menambah relay baru tidak perlu menambah fungsi baru.
# ==========================================================
async def set_relay_by_ip(ip: str, state: str):
    """Kirim 1x permintaan ke ESP32. Return (sukses: bool, alasan: str)."""
    url = f"http://{ip}/relay?state={state}"

    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(url)
        except httpx.TimeoutException:
            print(f"[{ip}] Timeout — request mungkin sampai, balasan tidak diterima")
            return False, "timeout"
        except httpx.ConnectError:
            print(f"[{ip}] Connection refused — ESP32 kemungkinan mati/tidak terjangkau")
            return False, "unreachable"
        except Exception as e:
            print(f"[{ip}] Error tak terduga:", e)
            return False, "error"

        try:
            data = r.json()
        except Exception:
            print(f"[{ip}] Balasan bukan JSON valid:", r.text[:200])
            return False, "bad_response"

        if data.get("status") != "ok":
            print(f"[{ip}] ESP melaporkan error:", data)
            return False, "esp_error"

        relay_state = data.get("relay")

        # Cukup percaya status:ok dari ESP — relay sudah dieksekusi
        # Verifikasi relay_state dihapus karena timing race antara digitalWrite
        # dan WiFiClient outgoing di ESP8266 bisa membuat response terlambat
        print(f"[{ip}] Relay {state.upper()} confirmed (status ok)")
        return True, "confirmed"


async def set_relay_safe_by_ip(ip: str, state: str, retry=3):
    """Retry set_relay_by_ip hingga `retry` kali. Return (sukses: bool, alasan: str)."""
    last_reason = "unknown"
    for i in range(retry):
        success, reason = await set_relay_by_ip(ip, state)
        if success:
            return True, reason
        last_reason = reason
        print(f"[{ip}] Retry {i+1}/{retry} (alasan: {reason})...")
        await asyncio.sleep(0.3)  # jeda kecil antar retry, hindari spam
    return False, last_reason


async def terapkan_relay_optimistic(param: str, ip: str, val: int):
    """
    Dipanggil SETELAH gl.{param} sudah di-set duluan (optimistic) dan
    broadcast pertama sudah terkirim. Fungsi ini menjalankan HTTP ke ESP32
    di background. Kalau gagal setelah retry, state gl dikoreksi balik
    ke nilai sebelumnya dan broadcast susulan dikirim untuk mengoreksi UI.

    Catatan: kalau ESP32 sukses menerima permintaan ini DAN sukses
    melapor balik lewat /relay_report, state akan tetap konsisten lewat
    jalur itu juga — kedua mekanisme saling melengkapi, tidak konflik.
    """
    state = "on" if val else "off"
    success, reason = await set_relay_safe_by_ip(ip, state)

    if success:
        print(f"[{param}] Dikonfirmasi ESP32: {state}")
        return  # tidak perlu broadcast lagi, state sudah benar dari awal

    # === GAGAL: koreksi balik state ke nilai sebelumnya ===
    nilai_revert = 0 if val else 1
    setattr(gl, param, nilai_revert)
    print(f"[{param}] GAGAL set ke {state} (alasan: {reason}). State dikoreksi balik ke {nilai_revert}.")

    ds.simpan_data_sqlite()

    global state_version
    async with state_lock:
        state_version += 1
        snapshot = {
            "type": "state_update",
            "kipas": gl.kipas.copy(),
            "mode": gl.mode_kandang,
            "usia": gl.usia_ayam,
            "version": state_version,
            "relay_error": {"param": param, "reason": reason},
            **get_tanaman_state_dict()
        }

    await broadcast(snapshot)


def get_relay_config(relay_id: str):
    return next((r for r in RELAY_TANAMAN if r["id"] == relay_id), None)

RELAY_TANAMAN_IDS = [r["id"] for r in RELAY_TANAMAN]


@api_router.get("/relay_report")
async def relay_report(id: str, state: str, source: str = "unknown"):
    """
    Dipanggil oleh ESP32 (push) setiap kali set_relay() dijalankan di firmware,
    baik dari manual, jadwal, maupun proteksi. Ini sumber kebenaran untuk
    sinkronisasi state relay ke semua client WebSocket — termasuk perubahan
    yang terjadi TANPA request dari Python (jadwal/proteksi otomatis).

    PENTING: body respons HARUS mengandung literal `"status":"ok"` karena
    firmware ESP32 mengecek string ini secara sederhana (bukan parsing JSON
    penuh) untuk menentukan sukses/gagal dan memicu retry/resync.
    """
    if id not in RELAY_TANAMAN_IDS:
        print(f"[RELAY_REPORT] id tidak dikenal: {id}")
        return JSONResponse({"error": "id tidak dikenal"}, status_code=400)

    val = 1 if state == "on" else 0
    current = getattr(gl, id, None)

    setattr(gl, id, val)
    print(f"[RELAY_REPORT] {id} dilaporkan = {val} (sumber: {source})")

    if current != val:
        # Hanya broadcast kalau memang ada perubahan, hindari spam tak perlu
        ds.simpan_data_sqlite()

        global state_version
        async with state_lock:
            state_version += 1
            snapshot = {
                "type": "state_update",
                "kipas": gl.kipas.copy(),
                "mode": gl.mode_kandang,
                "usia": gl.usia_ayam,
                "version": state_version,
                **get_tanaman_state_dict()
            }

        await broadcast(snapshot)

    return {"status": "ok", "id": id, "value": val}


@api_router.get("/esp-tester", response_class=HTMLResponse)
async def esp_tester():
    with open("esp_tester.html", "r") as f:
        return f.read()
    
@api_router.get("/bbt")
async def waktu_json():
    #gl.jumlah_http += 1
    tanggal_waktu_usia()
    data = {
        "dta": [1565, random.randint(1, 9), gl.internetConnected],
        "bbt": [
            gl.bobot_timbang, gl.bobot_rata_rata_timbang, gl.jumlah_sample_timbang,
            gl.jumlah_sample_timbang_kemarin, gl.standar_bobot, gl.standar_deviasi_bobot, gl.persentase_standar_deviasi
        ],
    }
    return json_response(data)

@api_router.get("/bbt_raw")
async def waktu_json():
    #gl.jumlah_http += 1
    tanggal_waktu_usia()
    data = {
        "dta": [1566, random.randint(1, 9), gl.internetConnected],
        "bbt": gl.list_bobot_timbang
    }
    return json_response(data)

@api_router.get("/waktu")
def get_waktu():
    now = datetime.now(TIMEZONE)
    return {
        "epoch" : int(time.time()),   # selalu UTC, dipakai setTime() di ESP
        "jam"   : now.hour,
        "menit" : now.minute,
        "detik" : now.second,
        "hari"  : now.day,
        "bulan" : now.month,
        "tahun" : now.year,
        "teks"  : now.strftime("%Y-%m-%d %H:%M:%S"),
    }

@api_router.get("/wkt")
async def waktu_json():
    #gl.jumlah_http += 1
    tanggal_waktu_usia()
    data = {
        "dta": [1561, random.randint(1, 9), gl.internetConnected],
        "wkt": [
            gl.usia_ayam, gl.data_waktu, gl.epoch_data_waktu,
            gl.jam, gl.menit, gl.detik, gl.hari, gl.bulan, gl.tahun,
            gl.tanggal_masuk_ayam_hari, gl.tanggal_masuk_ayam_bulan,
            gl.tanggal_masuk_ayam_tahun
        ],
    }
    return json_response(data)

@api_router.get("/dataweb")
async def dataweb_json():
    thg.pengolah_json()
    return json_response(gl.json_thingspeak)

import sqlite3



@api_router.get("/kps")
async def kipas_json():
    #gl.jumlah_http += 1
    data = {
        "dta": [1562, random.randint(1, 9)],
        "kps": gl.kipas,
        "kpi": gl.kipas,
        #"kpi": gl.kipas_inspeksi,
        "kcs": gl.kipas_saklar,
        "mtd": gl.flag_alarm_siaga
   }
    return json_response(data)

@api_router.get("/shu")
async def suhu_json():
    #gl.jumlah_http += 1
    data = {
        "dta": [1563, random.randint(1, 9)],
        "shu": [pd._to_int_no_decimal(gl.suhu_atas),
                pd._to_int_no_decimal(gl.suhu_bawah),
                pd._to_int_no_decimal(gl.suhu_luar),
                pd._to_int_no_decimal(gl.suhu_acuan)],
        "klb": [pd._to_int_no_decimal(gl.kelembapan_atas),
                pd._to_int_no_decimal(gl.kelembapan_bawah),
                pd._to_int_no_decimal(gl.kelembapan_luar)],
        "dhi": [pd._to_int_no_decimal(gl.data_HI_atas),
                pd._to_int_no_decimal(gl.data_HI_bawah),
                pd._to_int_no_decimal(gl.data_HI_luar)]
   }
    return json_response(data)

@api_router.get("/mtd")
async def metadata_json():
    #gl.jumlah_http += 1
    data = {
        "dta": [1564, random.randint(1, 9)],
        "mtd": [gl.harga_pakan_kg,
                gl.jumlah_ayam_awal,
                gl.harga_obat_ayam,
                gl.jumlah_ayam_mati,
                gl.harga_bibit_ayam,
                gl.jumlah_pakan_sak,
                gl.harga_kontrak_ayam,
                gl.bobot_rata_rata_timbang,
                gl.blok_kandang,
                gl.jumlah_ayam_dipanen
                ]
   }
    return json_response(data)

@api_router.get("/kipas_control")
async def kipas_web_json(nomor: int = Query(..., ge=0, le=4)):
    gl.jumlah_http += 1
    if gl.mode_kandang == 1:
        return JSONResponse(content={"error": "Mode auto, tidak bisa manual"}, status_code=403)
    kipas_state = gl.kipas
    kipas_state[nomor] = 0 if kipas_state[nomor] else 1
    await saklar_kipas(*kipas_state)
    print(f"Kipas {nomor+1} diubah ke {int(kipas_state[nomor])}")
    return {"status": f"Kipas {nomor+1} diubah ke {int(kipas_state[nomor])}"}


@api_router.get("/mode")
async def ubah_mode(val: int):
    gl.mode_kandang = val
    ds.simpan_data_sqlite()
    return {"ok": True}

@api_router.get("/jumlah_kipas")
async def ubah_jumlah_kipas_timer(val: int):
    gl.jumlah_kipas_timer = val
    ds.simpan_data_sqlite()
    return {"ok": True}

@api_router.get("/waktu_hidup")
async def ubah_waktu_hidup(val: int):
    gl.waktu_hidup = val
    ds.simpan_data_sqlite()
    return {"ok": True}

@api_router.get("/waktu_mati")
async def ubah_waktu_mati(val: int):
    gl.waktu_mati = val
    ds.simpan_data_sqlite()
    return {"ok": True}

@api_router.get("/ubah_setting")
async def ubah_setting(param: str, value: int):
    allowed = {
        "jumlah_kipas_timer": "jumlah_kipas_timer",
        "waktu_hidup": "waktu_hidup",
        "waktu_mati": "waktu_mati",
        "jumlah_ayam_awal" : "jumlah_ayam_awal",
        "jumlah_ayam_mati" : "jumlah_ayam_mati",
        "jumlah_pakan_sak" : "jumlah_pakan_sak",
        "bobot_rata_rata" : "bobot_rata_rata",
        "harga_kontrak_ayam" : "harga_kontrak_ayam",
        "harga_bibit_ayam" : "harga_bibit_ayam",
        "harga_obat_ayam" : "harga_obat_ayam",
        "harga_pakan_kg" : "harga_pakan_kg",
        "jumlah_ayam_dipanen" : "jumlah_ayam_dipanen"
        # Tambahkan variabel lain di sini
    }
    
    if param not in allowed:
        return JSONResponse({"error": "Parameter tidak dikenal"}, status_code=400)

    # Set nilai
    setattr(gl, allowed[param], value)

    ds.simpan_data_sqlite()

    return {"status": "ok", "ubah": param, "nilai_baru": value}

@api_router.get("/ceklist")
async def ceklist(
    prt_lst: int,
    flg_dtbs: int,
    flg_alrml: int
    ):
    # Simpan ke variabel global
    gl.cek_proteksi_listrik = prt_lst
    gl.flag_database_AI = flg_dtbs
    gl.flag_alarm_siaga = flg_alrml
    # Simpan ke file jika ada perubahan
    ds.simpan_data_sqlite()

    return {"ok": True}

@api_router.get("/atur_auto")
def atur_konfigurasi(tulis: str = Query(...)):
    try:
        data = tulis.split(",")

        if len(data) != 7:
            return {"error": "Format data salah"}

        usia_ayam = int(data[0])
        d1, d2, d3, d4, d5, d6 = data[1:]

        ds.edit_baris_konf_auto(
            usia_ayam,
            d1, d2, d3, d4, d5, d6
        )

        return {
            "status": "OK",
            "usia": usia_ayam
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "detail": str(e)
        }
    
@api_router.post("/detect_json")
async def detect(request: Request):
    start_time = time.time()

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    img = decode_jpeg(body)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    result = process_image_to_json(img, VISION_CONFIG)
    process_time_ms = (time.time() - start_time) * 1000

    return {
        "status": "ok",
        "process_time_ms": round(process_time_ms, 2),
        "result": result
    }

@api_router.post("/detect")
async def detect(request: Request):
    start_time = time.time()

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    img = decode_jpeg(body)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    result = process_image_to_json(img, VISION_CONFIG)

    # === OVERLAY ===
    overlay_img = draw_detection_overlay(img, result)

    # encode ke jpeg
    success, jpeg = cv2.imencode(".jpg", overlay_img)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode overlay")

    overlay_base64 = base64.b64encode(jpeg.tobytes()).decode("utf-8")

    process_time_ms = (time.time() - start_time) * 1000

    return {
        "status": "ok",
        "process_time_ms": round(process_time_ms, 2),
        "result": result,
        "overlay_image_base64": overlay_base64
    }
    
@api_router.get("/imagetest", response_class=HTMLResponse)
def test_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chili Vision Test</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 40px auto; }
            button { padding: 8px 16px; margin-top: 10px; }
            pre { background: #f4f4f4; padding: 12px; }
            img { max-width: 100%; margin-top: 10px; }
        </style>
    </head>
    <body>

    <h2>Chili Vision – Test Upload</h2>

    <input type="file" id="imageInput" accept="image/*">
    <br>
    <button id="sendBtn" disabled>Kirim ke Server</button>

    <div id="preview"></div>

    <h3>Hasil JSON</h3>
    <pre id="result">Belum ada hasil</pre>

    <h3>Hasil Overlay</h3>
    <img id="overlayImage" />

    <script>
    const imageInput = document.getElementById("imageInput");
    const sendBtn = document.getElementById("sendBtn");
    const resultBox = document.getElementById("result");
    const preview = document.getElementById("preview");

    let selectedFile = null;

    imageInput.addEventListener("change", () => {
        if (imageInput.files.length > 0) {
            selectedFile = imageInput.files[0];
            sendBtn.disabled = false;

            const img = document.createElement("img");
            img.src = URL.createObjectURL(selectedFile);
            preview.innerHTML = "";
            preview.appendChild(img);
        }
    });

    sendBtn.addEventListener("click", async () => {
        if (!selectedFile) return;

        resultBox.textContent = "Mengirim dan memproses...";

        const response = await fetch("/api/detect", {
            method: "POST",
            headers: {
                "Content-Type": "image/jpeg"
            },
            body: await selectedFile.arrayBuffer()
        });

        const data = await response.json();
        resultBox.textContent = JSON.stringify(data, null, 2);

        if (data.overlay_image_base64) {
            const overlayImg = document.getElementById("overlayImage");
            overlayImg.src = "data:image/jpeg;base64," + data.overlay_image_base64;
        }
    });

    </script>

    </body>
    </html>
    """
    
@api_router.get("/restart")
async def restart():
    #os.system("sudo reboot now")
    return {"msg": "Raspberry Pi akan restart..."}

import websockets  # ikut terpasang bersama uvicorn[standard]

PROXY_DEV = {"pompa": POMPA_SENDANG_IP, "kebun": KEBUN_BELAKANG_IP, "pupuk": PUPUK_IP}

@api_router.websocket("/ws/dev/{nama}")
async def ws_proxy_dev(ws: WebSocket, nama: str):
    ip = PROXY_DEV.get(nama)
    if not ip:
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        async with websockets.connect(f"ws://{ip}/ws", open_timeout=3, ping_interval=None) as up:
            async def ke_esp():
                while True:
                    await up.send(await ws.receive_text())

            async def ke_klien():
                async for msg in up:
                    await ws.send_text(msg if isinstance(msg, str) else msg.decode())

            tugas = [asyncio.create_task(ke_esp()), asyncio.create_task(ke_klien())]
            await asyncio.wait(tugas, return_when=asyncio.FIRST_COMPLETED)
            for t in tugas:
                t.cancel()
    except Exception as e:
        print(f"[proxy {nama}] {e}")
    finally:
        try:
            await ws.close()
        except Exception:
            pass

app.include_router(api_router)

# ==========================================================
#  RUN SERVER
# ==========================================================
def run_server():
    import uvicorn
    uvicorn.run("webserver:app", host="0.0.0.0", port=8080, reload=False)

#if __name__ == "__main__":
#    run_server()

print("Webserver.py dimuat.")