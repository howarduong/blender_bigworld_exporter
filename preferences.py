# 相对路径: preferences.py
# 主要功能: 插件全局设置 (Preferences)，包括:
#   - 导出根目录
#   - 引擎版本 (2.x / 3.x)
#   - 默认缩放
#   - 坐标系模式 (与 3ds Max 兼容 / Blender 原生)
#   - 校验与日志选项 (结构校验/Hex Diff/详细日志)
#
# 注意:
#   - 所有设置需持久化保存，供导出时统一使用。
#   - 字段默认值需与旧 3ds Max 插件保持一致。
#
# 开发前必读参考（每次构建前必须学习研究原 3ds Max 插件代码）:
# BigWorld_MAXScripts GitHub 仓库（宏脚本全集）：
# https://github.com/howarduong/BigWorld_MAXScripts/tree/1b7eb719e475c409afa319877f4550cf5accbafc/BigWorld_MacroScripts

import bpy


class BigWorldAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__  # 使用包名作为 ID

    # 导出根目录
    export_root: bpy.props.StringProperty(
        name="导出根目录",
        subtype='DIR_PATH',
        default=""
    )

    # 引擎版本
    engine_version: bpy.props.EnumProperty(
        name="引擎版本",
        items=[
            ('BW2', "2.x", "BigWorld 2.x"),
            ('BW3', "3.x", "BigWorld 3.x")
        ],
        default='BW3'
    )

    # 默认缩放
    default_scale: bpy.props.FloatProperty(
        name="默认缩放",
        default=1.0,
        min=0.0001,
        max=1000.0
    )

    # 坐标系模式
    coord_mode: bpy.props.EnumProperty(
        name="坐标系模式",
        items=[
            ('MAX_COMPAT', "与3ds Max兼容", "Y-Up → Z-Up"),
            ('BLENDER_NATIVE', "Blender原生", "保持 Blender 坐标系")
        ],
        default='MAX_COMPAT'
    )

    # 校验与日志选项
    enable_struct_check: bpy.props.BoolProperty(
        name="启用结构校验（严格）",
        default=False
    )

    enable_hex_diff: bpy.props.BoolProperty(
        name="启用十六进制差异比对",
        default=False
    )

    enable_verbose_log: bpy.props.BoolProperty(
        name="输出详细日志",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="BigWorld 导出插件 - 全局设置")

        box = layout.box()
        box.label(text="导出路径与版本")
        box.prop(self, "export_root")
        box.prop(self, "engine_version")

        box = layout.box()
        box.label(text="坐标与缩放")
        box.prop(self, "default_scale")
        box.prop(self, "coord_mode")

        box = layout.box()
        box.label(text="校验与日志")
        box.prop(self, "enable_struct_check")
        box.prop(self, "enable_hex_diff")
        box.prop(self, "enable_verbose_log")
