# -*- coding: utf-8 -*-
import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)


class BigWorldAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ if __package__ else "blender_bigworld_exporter"

    # 全局默认参数（导出根目录、引擎版本、默认缩放、坐标系模式）
    export_root: StringProperty(
        name="导出根目录",
        description="导出文件的根目录，可使用 // 表示相对当前 blend 的路径",
        default="//BigWorldExport"
    )

    engine_version: EnumProperty(
        name="引擎版本",
        description="BigWorld 引擎版本，影响导出格式与兼容性",
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
        description="坐标轴模式：兼容 3ds Max 或 Blender 原生",
        items=[
            ('YUP', "Y-Up", "Y轴向上（与某些旧版工具链兼容）"),
            ('ZUP', "Z-Up", "Z轴向上（Blender 原生）"),
        ],
        default='YUP'
    )

    # Validator 全局开关与参数（作为默认值）
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
        description="HexDiff 对比最多记录的差异数量",
        default=100,
        min=1,
        max=1000
    )

    def draw(self, context):
        layout = self.layout

        # 标题
        col = layout.column()
        col.label(text="BigWorld Exporter 插件偏好设置", icon='PREFERENCES')

        # 全局设置
        box = layout.box()
        box.label(text="导出根目录与版本")
        box.prop(self, "export_root")
        box.prop(self, "engine_version")
        box.prop(self, "coord_mode")

        box = layout.box()
        box.label(text="缩放与默认值")
        box.prop(self, "default_scale")

        # Validator 设置（默认值）
        box = layout.box()
        box.label(text="Validator 默认设置")
        row = box.row()
        row.prop(self, "enable_pathfix")
        row = box.row()
        row.prop(self, "enable_structure")
        row = box.row()
        row.prop(self, "enable_hexdiff")
        if self.enable_hexdiff:
            box.prop(self, "hexdiff_max")


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
