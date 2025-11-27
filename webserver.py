# webserver.py
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime
import asyncio
import random
import json
import os

# === IMPORT MODUL INTERNAL ===
from variabel_global import gl
from fungsi_umum import tanggal_waktu_usia, atur_usia
from kontrol_kipas import saklar_kipas
import penyimpanan_data as pd
#from sensor import baca_suhu, baca_kelembapan, baca_HI

# ==========================================================
#  INIT APP
# ==========================================================
app = FastAPI(title="Kandang Controller", version="1.0")

# ==========================================================
#  UTILITY RESPONSE
# ==========================================================
def json_response(data: dict):
    return JSONResponse(content=data)

# ==========================================================
#  ENDPOINT /
# ==========================================================
@app.get("/")
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
            gl.suhu_acuan,
        ],
    }
    return json_response(data)

# ==========================================================
#  ENDPOINT /set (HALAMAN HTML)
# ==========================================================
@app.get("/set", response_class=HTMLResponse)
async def halaman_pengatur_kipas():
    kipas_html = "".join([
        f"<button class='btn {'on' if k else 'off'}' onclick='toggleKipas({i})'>Kipas {i+1}</button>"
        for i, k in enumerate(gl.kipas)
    ])

    html = f"""
    <!DOCTYPE html><html><head>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Pengatur Kipas</title>
    <style>
      body {{ font-family: Arial; padding: 20px; margin: 0; }}
      label {{ margin:7px; display:inline-block; }}
      .button-container {{ display: flex; width: 100%; padding: 0; margin: 0; }}
      .btn {{ flex: 1; aspect-ratio: 1 / 1; font-size: 16px; border: 1px solid #ccc; margin: 2px; cursor: pointer; transition: background-color 0.3s; }}
      .on {{ background-color: #25D366; color: white; }}
      .off {{ background-color: red; color: white; }}
      .loader {{
        border: 8px solid #f3f3f3;
        border-top: 8px solid #3498db;
        border-radius: 50%;
        width: 40px; height: 40px;
        animation: spin 1s linear infinite;
      }}
      @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
      }}
    </style>
    </head><body>
    <div id='loading' style='display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(255,255,255,0.7);z-index:9999;text-align:center;'>
      <div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'>
        <div class='loader'></div><br>Loading...
      </div>
    </div>

    <h2>Pengatur Kipas</h2>

    <label for='usia'>Usia Ayam : </label>
    <select id='usia'>
    {"".join([f"<option value='{i}' {'selected' if gl.usia_ayam==i else ''}>{i}</option>" for i in range(46)])}
    </select>
    <button style='margin-left:3vw;' onclick='setUsia()'>Set</button>

    <br><br>

    <label for='mode'>Mode : </label>
    <select id='mode' onchange='setMode()'>
      <option value='1' {'selected' if gl.mode_kandang==1 else ''}>Auto</option>
      <option value='2' {'selected' if gl.mode_kandang==2 else ''}>Manual</option>
      <option value='3' {'selected' if gl.mode_kandang==3 else ''}>Timer</option>
      <option value='4' {'selected' if gl.mode_kandang==4 else ''}>Selesai Panen</option>
    </select>
    """

    if gl.mode_kandang == 3:

        # ===========================
        # BAGIAN JUMLAH KIPAS
        # ===========================
        html += f"""
        <br><label for='jumlah_kipas'>Jumlah Kipas : </label>
        <select id='jumlah_kipas' onchange='updateSetting("jumlah_kipas_timer", this.value)'>
            {''.join([f"<option value='{i}' {'selected' if gl.jumlah_kipas_timer==i else ''}>{i}</option>" for i in range(1,4)])}
        </select>
        """

        # ===========================
        # BAGIAN WAKTU HIDUP
        # ===========================
        opsi_hidup = [10, 15, 20, 30, 45, 60, 90, 120]
        found_hidup = gl.waktu_hidup in opsi_hidup

        # Tentukan apakah tombol custom yg dipilih
        custom_hidup_selected = not found_hidup

        html += """
        <br><label for='waktu_hidup'>Waktu Hidup : </label>
        <select id='waktu_hidup' onchange='toggleCustomInput("waktu_hidup"); updateSetting("waktu_hidup", this.value)'>
        """

        for v in opsi_hidup:
            html += f"<option value='{v}' {'selected' if gl.waktu_hidup==v else ''}>{v} Detik</option>"

        html += f"<option value='custom' {'selected' if custom_hidup_selected else ''}>Custom</option>"
        html += "</select>"

        # Tampilkan input custom hanya jika SELECTED == custom
        display_hidup = "block" if custom_hidup_selected else "none"

        html += f"""
        <div id='waktu_hidup_custom' style='display:{display_hidup}'>
            <input type='number' id='input_waktu_hidup' 
                   value='{gl.waktu_hidup if custom_hidup_selected else ""}' 
                   onblur='updateSetting("waktu_hidup", this.value)'>
            <span>Detik</span>
        </div>
        """

        # ===========================
        # BAGIAN WAKTU MATI
        # ===========================
        opsi_mati = [1, 2, 3, 5, 10, 15, 20, 30, 45, 60]
        found_mati = gl.waktu_mati in opsi_mati
        custom_mati_selected = not found_mati

        html += """
        <br><label for='waktu_mati'>Waktu Mati : </label>
        <select id='waktu_mati' onchange='toggleCustomInput("waktu_mati"); updateSetting("waktu_mati", this.value)'>
        """

        for v in opsi_mati:
            html += f"<option value='{v}' {'selected' if gl.waktu_mati==v else ''}>{v} Menit</option>"

        html += f"<option value='custom' {'selected' if custom_mati_selected else ''}>Custom</option>"
        html += "</select>"

        display_mati = "block" if custom_mati_selected else "none"

        html += f"""
        <div id='waktu_mati_custom' style='display:{display_mati}'>
            <input type='number' id='input_waktu_mati' 
                   value='{gl.waktu_mati if custom_mati_selected else ""}' 
                   onblur='updateSetting("waktu_mati", this.value)'>
            <span>Menit</span>
        </div>
        """

        html += "<br><br>"


    html += f"""
    <br><br><h3>Kipas</h3>
    <div class='button-container'>{kipas_html}</div>
    <br><div><span>{gl.keterangan_web}</span></div><br><br>
    
    
    <h3>Update Data Ayam</h3>

    <label for="varSelect">Pilih Variabel:</label><br>
    <select id="varSelect">
        <option value="jumlah_ayam_awal">Jumlah Ayam Awal</option>
        <option value="jumlah_ayam_mati">Jumlah Ayam Mati</option>
        <option value="jumlah_pakan_sak">Jumlah Pakan Sak</option>
        <option value="bobot_rata_rata">Bobot Rata-Rata</option>
        <option value="harga_kontrak_ayam">Harga Kontrak Ayam</option>
        <option value="harga_bibit_ayam">Harga Bibit Ayam</option>
        <option value="harga_obat_ayam">Harga Obat Ayam</option>
        <option value="harga_pakan_kg">Harga Pakan/kg</option>
        <option value="jumlah_ayam_dipanen">Jumlah Ayam Dipanen</option>
    </select>
    <br><br>

    <label for="nilai">Masukkan Nilai:</label><br>
    <input type="number" id="nilai"><br><br>

    <button onclick="kirimData()">Kirim ke Kandang</button><br><br><br><br>
    <button onclick="restartESP()">Restart Kipas</button>

    <script>
      let mode = {gl.mode_kandang};
      function toggleKipas(i) {{
        if ((mode == 1)||(mode == 3)) {{
          alert('Ganti dulu ke mode manual atau selesai panen!');
          return;
        }}
        document.getElementById('loading').style.display = 'block';
        fetch('/kipas?nomor=' + i).then(() => location.reload());
      }}
      
      function toggleCustomInput(field) {{
            var select = document.getElementById(field);
            var customDiv = document.getElementById(field + '_custom');
            if (select.value === 'custom') {{
                customDiv.style.display = 'block';
            }} else {{
                customDiv.style.display = 'none';
            }}
        }}

        function updateSetting(param, value) {{
            if (value === 'custom') return;

            document.getElementById('loading').style.display = 'block';

            fetch(`/ubah_setting?param=${{param}}&value=${{value}}`)
                .then(r => r.json())
                .then(() => {{
                    // Paksa browser ambil ulang HTML dari server tanpa cache
                    window.location.href = window.location.pathname + "?t=" + Date.now();
                }});
        }}
        
        function kirimData() {{
            const param = document.getElementById('varSelect').value;
            const value = document.getElementById('nilai').value;

            if (!value) {{
                alert("Isi nilai terlebih dahulu!");
                return;
            }}else{{
                updateSetting(param, value);
                alert("Berhasil memperbarui: " + param);
            }}

            document.getElementById('loading').style.display = 'block';
        }}

      function setMode() {{
        document.getElementById('loading').style.display = 'block';
        let val = document.getElementById('mode').value;
        fetch('/mode?val=' + val).then(() => location.reload());
      }}
      
      function setUsia() {{
        document.getElementById('loading').style.display = 'block';
        let val = document.getElementById('usia').value;
        fetch('/usia?val=' + val).then(() => location.reload());
      }}
      function restartESP() {{
        fetch('/restartx').then(r => alert('Kipas akan restart...'));
      }}
    </script>
    </body></html>
    """
    return html


# ==========================================================
#  ENDPOINT LAINNYA (disingkat tapi lengkap)
# ==========================================================

@app.get("/wkt")
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

@app.get("/kps")
async def kipas_json():
    #gl.jumlah_http += 1
    data = {
        "dta": [1562, random.randint(1, 9)],
        "kps": gl.kipas
   }
    return json_response(data)

@app.get("/shu")
async def suhu_json():
    #gl.jumlah_http += 1
    data = {
        "dta": [1563, random.randint(1, 9)],
        "shu": [pd._to_int_no_decimal(gl.suhu_atas),
                pd._to_int_no_decimal(gl.suhu_bawah),
                pd._to_int_no_decimal(gl.suhu_luar)],
        "klb": [pd._to_int_no_decimal(gl.kelembapan_atas),
                pd._to_int_no_decimal(gl.kelembapan_bawah),
                pd._to_int_no_decimal(gl.kelembapan_luar)],
        "dhi": [pd._to_int_no_decimal(gl.data_HI_atas),
                pd._to_int_no_decimal(gl.data_HI_bawah),
                pd._to_int_no_decimal(gl.data_HI_luar)]
   }
    return json_response(data)

@app.get("/mtd")
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
                gl.bobot_rata_rata,
                gl.blok_kandang,
                gl.jumlah_ayam_dipanen
                ]
   }
    return json_response(data)

@app.get("/kipas")
async def kipas_web_json(nomor: int = Query(..., ge=0, le=4)):
    gl.jumlah_http += 1
    if gl.mode_kandang == 1:
        return JSONResponse(content={"error": "Mode auto, tidak bisa manual"}, status_code=403)
    kipas_state = gl.kipas
    kipas_state[nomor] = 0 if kipas_state[nomor] else 1
    saklar_kipas(*kipas_state)
    print(f"Kipas {nomor+1} diubah ke {int(kipas_state[nomor])}")
    return {"status": f"Kipas {nomor+1} diubah ke {int(kipas_state[nomor])}"}


@app.get("/mode")
async def ubah_mode(val: int):
    gl.mode_kandang = val
    pd.simpan_data()
    return {"ok": True}

@app.get("/usia")
async def ubah_usia(val: int):
    atur_usia(val)
    return {"ok": True}

@app.get("/jumlah_kipas")
async def ubah_jumlah_kipas_timer(val: int):
    gl.jumlah_kipas_timer = val
    pd.simpan_data()
    return {"ok": True}

@app.get("/waktu_hidup")
async def ubah_waktu_hidup(val: int):
    gl.waktu_hidup = val
    pd.simpan_data()
    return {"ok": True}

@app.get("/waktu_mati")
async def ubah_waktu_mati(val: int):
    gl.waktu_mati = val
    pd.simpan_data()
    return {"ok": True}

@app.get("/ubah_setting")
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

    pd.simpan_data()

    return {"status": "ok", "ubah": param, "nilai_baru": value}

@app.get("/restart")
async def restart():
    #os.system("sudo reboot now")
    return {"msg": "Raspberry Pi akan restart..."}


# ==========================================================
#  RUN SERVER
# ==========================================================
def run_server():
    import uvicorn
    uvicorn.run("webserver:app", host="0.0.0.0", port=8080, reload=False)

#if __name__ == "__main__":
#    run_server()

print("webserver ok")

