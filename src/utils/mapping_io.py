"""MappingIO — JSON 映射文件读写工具

从 ScreenComponent 提取，纯数据转换，不依赖任何 UI。
支持 mirrorTouch 原生格式和 Scrcpy 兼容格式。
"""

from src.utils.widgets_data import WidgetsData, WidgetType


class MappingIO:
    """映射文件加载/导出

    ScreenComponent 调用示例:
        result = MappingIO.load(json_data)
        screen.screen_width = result['width']
        screen.screen_height = result['height']
        ...
        for data in result['widgets_data']:
            screen.add_widget(screen._create_widget(data))

        json_out = MappingIO.export(screen, widgets)
    """

    FORMAT_IDENTIFIER = "mirrorTouch"
    DEFAULT_WIDTH = 2400
    DEFAULT_HEIGHT = 1080

    # ── 加载 ──

    @classmethod
    def load(cls, json_data: dict) -> dict:
        """解析 JSON → 统一结果字典

        Returns:
            {
                'width': int,
                'height': int,
                'mouse_move_start': (float, float) | None,
                'mouse_move_speed_x': float,
                'mouse_move_speed_y': float,
                'widgets_data': list[WidgetsData],
            }
        """
        if json_data.get(cls.FORMAT_IDENTIFIER) is True:
            return cls._load_mirror_format(json_data)
        return cls._load_scrcpy_format(json_data)

    @classmethod
    def _load_mirror_format(cls, json_data: dict) -> dict:
        result = cls._parse_screen_info(json_data)
        result['widgets_data'] = [
            WidgetsData.from_dict(item)
            for item in json_data.get("widgets", [])
        ]
        return result

    @classmethod
    def _load_scrcpy_format(cls, json_data: dict) -> dict:
        result = cls._parse_screen_info(json_data)
        widgets_data = []
        for node in json_data.get("keyMapNodes", []):
            ntype = node.get("type", "")
            if ntype == "KMT_STEER_WHEEL":
                data = cls._parse_scrcpy_joystick(node)
            elif ntype == "KMT_CLICK":
                data = cls._parse_scrcpy_click(node)
            else:
                continue
            widgets_data.append(data)
        result['widgets_data'] = widgets_data
        return result

    @classmethod
    def _parse_screen_info(cls, json_data: dict) -> dict:
        mm = json_data.get("mouseMoveMap", {})
        return {
            'width': json_data.get("width", cls.DEFAULT_WIDTH),
            'height': json_data.get("height", cls.DEFAULT_HEIGHT),
            'mouse_move_start': (
                (mm.get("startPos", {}).get("x", 0.5),
                 mm.get("startPos", {}).get("y", 0.5))
                if mm else None
            ),
            'mouse_move_speed_x': mm.get("speedRatioX", 1.0) if mm else 1.0,
            'mouse_move_speed_y': mm.get("speedRatioY", 1.0) if mm else 1.0,
        }

    @staticmethod
    def _parse_scrcpy_joystick(node: dict) -> WidgetsData:
        pos = node.get("centerPos", {})
        key_str = "|".join([
            node.get("upKey", "Key_W"),
            node.get("downKey", "Key_S"),
            node.get("leftKey", "Key_A"),
            node.get("rightKey", "Key_D"),
        ])
        data = WidgetsData(
            key=key_str,
            comment=node.get("comment", "摇杆"),
            switch_map=node.get("switchMap", False),
            widget_type=WidgetType.JOYSTICK,
            pos_x=pos.get("x", 0.17), pos_y=pos.get("y", 0.77),
            scale_size=0.08,
        )
        data.turbo_key = node.get("upKey", "")
        data.turbo_offset = node.get("upOffset", 0.2)
        return data

    @staticmethod
    def _parse_scrcpy_click(node: dict) -> WidgetsData:
        pos = node.get("pos", {})
        return WidgetsData(
            key=node.get("key", ""),
            comment=node.get("comment", ""),
            switch_map=node.get("switchMap", False),
            widget_type=WidgetType.CLICK,
            pos_x=pos.get("x", 0), pos_y=pos.get("y", 0),
            scale_size=0.025,
        )

    # ── 导出 ──

    @staticmethod
    def export(screen_width: int, screen_height: int,
               mouse_move_start, mouse_move_speed_x: float,
               mouse_move_speed_y: float,
               widgets: list) -> dict:
        """导出为 mirrorTouch 格式 JSON"""
        return {
            MappingIO.FORMAT_IDENTIFIER: True,
            "width": screen_width,
            "height": screen_height,
            "mouseMoveMap": {
                "startPos": {
                    "x": mouse_move_start[0] if mouse_move_start else 0.5,
                    "y": mouse_move_start[1] if mouse_move_start else 0.5,
                },
                "speedRatioX": mouse_move_speed_x,
                "speedRatioY": mouse_move_speed_y,
            },
            "widgets": [w.data.to_dict() for w in widgets],
        }
