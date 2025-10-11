# -*- coding: utf-8 -*-
bl_info = {
    "name": "BigWorld Exporter",
    "author": "Your Team",
    "version": (1, 0, 0),
    "blender": (4, 5, 3),
    "location": "File > Export > BigWorld Exporter",
    "description": "Export BigWorld assets (.visual, .model, .primitives, .skeleton, .animation) "
                   "with validators and advanced options, aligned with legacy 3ds Max plugin.",
    "category": "Import-Export",
}

import bpy

# 导入子模块
from . import preferences
from . import ui_panel          # N 面板（3D 视图侧边栏）
from . import ui_panel_export   # 导出对话框右侧面板
from . import export_operator   # 核心导出操作符

# 如果未来有更多模块（如 ui_panel_n.py），也可以在这里统一导入
modules = (
    preferences,
    ui_panel,
    ui_panel_export,
    export_operator,
)


def register():
    for m in modules:
        if hasattr(m, "register"):
            m.register()


def unregister():
    for m in reversed(modules):
        if hasattr(m, "unregister"):
            m.unregister()
