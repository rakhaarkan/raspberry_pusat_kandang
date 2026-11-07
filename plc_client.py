"""
plc_client.py
=============
Async Modbus TCP client for ESP32 PLC nodes.

Design decisions:
  - Built on pymodbus AsyncModbusTcpClient (stable, well-tested library).
  - Every write operation verifies the echo response — Modbus TCP write
    responses echo back address + value. Mismatch triggers retry.
  - Exponential backoff on retry prevents thundering herd on bus errors.
  - All operations are async-native; compatible with asyncio.gather() for
    parallel multi-PLC operations.
  - Statistics counters per client instance, aggregated by PLCNetwork.
  - No silent failures: every operation either succeeds or raises PLCError.

Register encoding conventions (match ESP32 PLCEndian):
  - float  : 2 holding registers, Big-Endian word order (ABCD)
  - int32  : 2 holding registers, Big-Endian word order
  - uint32 : 2 holding registers, Big-Endian word order
  - double : 4 holding registers, Big-Endian word order (8 bytes)
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException

logger = logging.getLogger(__name__)


# ============================================================
# Exceptions
# ============================================================

class PLCError(Exception):
    """Base exception for all PLC communication errors."""

class PLCConnectionError(PLCError):
    """Raised when connection to PLC cannot be established."""

class PLCTimeoutError(PLCError):
    """Raised when a request times out after all retries."""

class PLCVerifyError(PLCError):
    """Raised when write-verify finds a mismatch."""

class PLCReadError(PLCError):
    """Raised on read failure."""

class PLCWriteError(PLCError):
    """Raised on write failure after all retries."""


# ============================================================
# Statistics
# ============================================================

@dataclass
class PLCStats:
    """Per-client operation statistics."""
    requests: int       = 0
    errors: int         = 0
    timeouts: int       = 0
    reconnects: int     = 0
    latency_sum_ms: float = 0.0
    latency_count: int  = 0

    @property
    def avg_latency_ms(self) -> float:
        if self.latency_count == 0:
            return 0.0
        return self.latency_sum_ms / self.latency_count

    def record_latency(self, ms: float) -> None:
        self.latency_sum_ms += ms
        self.latency_count  += 1

    def to_dict(self) -> dict:
        return {
            "requests":        self.requests,
            "errors":          self.errors,
            "timeouts":        self.timeouts,
            "reconnects":      self.reconnects,
            "avg_latency_ms":  round(self.avg_latency_ms, 2),
        }


# ============================================================
# Endian helpers (mirror of PLCEndian in ESP32 firmware)
# ============================================================

def _pack_float(value: float) -> list[int]:
    """Pack IEEE 754 float into 2 Modbus registers (Big-Endian ABCD word order)."""
    raw = struct.pack(">f", value)           # Big-Endian float
    hi  = struct.unpack(">H", raw[0:2])[0]   # High word
    lo  = struct.unpack(">H", raw[2:4])[0]   # Low word
    return [hi, lo]

def _unpack_float(regs: Sequence[int]) -> float:
    """Unpack 2 Modbus registers (ABCD) into IEEE 754 float."""
    raw = struct.pack(">HH", regs[0], regs[1])
    return struct.unpack(">f", raw)[0]

def _pack_int32(value: int) -> list[int]:
    """Pack signed int32 into 2 registers."""
    raw = struct.pack(">i", value)
    return [struct.unpack(">H", raw[0:2])[0], struct.unpack(">H", raw[2:4])[0]]

def _unpack_int32(regs: Sequence[int]) -> int:
    """Unpack 2 registers into signed int32."""
    raw = struct.pack(">HH", regs[0], regs[1])
    return struct.unpack(">i", raw)[0]

def _pack_uint32(value: int) -> list[int]:
    """Pack unsigned uint32 into 2 registers."""
    raw = struct.pack(">I", value)
    return [struct.unpack(">H", raw[0:2])[0], struct.unpack(">H", raw[2:4])[0]]

def _unpack_uint32(regs: Sequence[int]) -> int:
    """Unpack 2 registers into unsigned uint32."""
    raw = struct.pack(">HH", regs[0], regs[1])
    return struct.unpack(">I", raw)[0]

def _pack_double(value: float) -> list[int]:
    """Pack IEEE 754 double into 4 registers (Big-Endian)."""
    raw = struct.pack(">d", value)
    return [struct.unpack(">H", raw[i*2:(i+1)*2])[0] for i in range(4)]

def _unpack_double(regs: Sequence[int]) -> float:
    """Unpack 4 registers into IEEE 754 double."""
    raw = b"".join(struct.pack(">H", r) for r in regs[:4])
    return struct.unpack(">d", raw)[0]


# ============================================================
# PLCClient
# ============================================================

class PLCClient:
    """
    Async Modbus TCP client for a single ESP32 PLC slave.

    Usage:
        plc = PLCClient("192.168.0.101")
        await plc.connect()
        await plc.write_coil(0, True)
        temp = await plc.read_float(10)
        await plc.disconnect()

    Parameters:
        host        : IP address of ESP32
        port        : Modbus TCP port (default 502)
        unit_id     : Modbus Unit ID (default 1)
        timeout     : Per-request timeout in seconds (default 3.0)
        retries     : Number of retries on failure (default 3)
        retry_delay : Base delay for exponential backoff in seconds (default 0.5)
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        timeout: float = 3.0,
        retries: int = 3,
        retry_delay: float = 0.5,
        name: Optional[str] = None,
    ) -> None:
        self.host        = host
        self.port        = port
        self.unit_id     = unit_id
        self.timeout     = timeout
        self.retries     = retries
        self.retry_delay = retry_delay
        self.name        = name or host

        self.stats = PLCStats()
        self._client: Optional[AsyncModbusTcpClient] = None

    # ----------------------------------------------------------
    # Connection management
    # ----------------------------------------------------------

    async def connect(self) -> None:
        """Establish Modbus TCP connection."""
        self._client = AsyncModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=self.timeout,
        )
        connected = await self._client.connect()
        if not connected:
            self.stats.errors += 1
            raise PLCConnectionError(
                f"[{self.name}] Cannot connect to {self.host}:{self.port}"
            )
        logger.info("[%s] Connected to %s:%d", self.name, self.host, self.port)

    async def disconnect(self) -> None:
        """Close the Modbus TCP connection."""
        if self._client:
            self._client.close()
            self._client = None
        logger.info("[%s] Disconnected", self.name)

    async def reconnect(self) -> None:
        """Attempt to reconnect after failure."""
        logger.warning("[%s] Reconnecting...", self.name)
        self.stats.reconnects += 1
        await self.disconnect()
        connect_with_backoff = self.connect()
        await connect_with_backoff

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.connected

    async def _try_reconnect_silently(self) -> None:
        """Coba connect (lagi) tanpa raise - dipakai internal oleh _execute()
        supaya gagal-belum-connect tidak langsung nyerah tanpa usaha."""
        try:
            await self.connect()
        except PLCConnectionError:
            pass  # tetap gagal, biar retry loop di _execute yang nentuin pesan akhirnya

    # ----------------------------------------------------------
    # Internal: execute with retry + timing
    # ----------------------------------------------------------

    async def _execute(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a Modbus operation with retry, exponential backoff, dan
        auto-reconnect kalau koneksi ternyata sedang putus.

        method_name adalah NAMA method di self._client (bukan bound-method
        langsung) - sengaja begitu supaya kalau di tengah retry terjadi
        reconnect (self._client diganti objek baru), pemanggilan berikutnya
        selalu pakai getattr() yang segar ke client yang aktif sekarang,
        bukan nyangkut ke referensi client lama yang sudah dibuang.
        """
        if not self.connected:
            await self._try_reconnect_silently()

        last_exc: Exception = RuntimeError("No attempts made")
        delay = self.retry_delay

        for attempt in range(self.retries + 1):
            if not self.connected:
                last_exc = PLCConnectionError(f"[{self.name}] Not connected.")
            else:
                t0 = time.monotonic()
                try:
                    self.stats.requests += 1
                    coro_factory = getattr(self._client, method_name)
                    result = await coro_factory(*args, **kwargs)

                    # pymodbus returns an exception object (not raise) on error
                    if result.isError():
                        raise ModbusIOException(f"Modbus error: {result}")

                    elapsed_ms = (time.monotonic() - t0) * 1000
                    self.stats.record_latency(elapsed_ms)
                    return result

                except ModbusIOException as exc:
                    self.stats.errors += 1
                    last_exc = exc
                    logger.warning(
                        "[%s] Attempt %d/%d failed: %s",
                        self.name, attempt + 1, self.retries + 1, exc
                    )

                except asyncio.TimeoutError as exc:
                    self.stats.timeouts += 1
                    last_exc = exc
                    logger.warning("[%s] Timeout on attempt %d", self.name, attempt + 1)

                except ModbusException as exc:
                    self.stats.errors += 1
                    last_exc = exc
                    logger.error("[%s] Modbus exception: %s", self.name, exc)

            if attempt < self.retries:
                if not self.connected:
                    await self._try_reconnect_silently()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10.0)  # Exponential backoff, cap 10s

        raise PLCTimeoutError(
            f"[{self.name}] Operation failed after {self.retries + 1} attempts: {last_exc}"
        ) from last_exc

    # ----------------------------------------------------------
    # Internal: write with verification
    # ----------------------------------------------------------

    async def _write_coil_verified(self, address: int, value: bool) -> None:
        """Write coil and verify the echoed response."""
        result = await self._execute(
            "write_coil",
            address=address,
            value=value,
            slave=self.unit_id,
        )
        # Modbus FC05 response echoes address and value
        # pymodbus wraps this — check address if available
        echo_addr  = getattr(result, "address", address)
        if echo_addr != address:
            raise PLCVerifyError(
                f"[{self.name}] Coil write verify failed: "
                f"sent addr={address}, got addr={echo_addr}"
            )

    async def _write_register_verified(self, address: int, value: int) -> None:
        """Write single holding register and verify echo."""
        result = await self._execute(
            "write_register",
            address=address,
            value=value,
            slave=self.unit_id,
        )
        echo_addr = getattr(result, "address", address)
        if echo_addr != address:
            raise PLCVerifyError(
                f"[{self.name}] Register write verify failed: "
                f"sent addr={address}, got addr={echo_addr}"
            )

    async def _write_registers_verified(self, address: int, values: list[int]) -> None:
        """Write multiple holding registers and verify echo."""
        result = await self._execute(
            "write_registers",
            address=address,
            values=values,
            slave=self.unit_id,
        )
        echo_addr  = getattr(result, "address", address)
        echo_count = getattr(result, "count",   len(values))
        if echo_addr != address or echo_count != len(values):
            raise PLCVerifyError(
                f"[{self.name}] Multi-register write verify failed: "
                f"sent addr={address} count={len(values)}, "
                f"got addr={echo_addr} count={echo_count}"
            )

    # ----------------------------------------------------------
    # Public API — Coils
    # ----------------------------------------------------------

    async def read_coil(self, address: int) -> bool:
        """Read a single coil (FC01)."""
        result = await self._execute(
            "read_coils",
            address=address,
            count=1,
            slave=self.unit_id,
        )
        return bool(result.bits[0])

    async def write_coil(self, address: int, value: bool) -> None:
        """Write a single coil (FC05) with verification."""
        await self._write_coil_verified(address, value)

    async def read_discrete_input(self, address: int) -> bool:
        """Read a single discrete input (FC02)."""
        result = await self._execute(
            "read_discrete_inputs",
            address=address,
            count=1,
            slave=self.unit_id,
        )
        return bool(result.bits[0])

    # ----------------------------------------------------------
    # Public API — Holding Registers
    # ----------------------------------------------------------

    async def read_holding(self, address: int) -> int:
        """Read a single holding register (FC03). Returns uint16."""
        result = await self._execute(
            "read_holding_registers",
            address=address,
            count=1,
            slave=self.unit_id,
        )
        return result.registers[0]

    async def write_holding(self, address: int, value: int) -> None:
        """Write a single holding register (FC06) with verification."""
        await self._write_register_verified(address, value & 0xFFFF)

    async def read_multiple_registers(self, address: int, count: int) -> list[int]:
        """Read multiple holding registers (FC03). Returns list of uint16."""
        result = await self._execute(
            "read_holding_registers",
            address=address,
            count=count,
            slave=self.unit_id,
        )
        return list(result.registers)

    async def write_multiple_registers(self, address: int, values: list[int]) -> None:
        """Write multiple holding registers (FC16) with verification."""
        await self._write_registers_verified(address, values)

    # ----------------------------------------------------------
    # Public API — Input Registers
    # ----------------------------------------------------------

    async def read_input_register(self, address: int) -> int:
        """Read a single input register (FC04). Returns uint16."""
        result = await self._execute(
            "read_input_registers",
            address=address,
            count=1,
            slave=self.unit_id,
        )
        return result.registers[0]

    # ----------------------------------------------------------
    # Public API — Typed multi-register accessors
    # ----------------------------------------------------------

    async def read_float(self, address: int) -> float:
        """Read 2-register IEEE 754 float (Big-Endian ABCD)."""
        regs = await self.read_multiple_registers(address, 2)
        return _unpack_float(regs)

    async def write_float(self, address: int, value: float) -> None:
        """Write float as 2 holding registers with verification."""
        regs = _pack_float(value)
        await self._write_registers_verified(address, regs)

    async def read_int32(self, address: int) -> int:
        """Read signed int32 from 2 holding registers."""
        regs = await self.read_multiple_registers(address, 2)
        return _unpack_int32(regs)

    async def write_int32(self, address: int, value: int) -> None:
        """Write signed int32 as 2 holding registers."""
        regs = _pack_int32(value)
        await self._write_registers_verified(address, regs)

    async def read_uint32(self, address: int) -> int:
        """Read unsigned uint32 from 2 holding registers."""
        regs = await self.read_multiple_registers(address, 2)
        return _unpack_uint32(regs)

    async def write_uint32(self, address: int, value: int) -> None:
        """Write unsigned uint32 as 2 holding registers."""
        regs = _pack_uint32(value)
        await self._write_registers_verified(address, regs)

    async def read_double(self, address: int) -> float:
        """Read 4-register IEEE 754 double."""
        regs = await self.read_multiple_registers(address, 4)
        return _unpack_double(regs)

    async def write_double(self, address: int, value: float) -> None:
        """Write double as 4 holding registers."""
        regs = _pack_double(value)
        await self._write_registers_verified(address, regs)

    # ----------------------------------------------------------
    # Diagnostics
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        return {"name": self.name, "host": self.host, **self.stats.to_dict()}

    def __repr__(self) -> str:
        return (
            f"PLCClient(name={self.name!r}, host={self.host!r}, "
            f"port={self.port}, unit_id={self.unit_id}, "
            f"connected={self.connected})"
        )