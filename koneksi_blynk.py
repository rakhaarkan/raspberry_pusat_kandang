import BlynkLib
import threading
import time

# Initialize Blynk
#blynk = BlynkLib.Blynk('gDdRswSNzktJU8kB-iiwXRobPokhqbFC')

# Register Virtual Pins

BLYNK_AUTH = "gDdRswSNzktJU8kB-iiwXRobPokhqbFC"


# ===================================================
# Fungsi Blynk di proses terpisah
# ===================================================
def run_blynk():
    blynk = BlynkLib.Blynk(BLYNK_AUTH)

    # Contoh Virtual Write Handler
    @blynk.on("V1")
    def handle_v1_write(value):
        print("V1 =>", value)

    @blynk.on("V2")
    def handle_v2_write(value):
        print("V2 =>", value)

    @blynk.on("V3")
    def handle_v3_write(value):
        print("V3 =>", value)

    @blynk.on("V4")
    def handle_v4_write(value):
        print("V4 =>", value)

    @blynk.on("V5")
    def handle_v5_write(value):
        print("V5 =>", value)

    def send_time():
        blynk.virtual_write(7, "rakha")


    while True:
        try:
            blynk.run()
        except Exception as e:
            print("Blynk exception:", e)
            time.sleep(5)  # retry setelah delay
        else:
            time.sleep(0.05)  # sleep ringan agar CPU tidak full

    
if __name__ == "__main__":
    blynk_process = Process(target=kb.run_blynk, daemon=True)
    blynk_process.start()