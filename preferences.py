# -*- coding: utf-8 -*-
# preferences.py — BigWorld Exporter 插件偏好设置（完整不省略）
import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

ADDON_PACKAGE_NAME = __package__ if __package__ else "blender_bigworld_exporter"


class BigWorldAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_PACKAGE_NAME

    # 全局默认参数（导出根目录、引擎版本、默认缩放、坐标系模式）
    export_root: StringProperty(
        name="导出根目录",
        description="导出文件根目录，支持 // 相对当前 .blend 的路径",
        default="//BigWorldExport"
    )

    engine_version: EnumProperty(
        name="引擎版本",
        description="BigWorld 引擎版本（影响导出格式与兼容性）",
        items=[
            ('V2', "2.x", "BigWorld 2.x"),
            ('V3', "3.x", "BigWorld 3.x")
        ],
        default='V3'
    )

    default_scale: FloatProperty(
        name="默认单位缩放",
        description="导出时对几何的统一缩放倍数",
        default=1.0,
        min=0.001,
        max=100.0
    )

    coord_mode: EnumProperty(
        name="坐标系模式",
        description="坐标模式：Y-Up（与旧版工具链兼容）或 Z-Up（Blender 原生）",
        items=[
            ('YUP', "Y-Up", "Y轴向上（与旧版工具链兼容）"),
            ('ZUP', "Z-Up", "Z轴向上（Blender 原生）"),
        ],
        default='YUP'
    )

    # Validator 默认开关与参数
    enable_pathfix: BoolProperty(
        name="启用路径自动修复 (PathValidator)",
        default=True
    )

    enable_structure: BoolProperty(
        name="启用结构校验 (StructureChecker)",
        default=True
    )

    enable_hexdiff: BoolProperty(
        name="启用二进制对比 (HexDiff)",
        default=False
    )

    hexdiff_max: IntProperty(
        name="最大差异数",
        description="HexDiff 比对最多记录的差异数量",
        default=100,
        min=1,
        max=1000
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="BigWorld Exporter 插件偏好设置", icon='PREFERENCES')

        box = layout.box()
        box.label(text="导出根目录与版本")
        box.prop(self, "export_root")
        box.prop(self, "engine_version")
        box.prop(self, "coord_mode")

        box2 = layout.box()
        box2.label(text="缩放与默认值")
        box2.prop(self, "default_scale")

        box3 = layout.box()
        box3.label(text="Validator 默认设置")
        row = box3.row()
        row.prop(self, "enable_pathfix")
        row = box3.row()
        row.prop(self, "enable_structure")
        row = box3.row()
        row.prop(self, "enable_hexdiff")
        if self.enable_hexdiff:
            box3.prop(self, "hexdiff_max")


# 注册/卸载
classes = (
    BigWorldAddonPreferences,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
