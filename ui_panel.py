# -*- coding: utf-8 -*-
# ui_panel_n.py — BigWorld Exporter N 面板（完整不省略）
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


class VIEW3D_PT_bigworld_exporter(bpy.types.Panel):
    bl_label = "BigWorld Exporter"
    bl_idname = "VIEW3D_PT_bigworld_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BigWorld"

    def draw(self, context):
        layout = self.layout
        prefs = _get_addon_prefs()

        # 通过场景属性缓存一份 “当前会话参数”，避免 N 面板与导出对话框冲突
        scene = context.scene

        # 当前操作符可能不存在（非导出对话框），N 面板使用 Scene 层的属性或偏好设置作为展示与编辑入口
        # 如果你们已有 PropertyGroup，可替换为正式的 Scene 属性组
        # 简易映射：读取/写入 Scene 自定义属性（字符串、数值），并由 Operator 在执行时合并

        # 全局设置
        box = layout.box()
        box.label(text="全局设置", icon='SCENE_DATA')
        row = box.row(align=True)
        row.prop(scene, '["bw_export_root"]', text="导出根目录")
        if 'bw_export_root' not in scene:
            scene['bw_export_root'] = prefs.export_root if prefs else "//BigWorldExport"

        row = box.row(align=True)
        row.prop(scene, '["bw_default_scale"]', text="单位缩放")
        if 'bw_default_scale' not in scene:
            scene['bw_default_scale'] = prefs.default_scale if prefs else 1.0

        row = box.row(align=True)
        # 坐标系模式用文本选择（为简化 N 面板输入），Operator 合并时转换
        row.prop(scene, '["bw_coord_mode"]', text="坐标系模式")
        if 'bw_coord_mode' not in scene:
            scene['bw_coord_mode'] = prefs.coord_mode if prefs else "YUP"

        # Writer 设置
        box = layout.box()
        box.label(text="Writer 设置", icon='MODIFIER')
        col = box.column(align=True)
        # Skeleton
        col.label(text="Skeleton", icon='ARMATURE_DATA')
        col.prop(scene, '["bw_skeleton_rowmajor"]', text="行主序矩阵")
        col.prop(scene, '["bw_skeleton_unitscale"]', text="应用单位缩放")
        if 'bw_skeleton_rowmajor' not in scene: scene['bw_skeleton_rowmajor'] = True
        if 'bw_skeleton_unitscale' not in scene: scene['bw_skeleton_unitscale'] = True

        col.label(text="Animation", icon='ANIMATION')
        col.prop(scene, '["bw_anim_fps"]', text="FPS")
        col.prop(scene, '["bw_anim_rowmajor"]', text="行主序矩阵")
        col.prop(scene, '["bw_anim_cuetrack"]', text="CueTrack 导出")
        if 'bw_anim_fps' not in scene: scene['bw_anim_fps'] = 30
        if 'bw_anim_rowmajor' not in scene: scene['bw_anim_rowmajor'] = True
        if 'bw_anim_cuetrack' not in scene: scene['bw_anim_cuetrack'] = False

        col.label(text="Collision", icon='MESH_DATA')
        col.prop(scene, '["bw_collision_bake"]', text="烘焙世界矩阵")
        col.prop(scene, '["bw_collision_flip"]', text="翻转缠绕")
        col.prop(scene, '["bw_collision_index"]', text="索引类型 (U16/U32)")
        if 'bw_collision_bake' not in scene: scene['bw_collision_bake'] = True
        if 'bw_collision_flip' not in scene: scene['bw_collision_flip'] = False
        if 'bw_collision_index' not in scene: scene['bw_collision_index'] = "U16"

        col.label(text="Prefab", icon='OUTLINER_OB_GROUP_INSTANCE')
        col.prop(scene, '["bw_prefab_rowmajor"]', text="行主序矩阵")
        col.prop(scene, '["bw_prefab_visibility"]', text="写入可见性标志")
        if 'bw_prefab_rowmajor' not in scene: scene['bw_prefab_rowmajor'] = True
        if 'bw_prefab_visibility' not in scene: scene['bw_prefab_visibility'] = True

        # Validator 设置
        box = layout.box()
        box.label(text="Validator 设置", icon='CHECKMARK')
        col = box.column(align=True)
        col.label(text="PathValidator", icon='FILEBROWSER')
        col.prop(scene, '["bw_enable_pathfix"]', text="自动修复路径")
        if 'bw_enable_pathfix' not in scene: scene['bw_enable_pathfix'] = prefs.enable_pathfix if prefs else True

        col.separator()
        col.label(text="StructureChecker", icon='SEQ_STRIP_META')
        col.prop(scene, '["bw_enable_structure"]', text="严格模式 (错误阻断)")
        if 'bw_enable_structure' not in scene: scene['bw_enable_structure'] = prefs.enable_structure if prefs else True

        col.separator()
        col.label(text="HexDiff", icon='TEXT')
        col.prop(scene, '["bw_enable_hexdiff"]', text="启用")
        if 'bw_enable_hexdiff' not in scene: scene['bw_enable_hexdiff'] = prefs.enable_hexdiff if prefs else False
        if scene.get("bw_enable_hexdiff", False):
            col.prop(scene, '["bw_hexdiff_max"]', text="最大差异数")
            if 'bw_hexdiff_max' not in scene: scene['bw_hexdiff_max'] = prefs.hexdiff_max if prefs else 100

        # 执行控制（N 面板直接触发 Operator）
        box = layout.box()
        box.label(text="导出控制", icon='EXPORT')
        row = box.row(align=True)
        row.operator("export_scene.bigworld", text="导出")
        row.operator("export_scene.bigworld_check", text="导出前检查")

        # 导出报告
        box = layout.box()
        box.label(text="导出报告", icon='INFO')
        report_text = scene.get("bw_export_report", "")
        if report_text:
            for line in report_text.splitlines():
                box.label(text=line)
        else:
            box.label(text="暂无报告。执行导出后显示统计与校验结果。", icon='QUESTION')


# 可选：将 N 面板对应的 Scene 字段重置的 Operator（便于清理状态）
class VIEW3D_OT_bigworld_clear_report(bpy.types.Operator):
    bl_idname = "view3d.bigworld_clear_report"
    bl_label = "清除 BigWorld 报告"
    bl_description = "清除 Scene 中的导出报告文本"

    def execute(self, context):
        if "bw_export_report" in context.scene:
            del context.scene["bw_export_report"]
        self.report({'INFO'}, "报告已清除")
        return {'FINISHED'}


classes = (
    VIEW3D_PT_bigworld_exporter,
    VIEW3D_OT_bigworld_clear_report,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
