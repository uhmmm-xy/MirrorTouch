"""ProtocolPackHandler — 全量6指包协议

[MIRROR-TOUCH-T3] 
  全量包: cmd(8bit) + [(fid+status)(8bit)+pos(32bit)] × 6 = 31 bytes

  byte0: cmd = 0x00
  byte1-5:   finger0: fid(4bit)|status(4bit) | x(16bit) | y(16bit)
  byte6-10:  finger1: ...
  ...
  byte26-30: finger5

  status: 0x01=press, 0x00=release
  pos: x(16bit, 0~32767) + y(16bit, 0~32767)
"""

# ── 协议常量 ──
OP_ALL = 0x00
STATUS_RELEASE = 0x00
STATUS_PRESS   = 0x01


def pack_full_frame(fingers: list[dict]) -> bytes:
    """全量6指包 (31 bytes)

    Args:
        fingers: list of 6 dicts
            {"fid": 0, "status": STATUS_PRESS, "x": 16384, "y": 8192}
            x/y 已是归一值 (0~32767)
    """
    buf = bytearray()
    # byte0: cmd
    buf.append(OP_ALL)
    for f in fingers:
        fid = f["fid"] & 0x0F
        status = f["status"] & 0x0F
        xi = int(min(max(f["x"], 0), 32767))
        yi = int(min(max(f["y"], 0), 32767))
        # fid+status
        buf.append((fid << 4) | status)
        # x 低8位 + 高8位
        buf.append(xi & 0xFF)
        buf.append((xi >> 8) & 0x7F)
        # y 低8位 + 高8位
        buf.append(yi & 0xFF)
        buf.append((yi >> 8) & 0x7F)
    return bytes(buf)
