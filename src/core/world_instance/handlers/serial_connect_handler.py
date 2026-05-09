"""SerialConnectHandler — 开启/关闭/重连串口"""
import serial as pyserial
from src.utils.logger import log


def handle_connect(port: str, baudrate: int):
    ser = pyserial.Serial()
    ser.port = port
    ser.baudrate = baudrate
    ser.timeout = 1
    ser.dtr = False
    ser.rts = False
    ser.open()
    pyserial.time.sleep(0.5)
    ser.reset_input_buffer()
    log.info(f"[SerialConnect] 已连接 {port}@{baudrate}")
    return ser


def handle_disconnect(ser):
    if ser and ser.is_open:
        ser.dtr = False
        ser.rts = False
        ser.close()
        log.info("[SerialConnect] 已断开")
