# -*- coding: utf-8 -*-
# ui_panel_n.py — BigWorld Exporter N 面板（完整修复版）
import bpy
from typing import Optional, Any

ADDON_PACKAGE_NAME = __package__ if __package__ else "blender_bigworld_exporter"


def _get_addon_prefs() -> Optional[bpy.types.AddonPreferences]:
    try:
        addons = bpy.context.preferences.addons
        if ADDON_PACKAGE_NAME in addons:
            return addons[ADDON_PACKAGE_NAME].preferences
    except Exception:
        pass
    return None


# -----------------------------
# PropertyGroup 定义所有属性
# -----------------------------
class BigWorldSceneProps(bpy.types.PropertyGroup):
    bw_export_root: bpy.props.StringProperty(
        name="导出根目录",
        default="//BigWorldExport"
    )
    bw_default_scale: bpy.props.FloatProperty(
        name="单位缩放",
        default=1.0
    )
    bw_coord_mode: bpy.props.EnumProperty(
        name="坐标系模式",
        items=[("YUP", "Y Up", ""), ("ZUP", "Z Up", "")]
    )

    # Skeleton
    bw_skeleton_rowmajor: bpy.props.BoolProperty(
        name="行主序矩阵",
        default=True
    )
    bw_skeleton_unitscale: bpy.props.BoolProperty(
        name="应用单位缩放",
        default=True
    )

    # Animation
    bw_anim_fps: bpy.props.IntProperty(
        name="FPS",
        default=30
    )
    bw_anim_rowmajor: bpy.props.BoolProperty(
        name="行主序矩阵",
        default=True
    )
    bw_anim_cuetrack: bpy.props.BoolProperty(
        name="CueTrack 导出",
        default=False
    )

    # Collision
    bw_collision_bake: bpy.props.BoolProperty(
        name="烘焙世界矩阵",
        default=True
    )
    bw_collision_flip: bpy.props.BoolProperty(
        name="翻转缠绕",
        default=False
    )
    bw_collision_index: bpy.props.EnumProperty(
        name="索引类型",
        items=[("U16", "U16", ""), ("U32", "U32", "")],
        default="U16"
    )

    # Prefab
    bw_prefab_rowmajor: bpy.props.BoolProperty(
        name="行主序矩阵",
        default=True
    )
    bw_prefab_visibility: bpy.props.BoolProperty(
        name="写入可见性标志",
        default=True
    )

    # Validator
    bw_enable_pathfix: bpy.props.BoolProperty(
        name="自动修复路径",
        default=True
    )
    bw_enable_structure: bpy.props.BoolProperty(
        name="严格模式 (错误阻断)",
        default=True
    )
    bw_enable_hexdiff: bpy.props.BoolProperty(
        name="启用 HexDiff",
        default=False
    )
    bw_hexdiff_max: bpy.props.IntProperty(
        name="最大差异数",
        default=100
    )

    # 导出报告
    bw_export_report: bpy.props.StringProperty(
        name="导出报告",
        default=""
    )


# -----------------------------
# N 面板定义
# -----------------------------
class VIEW3D_PT_bigworld_exporter(bpy.types.Panel):
    bl_label = "BigWorld Exporter_n 参数面板"
    bl_idname = "VIEW3D_PT_bigworld_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BigWorld"

    def draw(self, context):
        layout = self.layout
        prefs = _get_addon_prefs()
        scene = context.scene.bigworld

        # 全局设置
        box = layout.box()
        box.label(text="全局设置", icon='SCENE_DATA')
        row = box.row(align=True)
        row.prop(scene, "bw_export_root")
        row = box.row(align=True)
        row.prop(scene, "bw_default_scale")
        row = box.row(align=True)
        row.prop(scene, "bw_coord_mode")

        # Writer 设置
        box = layout.box()
        box.label(text="Writer 设置", icon='MODIFIER')
        col = box.column(align=True)

        col.label(text="Skeleton", icon='ARMATURE_DATA')
        col.prop(scene, "bw_skeleton_rowmajor")
        col.prop(scene, "bw_skeleton_unitscale")

        col.label(text="Animation", icon='ACTION')
        col.prop(scene, "bw_anim_fps")
        col.prop(scene, "bw_anim_rowmajor")
        col.prop(scene, "bw_anim_cuetrack")

        col.label(text="Collision", icon='MESH_DATA')
        col.prop(scene, "bw_collision_bake")
        col.prop(scene, "bw_collision_flip")
        col.prop(scene, "bw_collision_index")

        col.label(text="Prefab", icon='OUTLINER_OB_GROUP_INSTANCE')
        col.prop(scene, "bw_prefab_rowmajor")
        col.prop(scene, "bw_prefab_visibility")

        # Validator 设置
        box = layout.box()
        box.label(text="Validator 设置", icon='CHECKMARK')
        col = box.column(align=True)
        col.label(text="PathValidator", icon='FILEBROWSER')
        col.prop(scene, "bw_enable_pathfix")

        col.separator()
        col.label(text="StructureChecker", icon='SEQ_STRIP_META')
        col.prop(scene, "bw_enable_structure")

        col.separator()
        col.label(text="HexDiff", icon='TEXT')
        col.prop(scene, "bw_enable_hexdiff")
        if scene.bw_enable_hexdiff:
            col.prop(scene, "bw_hexdiff_max")

        # 执行控制
        box = layout.box()
        box.label(text="导出控制", icon='EXPORT')
        row = box.row(align=True)
        row.operator("export_scene.bigworld", text="导出")
        row.operator("export_scene.bigworld_check", text="导出前检查")

        # 导出报告
        box = layout.box()
        box.label(text="导出报告", icon='INFO')
        if scene.bw_export_report:
            for line in scene.bw_export_report.splitlines():
                box.label(text=line)
        else:
            box.label(text="暂无报告。执行导出后显示统计与校验结果。", icon='QUESTION')


# -----------------------------
# 清除报告 Operator
# -----------------------------
class VIEW3D_OT_bigworld_clear_report(bpy.types.Operator):
    bl_idname = "view3d.bigworld_clear_report"
    bl_label = "清除 BigWorld 报告"
    bl_description = "清除 Scene 中的导出报告文本"

    def execute(self, context):
        context.scene.bigworld.bw_export_report = ""
        self.report({'INFO'}, "报告已清除")
        return {'FINISHED'}


# -----------------------------
# 注册
# -----------------------------
classes = (
    BigWorldSceneProps,
    VIEW3D_PT_bigworld_exporter,
    VIEW3D_OT_bigworld_clear_report,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bigworld = bpy.props.PointerProperty(type=BigWorldSceneProps)

def unregister():
    del bpy.types.Scene.bigworld
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
