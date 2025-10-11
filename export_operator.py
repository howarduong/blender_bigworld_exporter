# -*- coding: utf-8 -*-
# export_operator.py — BigWorld Exporter 核心导出操作符
import bpy
import os
import traceback
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    FloatProperty,
    StringProperty,
)
from bpy_extras.io_utils import ExportHelper

# 引入 core 与 validators
from .core import primitives_writer, visual_writer, model_writer, skeleton_writer, animation_writer
from .validators import path_validator, structure_checker, hex_diff


# ========== 报告结构 ==========
class ExportReport:
    def __init__(self):
        self.stats = {}
        self.errors = []
        self.warnings = []
        self.validators = {}

    def add_stat(self, key, value):
        self.stats[key] = value

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def add_validator_result(self, name, result):
        self.validators[name] = result


# ========== 上下文结构 ==========
class ExportContext:
    def __init__(self, operator):
        self.export_root = bpy.path.abspath(operator.export_root)
        self.engine_version = operator.engine_version
        self.coord_mode = operator.coord_mode
        self.default_scale = operator.default_scale
        self.apply_scale = operator.apply_scale
        self.verbose_log = operator.verbose_log

        self.export_type = operator.export_type
        self.export_range = operator.export_range

        self.options = {
            "gen_bsp": operator.gen_bsp,
            "export_hardpoints": operator.export_hardpoints,
            "export_portals": operator.export_portals,
            "gen_tangents": operator.gen_tangents,
            "enable_structure": operator.enable_structure,
            "enable_pathfix": operator.enable_pathfix,
            "enable_hexdiff": operator.enable_hexdiff,
            "hexdiff_max": operator.hexdiff_max,
            "skeleton_rowmajor": operator.skeleton_rowmajor,
            "skeleton_unitscale": operator.skeleton_unitscale,
            "anim_fps": operator.anim_fps,
            "anim_rowmajor": operator.anim_rowmajor,
            "anim_cuetrack": operator.anim_cuetrack,
            "collision_bake": operator.collision_bake,
            "collision_flip": operator.collision_flip,
            "collision_index": operator.collision_index,
            "prefab_rowmajor": operator.prefab_rowmajor,
            "prefab_visibility": operator.prefab_visibility,
        }

        self.report = ExportReport()
        self.objects = []


# ========== 工具函数 ==========
def collect_objects(ctx: ExportContext):
    objs = []
    if ctx.export_range == "ALL":
        objs = [o for o in bpy.context.scene.objects if o.type in {"MESH", "ARMATURE", "EMPTY"}]
    elif ctx.export_range == "SELECTED":
        objs = [o for o in bpy.context.selected_objects if o.type in {"MESH", "ARMATURE", "EMPTY"}]
    elif ctx.export_range == "COLLECTION":
        # 简化：导出当前激活集合
        layer = bpy.context.view_layer.active_layer_collection
        if layer:
            col = layer.collection
            objs = [o for o in col.objects if o.type in {"MESH", "ARMATURE", "EMPTY"}]
    ctx.objects = objs
    return objs


def run_writers(ctx: ExportContext):
    objs = collect_objects(ctx)
    root = ctx.export_root
    os.makedirs(root, exist_ok=True)

    if ctx.export_type == "STATIC":
        primitives_writer.write(ctx, objs)
        visual_writer.write(ctx, objs)

    elif ctx.export_type == "SKINNED":
        primitives_writer.write(ctx, objs)
        visual_writer.write(ctx, objs)
        model_writer.write(ctx, objs)
        skeleton_writer.write(ctx, objs)

    elif ctx.export_type == "ANIM":
        animation_writer.write(ctx, objs)

    elif ctx.export_type == "MODEL":
        model_writer.write(ctx, objs)

    else:
        ctx.report.add_error(f"未知导出类型: {ctx.export_type}")


def run_validators(ctx: ExportContext):
    if ctx.options["enable_pathfix"]:
        result = path_validator.validate_paths(ctx.objects, ctx.export_root, auto_fix=True)
        ctx.report.add_validator_result("PathValidator", result)

    if ctx.options["enable_structure"]:
        result = structure_checker.check_files(ctx.export_root, ctx.export_type)
        ctx.report.add_validator_result("StructureChecker", result)

    if ctx.options["enable_hexdiff"]:
        result = hex_diff.compare_exports(ctx.export_root, ctx.export_type, ctx.options["hexdiff_max"])
        ctx.report.add_validator_result("HexDiff", result)


def format_report(ctx: ExportContext) -> str:
    lines = []
    lines.append("======= 导出报告 =======")
    lines.append(f"导出类型: {ctx.export_type}")
    lines.append(f"导出范围: {ctx.export_range}")
    lines.append(f"导出根目录: {ctx.export_root}")
    lines.append(f"引擎版本: {ctx.engine_version}")
    lines.append(f"坐标系模式: {ctx.coord_mode}")
    lines.append(f"默认缩放: {ctx.default_scale} 应用缩放: {ctx.apply_scale}")
    lines.append("")

    if ctx.report.stats:
        lines.append("统计信息:")
        for k, v in ctx.report.stats.items():
            lines.append(f"  - {k}: {v}")
        lines.append("")

    if ctx.report.validators:
        lines.append("验证器结果:")
        for name, result in ctx.report.validators.items():
            lines.append(f"  [{name}]")
            for rk, rv in result.items():
                if isinstance(rv, list):
                    lines.append(f"    - {rk}: {len(rv)} 项")
                else:
                    lines.append(f"    - {rk}: {rv}")
        lines.append("")

    if ctx.report.warnings:
        lines.append("警告:")
        for w in ctx.report.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    if ctx.report.errors:
        lines.append("错误:")
        for e in ctx.report.errors:
            lines.append(f"  - {e}")
        lines.append("")

    lines.append("========================")
    return "\n".join(lines)


# ========== 导出操作符 ==========
class EXPORT_OT_bigworld(bpy.types.Operator, ExportHelper):
    """BigWorld Exporter"""
    bl_idname = "export_scene.bigworld"
    bl_label = "Export BigWorld"
    bl_options = {'PRESET'}

    filename_ext = ".visual"

    # 导出类型
    export_type: EnumProperty(
        name="导出类型",
        items=[
            ('STATIC', "Static Visual", ""),
            ('SKINNED', "Skinned Visual", ""),
            ('ANIM', "Animation", ""),
            ('MODEL', "Model with Nodes", ""),
        ],
        default='STATIC'
    )

    # 导出范围
    export_range: EnumProperty(
        name="导出范围",
        items=[
            ('ALL', "导出全部对象", ""),
            ('SELECTED', "仅导出选中对象", ""),
            ('COLLECTION', "导出所在集合", ""),
        ],
        default='ALL'
    )

    # 附加选项
    gen_bsp: BoolProperty(name="生成 BSP 碰撞树", default=False)
    export_hardpoints: BoolProperty(name="导出 HardPoints", default=True)
    export_portals: BoolProperty(name="导出 Portals", default=False)
    gen_tangents: BoolProperty(name="生成 Tangents/Normals", default=True)
    enable_structure: BoolProperty(name="启用结构校验", default=True)
    enable_pathfix: BoolProperty(name="启用路径自动修复", default=True)
    enable_hexdiff: BoolProperty(name="启用二进制对比", default=False)
    hexdiff_max: IntProperty(name="最大差异数", default=100, min=1, max=1000)
    verbose_log: BoolProperty(name="输出详细日志", default=False)

    # 高级设置
    skeleton_rowmajor: BoolProperty(
    name="Skeleton 行主序矩阵",
    description="以行主序导出骨骼矩阵（与旧版 Max 插件对齐）",
    default=True
)
    skeleton_unitscale: BoolProperty(
    name="Skeleton 应用单位缩放",
    description="将偏好设置或操作符中的单位缩放应用到骨骼",
    default=True
)

    anim_fps: IntProperty(
    name="Animation FPS",
    description="动画导出帧率",
    default=30, min=1, max=240
)
    anim_rowmajor: BoolProperty(
    name="Animation 行主序矩阵",
    description="以行主序导出动画矩阵（与骨骼行主序一致）",
    default=True
)
    anim_cuetrack: BoolProperty(
    name="启用 CueTrack 导出",
    description="导出动画 CueTrack",
    default=False
)

    collision_bake: BoolProperty(
    name="Collision 烘焙世界矩阵",
    description="将对象世界变换烘焙到碰撞数据",
    default=True
)
    collision_flip: BoolProperty(
    name="Collision 翻转三角缠绕",
    description="在导出碰撞数据时翻转三角形缠绕方向",
    default=False
)
    collision_index: EnumProperty(
    name="索引类型",
    description="碰撞/网格索引类型（与引擎兼容）",
    items=[('U16', "u16", ""), ('U32', "u32", "")],
    default='U16'
)

    prefab_rowmajor: BoolProperty(
    name="Prefab 行主序矩阵",
    description="以行主序导出 Prefab 的相关矩阵",
    default=True
)
    prefab_visibility: BoolProperty(
    name="Prefab 写入可见性标志",
    description="在 Prefab 中写入可见性标志位",
    default=True
)
    # 导出控制
    export_root: StringProperty(name="导出根目录", default="//")
    engine_version: EnumProperty(
        name="引擎版本",
        items=[('V2', "2.x", ""), ('V3', "3.x", "")],
        default='V3'
    )
    coord_mode: EnumProperty(
        name="坐标系模式",
        items=[('YUP', "Y-Up", ""), ('ZUP', "Z-Up", "")],
        default='YUP'
    )
    default_scale: FloatProperty(name="默认缩放", default=1.0, min=0.001, max=100.0)
    apply_scale: BoolProperty(name="应用缩放到几何", default=True)

    def invoke(self, context, event):
        # 可在此处从 AddonPreferences 读取默认值并覆盖空白
        prefs = None
        try:
            addons = bpy.context.preferences.addons
            pkg = __package__ if __package__ else "blender_bigworld_exporter"
            if pkg in addons:
                prefs = addons[pkg].preferences
        except Exception:
            prefs = None

        if prefs:
            # 仅当当前操作符属性为默认时，采用偏好设置值
            if not self.export_root or self.export_root == "//":
                self.export_root = prefs.export_root
            if not self.engine_version:
                self.engine_version = prefs.engine_version
            if not self.coord_mode:
                self.coord_mode = prefs.coord_mode
            # default_scale 若为默认 1.0，且偏好设置不为 1.0，则使用 prefs
            if abs(self.default_scale - 1.0) < 1e-9 and prefs.default_scale != 1.0:
                self.default_scale = prefs.default_scale

            # Validators 默认开关
            self.enable_pathfix = prefs.enable_pathfix
            self.enable_structure = prefs.enable_structure
            self.enable_hexdiff = prefs.enable_hexdiff
            self.hexdiff_max = prefs.hexdiff_max

        return super().invoke(context, event)

    def execute(self, context):
        ctx = ExportContext(self)

        try:
            run_writers(ctx)
            run_validators(ctx)
        except Exception as e:
            ctx.report.add_error(str(e))
            ctx.report.add_error(traceback.format_exc())

        # 汇总报告并写入 Scene，供 UI 展示
        report_text = format_report(ctx)
        bpy.context.scene["bw_export_report"] = report_text

        # 控制台也打印，便于调试
        print(report_text)

        if ctx.report.errors:
            self.report({'ERROR'}, "导出完成，但存在错误。请查看报告。")
        else:
            self.report({'INFO'}, "导出完成。")
        return {'FINISHED'}


# ========== 仅校验操作符（导出前检查） ==========
class EXPORT_OT_bigworld_check(bpy.types.Operator):
    """BigWorld Exporter — 导出前检查（只运行校验，不写文件）"""
    bl_idname = "export_scene.bigworld_check"
    bl_label = "BigWorld Export — Preflight Check"
    bl_options = {'REGISTER'}

    # 为保持与导出操作一致的上下文，我们镜像核心参数（可简化：也可从 Scene/N 面板读取）
    export_root: StringProperty(name="导出根目录", default="//")
    engine_version: EnumProperty(
        name="引擎版本",
        items=[('V2', "2.x", ""), ('V3', "3.x", "")],
        default='V3'
    )
    coord_mode: EnumProperty(
        name="坐标系模式",
        items=[('YUP', "Y-Up", ""), ('ZUP', "Z-Up", "")],
        default='YUP'
    )
    default_scale: FloatProperty(name="默认缩放", default=1.0, min=0.001, max=100.0)
    apply_scale: BoolProperty(name="应用缩放到几何", default=True)
    verbose_log: BoolProperty(name="输出详细日志", default=False)

    export_type: EnumProperty(
        name="导出类型",
        items=[
            ('STATIC', "Static Visual", ""),
            ('SKINNED', "Skinned Visual", ""),
            ('ANIM', "Animation", ""),
            ('MODEL', "Model with Nodes", ""),
        ],
        default='STATIC'
    )

    export_range: EnumProperty(
        name="导出范围",
        items=[
            ('ALL', "导出全部对象", ""),
            ('SELECTED', "仅导出选中对象", ""),
            ('COLLECTION', "导出所在集合", ""),
        ],
        default='ALL'
    )

    # 附加选项与高级设置（与导出操作一致）
    gen_bsp: BoolProperty(name="生成 BSP 碰撞树", default=False)
    export_hardpoints: BoolProperty(name="导出 HardPoints", default=True)
    export_portals: BoolProperty(name="导出 Portals", default=False)
    gen_tangents: BoolProperty(name="生成 Tangents/Normals", default=True)

    enable_structure: BoolProperty(name="启用结构校验", default=True)
    enable_pathfix: BoolProperty(name="启用路径自动修复", default=True)
    enable_hexdiff: BoolProperty(name="启用二进制对比", default=False)
    hexdiff_max: IntProperty(name="最大差异数", default=100, min=1, max=1000)

    skeleton_rowmajor: BoolProperty(name="Skeleton 行主序矩阵", default=True)
    skeleton_unitscale: BoolProperty(name="Skeleton 应用单位缩放", default=True)
    anim_fps: IntProperty(name="Animation FPS", default=30, min=1, max=240)
    anim_rowmajor: BoolProperty(name="Animation 行主序矩阵", default=True)
    anim_cuetrack: BoolProperty(name="启用 CueTrack 导出", default=False)
    collision_bake: BoolProperty(name="Collision 烘焙世界矩阵", default=True)
    collision_flip: BoolProperty(name="Collision 翻转三角缠绕", default=False)
    collision_index: EnumProperty(
        name="索引类型",
        items=[('U16', "u16", ""), ('U32', "u32", "")],
        default='U16'
    )
    prefab_rowmajor: BoolProperty(name="Prefab 行主序矩阵", default=True)
    prefab_visibility: BoolProperty(name="Prefab 写入可见性标志", default=True)

    def invoke(self, context, event):
        # 从 AddonPreferences 提供默认值
        try:
            addons = bpy.context.preferences.addons
            pkg = __package__ if __package__ else "blender_bigworld_exporter"
            if pkg in addons:
                prefs = addons[pkg].preferences
                self.export_root = prefs.export_root
                self.engine_version = prefs.engine_version
                self.coord_mode = prefs.coord_mode
                self.default_scale = prefs.default_scale
        except Exception:
            pass
        return super().invoke(context, event)

    def execute(self, context):
        # 构建上下文，但不写文件，仅运行 validators
        class _DummyOperator:
            pass
        op = _DummyOperator()
        # 填充与 EXPORT_OT_bigworld 相同字段
        op.export_root = self.export_root
        op.engine_version = self.engine_version
        op.coord_mode = self.coord_mode
        op.default_scale = self.default_scale
        op.apply_scale = self.apply_scale
        op.verbose_log = self.verbose_log

        op.export_type = self.export_type
        op.export_range = self.export_range

        op.gen_bsp = self.gen_bsp
        op.export_hardpoints = self.export_hardpoints
        op.export_portals = self.export_portals
        op.gen_tangents = self.gen_tangents

        op.enable_structure = self.enable_structure
        op.enable_pathfix = self.enable_pathfix
        op.enable_hexdiff = self.enable_hexdiff
        op.hexdiff_max = self.hexdiff_max

        op.skeleton_rowmajor = self.skeleton_rowmajor
        op.skeleton_unitscale = self.skeleton_unitscale
        op.anim_fps = self.anim_fps
        op.anim_rowmajor = self.anim_rowmajor
        op.anim_cuetrack = self.anim_cuetrack
        op.collision_bake = self.collision_bake
        op.collision_flip = self.collision_flip
        op.collision_index = self.collision_index
        op.prefab_rowmajor = self.prefab_rowmajor
        op.prefab_visibility = self.prefab_visibility

        ctx = ExportContext(op)

        try:
            # 仅收集对象与运行校验，不写文件（一些校验可能需要文件存在，你们可在 validators 内处理内存缓冲或模拟）
            collect_objects(ctx)
            run_validators(ctx)
        except Exception as e:
            ctx.report.add_error(str(e))
            ctx.report.add_error(traceback.format_exc())

        report_text = format_report(ctx)
        bpy.context.scene["bw_export_report"] = report_text
        print(report_text)

        if ctx.report.errors:
            self.report({'ERROR'}, "检查完成，存在错误。请查看报告。")
        else:
            self.report({'INFO'}, "检查完成。")
        return {'FINISHED'}


# ========== 菜单注册 ==========
def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_bigworld.bl_idname, text="BigWorld Exporter (.visual/.model/.primitives)")


classes = (
    EXPORT_OT_bigworld,
    EXPORT_OT_bigworld_check,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
