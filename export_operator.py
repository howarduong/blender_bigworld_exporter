# 相对路径: blender_bigworld_exporter/export_operator.py
# 设计目标（不精简、不省略）：
# - 一次导出自动生成三类文件：.primitives（几何）→ .visual（材质）→ .model（节点树与引用、及各模块节）
# - .model 必须包含对 .visual 和 .primitives 的路径引用
# - Skeleton / Animation / CueTrack / Portal / Collision / Prefab / Hitbox 等均写入 .model，缺数据也写空节或占位
# - UI/Operator 属性与 Addon Preferences 完整同步
# - 集成路径校验、结构校验、HexDiff，均为钩子式调用，不中断导出
# - 不做逻辑合并或精简，严格模块化写出

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator
from pathlib import Path

from .core.binsection_writer import BinWriter, BWHeaderWriter
from .core.primitives_writer import PrimitivesWriter, MeshExportOptions
from .core.material_writer import MaterialWriter, MaterialExportOptions
from .core.model_writer import ModelWriter
from .core.skeleton_writer import SkeletonWriter
from .core.animation_writer import AnimationWriter
from .core.collision_writer import CollisionWriter, CollisionExportOptions
from .core.portal_writer import PortalWriter
from .core.prefab_assembler import PrefabAssembler
from .core.hitbox_xml_writer import HitboxXMLWriter, HitboxBinaryWriter

from .validators.path_validator import PathValidator
from .validators.structure_checker import StructureChecker
from .validators.hex_diff import HexDiffer

from .preferences import BigWorldAddonPreferences


class EXPORT_OT_bigworld(Operator, ExportHelper):
    """导出 BigWorld 资源（一次导出同时生成 .primitives / .visual / .model 三文件）"""
    bl_idname = "export_scene.bigworld"
    bl_label = "导出 BigWorld 资源"
    bl_options = {'PRESET'}

    filename_ext = ".model"

    filter_glob: bpy.props.StringProperty(
        default="*.model",
        options={'HIDDEN'},
        maxlen=255,
    )

    # -------- 全局导出参数 --------
    export_root: bpy.props.StringProperty(
        name="导出根目录",
        subtype='DIR_PATH',
        default=""
    )
    engine_version: bpy.props.EnumProperty(
        name="引擎版本",
        items=[('BW2', "2.x", ""), ('BW3', "3.x", "")],
        default='BW3'
    )
    default_scale: bpy.props.FloatProperty(
        name="默认缩放",
        default=1.0,
        min=0.0001,
        max=1000.0
    )
    coord_mode: bpy.props.EnumProperty(
        name="坐标系模式",
        items=[('MAX_COMPAT', "与3ds Max兼容", ""), ('BLENDER_NATIVE', "Blender原生", "")],
        default='MAX_COMPAT'
    )
    only_selected: bpy.props.BoolProperty(name="仅导出选中对象", default=True)
    include_collections: bpy.props.BoolProperty(name="导出所在集合", default=False)
    apply_scale: bpy.props.BoolProperty(name="应用缩放到几何", default=False)

    # -------- 校验与日志 --------
    enable_struct_check: bpy.props.BoolProperty(name="启用结构校验（严格）", default=False)
    enable_hex_diff: bpy.props.BoolProperty(name="启用十六进制差异比对", default=False)
    enable_verbose_log: bpy.props.BoolProperty(name="输出详细日志", default=False)

    # -------- 导出模块开关 --------
    export_mesh: bpy.props.BoolProperty(name="网格 (Mesh)", default=True)
    export_material: bpy.props.BoolProperty(name="材质 (Material)", default=True)
    export_skeleton: bpy.props.BoolProperty(name="骨骼 (Skeleton)", default=True)
    export_animation: bpy.props.BoolProperty(name="动画 (Animation)", default=False)
    export_collision: bpy.props.BoolProperty(name="碰撞 (Collision)", default=False)
    export_portal: bpy.props.BoolProperty(name="门户 (Portal)", default=False)
    export_prefab: bpy.props.BoolProperty(name="预制/实例表 (Prefab/Instances)", default=False)
    export_hitbox: bpy.props.BoolProperty(name="Hitbox / XML", default=False)
    export_cuetrack: bpy.props.BoolProperty(name="事件轨道 (Cue Track)", default=False)

    # -------- 高级选项 --------
    check_paths: bpy.props.BoolProperty(name="校验资源路径", default=False)
    auto_fix_paths: bpy.props.BoolProperty(name="自动修复路径", default=False)

    # -------- UI 绘制 --------
    def invoke(self, context, event):
        # 同步 Addon Preferences 默认值
        prefs = context.preferences.addons[__package__].preferences
        if not self.export_root:
            self.export_root = prefs.export_root
        self.engine_version = prefs.engine_version
        self.default_scale = prefs.default_scale
        self.coord_mode = prefs.coord_mode
        self.enable_struct_check = prefs.enable_struct_check
        self.enable_hex_diff = prefs.enable_hex_diff
        self.enable_verbose_log = prefs.enable_verbose_log
        return super().invoke(context, event)

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="导出路径与版本")
        col.prop(self, "export_root")
        row = col.row(align=True)
        row.prop(self, "engine_version")
        row.prop(self, "coord_mode")

        col.separator()
        col.label(text="缩放与应用")
        row = col.row(align=True)
        row.prop(self, "default_scale")
        row.prop(self, "apply_scale")

        col.separator()
        col.label(text="范围与集合")
        row = col.row(align=True)
        row.prop(self, "only_selected")
        row.prop(self, "include_collections")

        col.separator()
        col.label(text="校验与日志")
        row = col.row(align=True)
        row.prop(self, "enable_struct_check")
        row.prop(self, "enable_hex_diff")
        row.prop(self, "enable_verbose_log")

        col.separator()
        col.label(text="导出模块")
        col.prop(self, "export_mesh")
        col.prop(self, "export_material")
        col.prop(self, "export_skeleton")
        col.prop(self, "export_animation")
        col.prop(self, "export_collision")
        col.prop(self, "export_portal")
        col.prop(self, "export_prefab")
        col.prop(self, "export_hitbox")
        col.prop(self, "export_cuetrack")

        col.separator()
        col.label(text="高级选项")
        col.prop(self, "check_paths")
        col.prop(self, "auto_fix_paths")

    # -------- 工具方法 --------
    def _collect_objects(self, context):
        return list(context.selected_objects) if self.only_selected else list(context.scene.objects)

    def _resolve_export_root(self):
        return bpy.path.abspath(self.export_root) if self.export_root else ""

    # -------- 主执行：一次导出生成 .primitives / .visual / .model，及验证器调用 --------
    def execute(self, context):
        # 同步偏好设置
        prefs = context.preferences.addons[__package__].preferences
        prefs.export_root = self.export_root
        prefs.engine_version = self.engine_version
        prefs.default_scale = self.default_scale
        prefs.coord_mode = self.coord_mode
        prefs.enable_struct_check = self.enable_struct_check
        prefs.enable_hex_diff = self.enable_hex_diff
        prefs.enable_verbose_log = self.enable_verbose_log

        export_root_resolved = self._resolve_export_root()
        objects = self._collect_objects(context)

        # 校验器实例化（不省略）
        path_validator = PathValidator(
            export_root=export_root_resolved,
            auto_fix=self.auto_fix_paths,
            coord_mode=self.coord_mode
        )
        struct_checker = StructureChecker(
            engine_version=self.engine_version,
            verbose=self.enable_verbose_log
        )
        hex_differ = HexDiffer(verbose=self.enable_verbose_log)

        # 导出前路径校验（可选，但不省略调用）
        if self.check_paths:
            path_validator.validate_scene_paths(context)
        if self.include_collections:
            # 集合校验占位：由 PathValidator 处理集合相关规则
            path_validator.validate_collections(context)

        # 遍历对象，严格按照 .primitives → .visual → .model 写出
        for obj in objects:
            if not hasattr(obj, "bw_settings"):
                # 保持占位策略：无 bw_settings 不抛异常，跳过
                continue

            s = obj.bw_settings
            obj_name = obj.name
            primitives_path = Path(export_root_resolved) / f"{obj_name}.primitives"
            visual_path = Path(export_root_resolved) / f"{obj_name}.visual"
            model_path = Path(export_root_resolved) / f"{obj_name}.model"

            # ------- 1) 写 .primitives：几何数据 -------
            if obj.type == 'MESH' and self.export_mesh:
                primitives_path.parent.mkdir(parents=True, exist_ok=True)
                with open(primitives_path, "wb") as f_prim:
                    binw_prim = BinWriter(f_prim, little_endian=True)
                    BWHeaderWriter(binw_prim).write_header(
                        b"BWV\0", version=3 if self.engine_version == 'BW3' else 2
                    )
                    pw = PrimitivesWriter(binw_prim)
                    mesh_opts = MeshExportOptions(
                        flip_winding_enabled=getattr(s, "flip_winding", True),
                        rebuild_normals_enabled=getattr(s, "rebuild_normals", False),
                        normals_angle_threshold=getattr(s, "norm_angle", 45.0),
                        apply_scene_scale=self.apply_scale,
                        default_scale=self.default_scale,
                        coord_mode=self.coord_mode
                    )
                    pw.write_mesh(obj.data, mesh_opts)  # 顶点/索引/分组/权重等完整写出（由 PrimitivesWriter 内部实现）

            # ------- 2) 写 .visual：材质与渲染参数 -------
            if obj.type == 'MESH' and self.export_material:
                visual_path.parent.mkdir(parents=True, exist_ok=True)
                with open(visual_path, "wb") as f_vis:
                    binw_vis = BinWriter(f_vis, little_endian=True)
                    BWHeaderWriter(binw_vis).write_header(
                        b"BWV\0", version=3 if self.engine_version == 'BW3' else 2
                    )
                    mopts = MaterialExportOptions(
                        export_root=export_root_resolved,
                        force_relative_paths=True,
                        default_shader="std_effect"
                    )
                    mw = MaterialWriter(binw_vis, mopts)
                    mw.write_object_materials(obj)  # 保留空材质 slot，占位字段不省略

            # ------- 3) 写 .model：节点树、引用、及附属模块（骨骼/动画/事件/门户/碰撞/预制/Hitbox） -------
            model_path.parent.mkdir(parents=True, exist_ok=True)
            with open(model_path, "wb") as f_model:
                binw_model = BinWriter(f_model, little_endian=True)
                BWHeaderWriter(binw_model).write_header(
                    b"BWV\0", version=3 if self.engine_version == 'BW3' else 2
                )

                # 3.1 节点树 + 引用路径（不省略）
                mwriter = ModelWriter(
                    binw=binw_model,
                    engine_version=self.engine_version,
                    coord_mode=self.coord_mode,
                    default_scale=self.default_scale,
                    apply_scene_scale=self.apply_scale,
                    verbose=self.enable_verbose_log
                )
                # 写模型头（若 ModelWriter 内部需要）
                mwriter.write_model_header(obj)
                # 写节点树（根节点为 obj，含子节点；无子时写空节）
                mwriter.write_node_tree(obj)
                # 写引用（即使未导出材质或几何，也写空字符串）
                mwriter.write_references(
                    visual_path.name if (obj.type == 'MESH' and self.export_material) else "",
                    primitives_path.name if (obj.type == 'MESH' and self.export_mesh) else ""
                )

                # 3.2 骨骼（ARMATURE 对象）
                if obj.type == 'ARMATURE' and self.export_skeleton:
                    sw = SkeletonWriter(binw_model)
                    sw.write_skeleton(obj)  # SkeletonWriter 内部需保证空节占位

                # 3.3 动画（ARMATURE 对象）
                if obj.type == 'ARMATURE' and self.export_animation:
                    aw = AnimationWriter(binw_model)
                    if obj.animation_data and obj.animation_data.action:
                        aw.write_animations(obj)  # 多动作由 AnimationWriter 内部处理
                    else:
                        aw.write_empty_animation_section()  # 占位空节

                # 3.4 事件轨道（Cue Track）
                if self.export_cuetrack:
                    aw_cue = AnimationWriter(binw_model)
                    if hasattr(s, "cue_events") and s.cue_events:
                        # cue_events 预期格式： [{"time": t, "name": n, "param": p}, ...]
                        aw_cue.write_cue_track(s.cue_events)
                    else:
                        aw_cue.write_empty_cue_track()  # 占位空节

                # 3.5 门户（Portal）
                if self.export_portal and getattr(s, "portal_type", "none") and s.portal_type != 'none':
                    pw_portal = PortalWriter(binw_model)
                    pw_portal.write_portals([{
                        "type": s.portal_type,
                        "label": getattr(s, "portal_label", ""),
                        "geometry": getattr(s, "portal_geom", None),  # 可为空占位
                        "object": obj
                    }])

                # 3.6 碰撞（Collision）
                if self.export_collision and getattr(s, "is_collider", False) and obj.type == 'MESH':
                    copt = CollisionExportOptions()
                    cw = CollisionWriter(binw_model, copt)  # 若你的 ctor 只需要 binw，则改为 CollisionWriter(binw_model)
                    cw.write_collision_mesh(obj.data, copt)

                # 3.7 预制与实例表（Prefab/Instances）
                if self.export_prefab:
                    assembler = PrefabAssembler(binw_model)
                    instance_entry = {
                        "prefab": getattr(s, "prefab_name", ""),
                        "instance_id": getattr(s, "instance_id", ""),
                        "collection": obj.users_collection[0].name if obj.users_collection else "",
                        "object_name": obj.name,
                        "matrix": list(obj.matrix_world) if hasattr(obj, "matrix_world") else [1.0] * 16
                    }
                    assembler.write_instances([instance_entry])

                # 3.8 Hitbox：XML（磁盘） + Binary（写入 .model）
                if self.export_hitbox and getattr(s, "hitbox_name", ""):
                    hx = HitboxXMLWriter()
                    hb = HitboxBinaryWriter(binw_model)

                    # 优先骨骼矩阵，其次对象矩阵，最后单位矩阵（不省略）
                    mat_world = None
                    if hasattr(s, "hp_bone") and s.hp_bone and obj.type == 'ARMATURE':
                        bone = obj.data.bones.get(s.hp_bone, None)
                        if bone:
                            mat_world = list((obj.matrix_world @ bone.matrix_local).to_4x4())
                    if mat_world is None:
                        mat_world = list(obj.matrix_world) if hasattr(obj, "matrix_world") else [1.0] * 16

                    xml_out_path = str(Path(export_root_resolved) / f"{obj_name}_hitbox.xml")
                    hx.write_xml(xml_out_path, [{
                        "name": s.hitbox_name,
                        "type": getattr(s, "hitbox_type", "box"),
                        "level": getattr(s, "hitbox_level", 0),
                        "bone": getattr(s, "hp_bone", ""),
                        "matrix": mat_world
                    }])
                    hb.write_hitboxes([{
                        "name": s.hitbox_name,
                        "type": getattr(s, "hitbox_type", "box"),
                        "level": getattr(s, "hitbox_level", 0),
                        "bone": getattr(s, "hp_bone", ""),
                        "matrix": mat_world
                    }])

            # ------- 4) 每对象结构校验 -------
            if self.enable_struct_check:
                struct_checker.check_model_file(str(model_path))
                if obj.type == 'MESH' and self.export_mesh:
                    struct_checker.check_primitives_file(str(primitives_path))
                if obj.type == 'MESH' and self.export_material:
                    struct_checker.check_visual_file(str(visual_path))

            # ------- 5) 每对象 HexDiff（与遗留参考输出比对，不中断导出） -------
            if self.enable_hex_diff:
                legacy_dir = getattr(prefs, "legacy_reference_root", "")
                if legacy_dir:
                    ref_model = Path(legacy_dir) / f"{obj_name}.model"
                    ref_prims = Path(legacy_dir) / f"{obj_name}.primitives"
                    ref_visual = Path(legacy_dir) / f"{obj_name}.visual"
                    if ref_model.exists():
                        hex_differ.compare_files(str(model_path), str(ref_model))
                    if obj.type == 'MESH' and self.export_mesh and ref_prims.exists():
                        hex_differ.compare_files(str(primitives_path), str(ref_prims))
                    if obj.type == 'MESH' and self.export_material and ref_visual.exists():
                        hex_differ.compare_files(str(visual_path), str(ref_visual))

        self.report({'INFO'}, f"导出完成: {export_root_resolved}")
        return {'FINISHED'}
