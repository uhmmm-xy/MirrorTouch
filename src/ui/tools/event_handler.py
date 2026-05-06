from typing import Callable, Dict, List
from src.utils.enums import ComponentEvent
from src.ui.tools.base_component import BaseComponent


class EventHandler:
    """事件分发器：管理所有组件的回调注册与分发"""

    def __init__(self):
        self._listeners: Dict[ComponentEvent, List[tuple]] = {
            e: [] for e in ComponentEvent
        }

    def register(self, component: 'BaseComponent', event: ComponentEvent, callback: Callable):
        """为指定组件注册事件回调"""
        cid = id(component)
        self._listeners[event].append((cid, callback))

    def unregister(self, component: 'BaseComponent', event: ComponentEvent = None):
        """取消注册"""
        cid = id(component)
        if event:
            self._listeners[event] = [
                (cid_cb, cb) for (cid_cb, cb) in self._listeners[event] if cid_cb != cid
            ]
        else:
            for e in ComponentEvent:
                self._listeners[e] = [
                    (cid_cb, cb) for (cid_cb, cb) in self._listeners[e] if cid_cb != cid
                ]

    def dispatch(self, component: 'BaseComponent', event: ComponentEvent, *args):
        """分发事件给所有注册了该事件的回调"""
        cid = id(component)
        for cid_cb, callback in self._listeners[event]:
            if cid_cb == cid:
                callback(component, *args)