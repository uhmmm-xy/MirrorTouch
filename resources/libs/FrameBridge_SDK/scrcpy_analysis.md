# Scrcpy 投屏原理深度分析

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Android 设备 (Server端)                       │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ SurfaceFlinger│───▶│  MediaCodec  │───▶│  scrcpy-server (Java)│  │
│  │ (屏幕捕获)    │    │  (H.264编码) │    │  localabstract:scrcpy │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                     │               │
├─────────────────────────────────────────────────────┼───────────────┤
│                                                     │ ADB Daemon     │
│  ┌──────────────────────────────────────────────────┘               │
│  │  adb daemon (adbd) 通过 USB/TCP 转发数据                         │
│  └──────────────────────────────────────────────────┐               │
│                                                     │               │
├─────────────────────────────────────────────────────┼───────────────┤
│                        PC (Client端)                │               │
│                                                     ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  ADB Client  │───▶│ TCP:27183    │───▶│  Scrcpy Client (C)   │  │
│  │  (adb.exe)   │    │ forward 端口  │    │  FFmpeg/SDL2 解码渲染│  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                     │
│  ★ 我们的中间件替换 Scrcpy Client，只保留解码+分发                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  ADB Client  │───▶│ TCP:27183    │───▶│  FrameBridge (C++)    │  │
│  │  (adb.exe)   │    │ forward 端口  │    │  硬件解码→共享内存    │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                     │               │
│                                          ┌──────────▼───────────┐  │
│                                          │  共享内存环形缓冲区    │  │
│                                          │  (capacity=2)         │  │
│                                          └─────┬──────────┬─────┘  │
│                                                │          │        │
│                                     ┌──────────▼──┐ ┌─────▼──────┐│
│                                     │ Python UI   │ │ AI 推理    ││
│                                     │ (ctypes)    │ │ (ctypes)   ││
│                                     └─────────────┘ └────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## 二、ADB 隧道协议详解

### 2.1 隧道建立流程

```
步骤1: adb push scrcpy-server /data/local/tmp/
  └─ 将 scrcpy-server jar 推送到设备临时目录

步骤2: adb forward tcp:27183 localabstract:scrcpy
  └─ 将 PC 本地 TCP 27183 端口转发到设备的 scrcpy 抽象 socket
  └─ localabstract:scrcpy 实际对应 /dev/socket/scrcpy（或类似路径）

步骤3: adb shell CLASSPATH=/data/local/tmp/scrcpy-server \
        app_process / com.genymobile.scrcpy.Server 2.7 \
        tunnel_forward=true audio=false control=false ...
  └─ 通过 app_process 启动 Java 进程
  └─ Server 端打开 localabstract:scrcpy socket 等待连接
  └─ PC 端连接 tcp:27183 即可收到数据
```

### 2.2 关键参数说明

| 参数 | 值 | 含义 |
|------|-----|------|
| tunnel_forward=true | 开启 | 使用 ADB 隧道转发，不走 socket 直连 |
| audio=false | 关闭 | 不传输音频 |
| control=false | 关闭 | 不接收控制指令 |
| cleanup=false | 关闭 | 不自动清理（我们手动管理） |
| send_device_meta=false | 关闭 | 不发设备元信息（我们自己获取分辨率） |
| send_frame_meta=false | 关闭 | 不发逐帧元信息 |
| send_dummy_byte=false | 关闭 | 不发哑字节（协议兼容用） |
| raw_video_stream=true | 开启 | **纯 H.264 Annex B 码流，无任何包装** |
| max_size=1080 | 1080p | 最大分辨率 |
| max_fps=90 | 90fps | 最大帧率 |
| video_bit_rate=16000000 | 16Mbps | 视频码率 |
| video_codec=h264 | H.264 | 视频编码格式 |

### 2.3 raw_video_stream=true 的数据格式

```
开启 raw_video_stream 后，Server 端只发纯 H.264 Annex B 码流：

| 0x00 0x00 0x00 0x01 | SPS NAL | 0x00 0x00 0x00 0x01 | PPS NAL |
| 0x00 0x00 0x00 0x01 | IDR NAL (I帧) |
| 0x00 0x00 0x00 0x01 | non-IDR NAL (P帧) |
| 0x00 0x00 0x00 0x01 | non-IDR NAL (P帧) |
...

特点：
- 无任何头部/尾部包装
- 无长度前缀（标准 Annex B 格式）
- SPS/PPS 只在开始时出现一次，或每隔一段时间刷新
- 每个 NAL Unit 以 4 字节起始码 0x00000001 分隔
```

## 三、H.264 Annex B 码流解析

### 3.1 SPS (Sequence Parameter Set) 中提取分辨率

```
SPS 数据结构（简化）：
┌──────────────────────────────────────────────────────┐
│ nal_unit_type (5 bits) = 7 (SPS)                     │
│ profile_idc (8 bits)                                 │
│ ...                                                  │
│ pic_width_in_mbs_minus1 (UE-Golomb)                  │
│ pic_height_in_map_units_minus1 (UE-Golomb)            │
│ frame_cropping_flag (1 bit)                          │
│  (if cropping):                                      │
│   frame_crop_left_offset, frame_crop_right_offset    │
│   frame_crop_top_offset, frame_crop_bottom_offset    │
└──────────────────────────────────────────────────────┘

计算公式：
width  = (pic_width_in_mbs_minus1 + 1) * 16
height = (pic_height_in_map_units_minus1 + 1) * 16
// 如果有 crop，再减去 crop 值
```

## 四、数据流时序

```
时间轴 →

Android:   [编码] [编码] [编码] [编码] [编码] ...
              │      │      │      │      │
ADB隧道:      │      │      │      │      │
              ▼      ▼      ▼      ▼      ▼
接收线程:   [收包] [收包] [收包] [收包] [收包] ...
              │      │      │      │      │
              ▼      ▼      ▼      ▼      ▼
H.264解析:  [SPS] [IDR] [P帧] [P帧] [P帧] ...
              │      │      │      │      │
              ▼      ▼      ▼      ▼      ▼
硬件解码:   [init][解码] [解码] [解码] [解码] ...
              │      │      │      │      │
              ▼      ▼      ▼      ▼      ▼
共享内存:    [×]   [帧0]  [帧1]  [帧0]  [帧1]  ← 环形覆盖
              │      │      │      │      │
              ▼      ▼      ▼      ▼      ▼
消费端:     waiting[读取] [读取] [读取] [读取] ...

环形缓冲区容量=2:
- slot 0: 当前最新帧
- slot 1: 上一帧（可能被覆盖）
- 每个消费者独立获取最新帧索引
```

## 五、为什么容量=2就够了

```
解码线程（生产者）速度 = 90fps (11ms/帧)
UI线程（消费者）速度 = 60fps (16ms/帧)   
AI线程（消费者）速度 = 10fps (100ms/帧)

容量=2 时：
- 生产者永远写最新slot，不会阻塞（覆盖旧帧）
- 消费者总是读最新slot，16ms超时不会饿死
- 即使 AI 线程 100ms 才读一次，也只是跳帧，不影响其他消费者
- 更多容量无意义（消费者只需要最新帧，不需要历史帧队列）
```

## 六、与原 Scrcpy Client 的对比

| 组件 | 原 Scrcpy Client | FrameBridge 中间件 |
|------|-----------------|-------------------|
| 解码 | FFmpeg + SDL2 | DXVA2/VAAPI/VT + FFmpeg回退 |
| 渲染 | SDL2 窗口 | 无渲染 |
| 音频 | 支持 | 不支持 |
| 控制 | 支持触控/键盘 | 不支持 |
| 分发 | 无 | 共享内存环形缓冲区 |
| 接口 | Java/C 内部API | C API (ctypes 可调) |
| 依赖 | FFmpeg, SDL2, libusb | 仅 FFmpeg(回退), 系统API |
```

## 七、关键实现细节

### 7.1 ADB 隧道连接

```
TCP socket 接收到的数据是连续的 H.264 Annex B 码流。
需要做 NAL Unit 分帧（按 0x00000001 起始码分割）。

注意：
- 单个 recv() 可能收到多个 NAL Unit
- 单个 NAL Unit 可能被拆分成多个 recv() 接收
- 需要缓冲区拼接，按起始码边界切分
```

### 7.2 解码管线

```
Socket recv() → H.264 Annex B parser → NAL Units → Decoder → RGB frame → SHM
```

### 7.3 共享内存布局

```
┌─────────────────────────────────────────────────┐
│  FrameBridge SHM Header                         │
│  ┌───────────────────────────────────────────┐  │
│  │ uint32_t magic = 0x46424252 ("RBBF")      │  │
│  │ uint32_t version = 1                      │  │
│  │ uint32_t write_index  (当前写入slot)      │  │
│  │ uint32_t padding                          │  │
│  └───────────────────────────────────────────┘  │
│  Frame Slot 0                                   │
│  ┌───────────────────────────────────────────┐  │
│  │ uint64_t frame_id                         │  │
│  │ uint64_t timestamp_ms                     │  │
│  │ int32_t  width                            │  │
│  │ int32_t  height                           │  │
│  │ int32_t  size                             │  │
│  │ int32_t  padding                          │  │
│  │ uint8_t  data[width * height * 3]         │  │
│  └───────────────────────────────────────────┘  │
│  Frame Slot 1 (同 Slot 0 结构)                  │
└─────────────────────────────────────────────────┘

总大小 = sizeof(Header) + 2 * (sizeof(FrameMeta) + max_frame_size)
max_frame_size = 1080 * 1920 * 3 = 6,220,800 bytes ≈ 6MB
总大小 ≈ 16 + 2 * (32 + 6,220,800) ≈ 12.4MB
```
