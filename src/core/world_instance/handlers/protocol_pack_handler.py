"""ProtocolPackHandler — 4 字节小端协议打包 (位运算)"""
import struct


def pack_d(fid: int, x: int, y: int) -> bytes:
    """点击 D(id, x, y)"""
    return _pack(0, fid, x, y)


def pack_s(fid: int, x: int, y: int) -> bytes:
    """滑动 S(id, x, y)"""
    return _pack(1, fid, x, y)


def pack_h(fid: int, x: int, y: int) -> bytes:
    """长按 H(id, x, y)"""
    return _pack(2, fid, x, y)


def pack_u(fid: int) -> bytes:
    """抬起 U(id)"""
    return _pack(3, fid, 0, 0)


def _pack(cmd: int, fid: int, x: int, y: int) -> bytes:
    """位运算打包：cmd(2b) | id(4b) | x(13b) | y(13b) → uint32 LE"""
    v = (cmd & 0x03) | ((fid & 0x0F) << 2) | ((x & 0x1FFF) << 6) | ((y & 0x1FFF) << 19)
    return struct.pack('<I', v)
