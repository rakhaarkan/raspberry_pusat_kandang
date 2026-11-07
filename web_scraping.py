import requests
from bs4 import BeautifulSoup
from variabel_global import gl
import re

def parse_harga(text):
    """
    Ambil angka dari berbagai format:
    - 20000
    - 20.000
    - 20000-21000
    """
    nums = re.findall(r'\d+', text.replace(".", "").replace(",", ""))
    
    if len(nums) == 0:
        return None, None
    elif len(nums) == 1:
        val = int(nums[0])
        return val, val
    else:
        return int(nums[0]), int(nums[1])


def is_jogja(text):
    text = text.lower()
    return any(x in text for x in ["yogya", "jogja", "yogyakarta", "diy"])


def is_kecil(berat):
    return "<" in berat or "kecil" in berat.lower()


def is_besar(berat):
    return ">" in berat or "besar" in berat.lower()


def ambil_harga_jogja():
    url = "https://chickin.id/blog/update/harga-ayam/jawa-tengah/"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.find_all("tr")

    last_kota = ""
    harga_pasar = [None, None, None, None]

    for row in rows:
        cols = row.find_all("td")

        if len(cols) < 3:
            continue

        # 🔥 Ambil semua text kolom
        texts = [c.text.strip() for c in cols]

        # 🔥 Deteksi kota (biasanya kolom 1)
        kota = texts[1] if len(texts) > 1 else ""
        if kota:
            last_kota = kota

        if not is_jogja(last_kota):
            continue

        # 🔥 Cari berat & harga secara fleksibel
        berat = ""
        harga_text = ""

        for t in texts:
            if "<" in t or ">" in t:
                berat = t
            elif re.search(r'\d', t):  # mengandung angka
                harga_text = t

        if not berat or not harga_text:
            continue

        harga_min, harga_max = parse_harga(harga_text)

        if harga_min is None:
            continue

        # 🔥 Mapping ke array
        if is_kecil(berat):
            harga_pasar[0] = harga_min
            harga_pasar[1] = harga_max

        elif is_besar(berat):
            harga_pasar[2] = harga_min
            harga_pasar[3] = harga_max

    gl.harga_pasar = harga_pasar
    return harga_pasar


# ===== TEST =====
hasil = ambil_harga_jogja()

print("Harga Pasar:", hasil)
print("Min <2kg:", hasil[0])
print("Max <2kg:", hasil[1])
print("Min >2kg:", hasil[2])
print("Max >2kg:", hasil[3])