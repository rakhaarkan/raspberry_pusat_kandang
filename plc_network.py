"""
plc_network.py
==============
Multi-PLC network manager.

Manages a named collection of PLCClient instances.
Supports:
  - Parallel connect/disconnect
  - Per-node access by name
  - Aggregate statistics
  - Broadcast writes to all nodes
  - Health monitoring
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterator, Optional

from plc_client import PLCClient, PLCConnectionError

logger = logging.getLogger(__name__)


class PLCNetwork:
    """
    Manager for a collection of named PLCClient instances.

    Usage:
        network = PLCNetwork()
        network.add("kandang1", "192.168.0.101")
        network.add("kandang2", "192.168.0.102")
        network.add("kandang3", "192.168.0.103")

        await network.connect_all()

        # Access individual PLC
        await network["kandang1"].write_coil(0, True)
        temp = await network["kandang2"].read_float(10)

        # Broadcast write to all PLCs
        results = await network.broadcast_write_coil(4, True)  # Enable all fans

        # Get aggregate stats
        print(network.get_stats())

        await network.disconnect_all()
    """

    def __init__(
        self,
        port: int = 502,
        unit_id: int = 1,
        timeout: float = 3.0,
        retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        """
        Default connection parameters applied to all nodes.
        Individual nodes can override via add() kwargs.
        """
        self._defaults = dict(
            port=port,
            unit_id=unit_id,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
        )
        self._nodes: Dict[str, PLCClient] = {}

    # ----------------------------------------------------------
    # Node management
    # ----------------------------------------------------------

    def add(
        self,
        name: str,
        host: str,
        *,
        port: Optional[int] = None,
        unit_id: Optional[int] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ) -> "PLCNetwork":
        """
        Register a PLC node. Returns self for chaining.

        Args:
            name    : Logical name (e.g. "kandang1")
            host    : IP address
            port    : Override default port
            unit_id : Override default Modbus Unit ID
            timeout : Override default request timeout
            retries : Override default retry count
        """
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already registered.")

        params = {**self._defaults}
        if port        is not None: params["port"]        = port
        if unit_id     is not None: params["unit_id"]     = unit_id
        if timeout     is not None: params["timeout"]     = timeout
        if retries     is not None: params["retries"]     = retries
        if retry_delay is not None: params["retry_delay"] = retry_delay

        self._nodes[name] = PLCClient(host=host, name=name, **params)
        logger.debug("[PLCNetwork] Registered node '%s' -> %s", name, host)
        return self

    def remove(self, name: str) -> None:
        """Unregister a node (does not disconnect)."""
        self._nodes.pop(name, None)

    def __getitem__(self, name: str) -> PLCClient:
        """Access a node by name: network["kandang1"]"""
        try:
            return self._nodes[name]
        except KeyError:
            raise KeyError(
                f"No PLC node named '{name}'. "
                f"Registered: {list(self._nodes.keys())}"
            )

    def __contains__(self, name: str) -> bool:
        return name in self._nodes

    def __iter__(self) -> Iterator[PLCClient]:
        return iter(self._nodes.values())

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def names(self) -> list[str]:
        return list(self._nodes.keys())

    # ----------------------------------------------------------
    # Connection management
    # ----------------------------------------------------------

    async def connect_all(self, ignore_errors: bool = False) -> dict[str, bool]:
        """
        Connect all registered nodes in parallel.

        Args:
            ignore_errors: If True, log failures but continue.
                           If False, raise on first failure.

        Returns:
            Dict of {name: True/False} connection results.
        """
        async def _connect_one(name: str, client: PLCClient) -> tuple[str, bool]:
            try:
                await client.connect()
                return name, True
            except PLCConnectionError as exc:
                logger.error("[PLCNetwork] Failed to connect '%s': %s", name, exc)
                if not ignore_errors:
                    raise
                return name, False

        tasks = [
            _connect_one(name, client)
            for name, client in self._nodes.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return dict(results)

    async def disconnect_all(self) -> None:
        """Disconnect all nodes in parallel."""
        await asyncio.gather(
            *[client.disconnect() for client in self._nodes.values()],
            return_exceptions=True,
        )
        logger.info("[PLCNetwork] All nodes disconnected.")

    async def reconnect_all(self) -> None:
        """Reconnect all nodes."""
        await self.disconnect_all()
        await self.connect_all(ignore_errors=True)

    # ----------------------------------------------------------
    # Health check
    # ----------------------------------------------------------

    async def ping_all(self) -> dict[str, bool]:
        """
        Check connectivity of all nodes by reading a single holding register.
        Returns dict of {name: is_alive}.
        """
        async def _ping(name: str, client: PLCClient) -> tuple[str, bool]:
            try:
                await client.read_holding(0)
                return name, True
            except Exception:
                return name, False

        results = await asyncio.gather(
            *[_ping(name, client) for name, client in self._nodes.items()],
            return_exceptions=False,
        )
        return dict(results)

    # ----------------------------------------------------------
    # Broadcast operations
    # ----------------------------------------------------------

    async def broadcast_write_coil(
        self,
        address: int,
        value: bool,
        ignore_errors: bool = True,
    ) -> dict[str, bool]:
        """Write coil to ALL nodes simultaneously. Returns {name: success}."""

        async def _write(name: str, client: PLCClient) -> tuple[str, bool]:
            try:
                await client.write_coil(address, value)
                return name, True
            except Exception as exc:
                logger.error("[%s] broadcast write_coil failed: %s", name, exc)
                if not ignore_errors:
                    raise
                return name, False

        results = await asyncio.gather(
            *[_write(name, client) for name, client in self._nodes.items()],
            return_exceptions=False,
        )
        return dict(results)

    async def broadcast_write_holding(
        self,
        address: int,
        value: int,
        ignore_errors: bool = True,
    ) -> dict[str, bool]:
        """Write holding register to ALL nodes simultaneously."""

        async def _write(name: str, client: PLCClient) -> tuple[str, bool]:
            try:
                await client.write_holding(address, value)
                return name, True
            except Exception as exc:
                logger.error("[%s] broadcast write_holding failed: %s", name, exc)
                if not ignore_errors:
                    raise
                return name, False

        results = await asyncio.gather(
            *[_write(name, client) for name, client in self._nodes.items()],
            return_exceptions=False,
        )
        return dict(results)

    async def read_all_float(self, address: int) -> dict[str, Optional[float]]:
        """Read a float register from all nodes. Returns {name: value|None}."""

        async def _read(name: str, client: PLCClient) -> tuple[str, Optional[float]]:
            try:
                v = await client.read_float(address)
                return name, v
            except Exception as exc:
                logger.warning("[%s] read_all_float failed: %s", name, exc)
                return name, None

        results = await asyncio.gather(
            *[_read(name, client) for name, client in self._nodes.items()],
            return_exceptions=False,
        )
        return dict(results)

    # ----------------------------------------------------------
    # Aggregate statistics
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        """Return statistics for all nodes."""
        return {
            name: client.get_stats()
            for name, client in self._nodes.items()
        }

    def print_stats(self) -> None:
        """Print a formatted statistics table to stdout."""
        print(f"\n{'─' * 70}")
        print(f"{'NODE':<15} {'HOST':<16} {'REQS':>6} {'ERR':>5} "
              f"{'TIMEOUT':>8} {'RECONN':>7} {'AVG_LAT':>10}")
        print(f"{'─' * 70}")
        for name, client in self._nodes.items():
            s = client.stats
            print(
                f"{name:<15} {client.host:<16} {s.requests:>6} {s.errors:>5} "
                f"{s.timeouts:>8} {s.reconnects:>7} "
                f"{s.avg_latency_ms:>8.1f}ms"
            )
        print(f"{'─' * 70}\n")

    def __repr__(self) -> str:
        return f"PLCNetwork(nodes={self.names})"
