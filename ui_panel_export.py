# -*- coding: utf-8 -*-
# ui_panel_export.py — BigWorld Exporter 导出对话框右侧面板
import bpy

class EXPORT_PT_bigworld(bpy.types.Panel):
    bl_label = "BigWorld Exporter 导出面板"
    bl_idname = "EXPORT_PT_bigworld"
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        op = getattr(context.space_data, "active_operator", None)
        if not op:
            return False
        return op.bl_idname in {"EXPORT_SCENE_OT_bigworld", "export_scene.bigworld"}

    def draw(self, context):
        layout = self.layout
        op = context.space_data.active_operator

        # 导出类型
        box = layout.box()
        box.label(text="导出类型 Export Type", icon='EXPORT')
        box.prop(op, "export_type", expand=True)

        # 导出范围
        box = layout.box()
        box.label(text="导出范围 Export Range", icon='RESTRICT_SELECT_OFF')
        box.prop(op, "export_range", expand=True)

        # 附加选项
        box = layout.box()
        box.label(text="附加选项 Additional Options", icon='PREFERENCES')
        box.prop(op, "gen_bsp")
        box.prop(op, "export_hardpoints")
        box.prop(op, "export_portals")
        box.prop(op, "gen_tangents")
        box.prop(op, "enable_structure")
        box.prop(op, "enable_pathfix")
        box.prop(op, "enable_hexdiff")
        if op.enable_hexdiff:
            box.prop(op, "hexdiff_max")
        box.prop(op, "verbose_log")

        # 高级设置
        box = layout.box()
        box.label(text="高级设置 Advanced Settings", icon='SETTINGS')
        col = box.column(align=True)
        col.label(text="Skeleton")
        col.prop(op, "skeleton_rowmajor")
        col.prop(op, "skeleton_unitscale")

        col.label(text="Animation")
        col.prop(op, "anim_fps")
        col.prop(op, "anim_rowmajor")
        col.prop(op, "anim_cuetrack")

        col.label(text="Collision")
        col.prop(op, "collision_bake")
        col.prop(op, "collision_flip")
        col.prop(op, "collision_index")

        col.label(text="Prefab")
        col.prop(op, "prefab_rowmajor")
        col.prop(op, "prefab_visibility")

        # 导出控制
        box = layout.box()
        box.label(text="导出控制 Export Control", icon='FILE_FOLDER')
        box.prop(op, "export_root")
        box.prop(op, "engine_version")
        box.prop(op, "coord_mode")
        box.prop(op, "default_scale")
        box.prop(op, "apply_scale")

        row = box.row(align=True)
        row.operator("export_scene.bigworld", text="导出")
        row.operator("export_scene.bigworld_check", text="导出前检查")

        # 导出报告
        box = layout.box()
        box.label(text="导出报告 Export Report", icon='INFO')
        report_text = bpy.context.scene.get("bw_export_report", "")
        if report_text:
            for line in report_text.splitlines():
                box.label(text=line)
        else:
            box.label(text="暂无报告，请先执行导出", icon='QUESTION')


classes = (
    EXPORT_PT_bigworld,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
