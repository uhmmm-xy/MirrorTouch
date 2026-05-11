"""ProtocolPackHandler — 5 字节协议打包（比例归一化）

[MIRROR-TOUCH-T3] 操作码映射:
  Opcode 0: SET_SIZE  — 虚拟画布 32767×32767
  Opcode 1: DOWN      — 手指按下  (id, ratio_x, ratio_y)
  Opcode 2: MOVE      — 手指滑动  (id, ratio_x, ratio_y)
  Opcode 3: UP        — 手指抬起  (id)

帧结构 (5 bytes, 大端手动拼接):
  byte0: cmd(低4bit) | id(高4bit)
  byte1: x 低8位
  byte2: x 高8位  (0~32767, 即 0x0000~0x7FFF)
  byte3: y 低8位
  byte4: y 高8位  (同 x)
"""

# ── 协议常量 ──
OP_SET_SIZE = 0
OP_DOWN     = 1
OP_MOVE     = 2
OP_UP       = 3
RATIO_SCALE = 32767   # 归一化因子


def pack_set_size() -> bytes:
    """初始化虚拟画布 32767×32767"""
    return _pack(OP_SET_SIZE, 0, 1.0, 1.0)


def pack_down(fid: int, ratio_x: float, ratio_y: float) -> bytes:
    """按下 DOWN(id, r_x, r_y) — Opcode 1"""
    return _pack(OP_DOWN, fid, ratio_x, ratio_y)


def pack_move(fid: int, ratio_x: float, ratio_y: float) -> bytes:
    """滑动 MOVE(id, r_x, r_y) — Opcode 2"""
    return _pack(OP_MOVE, fid, ratio_x, ratio_y)


def pack_up(fid: int) -> bytes:
    """抬起 UP(id) — Opcode 3"""
    return _pack(OP_UP, fid, 0.0, 0.0)


def _pack(cmd: int, fid: int, ratio_x: float, ratio_y: float) -> bytes:
    """5 字节手动拼接: cmd(4b)|id(4b)|x(16b)|y(16b)"""
    xi = int(min(max(ratio_x, 0.0), 1.0) * RATIO_SCALE)
    yi = int(min(max(ratio_y, 0.0), 1.0) * RATIO_SCALE)

    byte0 = ((cmd & 0x0F) << 4) | (fid & 0x0F)

    # x 拆分高低位
    x_low  = (xi & 0xFF)
    x_high = ((xi >> 8) & 0x7F)  # 限制 0~0x7F

    # y 拆分高低位
    y_low  = (yi & 0xFF)
    y_high =((yi >> 8) & 0x7F)  # 限制 0~0x7F
    return bytes([
        byte0,
        x_low,
        x_high,
        y_low,
        y_high,
    ])
