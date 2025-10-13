# File: ./preferences.py
# Relative path: blender_bigworld_exporter/preferences.py
# 功能描述:
# 本文件严格对齐《BigWorld Blender Exporter 最终定版方案》的“插件偏好设置”板块，实现 AddonPreferences。
# 该面板用于定义项目级默认行为（项目路径、默认导出路径、坐标模式、默认缩放、日志等级、默认校验开关），为导出会话提供初始值。
# 字段命名、类型、默认值与 Max 插件字段保持一一映射关系。偏好设置不直接执行导出，仅为 ui_panel_export.py 的会话级参数提供默认源。
# 关联依赖与核心：
# - 导出入口: export_operator.py 在执行时优先读取 Scene.bw_export_v2，若为空或未设置，回退到 AddonPreferences 的默认值。
# - 核心工具: core/utils.py 的坐标转换与缩放策略参考此偏好设置，确保与 Max 插件对齐。
# - 验证工具: validators/* 的默认开关状态参考此偏好设置（严格结构校验、Hex Diff、路径修复、保存报告）。

import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    StringProperty
)


class BigWorldAddonPreferences(AddonPreferences):
    bl_idname = __package__ if __package__ else "blender_bigworld_exporter"

    # —— 项目路径与默认导出路径（与会话级字段对应）——
    project_root: StringProperty(
        name="项目根目录",
        description="项目根目录（用于相对路径解析与资源定位）",
        subtype='DIR_PATH',
        default=""
    )
    default_export_path: StringProperty(
        name="默认导出目录",
        description="默认导出路径（会话级未设置时使用）",
        subtype='DIR_PATH',
        default=""
    )

    # —— 坐标与缩放（与 Max 插件对齐）——
    coordinate_system: EnumProperty(
        name="坐标模式",
        description="默认坐标模式（与 Max 兼容 / Blender 原生）",
        items=[
            ("MAX_COMPAT", "与 Max 兼容", ""),
            ("BLENDER_NATIVE", "Blender 原生", "")
        ],
        default="MAX_COMPAT"
    )
    default_scale: FloatProperty(
        name="默认缩放",
        description="默认单位缩放（与 Max 插件对齐）",
        default=1.0,
        min=0.0001
    )

    # —— 默认导出行为（校验与日志）——
    enable_structure_check: BoolProperty(
        name="默认启用结构校验（严格）",
        description="默认启用导出前后结构校验",
        default=True
    )
    enable_hex_diff: BoolProperty(
        name="默认启用 Hex 对比",
        description="默认启用逐字节对比",
        default=True
    )
    enable_path_fix: BoolProperty(
        name="默认启用路径自动修复",
        description="默认启用路径自动修复（将记录到报告）",
        default=False
    )
    save_report: BoolProperty(
        name="默认保存报告",
        description="默认以文件形式保存导出与校验报告",
        default=True
    )
    log_level: EnumProperty(
        name="日志等级",
        description="默认日志输出等级",
        items=[
            ("INFO", "Info", ""),
            ("DEBUG", "Debug", ""),
            ("ERROR", "Error", "")
        ],
        default="INFO"
    )

    def draw(self, context):
        layout = self.layout

        # ▶ 项目路径
        box_proj = layout.box()
        box_proj.label(text="BigWorld 插件设置")
        col_proj = box_proj.column(align=True)
        col_proj.label(text="项目路径")
        col_proj.prop(self, "project_root")
        col_proj.prop(self, "default_export_path")

        # ▶ 坐标与缩放
        box_coord = layout.box()
        box_coord.label(text="坐标与缩放")
        col_coord = box_coord.column(align=True)
        col_coord.prop(self, "coordinate_system")
        col_coord.prop(self, "default_scale")

        # ▶ 默认导出行为
        box_beh = layout.box()
        box_beh.label(text="默认导出行为")
        col_beh = box_beh.column(align=True)
        col_beh.prop(self, "enable_structure_check")
        col_beh.prop(self, "enable_hex_diff")
        col_beh.prop(self, "enable_path_fix")
        col_beh.prop(self, "save_report")
        col_beh.prop(self, "log_level")


def register():
    bpy.utils.register_class(BigWorldAddonPreferences)


def unregister():
    bpy.utils.unregister_class(BigWorldAddonPreferences)
