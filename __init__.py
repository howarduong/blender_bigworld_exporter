# -*- coding: utf-8 -*-
bl_info = {
    "name": "BigWorld Exporter",
    "author": "Your Team",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),  # 支持 Blender 4.5+
    "location": "File > Export > BigWorld Exporter",
    "description": "Export BigWorld assets (.visual, .model, .primitives, .skeleton, .animation) "
                   "with validators and advanced options, aligned with legacy 3ds Max plugin.",
    "category": "Import-Export",
}

import bpy

# 导入子模块
from . import preferences
from . import ui_panel          # 对象级参数面板（N 面板）
from . import ui_panel_export   # 场景级导出对话框
from . import export_operator   # 核心导出操作符

modules = [
    preferences,
    ui_panel,
    ui_panel_export,
    export_operator,
]

def register():
    for m in modules:
        try:
            if hasattr(m, "register"):
                m.register()
        except Exception as e:
            print(f"[BigWorld Exporter] 模块 {m.__name__} 注册失败: {e}")

def unregister():
    for m in reversed(modules):
        try:
            if hasattr(m, "unregister"):
                m.unregister()
        except Exception as e:
            print(f"[BigWorld Exporter] 模块 {m.__name__} 注销失败: {e}")
