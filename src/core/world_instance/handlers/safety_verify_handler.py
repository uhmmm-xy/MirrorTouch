"""SafetyVerifyHandler — 发送前验证串口连接"""


def is_ok(ser) -> bool:
    return ser is not None and ser.is_open
