# FrameBridge Python 对接文档

通过 ctypes 调用 FrameBridge C API，从共享内存获取解码后的 RGB24 视频帧。

---

## 1. 加载 DLL

```python
import ctypes
import os

dll = ctypes.CDLL("framebridge.dll")  # 或完整路径

# 或自动查找（推荐）
def load_framebridge():
    """自动查找 framebridge.dll"""
    search = [
        "framebridge.dll",
        "build/Release/framebridge.dll",
        os.path.join(os.path.dirname(__file__), "build/Release/framebridge.dll"),
    ]
    for p in search:
        if os.path.exists(p):
            return ctypes.CDLL(p)
    raise FileNotFoundError("framebridge.dll not found. Build the project first.")

dll = load_framebridge()
```

---

## 2. API 函数签名

### 2.1 函数绑定

```python
from ctypes import c_int32, c_char_p, c_uint64, POINTER, Structure

# int frame_server_start(const char* adb_path, const char* server_path,
#                        const char* serial, int max_size, int max_fps,
#                        int bit_rate_kbps)
dll.frame_server_start.argtypes = [
    c_char_p, c_char_p, c_char_p,
    c_int32, c_int32, c_int32,
]
dll.frame_server_start.restype = c_int32  # 0=成功, -1=失败

# FrameData* frame_server_read(int timeout_ms)
dll.frame_server_read.argtypes = [c_int32]
dll.frame_server_read.restype = c_void_p  # 返回 FrameData* 指针

# void frame_server_stop()
dll.frame_server_stop.argtypes = []
dll.frame_server_stop.restype = None

# const char* frame_server_get_error()
dll.frame_server_get_error.argtypes = []
dll.frame_server_get_error.restype = c_char_p
```

### 2.2 FrameData 结构体

必须与 C 端 `frame_server.h` 完全对齐：

```python
class FrameData(Structure):
    _fields_ = [
        ("frame_id",     c_uint64),   # 帧序号，从 1 递增
        ("timestamp_ms", c_uint64),   # 解码时刻（毫秒）
        ("width",        c_int32),    # 帧宽度
        ("height",       c_int32),    # 帧高度
        ("size",         c_int32),    # RGB 数据字节数 = width * height * 3
        ("_padding",     c_int32),    # 对齐填充，忽略
    ]
    # data[] 是柔性数组，紧跟在结构体之后
```

### 2.3 帧数据读取

```python
def read_frame(dll, timeout_ms=16):
    """
    读取最新帧

    Args:
        timeout_ms: 超时毫秒。 -1=无限等待, 0=立即返回, >0=超时返回

    Returns:
        dict 或 None:
        {
            "frame_id":     int,     # 帧序号
            "timestamp_ms": int,     # 时间戳
            "width":        int,     # 宽度
            "height":       int,     # 高度
            "size":         int,     # 字节数
            "data":         bytes,   # RGB24 原始数据
        }
    """
    ptr = dll.frame_server_read(timeout_ms)
    if not ptr:
        return None

    # 读取 FrameData 元数据
    frame = FrameData.from_address(ptr)

    # 读取柔性数组 data[] 的数据
    data_offset = ctypes.sizeof(FrameData)
    buf_type = ctypes.c_uint8 * frame.size
    data_buf = buf_type.from_address(ptr + data_offset)

    return {
        "frame_id":     frame.frame_id,
        "timestamp_ms": frame.timestamp_ms,
        "width":        frame.width,
        "height":       frame.height,
        "size":         frame.size,
        "data":         bytes(data_buf),
    }
```

> **注意**：返回的 `data` 是共享内存映射区域的副本（`bytes()` 会拷贝）。如果性能敏感，可以直接用 `memoryview` 避免拷贝。

---

## 3. Python 封装类

```python
class FrameBridge:
    """FrameBridge 中间件 Python 封装"""

    def __init__(self, dll_path=None):
        if dll_path is None:
            # 自动查找
            search = [
                "framebridge.dll",
                "build/Release/framebridge.dll",
                os.path.join(os.path.dirname(__file__), "build/Release/framebridge.dll"),
            ]
            for p in search:
                if os.path.exists(p):
                    dll_path = p
                    break
            else:
                raise FileNotFoundError("framebridge.dll not found")

        self.lib = ctypes.CDLL(dll_path)
        self._setup_api()

    def _setup_api(self):
        self.lib.frame_server_start.argtypes = [c_char_p]*3 + [c_int32]*3
        self.lib.frame_server_start.restype = c_int32
        self.lib.frame_server_read.argtypes = [c_int32]
        self.lib.frame_server_read.restype = c_void_p
        self.lib.frame_server_stop.argtypes = []
        self.lib.frame_server_stop.restype = None
        self.lib.frame_server_get_error.restype = c_char_p

    def start(self, *, adb_path=None, server_path=None, serial=None,
              max_size=1080, max_fps=90, bit_rate_kbps=8000):
        """
        启动帧服务器

        Args:
            adb_path:    ADB 可执行文件路径，None=自动查找
            server_path: scrcpy-server 路径，None=默认路径
            serial:      设备序列号，None=自动选择
            max_size:    最大分辨率（短边），如 1080
            max_fps:     最大帧率，如 120
            bit_rate_kbps: 视频码率 (kbps)，如 8000

        Raises:
            RuntimeError: 启动失败
        """
        ret = self.lib.frame_server_start(
            adb_path.encode() if adb_path else None,
            server_path.encode() if server_path else None,
            serial.encode() if serial else None,
            max_size, max_fps, bit_rate_kbps,
        )
        if ret != 0:
            err = self.lib.frame_server_get_error()
            msg = err.decode('gbk', errors='replace') if err else "unknown"
            raise RuntimeError(f"frame_server_start failed: {msg}")

    def read(self, timeout_ms=16):
        """读取最新帧，超时返回 None"""
        ptr = self.lib.frame_server_read(timeout_ms)
        if not ptr:
            return None

        frame = FrameData.from_address(ptr)
        data_offset = ctypes.sizeof(FrameData)
        buf_type = ctypes.c_uint8 * frame.size
        data_buf = buf_type.from_address(ptr + data_offset)

        return {
            "frame_id":     frame.frame_id,
            "timestamp_ms": frame.timestamp_ms,
            "width":        frame.width,
            "height":       frame.height,
            "size":         frame.size,
            "data":         bytes(data_buf),
        }

    def stop(self):
        """停止帧服务器"""
        self.lib.frame_server_stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
```

---

## 4. NumPy / OpenCV 转换

```python
import numpy as np
import cv2

def frame_to_bgr(frame_dict):
    """
    FrameData → OpenCV BGR numpy 数组

    Args:
        frame_dict: read_frame() 返回的字典

    Returns:
        numpy.ndarray (H, W, 3), dtype=uint8, BGR 顺序
    """
    arr = np.frombuffer(frame_dict["data"], dtype=np.uint8)
    rgb = arr.reshape((frame_dict["height"], frame_dict["width"], 3))
    return rgb[:, :, ::-1].copy()  # RGB → BGR


def frame_to_rgb(frame_dict):
    """
    FrameData → RGB numpy 数组

    Returns:
        numpy.ndarray (H, W, 3), dtype=uint8, RGB 顺序
    """
    arr = np.frombuffer(frame_dict["data"], dtype=np.uint8)
    return arr.reshape((frame_dict["height"], frame_dict["width"], 3)).copy()
```

---

## 5. MirrorTouch 对接示例

### 5.1 ScrcpyLauncher → frame_server_start

```python
from framebridge import FrameBridge

class ScrcpyLauncher:
    def __init__(self, config):
        self.config = config
        self.fb = FrameBridge()

    def start(self):
        self.fb.start(
            adb_path=self.config.get("adb_path"),
            server_path=self.config.get("server_path"),
            serial=self.config.get("device_serial"),
            max_size=self.config.get("max_size", 1080),
            max_fps=self.config.get("max_fps", 90),
            bit_rate_kbps=self.config.get("bit_rate", 8000),
        )
        # 等待第一帧确认连接正常
        frame = self.fb.read(timeout_ms=3000)
        if not frame:
            raise TimeoutError("No frame from device within 3s")

    def stop(self):
        self.fb.stop()
```

### 5.2 RenderComponent → frame_server_read

```python
class RenderComponent:
    def __init__(self, framebridge):
        self.fb = framebridge

    def _tick(self):
        """每帧渲染调用（~60fps = 16ms）"""
        frame = self.fb.read(timeout_ms=16)
        if not frame:
            return  # 无新帧，保持上一帧

        img = frame_to_bgr(frame)
        self._render_to_screen(img)
```

### 5.3 AI 推理线程 → frame_server_read

```python
import threading

class AIInferenceThread(threading.Thread):
    def __init__(self, framebridge):
        super().__init__(daemon=True)
        self.fb = framebridge
        self.running = True

    def run(self):
        while self.running:
            frame = self.fb.read(timeout_ms=100)  # 100ms = 10fps
            if frame:
                # 直接使用 RGB 数据（AI 模型通常用 RGB）
                rgb = frame_to_rgb(frame)
                result = self.model.infer(rgb)
                self._handle_result(result)

    def stop(self):
        self.running = False
```

### 5.4 app_builder 装配

```python
class AppBuilder:
    def build(self):
        # 去掉 VideoPipeline，只装配 Launcher 和 Render
        config = ConfigManager.load()
        self.launcher = ScrcpyLauncher(config)
        self.render = RenderComponent(self.launcher.fb)
        self.ai_thread = AIInferenceThread(self.launcher.fb)

        # 启动
        self.launcher.start()
        self.ai_thread.start()
        self.render.run_loop()  # 主循环
```

---

## 6. 错误处理

```python
from framebridge import FrameBridge

fb = FrameBridge()

try:
    fb.start(max_size=1080, max_fps=90)
except RuntimeError as e:
    print(f"启动失败: {e}")
    # 常见原因:
    # - "ADB executable not found"          → 安装 Android SDK Platform Tools
    # - "No Android device connected"       → USB 连接 + 开启 USB 调试
    # - "Failed to push scrcpy-server"     → resources/ 目录缺少文件
    # - "Connection refused"               → 设备端 Server 未启动
    sys.exit(1)

try:
    while True:
        frame = fb.read(timeout_ms=16)
        if frame:
            # 处理帧...
            pass
except KeyboardInterrupt:
    pass
finally:
    fb.stop()
```

---

## 7. 性能指南

| 场景 | 推荐 timeout | 说明 |
|------|:----------:|------|
| UI 渲染 (60fps) | **16ms** | 匹配 60Hz 刷新率 |
| UI 渲染 (120fps) | **8ms** | 匹配 120Hz 刷新率 |
| AI 推理 | **100ms** | 10fps，降低 CPU/GPU 占用 |
| 等待首帧 | **3000ms** | 启动后等待设备开始推流 |
| 非阻塞检查 | **0** | 立即返回，有帧取帧无帧跳过 |

**解码方式建议：**
- DXVA2 硬解：延迟低，适合高帧率场景
- FFmpeg 软解：兼容性好，适合无 GPU 环境

---

## 8. FrameData 内存布局

```
┌──────────────────────────────────────┐
│  FrameData (32 bytes)                │
│  ┌────────────────────────────────┐  │
│  │ uint64_t frame_id      (8B)    │  │
│  │ uint64_t timestamp_ms  (8B)    │  │
│  │ int32_t  width         (4B)    │  │
│  │ int32_t  height        (4B)    │  │
│  │ int32_t  size          (4B)    │  │
│  │ int32_t  _padding      (4B)    │  │
│  └────────────────────────────────┘  │
│  uint8_t  data[size]                 │
│  ┌────────────────────────────────┐  │
│  │ R G B R G B R G B ...          │  │
│  │ (width × height × 3 字节)      │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

> **data 格式**: RGB24（8位无符号，R-G-B 像素交错），行优先存储，无 stride padding。
