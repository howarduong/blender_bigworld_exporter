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

# ========== 属性组定义 ==========
class BigWorldObjectSettingsV2(bpy.types.PropertyGroup):
    # 用于 UI 列表的索引属性
    bw_material_slot_map_index: bpy.props.IntProperty(
        name="Material Slot Map Index",
        default=0
    )
    bw_animation_events_index: bpy.props.IntProperty(
        name="Animation Events Index",
        default=0
    )


# ========== 注册 / 注销 ==========
def register():
    # 注册属性组并挂到 Object
    bpy.utils.register_class(BigWorldObjectSettingsV2)
    bpy.types.Object.bigworld_settings = bpy.props.PointerProperty(type=BigWorldObjectSettingsV2)

    # 注册子模块
    for m in modules:
        try:
            if hasattr(m, "register"):
                m.register()
        except Exception as e:
            print(f"[BigWorld Exporter] 模块 {m.__name__} 注册失败: {e}")

    # 注册导出菜单
    from .export_operator import BW_OT_Export, menu_func_export
    bpy.utils.register_class(BW_OT_Export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    # 移除导出菜单
    from .export_operator import BW_OT_Export, menu_func_export
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(BW_OT_Export)

    # 注销子模块
    for m in reversed(modules):
        try:
            if hasattr(m, "unregister"):
                m.unregister()
        except Exception as e:
            print(f"[BigWorld Exporter] 模块 {m.__name__} 注销失败: {e}")

    # 注销属性组
    del bpy.types.Object.bigworld_settings
    bpy.utils.unregister_class(BigWorldObjectSettingsV2)
