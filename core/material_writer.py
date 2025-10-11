# 相对路径: core/material_writer.py
# 功能: 导出材质信息 (.visual)，包括:
#   - 材质名称
#   - Shader 名称
#   - 各类纹理路径 (diffuse/normal/specular/opacity/envmap)
#   - 基础参数 (Specular、Alpha)
#   - 占位字段 (双面标志、排序偏移、保留字段)
#
# 注意:
#   - 字段顺序必须固定，不能省略
#   - 即使没有值，也要写默认值
#   - Shader 名称可通过自定义属性 "bw_shader" 指定，否则默认 "std_effect"

from typing import List
import bpy

from .binsection_writer import BinWriter, SectionWriter
from .utils import make_relative_path, get_obj_prop


class MaterialExportOptions:
    """材质导出选项"""
    def __init__(self,
                 export_root: str = "",
                 force_relative_paths: bool = True,
                 default_shader: str = "std_effect"):
        # 导出根目录，用于 make_relative_path
        self.export_root = export_root
        # 是否强制相对路径
        self.force_relative_paths = force_relative_paths
        # 默认 Shader 名称
        self.default_shader = default_shader


class MaterialWriter:
    """材质导出器 (.visual)"""

    def __init__(self, binw: BinWriter, opts: MaterialExportOptions):
        self.binw = binw
        self.secw = SectionWriter(binw)
        self.opts = opts

    def write_object_materials(self, obj: bpy.types.Object):
        """
        导出对象的材质信息。
        """
        mats = [slot.material for slot in obj.material_slots if slot.material]
        self.secw.begin_section(section_id=0x2001)  # 示例 ID，需在 schema 固化
        self.binw.write_u32(len(mats))

        for mat in mats:
            self._write_single_material(mat)

        self.secw.end_section()

    def _write_single_material(self, mat: bpy.types.Material):
        """
        导出单个材质，字段顺序必须固定。
        """
        # 材质名称
        self.binw.write_cstring(mat.name)

        # Shader 名称
        shader_name = get_obj_prop(mat, "bw_shader", self.opts.default_shader)
        self.binw.write_cstring(shader_name)

        # Diffuse 纹理路径
        diffuse_path = self._find_texture_path(mat, ["diffuse", "albedo", "basecolor"])
        if diffuse_path:
            self.binw.write_cstring(make_relative_path(self.opts.export_root, diffuse_path))
        else:
            self.binw.write_cstring("")

        # Normal 纹理路径
        normal_path = self._find_texture_path(mat, ["normal", "bump"])
        if normal_path:
            self.binw.write_cstring(make_relative_path(self.opts.export_root, normal_path))
        else:
            self.binw.write_cstring("")

        # Specular 纹理路径
        specular_path = self._find_texture_path(mat, ["specular", "spec"])
        if specular_path:
            self.binw.write_cstring(make_relative_path(self.opts.export_root, specular_path))
        else:
            self.binw.write_cstring("")

        # Opacity 纹理路径
        opacity_path = self._find_texture_path(mat, ["opacity", "alpha", "transparency"])
        if opacity_path:
            self.binw.write_cstring(make_relative_path(self.opts.export_root, opacity_path))
        else:
            self.binw.write_cstring("")

        # Specular 参数
        specular_val = float(get_obj_prop(mat, "bw_specular", 1.0))
        self.binw.write_f32(specular_val)

        # Alpha 参数
        alpha_val = float(get_obj_prop(mat, "bw_alpha", 1.0))
        self.binw.write_f32(alpha_val)

        # 占位字段: 双面标志
        double_sided = int(get_obj_prop(mat, "bw_double_sided", 0))
        self.binw.write_u8(double_sided)

        # 占位字段: 排序偏移
        sort_offset = int(get_obj_prop(mat, "bw_sort_offset", 0))
        self.binw.write_i32(sort_offset)

        # 环境贴图路径 (统一路径处理)
        envmap_path = get_obj_prop(mat, "bw_envmap", "")
        if envmap_path:
            self.binw.write_cstring(make_relative_path(self.opts.export_root, envmap_path))
        else:
            self.binw.write_cstring("")

        # 额外占位字段: 保留参数1 (float)
        self.binw.write_f32(0.0)

        # 额外占位字段: 保留参数2 (int)
        self.binw.write_i32(0)

    def _find_texture_path(self, mat: bpy.types.Material, keywords: List[str]) -> str:
        """
        在材质节点树中查找包含指定关键字的纹理路径。
        """
        if not mat.node_tree:
            return ""
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                path = bpy.path.abspath(node.image.filepath)
                name = node.name.lower()
                for kw in keywords:
                    if kw in name:
                        return path
        return ""
