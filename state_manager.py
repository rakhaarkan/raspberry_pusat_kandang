import asyncio
import variabel_global as gl
from kontrol_kipas import saklar_kipas

clients = set()
state_lock = asyncio.Lock()
state_version = 0

async def broadcast(snapshot):
    dead = []

    for c in clients:
        try:
            await c.send_json(snapshot)
        except:
            dead.append(c)

    for d in dead:
        clients.discard(d)

async def apply_kipas_state(new_state: list, source: str = "unknown"):
    """
    Satu-satunya pintu perubahan kipas.
    """

    from main import state_version, broadcast, state_lock  # sesuaikan import kamu

    async with state_lock:
        # Update hardware
        saklar_kipas(*new_state)

        # Naikkan versi global
        state_version += 1

        snapshot = {
            "type": "state_update",
            "kipas": gl.kipas.copy(),
            "mode": gl.mode_kandang,
            "usia": gl.usia_ayam,
            "version": state_version,
            "source": source
        }

    await broadcast(snapshot)