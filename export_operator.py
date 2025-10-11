# -*- coding: utf-8 -*-
import bpy
import os
import traceback
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    FloatProperty,
    StringProperty,
)
from bpy_extras.io_utils import ExportHelper


# ========== 统一上下文与报告结构 ==========
@dataclass
class ExportReport:
    # 统计信息
    stats: Dict[str, Any] = field(default_factory=dict)
    # 错误与警告
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    # 验证器输出（集中收集）
    validators: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_stat(self, key: str, value: Any):
        self.stats[key] = value

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_validator_result(self, name: str, result: Dict[str, Any]):
        self.validators[name] = result


@dataclass
class ExportContext:
    # 环境配置
    export_root: str
    engine_version: str
    coord_mode: str
    default_scale: float
    apply_scale: bool
    verbose_log: bool

    # 导出类型与范围
    export_type: str
    export_range: str

    # 选项与高级参数
    options: Dict[str, Any] = field(default_factory=dict)

    # 报告
    report: ExportReport = field(default_factory=ExportReport)

    # 导出目标清单（由类型/范围解析得到）
    targets: Dict[str, Any] = field(default_factory=dict)

    # 运行时辅助（如缓存、会话对象等）
    runtime: Dict[str, Any] = field(default_factory=dict)


# ========== 工具函数 ==========
def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def log(ctx: ExportContext, msg: str):
    if ctx.verbose_log:
        print(f"[BigWorld Export] {msg}")


def safe_join(root: str, *parts: str) -> str:
    p = os.path.normpath(os.path.join(root, *parts))
    return p


def normalize_rel(path: str) -> str:
    # Blender 导出对话框常用 // 相对路径
    if path.startswith("//"):
        return bpy.path.abspath(path)
    return path


# ========== 导出类型 → 文件清单解析 ==========
def resolve_export_targets(ctx: ExportContext) -> Dict[str, Any]:
    """
    对齐旧版 Max 插件：
    - Static Visual → .visual + .primitives（静态网格/材质/纹理）
    - Skinned Visual → .visual + .primitives + .model + .skeleton（绑定骨骼）
    - Animation → .animation（针对 Armature/Action）
    - Model with Nodes → .model（包含节点/Portal/占位等）
    """
    t = ctx.export_type
    r = ctx.export_range
    targets: Dict[str, Any] = {
        "export_type": t,
        "export_range": r,
        "files": [],
        "sections": [],
    }

    if t == "STATIC":
        targets["files"] = [".visual", ".primitives"]
        # 附加选项影响的 section（Tangents/Normals、Portals）
        if ctx.options.get("gen_tangents", True):
            targets["sections"].append("TANGENTS")
        if ctx.options.get("export_portals", False):
            targets["sections"].append("PORTALS")
    elif t == "SKINNED":
        targets["files"] = [".visual", ".primitives", ".model", ".skeleton"]
        if ctx.options.get("gen_tangents", True):
            targets["sections"].append("TANGENTS")
        if ctx.options.get("export_hardpoints", True):
            targets["sections"].append("HARDPOINTS")
        if ctx.options.get("export_portals", False):
            targets["sections"].append("PORTALS")
    elif t == "ANIM":
        targets["files"] = [".animation"]
        # Animation 附加项
        if ctx.options.get("anim_cuetrack", False):
            targets["sections"].append("CUETRACK")
    elif t == "MODEL":
        targets["files"] = [".model"]
        if ctx.options.get("export_portals", False):
            targets["sections"].append("PORTALS")
        if ctx.options.get("export_hardpoints", True):
            targets["sections"].append("HARDPOINTS")
    else:
        ctx.report.add_error(f"未知的导出类型: {t}")

    # 范围解析：决定对象集合
    # 这里留出钩子，你可以在后续把集合/选中/全部的对象解析清单写入 ctx.targets
    targets["object_scope"] = r

    return targets


# ========== 验证器统一调用入口（占位，可与你们现有 validators 对接） ==========
def run_validators(ctx: ExportContext):
    """
    统一的验证器入口：
    - PathValidator: 自动修复路径（textures/ 下），不合法时报错或修复
    - StructureChecker: 对 .model/.visual/.primitives 的 section 顺序/长度/对齐进行检查
    - HexDiff: 二进制级别对比（与 Max 插件产物比对）
    """
    # PathValidator
    if ctx.options.get("enable_pathfix", True):
        # TODO: 你们的 validators.path_validator.validate_paths(...)
        # 示例结构化结果：
        result = {
            "fixed": ["textures/default.dds"],
            "errors": [],
            "valid": ["textures/albedo.dds", "textures/normal.dds"]
        }
        ctx.report.add_validator_result("PathValidator", result)

    # StructureChecker
    if ctx.options.get("enable_structure", True):
        # TODO: 调用 validators.structure_checker.check_visual/model/primitives(...)
        result = {
            "errors": [],
            "warnings": ["Section Reserved field mismatch (visual:References)"],
            "sections": ["HEADER", "GEOMETRY", "MATERIALS", "REFERENCES"]
        }
        ctx.report.add_validator_result("StructureChecker", result)

    # HexDiff
    if ctx.options.get("enable_hexdiff", False):
        # TODO: 调用 validators.hex_diff.compare_files(file1, file2, max_diffs=ctx.options["hexdiff_max"])
        result = {
            "same": True,
            "total_diffs": 0,
            "diffs": []
        }
        ctx.report.add_validator_result("HexDiff", result)


# ========== Writers 统一调度入口（占位，可与你们现有 writers 对接） ==========
def run_writers(ctx: ExportContext):
    """
    按照 ctx.targets["files"] 写出对应文件：
    - .primitives / .visual / .model / .skeleton / .animation 等
    - 受附加选项（sections）影响的内容按需写出
    """
    ensure_dir(ctx.export_root)

    files = ctx.targets.get("files", [])
    sections = ctx.targets.get("sections", [])
    engine_version = ctx.engine_version

    log(ctx, f"准备导出: {files}, sections={sections}, engine={engine_version}")

    for fext in files:
        if fext == ".primitives":
            # TODO: 调用你们的 primitives_writer
            # 传递参数示例：
            # primitives_writer.write(ctx=ctx, sections=sections, ...)
            ctx.report.add_stat("primitives_vertices", 12345)
            ctx.report.add_stat("primitives_indices", 27456)
        elif fext == ".visual":
            # TODO: 调用你们的 visual_writer
            ctx.report.add_stat("materials", 8)
            ctx.report.add_stat("textures", 16)
        elif fext == ".model":
            # TODO: 调用你们的 model_writer
            if "PORTALS" in sections:
                ctx.report.add_stat("portals", 3)
            if "HARDPOINTS" in sections:
                ctx.report.add_stat("hardpoints", 5)
        elif fext == ".skeleton":
            # TODO: 调用你们的 skeleton_writer
            # 使用高级设置：
            # rowmajor = ctx.options.get("skeleton_rowmajor", True)
            # unitscale = ctx.options.get("skeleton_unitscale", True)
            ctx.report.add_stat("bones", 42)
        elif fext == ".animation":
            # TODO: 调用你们的 animation_writer
            # anim_fps = ctx.options.get("anim_fps", 30)
            ctx.report.add_stat("animations", 12)
            ctx.report.add_stat("fps", ctx.options.get("anim_fps", 30))
        else:
            ctx.report.add_warning(f"未识别的导出后缀: {fext}")


# ========== 报告格式化 ==========
def format_report(ctx: ExportContext) -> str:
    lines: List[str] = []
    r = ctx.report
    lines.append("======= 导出报告 =======")
    lines.append(f"导出类型: {ctx.export_type}")
    lines.append(f"导出范围: {ctx.export_range}")
    lines.append(f"导出根目录: {ctx.export_root}")
    lines.append(f"引擎版本: {ctx.engine_version}")
    lines.append(f"坐标系模式: {ctx.coord_mode}")
    lines.append(f"默认缩放: {ctx.default_scale} 应用缩放: {ctx.apply_scale}")
    lines.append("")

    if r.stats:
        lines.append("统计信息:")
        for k, v in r.stats.items():
            lines.append(f"  - {k}: {v}")
        lines.append("")

    if r.validators:
        lines.append("验证器结果:")
        for name, result in r.validators.items():
            lines.append(f"  [{name}]")
            # 简要打印
            for rk, rv in result.items():
                # rv 如果是列表/字典，截断显示
                if isinstance(rv, list):
                    lines.append(f"    - {rk}: {len(rv)} 项")
                else:
                    lines.append(f"    - {rk}: {rv}")
        lines.append("")

    if r.warnings:
        lines.append("警告:")
        for w in r.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    if r.errors:
        lines.append("错误:")
        for e in r.errors:
            lines.append(f"  - {e}")
        lines.append("")

    lines.append("========================")
    return "\n".join(lines)


# ========== 导出操作符（第1部分：属性定义与流程框架） ==========
class EXPORT_OT_bigworld(bpy.types.Operator, ExportHelper):
    """BigWorld Exporter"""
    bl_idname = "export_scene.bigworld"
    bl_label = "Export BigWorld"
    bl_options = {'PRESET'}

    filename_ext = ".visual"

    # —— 导出类型 —— 对齐旧版 Max 插件
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

    # —— 导出范围 —— 对齐旧版 Max 插件
    export_range: EnumProperty(
        name="导出范围",
        items=[
            ('ALL', "导出全部对象", ""),
            ('SELECTED', "仅导出选中对象", ""),
            ('COLLECTION', "导出所在集合", ""),
        ],
        default='ALL'
    )

    # —— 附加选项 —— 对齐旧版 Max 插件
    gen_bsp: BoolProperty(name="生成 BSP 碰撞树", default=False)
    export_hardpoints: BoolProperty(name="导出 HardPoints", default=True)
    export_portals: BoolProperty(name="导出 Portals", default=False)
    gen_tangents: BoolProperty(name="生成 Tangents/Normals", default=True)

    # —— Validators 开关与参数 —— 我们新增
    enable_structure: BoolProperty(name="启用结构校验", default=True)
    enable_pathfix: BoolProperty(name="启用路径自动修复", default=True)
    enable_hexdiff: BoolProperty(name="启用二进制对比", default=False)
    hexdiff_max: IntProperty(name="最大差异数", default=100, min=1, max=1000)
    verbose_log: BoolProperty(name="输出详细日志", default=False)

    # —— 高级设置 —— Skeleton/Animation/Collision/Prefab
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

    # —— 导出控制 —— 路径、版本、坐标、缩放
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

    def _build_context(self) -> ExportContext:
        # 统一路径规范
        root_abs = normalize_rel(self.export_root)

        options = {
            # 旧版 Max 附加选项
            "gen_bsp": self.gen_bsp,
            "export_hardpoints": self.export_hardpoints,
            "export_portals": self.export_portals,
            "gen_tangents": self.gen_tangents,
            # 验证器
            "enable_structure": self.enable_structure,
            "enable_pathfix": self.enable_pathfix,
            "enable_hexdiff": self.enable_hexdiff,
            "hexdiff_max": self.hexdiff_max,
            # 高级设置
            "skeleton_rowmajor": self.skeleton_rowmajor,
            "skeleton_unitscale": self.skeleton_unitscale,
            "anim_fps": self.anim_fps,
            "anim_rowmajor": self.anim_rowmajor,
            "anim_cuetrack": self.anim_cuetrack,
            "collision_bake": self.collision_bake,
            "collision_flip": self.collision_flip,
            "collision_index": self.collision_index,
            "prefab_rowmajor": self.prefab_rowmajor,
            "prefab_visibility": self.prefab_visibility,
        }

        ctx = ExportContext(
            export_root=root_abs,
            engine_version=self.engine_version,
            coord_mode=self.coord_mode,
            default_scale=self.default_scale,
            apply_scale=self.apply_scale,
            verbose_log=self.verbose_log,
            export_type=self.export_type,
            export_range=self.export_range,
            options=options,
        )

        # 解析导出目标清单
        ctx.targets = resolve_export_targets(ctx)
        return ctx

    def _export_impl(self, ctx: ExportContext) -> Tuple[bool, str]:
        """
        核心执行流程：
        1) 运行 Writers 写出文件
        2) 运行 Validators 校验一致性
        3) 汇总报告
        """
        try:
            log(ctx, "开始执行导出流程")
            run_writers(ctx)

            log(ctx, "运行校验流程")
            run_validators(ctx)

            report_text = format_report(ctx)
            return True, report_text
        except Exception as e:
            ctx.report.add_error(str(e))
            ctx.report.add_error(traceback.format_exc())
            report_text = format_report(ctx)
            return False, report_text

    def execute(self, context):
        ctx = self._build_context()
        ok, report_text = self._export_impl(ctx)
        if ok:
            self.report({'INFO'}, "导出完成")
        else:
            self.report({'ERROR'}, "导出失败")
        # 将报告打印到控制台，或后续由 ui_panel 显示
        print(report_text)
        return {'FINISHED'}
# ========== 范围解析：对象集合 ==========
def collect_objects_by_range(ctx: ExportContext) -> List[bpy.types.Object]:
    scope = ctx.targets.get("object_scope", "ALL")
    objs: List[bpy.types.Object] = []

    if scope == "ALL":
        # 收集场景中所有导出相关对象（Mesh、Armature 等）
        for obj in bpy.context.scene.objects:
            if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
                objs.append(obj)
    elif scope == "SELECTED":
        for obj in bpy.context.selected_objects:
            if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
                objs.append(obj)
    elif scope == "COLLECTION":
        # 当前激活集合或所有可见集合
        vlayers = bpy.context.view_layer.layer_collection
        # 简化：遍历所有可见集合
        def walk_layers(layer):
            for c in layer.children:
                walk_layers(c)
        # 这里可以根据你们的方案，指定某个集合名称，然后收集该集合内对象
        # 占位简化：使用场景所有对象，并在实际写入时过滤 collection
        for obj in bpy.context.scene.objects:
            if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
                # TODO: 按集合过滤
                objs.append(obj)
    else:
        ctx.report.add_warning(f"未知范围: {scope}, 默认使用 ALL")
        for obj in bpy.context.scene.objects:
            if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
                objs.append(obj)

    log(ctx, f"对象集合({scope}) 数量: {len(objs)}")
    return objs


# ========== Writers 调用深化（示例钩子） ==========
def run_writers(ctx: ExportContext):
    ensure_dir(ctx.export_root)

    files = ctx.targets.get("files", [])
    sections = ctx.targets.get("sections", [])
    engine_version = ctx.engine_version

    objs = collect_objects_by_range(ctx)
    ctx.runtime["objects"] = objs

    log(ctx, f"准备导出: {files}, sections={sections}, engine={engine_version}, objs={len(objs)}")

    for fext in files:
        if fext == ".primitives":
            # 你们的 primitives_writer 接口示例：
            # primitives_writer.write(
            #     objects=objs,
            #     export_root=ctx.export_root,
            #     engine_version=engine_version,
            #     gen_tangents=ctx.options.get("gen_tangents", True),
            #     coord_mode=ctx.coord_mode,
            #     default_scale=ctx.default_scale,
            #     apply_scale=ctx.apply_scale,
            # )
            ctx.report.add_stat("primitives_vertices", 12345)
            ctx.report.add_stat("primitives_indices", 27456)

        elif fext == ".visual":
            # visual_writer.write(
            #     objects=objs,
            #     export_root=ctx.export_root,
            #     engine_version=engine_version,
            #     export_portals=ctx.options.get("export_portals", False),
            #     gen_tangents=ctx.options.get("gen_tangents", True),
            # )
            ctx.report.add_stat("materials", 8)
            ctx.report.add_stat("textures", 16)

        elif fext == ".model":
            # model_writer.write(
            #     objects=objs,
            #     export_root=ctx.export_root,
            #     engine_version=engine_version,
            #     export_portals=ctx.options.get("export_portals", False),
            #     export_hardpoints=ctx.options.get("export_hardpoints", True),
            # )
            if "PORTALS" in sections:
                ctx.report.add_stat("portals", 3)
            if "HARDPOINTS" in sections:
                ctx.report.add_stat("hardpoints", 5)

        elif fext == ".skeleton":
            # skeleton_writer.write(
            #     armatures=[o for o in objs if o.type == "ARMATURE"],
            #     export_root=ctx.export_root,
            #     engine_version=engine_version,
            #     rowmajor=ctx.options.get("skeleton_rowmajor", True),
            #     unitscale=ctx.options.get("skeleton_unitscale", True),
            # )
            ctx.report.add_stat("bones", 42)

        elif fext == ".animation":
            # animation_writer.write(
            #     armatures=[o for o in objs if o.type == "ARMATURE"],
            #     export_root=ctx.export_root,
            #     engine_version=engine_version,
            #     fps=ctx.options.get("anim_fps", 30),
            #     rowmajor=ctx.options.get("anim_rowmajor", True),
            #     cuetrack=ctx.options.get("anim_cuetrack", False),
            # )
            ctx.report.add_stat("animations", 12)
            ctx.report.add_stat("fps", ctx.options.get("anim_fps", 30))

        else:
            ctx.report.add_warning(f"未识别的导出后缀: {fext}")
# ========== Validators 调用深化（示例钩子） ==========
def run_validators(ctx: ExportContext):
    if ctx.options.get("enable_pathfix", True):
        # PathValidator 示例：你们可以按对象材质贴图路径进行检查与修复
        # result = path_validator.validate_paths(objects=ctx.runtime["objects"], root_dir=ctx.export_root, auto_fix=True)
        result = {
            "fixed": ["textures/default.dds"],
            "errors": [],
            "valid": ["textures/albedo.dds", "textures/normal.dds"]
        }
        ctx.report.add_validator_result("PathValidator", result)

    if ctx.options.get("enable_structure", True):
        # StructureChecker 示例：对已写出的文件（或缓冲）进行 schema 校验
        # result_visual = structure_checker.check_visual(file_path=..., strict=True)
        # 这里合并结果展示
        result = {
            "errors": [],
            "warnings": ["Section Reserved field mismatch (visual:References)"],
            "sections": ["HEADER", "GEOMETRY", "MATERIALS", "REFERENCES"]
        }
        ctx.report.add_validator_result("StructureChecker", result)

    if ctx.options.get("enable_hexdiff", False):
        max_diffs = ctx.options.get("hexdiff_max", 100)
        # HexDiff 示例：与 Max 插件产物进行对比（路径需要你们在 ctx.runtime 或 ctx.options 提供参考文件）
        # compare = hex_diff.compare_files(file1=..., file2=..., max_diffs=max_diffs)
        compare = {
            "same": True,
            "total_diffs": 0,
            "diffs": []
        }
        ctx.report.add_validator_result("HexDiff", compare)


# ========== 菜单注册 ==========
def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_bigworld.bl_idname, text="BigWorld Exporter (.visual/.model/.primitives)")


classes = (
    EXPORT_OT_bigworld,
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
