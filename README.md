# MirrorTouch

**镜触**  基于 Scrcpy 投屏 + ESP32 串口触控的移动设备镜像控制系统。

通过 PC 端观看手机投屏画面，使用鼠标直接操作，触控指令经 ESP32 串口固件注入手机，实现低延迟、高精度的远程触控体验。

## ✨ 特性

- **Scrcpy 投屏集成**：调用 Scrcpy 实现高清低延迟的手机画面投屏
- **鼠标触控映射**：在投屏画面上直接用鼠标模拟手指触摸操作
- **ESP32 串口通信**：通过串口将触控指令发送至 ESP32 固件
- **多点触控支持**：支持单点/多点触控映射（计划中）
- **跨平台运行**：Windows / Linux / macOS 全平台支持
- **Fluent Design 界面**：基于 PyQt-Fluent-Widgets 的现代化 UI
- **轻量打包**：可打包为独立 exe，无需 Python 环境

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Scrcpy（需单独安装并加
- ESP32 串口固件（已烧录）
- 开启了 USB 调试的 Android 设备

### 安装依赖

```
pip install -r requirements.txt
``` 

### 运行

```
python main.py
```

### 打包为可执行文件

```
pip install pyinstaller
pyinstaller --onefile --windowed --name MirrorTouch main.py
```

## 🏗️ 项目结构

```
MirrorTouch/
├── main.py                     # 程序入口
├── resources/                  # 静态资源（图标、样式、配置）
│   ├── icons/                  # 图标文件
│   ├── styles/                 # QSS 主题样式
│   └── config/                 # 默认配置文件
└── src/                        # 源代码
    ├── ui/                     # 界面层（PyQt-Fluent-Widgets）
    │   ├── main_window.py      # 主窗口
    │   ├── mirror_page.py      # 投屏页面
    │   ├── serial_page.py      # 串口设置页面
    │   ├── overlay.py          # 透明触摸覆盖层
    │   └── widgets/            # 自定义控件
    ├── core/                   # 核心逻辑
    │   ├── serial_bridge.py    # 串口通信
    │   ├── touch_mapper.py     # 坐标映射
    │   ├── scrcpy_launcher.py  # Scrcpy 进程管理
    │   └── config_manager.py   # 配置管理
    └── utils/                  # 工具函数
```

## ⌨️ 串口通信协议

| 位段 | 位宽 | 说明 |
|:---|:---|:---|
| cmd | bits 0-1 | 指令类型（0:点击 1:滑动 2:长按 3:抬起） |
| touchId | bits 2-5 | 触控点 ID |
| x | bits 6-18 | X 坐标 |
| y | bits 19-31 | Y 坐标 |

## 🔌 获取 ESP32 固件

MirrorTouch 需要配合 ESP32 串口固件使用。固件源码及烧录教程不随本仓库开源分发。

如需要获取固件，可通过以下方式支持本项目：

- 🧧 **爱发电支持**：[https://afdian.com/a/uhmmm-xy](https://afdian.com/a/uhmmm-xy)（投喂后可在爱发电私信中获取固件及联系邮箱）

你的支持是我持续开发的动力 ❤️

## 📄 开源协议

本项目基于 **GNU General Public License v3.0 (GPLv3)** 开源。

- 个人使用、学习、研究完全免费
- 分发或修改需继续使用 GPLv3 协议并公开源代码

详见 [LICENSE](./LICENSE) 文件。

## 🙏 致谢

- [Scrcpy](https://github.com/Genymobile/scrcpy) - 优秀的 Android 投屏工具
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) - 精美的 Fluent Design 组件库
- [pyserial](https://github.com/pyserial/pyserial) - Python 串口通信库

## 👤 作者

GitHub: [@uhmmm-xy](https://github.com/uhmmm-xy)
