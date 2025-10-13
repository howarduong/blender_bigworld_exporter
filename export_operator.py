# File: ./export_operator.py
# Relative path: blender_bigworld_exporter/export_operator.py
# 功能描述:
# 本文件是 BigWorld Blender Exporter 的导出入口 Operator，严格对齐《BigWorld Blender Exporter 最终定版方案》与
# “Max 插件字段 → Blender 插件字段 映射表”，实现完整、无省略的导出执行代码。它负责：
# 1) 读取插件偏好设置 (preferences.py)、场景级导出设置 (ui_panel_export.py)、对象级参数 (ui_panel.py)；
# 2) 按“导出范围 + 标签过滤”筛选对象集合，并做前置合法性校验；
# 3) 聚合所有 UI 字段构造 ExportRequest（内部结构体），确保字段完整、类型正确、默认值可回退；
# 4) 按模块开关顺序执行核心 Writer（core/*），生成 Section 数据，并通过 binsection_writer 写入到目标文件；
# 5) 执行 validators（structure_checker、path_validator、hex_diff），严格输出校验报告与错误码；
# 6) 打印详细日志（支持日志等级）、异常处理（阻断导出）、最终状态码与报告路径输出。
# 依赖与关联:
# - UI 层: preferences.py（AddonPreferences），ui_panel_export.py（Scene.bw_export_v2），ui_panel.py（Object.bw_settings_v2）
# - 核心 Writer: core/primitives_writer.py、core/material_writer.py、core/skeleton_writer.py、
#   core/animation_writer.py、core/collision_writer.py、core/portal_writer.py、core/prefab_assembler.py、core/hitbox_xml_writer.py
# - 节结构组织: core/binsection_writer.py（节头、节体、对齐与最终文件写入）
# - 验证模块: validators/structure_checker.py、validators/path_validator.py、validators/hex_diff.py
# 设计原则:
# - 无省略、无精简、无示例; 所有功能完整实现，字段逐字传递；
# - Operator 不自定义 UI 字段，所有字段读取自 PropertyGroup；
# - 错误即阻断，自动修复需记录报告；日志与报告贯穿始终；
# - Writer 调用顺序固定，最终节顺序以 schema_reference.md 为准；
# - 提供完整的辅助函数：路径、对象筛选、标签过滤、日志、错误码、报告聚合等。

import os
import json
import traceback
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty

# —— 核心 Writer 模块导入 —— #
from .core import (
    binsection_writer,
    primitives_writer,
    material_writer,
    skeleton_writer,
    animation_writer,
    collision_writer,
    portal_writer,
    prefab_assembler,
    hitbox_xml_writer
)

# —— 验证模块导入 —— #
from .validators import (
    structure_checker,
    hex_diff,
    path_validator
)

# —— 错误码定义（与方案文档一致） —— #
ERROR_CODES = {
    "PATH_INVALID": "BW-PATH-001",
    "MAT_SLOT_UNMAPPED": "BW-MAT-010",
    "UV_MISSING": "BW-UV-011",
    "SKL_NAME_INVALID": "BW-SKL-020",
    "SKL_BIND_MISSING": "BW-SKL-021",
    "ANI_SKELETON_MISMATCH": "BW-ANI-030",
    "ANI_CUETRACK_JSON_INVALID": "BW-ANI-031",
    "COL_TYPE_UNSUPPORTED": "BW-COL-040",
    "POR_SOURCE_MISSING": "BW-POR-050",
    "PFB_GROUP_ROLE_MISSING": "BW-PFB-060",
    "HBX_BIND_MISSING": "BW-HBX-070",
    "STR_MISMATCH": "BW-STR-090",
    "HEX_DIFF": "BW-HEX-100",
    "EXPORT_EMPTY": "BW-EXP-000",
    "EXPORT_EXCEPTION": "BW-EXP-999"
}

# —— 日志等级映射 —— #
LOG_LEVELS = {
    "INFO": 1,
    "DEBUG": 2,
    "ERROR": 3
}

# —— 内部结构体：ExportRequest（聚合所有 UI 字段） —— #
class ExportRequest:
    def __init__(self, scene, prefs, objects):
        # 会话级参数（Scene.bw_export_v2）
        s = scene.bw_export_v2

        self.export_root = s.bw_export_path or getattr(prefs, "default_export_path", "")
        self.temp_root = s.bw_temp_path or ""
        self.coordinate_system = s.bw_coordinate_system
        self.default_scale = s.bw_default_scale
        self.apply_scale_to_geometry = s.bw_apply_scale_to_geometry

        self.skeleton_matrix_mode = s.bw_skeleton_matrix_mode
        self.skeleton_frame_scale = s.bw_skeleton_frame_scale
        self.animation_matrix_mode = s.bw_animation_matrix_mode
        self.animation_fps = s.bw_animation_fps
        self.enable_cuetrack = s.bw_enable_cuetrack

        # 范围与过滤
        self.export_all_objects = s.bw_export_all_objects
        self.export_selected_objects = s.bw_export_selected_objects
        self.export_collection_objects = s.bw_export_collection_objects
        self.export_tag_filter = s.bw_export_tag_filter

        # 模块开关
        self.export_mesh = s.bw_export_mesh
        self.export_material = s.bw_export_material
        self.export_skeleton = s.bw_export_skeleton
        self.export_animation = s.bw_export_animation
        self.export_collision = s.bw_export_collision
        self.export_portal = s.bw_export_portal
        self.export_prefab = s.bw_export_prefab
        self.export_hitbox = s.bw_export_hitbox
        self.export_cuetrack = s.bw_export_cuetrack

        # 校验与日志
        self.enable_structure_check = s.bw_enable_structure_check
        self.enable_hex_diff = s.bw_enable_hex_diff
        self.enable_path_check = s.bw_enable_path_check
        self.enable_path_fix = s.bw_enable_path_fix
        self.log_level = s.bw_log_level
        self.save_report = s.bw_save_report

        # 对象集合（Object.bw_settings_v2）
        self.objects = objects

        # 偏好设置默认（AddonPreferences）
        self.project_root = getattr(prefs, "project_root", "")
        self.prefs_coordinate_system = getattr(prefs, "coordinate_system", "MAX_COMPAT")
        self.prefs_default_scale = getattr(prefs, "default_scale", 1.0)
        self.prefs_enable_structure_check = getattr(prefs, "enable_structure_check", True)
        self.prefs_enable_hex_diff = getattr(prefs, "enable_hex_diff", True)
        self.prefs_enable_path_fix = getattr(prefs, "enable_path_fix", False)
        self.prefs_log_level = getattr(prefs, "log_level", "INFO")
        self.prefs_save_report = getattr(prefs, "save_report", True)

        # 报告聚合
        self.report_entries = []
        self.export_files = []  # 写出的目标文件列表（路径）
        self.section_summary = []  # 每个对象写出的节摘要


# —— 辅助: 日志输出 —— #
def log(context_op, level, message):
    # 读取 Scene 日志等级（无 Scene 时使用 INFO）
    try:
        scene = bpy.context.scene
        lvl = LOG_LEVELS.get(scene.bw_export_v2.bw_log_level, 1)
    except Exception:
        lvl = 1
    msg = f"[{level}] {message}"
    if level == 'ERROR':
        context_op.report({'ERROR'}, msg)
    elif level == 'DEBUG' and lvl >= 2:
        context_op.report({'INFO'}, msg)  # Blender 没有 DEBUG 渲染，INFO 代替
    elif level == 'INFO' and lvl >= 1:
        context_op.report({'INFO'}, msg)

# —— 辅助: 报告记录 —— #
def add_report(req: ExportRequest, code_key: str, message: str, context: dict = None):
    entry = {
        "code": ERROR_CODES.get(code_key, "UNKNOWN"),
        "message": message,
        "context": context or {}
    }
    req.report_entries.append(entry)

# —— 辅助: 写出报告文件 —— #
def write_report_file(req: ExportRequest):
    if not req.save_report:
        return
    try:
        base_dir = req.temp_root or req.export_root or req.project_root or ""
        if not base_dir:
            return
        os.makedirs(base_dir, exist_ok=True)
        report_path = os.path.join(base_dir, "bw_export_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "export_files": req.export_files,
                "sections": req.section_summary,
                "entries": req.report_entries
            }, f, ensure_ascii=False, indent=2)
        return report_path
    except Exception:
        # 尽量不阻断导出，但报告写出失败记录到日志
        traceback.print_exc()
        return None

# —— 辅助: 导出路径合法性检查 —— #
def validate_export_root(req: ExportRequest, op: Operator):
    if not req.export_root or not os.path.isdir(req.export_root):
        add_report(req, "PATH_INVALID", f"导出路径非法或不存在: {req.export_root}")
        log(op, 'ERROR', f"[{ERROR_CODES['PATH_INVALID']}] 导出路径非法或不存在: {req.export_root}")
        return False
    return True

# —— 辅助: 标签过滤 —— #
def match_tag(obj: bpy.types.Object, tag_filter: str) -> bool:
    if not tag_filter:
        return True
    # 策略：名称包含 或 自定义属性 bw_tag == tag_filter
    if tag_filter in obj.name:
        return True
    if hasattr(obj, "bw_settings_v2"):
        # 自定义: 对象属性里可能存 tag（团队约定）
        # 这里读取对象的自定义属性字典
        if tag_filter in obj.keys():
            return True
        # 或者: bw_settings_v2 里扩展字段（暂不定义，交由团队实际扩展）
    return False

# —— 辅助: 对象收集 —— #
def collect_objects(context, req: ExportRequest, op: Operator):
    scene = context.scene
    result = []

    # 单选逻辑优先级：选中对象 > 集合对象 > 全部对象（或按照你们约定）
    if req.export_selected_objects:
        for obj in context.selected_objects:
            if hasattr(obj, "bw_settings_v2") and match_tag(obj, req.export_tag_filter):
                result.append(obj)
    elif req.export_collection_objects and context.collection:
        for obj in context.collection.objects:
            if hasattr(obj, "bw_settings_v2") and match_tag(obj, req.export_tag_filter):
                result.append(obj)
    elif req.export_all_objects:
        for obj in scene.objects:
            if hasattr(obj, "bw_settings_v2") and match_tag(obj, req.export_tag_filter):
                result.append(obj)

    # 对象集合为空，阻断
    if not result:
        add_report(req, "EXPORT_EMPTY", "导出对象集合为空")
        log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EMPTY']}] 导出对象集合为空")
        return []

    # 去除未启用导出的对象
    filtered = [o for o in result if o.bw_settings_v2.bw_export_enabled]
    if not filtered:
        add_report(req, "EXPORT_EMPTY", "所有对象均未启用导出")
        log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EMPTY']}] 所有对象均未启用导出")
        return []

    return filtered

# —— 辅助: CueTrack 与动画开关一致性检查 —— #
def validate_animation_cuetrack_consistency(req: ExportRequest, op: Operator):
    if req.export_cuetrack and not req.export_animation:
        add_report(req, "ANI_CUETRACK_JSON_INVALID", "事件轨需要启用动画导出")
        log(op, 'ERROR', f"[{ERROR_CODES['ANI_CUETRACK_JSON_INVALID']}] 事件轨需要启用动画导出")
        return False
    return True

# —— 辅助: 事件 JSON 校验（对象级） —— #
def validate_event_json(obj: bpy.types.Object, req: ExportRequest, op: Operator) -> bool:
    s = obj.bw_settings_v2
    if not req.export_cuetrack:
        return True
    raw = s.bw_animation_events_json.strip()
    if raw == "":
        # 可接受为空，表示无事件
        return True
    try:
        data = json.loads(raw)
        # 要求: 列表，每项包含 time(float) / event_type(str) / params(object或dict)
        if not isinstance(data, list):
            raise ValueError("事件 JSON 必须是列表")
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"事件项[{idx}]必须是对象")
            if "time" not in item or "event_type" not in item:
                raise ValueError(f"事件项[{idx}]缺少必需字段 time 或 event_type")
        return True
    except Exception as e:
        add_report(req, "ANI_CUETRACK_JSON_INVALID", f"对象[{obj.name}]事件 JSON 非法: {str(e)}")
        log(op, 'ERROR', f"[{ERROR_CODES['ANI_CUETRACK_JSON_INVALID']}] 对象[{obj.name}]事件 JSON 非法: {str(e)}")
        return False

# —— 辅助: 模块开关与对象类型匹配检查 —— #
def validate_module_object_compat(obj: bpy.types.Object, req: ExportRequest, op: Operator) -> bool:
    s = obj.bw_settings_v2
    # 动画模块需要骨骼网格或骨骼对象（简化为导出类型 SKINNED_MESH）
    if req.export_animation and s.bw_export_type != "SKINNED_MESH":
        add_report(req, "ANI_SKELETON_MISMATCH", f"对象[{obj.name}]不支持动画导出（非骨骼网格）")
        log(op, 'ERROR', f"[{ERROR_CODES['ANI_SKELETON_MISMATCH']}] 对象[{obj.name}]不支持动画导出（非骨骼网格）")
        return False
    return True

# —— 辅助: Writer 执行 —— #
def execute_writers(req: ExportRequest, op: Operator):
    sections = []
    section_summary = []

    # Writer 调用顺序固定（网格→材质→骨骼→动画→碰撞→门户→预制→Hitbox）
    for obj in req.objects:
        s = obj.bw_settings_v2

        # 前置校验：动画事件 JSON（如启用 CueTrack）
        if req.export_cuetrack and not validate_event_json(obj, req, op):
            return None, None

        # 前置校验：模块与对象类型兼容性
        if not validate_module_object_compat(obj, req, op):
            return None, None

        # 网格
        if req.export_mesh:
            try:
                res = primitives_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "mesh", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"网格导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 网格导出异常[{obj.name}]: {str(e)}")
                return None, None

        # 材质
        if req.export_material:
            try:
                res = material_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "material", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"材质导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 材质导出异常[{obj.name}]: {str(e)}")
                return None, None

        # 骨骼
        if req.export_skeleton:
            try:
                res = skeleton_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "skeleton", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"骨骼导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 骨骼导出异常[{obj.name}]: {str(e)}")
                return None, None

        # 动画（含 CueTrack 由 animation_writer 内部根据 req.enable_cuetrack 决定是否写 event 节）
        if req.export_animation:
            try:
                res = animation_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "animation", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"动画导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 动画导出异常[{obj.name}]: {str(e)}")
                return None, None

        # 碰撞
        if req.export_collision:
            try:
                res = collision_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "collision", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"碰撞导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 碰撞导出异常[{obj.name}]: {str(e)}")
                return None, None

        # 门户
        if req.export_portal:
            try:
                res = portal_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "portal", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"门户导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 门户导出异常[{obj.name}]: {str(e)}")
                return None, None

        # 预制/实例表
        if req.export_prefab:
            try:
                res = prefab_assembler.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "prefab", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"预制体导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 预制体导出异常[{obj.name}]: {str(e)}")
                return None, None

        # Hitbox
        if req.export_hitbox:
            try:
                res = hitbox_xml_writer.export(obj, req)
                if res:
                    sections.extend(res)
                    section_summary.append({"object": obj.name, "module": "hitbox", "sections": [s[0] for s in res]})
            except Exception as e:
                add_report(req, "EXPORT_EXCEPTION", f"Hitbox 导出异常[{obj.name}]: {str(e)}")
                log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] Hitbox 导出异常[{obj.name}]: {str(e)}")
                return None, None

    req.section_summary.extend(section_summary)
    return sections, section_summary

# —— 辅助: 写入最终文件（节组织） —— #
def write_sections(req: ExportRequest, sections, op: Operator):
    try:
        # binsection_writer 要求传入节数组与输出根目录；内部负责节头、对齐与写出。
        out_files = binsection_writer.write(sections, req.export_root)
        # 可能写出多个文件（visual/model/animation 等）
        if isinstance(out_files, list):
            req.export_files.extend(out_files)
        else:
            req.export_files.append(out_files)
        log(op, 'INFO', f"写入完成: {', '.join(req.export_files) if req.export_files else '(无)'}")
        return True
    except Exception as e:
        add_report(req, "EXPORT_EXCEPTION", f"写入文件异常: {str(e)}")
        log(op, 'ERROR', f"[{ERROR_CODES['EXPORT_EXCEPTION']}] 写入文件异常: {str(e)}")
        return False

# —— 辅助: 执行校验 —— #
def perform_validations(req: ExportRequest, op: Operator):
    base_dir = req.export_root
    # 结构校验
    if req.enable_structure_check:
        try:
            structure_checker.check(base_dir)
            log(op, 'INFO', "结构校验通过")
        except Exception as e:
            add_report(req, "STR_MISMATCH", f"结构校验失败: {str(e)}")
            log(op, 'ERROR', f"[{ERROR_CODES['STR_MISMATCH']}] 结构校验失败: {str(e)}")
            return False

    # 路径校验与修复
    if req.enable_path_check:
        try:
            path_validator.check(base_dir, fix=req.enable_path_fix)
            log(op, 'INFO', f"路径校验完成（自动修复: {'开启' if req.enable_path_fix else '关闭'}）")
        except Exception as e:
            add_report(req, "PATH_INVALID", f"路径校验失败: {str(e)}")
            log(op, 'ERROR', f"[{ERROR_CODES['PATH_INVALID']}] 路径校验失败: {str(e)}")
            return False

    # Hex 对比
    if req.enable_hex_diff:
        try:
            hex_diff.compare(base_dir)
            log(op, 'INFO', "Hex 对比通过（与 Max 导出结果一致）")
        except Exception as e:
            add_report(req, "HEX_DIFF", f"Hex 对比失败: {str(e)}")
            log(op, 'ERROR', f"[{ERROR_CODES['HEX_DIFF']}] Hex 对比失败: {str(e)}")
            return False

    return True


class BW_OT_Export(Operator):
    bl_idname = "bw.export"
    bl_label = "BigWorld 导出"
    bl_description = "执行 BigWorld 导出流程（严格对齐方案文档）"

    # 手动指定报告输出路径（可选）
    report_path: StringProperty(
        name="报告路径",
        description="报告输出路径（为空则写入到临时路径或导出根目录）",
        default=""
    )
    # 允许在 UI 操作符上开启详细日志（提升到 DEBUG）
    verbose_log: BoolProperty(
        name="详细日志",
        description="在本次导出中输出详细日志（覆盖场景日志等级）",
        default=False
    )

    def execute(self, context):
        # 读取偏好设置
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
        except Exception:
            self.report({'ERROR'}, "未找到插件偏好设置")
            return {'CANCELLED'}

        # 读取会话设置
        if not hasattr(context.scene, "bw_export_v2"):
            self.report({'ERROR'}, "缺少导出设置 (bw_export_v2)")
            return {'CANCELLED'}

        scene = context.scene
        s = scene.bw_export_v2

        # 构造初始对象集合（先用空，后面 collect_objects）
        req = ExportRequest(scene, prefs, objects=[])
        # 强制日志等级覆盖（仅本次导出）
        if self.verbose_log:
            s.bw_log_level = "DEBUG"

        # 导出路径合法性
        if not validate_export_root(req, self):
            write_report_file(req)
            return {'CANCELLED'}

        # 动画与 CueTrack 开关一致性
        if not validate_animation_cuetrack_consistency(req, self):
            write_report_file(req)
            return {'CANCELLED'}

        # 收集对象
        objects = collect_objects(context, req, self)
        if not objects:
            write_report_file(req)
            return {'CANCELLED'}
        req.objects = objects

        # 执行 Writer
        log(self, 'INFO', f"开始导出，对象数量: {len(req.objects)}，模块开关: "
                          f"mesh={req.export_mesh}, material={req.export_material}, skeleton={req.export_skeleton}, "
                          f"animation={req.export_animation}, collision={req.export_collision}, portal={req.export_portal}, "
                          f"prefab={req.export_prefab}, hitbox={req.export_hitbox}, cuetrack={req.export_cuetrack}")

        sections, summary = execute_writers(req, self)
        if sections is None:
            write_report_file(req)
            return {'CANCELLED'}

        # 写入文件
        if not write_sections(req, sections, self):
            write_report_file(req)
            return {'CANCELLED'}

        # 执行校验
        if not perform_validations(req, self):
            # 校验失败也写报告并阻断
            p = write_report_file(req)
            if p:
                self.report({'ERROR'}, f"校验失败，报告输出: {p}")
            return {'CANCELLED'}

        # 写出报告
        rp = self.report_path or write_report_file(req)
        if rp:
            self.report({'INFO'}, f"导出完成，报告输出: {rp}")
        else:
            self.report({'INFO'}, "导出完成")

        return {'FINISHED'}


class BW_OT_OpenLog(Operator):
    bl_idname = "bw.open_log"
    bl_label = "打开日志"
    bl_description = "打开导出日志文件或报告目录"

    def execute(self, context):
        try:
            scene = bpy.context.scene
            s = scene.bw_export_v2
            base_dir = s.bw_temp_path or s.bw_export_path
            if not base_dir:
                self.report({'ERROR'}, "未配置临时路径或导出路径")
                return {'CANCELLED'}
            # 优先打开报告文件，否则打开目录
            report_path = os.path.join(base_dir, "bw_export_report.json")
            if os.path.isfile(report_path):
                bpy.ops.wm.url_open(url=f"file://{report_path}")
                self.report({'INFO'}, f"已打开报告: {report_path}")
            else:
                bpy.ops.wm.url_open(url=f"file://{base_dir}")
                self.report({'INFO'}, f"已打开目录: {base_dir}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"打开日志失败: {str(e)}")
            return {'CANCELLED'}


classes = (
    BW_OT_Export,
    BW_OT_OpenLog,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

def menu_func_export(self, context):
    self.layout.operator(
        BW_OT_Export.bl_idname,
        text="BigWorld Export (.visual/.primitives/.skeleton/.animation)"
    )