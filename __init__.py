# -*- coding: utf-8 -*-
bl_info = {
    "name": "BigWorld Exporter",
    "author": "Your Team",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "File > Export > BigWorld Exporter",
    "description": "Export BigWorld assets (.visual, .model, .primitives, .skeleton, .animation) with validators and advanced options, aligned with legacy 3ds Max plugin.",
    "category": "Import-Export",
}

import bpy
from . import preferences
from . import ui_panel
from . import ui_panel_export
from . import export_operator

modules = [preferences, ui_panel, ui_panel_export, export_operator]


class BigWorldObjectSettingsV2(bpy.types.PropertyGroup):
    bw_material_slot_map: bpy.props.CollectionProperty(type=ui_panel.BigWorldMaterialSlotItem)
    bw_material_slot_map_index: bpy.props.IntProperty(name="Material Slot Map Index", default=0, min=0)
    bw_animation_events: bpy.props.CollectionProperty(type=ui_panel.BigWorldAnimationEventItem)
    bw_animation_events_index: bpy.props.IntProperty(name="Animation Events Index", default=0, min=0)


def register():
    # 先注册子模块，确保 ui_panel 中的集合项类已注册
    for m in modules:
        try:
            if hasattr(m, "register"):
                m.register()
        except Exception as e:
            print(f"[BigWorld Exporter] 模块 {m.__name__} 注册失败: {e}")

    # 注册集中式对象级设置并挂载到 Object
    bpy.utils.register_class(BigWorldObjectSettingsV2)
    bpy.types.Object.bw_settings_v2 = bpy.props.PointerProperty(type=BigWorldObjectSettingsV2)

    # 导出菜单挂载（若存在）
    try:
        from .export_operator import menu_func_export
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    except Exception as e:
        print(f"[BigWorld Exporter] 导出菜单挂载失败: {e}")


def unregister():
    # 移除导出菜单（若存在）
    try:
        from .export_operator import menu_func_export
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    except Exception:
        pass

    # 注销集中式对象级设置
    if hasattr(bpy.types.Object, "bw_settings_v2"):
        del bpy.types.Object.bw_settings_v2
    try:
        bpy.utils.unregister_class(BigWorldObjectSettingsV2)
    except Exception:
        pass

    # 反向注销子模块
    for m in reversed(modules):
        try:
            if hasattr(m, "unregister"):
                m.unregister()
        except Exception as e:
            print(f"[BigWorld Exporter] 模块 {m.__name__} 注销失败: {e}")
