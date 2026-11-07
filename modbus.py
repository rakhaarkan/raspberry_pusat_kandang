"""
============================================================
MODBUS COMMUNICATION MODULE
============================================================

Author  : Rakha
Purpose : Centralized Modbus TCP communication layer
Version : 1.0

============================================================
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

import time
import threading


# ============================================================
# GLOBAL CONFIG
# ============================================================

DEFAULT_PORT = 502
DEFAULT_TIMEOUT = 3
AUTO_RECONNECT = True


# ============================================================
# BASE MODBUS DEVICE
# ============================================================

class ModbusDevice:

    def __init__(
        self,
        ip,
        port=DEFAULT_PORT,
        name="MODBUS_DEVICE"
    ):

        self.ip = ip
        self.port = port
        self.name = name

        self.client = ModbusTcpClient(
            host=self.ip,
            port=self.port,
            timeout=DEFAULT_TIMEOUT
        )

        self.connected = False

        self.lock = threading.Lock()

    # ========================================================
    # CONNECTION
    # ========================================================

    def connect(self):

        with self.lock:

            if self.connected:
                return True

            try:

                print(f"[{self.name}] Connecting...")

                self.connected = self.client.connect()

                if self.connected:
                    print(f"[{self.name}] Connected")
                else:
                    print(f"[{self.name}] Connection Failed")

                return self.connected

            except Exception as e:

                print(f"[{self.name}] Connect Exception: {e}")

                self.connected = False

                return False

    def disconnect(self):

        with self.lock:

            self.client.close()

            self.connected = False

            print(f"[{self.name}] Disconnected")

    def reconnect(self):

        self.disconnect()

        time.sleep(1)

        return self.connect()

    # ========================================================
    # INTERNAL SAFE CONNECTION CHECK
    # ========================================================

    def _ensure_connection(self):

        if self.connected:
            return True

        if AUTO_RECONNECT:
            return self.connect()

        return False

    # ========================================================
    # READ SINGLE REGISTER
    # ========================================================

    def read_register(self, register):

        with self.lock:

            try:

                if not self._ensure_connection():
                    return None

                result = self.client.read_holding_registers(
                    address=register,
                    count=1
                )

                if result.isError():

                    print(
                        f"[{self.name}] Read Error Reg {register}"
                    )

                    return None

                return result.registers[0]

            except ModbusException as e:

                print(
                    f"[{self.name}] Modbus Exception: {e}"
                )

                self.connected = False

                return None

            except Exception as e:

                print(
                    f"[{self.name}] General Exception: {e}"
                )

                self.connected = False

                return None

    # ========================================================
    # READ MULTIPLE REGISTERS
    # ========================================================

    def read_registers(self, register, count):

        with self.lock:

            try:

                if not self._ensure_connection():
                    return None

                result = self.client.read_holding_registers(
                    address=register,
                    count=count
                )

                if result.isError():

                    print(
                        f"[{self.name}] Read Error Reg {register}"
                    )

                    return None

                return result.registers

            except Exception as e:

                print(
                    f"[{self.name}] Read Registers Exception: {e}"
                )

                self.connected = False

                return None

    # ========================================================
    # WRITE SINGLE REGISTER
    # ========================================================

    def write_register(self, register, value):

        with self.lock:

            try:

                if not self._ensure_connection():
                    return False

                result = self.client.write_register(
                    address=register,
                    value=value
                )

                if result.isError():

                    print(
                        f"[{self.name}] Write Error Reg {register}"
                    )

                    return False

                return True

            except Exception as e:

                print(
                    f"[{self.name}] Write Exception: {e}"
                )

                self.connected = False

                return False

    # ========================================================
    # WRITE MULTIPLE REGISTERS
    # ========================================================

    def write_registers(self, register, values):

        with self.lock:

            try:

                if not self._ensure_connection():
                    return False

                result = self.client.write_registers(
                    address=register,
                    values=values
                )

                if result.isError():

                    print(
                        f"[{self.name}] Write Multi Error"
                    )

                    return False

                return True

            except Exception as e:

                print(
                    f"[{self.name}] Write Multi Exception: {e}"
                )

                self.connected = False

                return False

    # ========================================================
    # HEARTBEAT
    # ========================================================

    def heartbeat(self, register, value=1):

        return self.write_register(register, value)

    # ========================================================
    # PING TEST
    # ========================================================

    def ping(self):

        return self.read_register(0) is not None


# ============================================================
# FAN CONTROLLER DEVICE
# ============================================================

class FanController(ModbusDevice):

    FAN_REGISTERS = {
        1: 100,
        2: 101,
        3: 102,
        4: 103,
        5: 104,
    }

    # ========================================================
    # SET FAN
    # ========================================================

    def set_fan(self, fan_id, state):

        if fan_id not in self.FAN_REGISTERS:

            print(
                f"[{self.name}] Invalid Fan ID"
            )

            return False

        register = self.FAN_REGISTERS[fan_id]

        value = 1 if state else 0

        success = self.write_register(
            register,
            value
        )

        if success:

            print(
                f"[{self.name}] Fan {fan_id} -> "
                f"{'ON' if state else 'OFF'}"
            )

        return success

    # ========================================================
    # GET FAN
    # ========================================================

    def get_fan(self, fan_id):

        if fan_id not in self.FAN_REGISTERS:
            return None

        register = self.FAN_REGISTERS[fan_id]

        value = self.read_register(register)

        if value is None:
            return None

        return bool(value)

    # ========================================================
    # TOGGLE FAN
    # ========================================================

    def toggle_fan(self, fan_id):

        current = self.get_fan(fan_id)

        if current is None:
            return False

        return self.set_fan(
            fan_id,
            not current
        )

    # ========================================================
    # ALL FANS
    # ========================================================

    def set_all_fans(self, state):

        success = True

        for fan_id in self.FAN_REGISTERS:

            result = self.set_fan(
                fan_id,
                state
            )

            if not result:
                success = False

        return success

    # ========================================================
    # GET ALL STATUS
    # ========================================================

    def get_all_status(self):

        status = {}

        for fan_id in self.FAN_REGISTERS:

            status[fan_id] = self.get_fan(
                fan_id
            )

        return status

    # ========================================================
    # PRINT STATUS
    # ========================================================

    def print_status(self):

        print("\n================================")
        print(f"{self.name} STATUS")
        print("================================")

        status = self.get_all_status()

        for fan_id, state in status.items():

            if state is None:
                text = "ERROR"
            else:
                text = "ON" if state else "OFF"

            print(f"Fan {fan_id}: {text}")

        print("================================\n")


# ============================================================
# SENSOR NODE DEVICE
# ============================================================

class SensorNode(ModbusDevice):

    REG_TEMP = 10
    REG_HUMIDITY = 11
    REG_PRESSURE = 12

    def get_temperature(self):

        value = self.read_register(
            self.REG_TEMP
        )

        if value is None:
            return None

        return value / 10.0

    def get_humidity(self):

        value = self.read_register(
            self.REG_HUMIDITY
        )

        if value is None:
            return None

        return value / 10.0

    def get_pressure(self):

        return self.read_register(
            self.REG_PRESSURE
        )


# ============================================================
# DEVICE MANAGER
# ============================================================

class DeviceManager:

    def __init__(self):

        self.devices = {}

    def add_device(self, name, device):

        self.devices[name] = device

    def get_device(self, name):

        return self.devices.get(name)

    def connect_all(self):

        for device in self.devices.values():

            device.connect()

    def disconnect_all(self):

        for device in self.devices.values():

            device.disconnect()

    def print_all_status(self):

        for name, device in self.devices.items():

            print(f"\n=== {name} ===")

            if isinstance(device, FanController):

                device.print_status()

    def list_devices(self):

        return list(self.devices.keys())