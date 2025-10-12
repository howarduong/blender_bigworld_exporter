# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Material & Visual Writer (strictly aligned)

- Integrates .visual file writing inside material module (aligned to legacy Max plugin)
- Writes Visual header, references to .primitives, LOD placeholders, render flags
- Writes material blocks (shader, textures, numeric params, reserved fields)
- Relative path normalization (lowercase, POSIX), strict placeholders for excluded features
- Hard blocking validation on counts and consistency with primitives groups

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import bpy

from .binsection_writer import BinSectionWriter, BinaryWriter
from .utils import ensure_posix_lower_relative_path
from ..validators.path_validator import validate_output_path


# ====== Specification constants (logical keys mapped by BinSectionWriter) ======
class SPEC:
    # Sections for .visual file
    SECTION_VISUAL_HEADER = "VISUAL_HEADER"
    SECTION_VISUAL_LOD = "VISUAL_LOD"
    SECTION_VISUAL_MATERIALS = "VISUAL_MATERIALS"

    # Visual header constants
    VISUAL_VERSION = 3
    RESERVED_U32 = 0
    RESERVED_U8 = 0

    # LOD placeholders (single LOD aligned to scheme; multi-LOD excluded but reserved)
    DEFAULT_LOD_COUNT = 1

    # Material field sizes and defaults
    NAME_LEN = 128
    SHADER_LEN = 64
    TEX_PATH_LEN = 256  # not fixed sized write; we write [len + bytes], kept here for reference

    # Default shader name aligned with legacy
    DEFAULT_SHADER = "std_effect"

    # Texture keys (standard set)
    TEX_DIFFUSE = "diffuse"
    TEX_NORMAL = "normal"
    TEX_SPECULAR = "specular"
    TEX_OPACITY = "opacity"
    TEX_ENVMAP = "envmap"


@dataclass
class MaterialExportOptions:
    export_root: str
    default_shader: str = SPEC.DEFAULT_SHADER
    write_envmap: bool = True
    write_normal: bool = True
    write_specular: bool = True
    write_opacity: bool = True
    force_lower_paths: bool = True
    force_posix_sep: bool = True


@dataclass
class ExportContext:
    export_root: str = ""
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "visual" not in self.report:
            self.report["visual"] = {}
        self.report["visual"][key] = value


# ====== Material writer (with integrated .visual writer) ======
class MaterialWriter:
    def __init__(self, ctx: ExportContext, opts: MaterialExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    # ====== Public: write a .visual file ======
    def write_visual(
        self,
        obj: bpy.types.Object,
        output_path: str,
        primitives_path: str,
        expected_group_count: Optional[int] = None,
    ) -> None:
        """
        Write a .visual file that references the given .primitives and contains
        material blocks mapped from the object's material slots.

        - Header: version, flags (reserved), reference to primitives (path normalized), reserved fields
        - LOD: single LOD placeholder (count=1, values defaulted)
        - Materials: one block per material slot, aligned to legacy field order
        """
        validate_output_path(output_path)

        # Normalize reference to primitives
        prim_ref = ensure_posix_lower_relative_path(self.opts.export_root, primitives_path)

        # Collect materials from object
        mats = self._collect_object_materials(obj)
        mat_count = len(mats)

        # Optional consistency check with primitives groups (must match)
        if expected_group_count is not None and expected_group_count != mat_count:
            raise ValueError(f"VISUAL: material count ({mat_count}) != expected primitives groups ({expected_group_count}) for object '{obj.name}'")

        with self.ctx.binsection.open(output_path) as secw:
            # Header
            secw.begin_section(SPEC.SECTION_VISUAL_HEADER)
            self._write_visual_header(self.ctx.binw, obj.name, prim_ref)
            secw.end_section()

            # LOD (single placeholder, reserved for strict alignment)
            secw.begin_section(SPEC.SECTION_VISUAL_LOD)
            self._write_visual_lod(self.ctx.binw, mat_count)
            secw.end_section()

            # Materials
            secw.begin_section(SPEC.SECTION_VISUAL_MATERIALS)
            self._write_material_table(self.ctx.binw, mats)
            secw.end_section()

        # Report
        self.ctx.add_report_stat("object_name", obj.name)
        self.ctx.add_report_stat("material_count", mat_count)
        self.ctx.add_report_stat("primitives_ref", prim_ref)

    # ====== Header ======
    def _write_visual_header(self, binw: BinaryWriter, object_name: str, prim_ref: str) -> None:
        """
        Visual Header layout:
        - version (u32)
        - reserved flags (u32)
        - object name (fixed 128 bytes)
        - primitives path (len + bytes, normalized relative path)
        - reserved u32
        """
        binw.write_u32(SPEC.VISUAL_VERSION)
        binw.write_u32(SPEC.RESERVED_U32)

        name_bytes = object_name.encode('utf-8')
        name_padded = name_bytes[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)

        # write normalized primitives path
        pbytes = prim_ref.encode('utf-8')
        binw.write_u32(len(pbytes))
        binw.write_bytes(pbytes)

        binw.write_u32(SPEC.RESERVED_U32)

    # ====== LOD (single placeholder) ======
    def _write_visual_lod(self, binw: BinaryWriter, material_count: int) -> None:
        """
        LOD layout (placeholder aligned to legacy):
        - lod_count (u32) == 1
        - lod_thresholds (lod_count * f32) default values
        - reserved fields
        """
        binw.write_u32(SPEC.DEFAULT_LOD_COUNT)
        # Single LOD threshold default (e.g., 0.0f)
        binw.write_f32(0.0)
        # Reserved placeholders
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u32(SPEC.RESERVED_U32)

    # ====== Materials ======
    def _write_material_table(self, binw: BinaryWriter, mats: List[bpy.types.Material]) -> None:
        """
        Material table layout:
        - count (u32)
        - repeated blocks per material:
            - name (fixed 128 bytes)
            - shader name (fixed 64 bytes)
            - textures (diffuse/normal/specular/opacity/envmap) as [len + bytes]
            - numeric params: specular (f32), alpha (f32)
            - render flags: two-sided (u8), transparent (u8), sort_bias (i32)
            - reserved fields
        """
        binw.write_u32(len(mats))
        for m in mats:
            self._write_single_material(binw, m)

    def _write_single_material(self, binw: BinaryWriter, mat: bpy.types.Material) -> None:
        # Material name (padded)
        name_padded = mat.name.encode('utf-8')[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)

        # Shader name: custom prop 'bw_shader' or default
        shader_name = mat.get("bw_shader", self.opts.default_shader)
        shader_padded = str(shader_name).encode('utf-8')[:SPEC.SHADER_LEN].ljust(SPEC.SHADER_LEN, b'\x00')
        binw.write_bytes(shader_padded)

        # Textures
        tex_paths = self._collect_textures(mat)

        # Standard set; write even if empty (len=0) to keep alignment
        self._write_texture(binw, tex_paths.get(SPEC.TEX_DIFFUSE))
        self._write_texture(binw, tex_paths.get(SPEC.TEX_NORMAL) if self.opts.write_normal else None)
        self._write_texture(binw, tex_paths.get(SPEC.TEX_SPECULAR) if self.opts.write_specular else None)
        self._write_texture(binw, tex_paths.get(SPEC.TEX_OPACITY) if self.opts.write_opacity else None)
        self._write_texture(binw, tex_paths.get(SPEC.TEX_ENVMAP) if self.opts.write_envmap else None)

        # Numeric params: specular, alpha (custom props or defaults)
        spec_value = float(mat.get("bw_specular", 1.0))
        alpha_value = float(mat.get("bw_alpha", 1.0))
        binw.write_f32(spec_value)
        binw.write_f32(alpha_value)

        # Render flags (two-sided, transparent) and sort bias (int32)
        two_sided = int(bool(mat.get("bw_two_sided", False)))
        transparent = int(bool(self._infer_transparent(mat)))
        sort_bias = int(mat.get("bw_sort_bias", 0))

        binw.write_u8(two_sided)
        binw.write_u8(transparent)
        binw.write_i32(sort_bias)

        # Reserved fields (kept for strict alignment)
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u32(SPEC.RESERVED_U32)

    # ====== Helpers ======
    def _collect_object_materials(self, obj: bpy.types.Object) -> List[bpy.types.Material]:
        """
        Collect materials from object material slots, maintain slot order.
        """
        mats: List[bpy.types.Material] = []
        if hasattr(obj, "material_slots"):
            for slot in obj.material_slots:
                if slot and slot.material:
                    mats.append(slot.material)
        # If object has no materials, still write count=0 (strict alignment at file level)
        return mats

    def _collect_textures(self, mat: bpy.types.Material) -> Dict[str, Optional[str]]:
        """
        Collect texture paths from material nodes or custom props.
        - Prefer custom props: 'bw_diffuse', 'bw_normal', 'bw_specular', 'bw_opacity', 'bw_envmap'
        - Fallback to Principled BSDF nodes where possible
        - Normalize all paths to relative, lowercase, POSIX
        """
        result: Dict[str, Optional[str]] = {
            SPEC.TEX_DIFFUSE: None,
            SPEC.TEX_NORMAL: None,
            SPEC.TEX_SPECULAR: None,
            SPEC.TEX_OPACITY: None,
            SPEC.TEX_ENVMAP: None,
        }

        # Custom props first
        for k in result.keys():
            prop_key = f"bw_{k}"
            if mat.get(prop_key):
                result[k] = ensure_posix_lower_relative_path(self.opts.export_root, str(mat.get(prop_key)))

        # Fallback: scan node tree (Principled BSDF)
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and node.image.filepath:
                    # Heuristic: map by node name or links
                    path_norm = ensure_posix_lower_relative_path(self.opts.export_root, node.image.filepath)
                    nm = node.name.lower()
                    if SPEC.TEX_DIFFUSE in nm or "basecolor" in nm or "albedo" in nm:
                        result[SPEC.TEX_DIFFUSE] = result[SPEC.TEX_DIFFUSE] or path_norm
                    elif SPEC.TEX_NORMAL in nm:
                        result[SPEC.TEX_NORMAL] = result[SPEC.TEX_NORMAL] or path_norm
                    elif SPEC.TEX_SPECULAR in nm or "metal" in nm or "spec" in nm:
                        result[SPEC.TEX_SPECULAR] = result[SPEC.TEX_SPECULAR] or path_norm
                    elif SPEC.TEX_OPACITY in nm or "opacity" in nm or "alpha" in nm:
                        result[SPEC.TEX_OPACITY] = result[SPEC.TEX_OPACITY] or path_norm
                    elif SPEC.TEX_ENVMAP in nm or "env" in nm or "cube" in nm:
                        result[SPEC.TEX_ENVMAP] = result[SPEC.TEX_ENVMAP] or path_norm

        return result

    def _write_texture(self, binw: BinaryWriter, path: Optional[str]) -> None:
        """
        Write texture path as [len + bytes]; empty if None.
        """
        if not path:
            binw.write_u32(0)
            return
        data = path.encode('utf-8')
        binw.write_u32(len(data))
        binw.write_bytes(data)

    def _infer_transparent(self, mat: bpy.types.Material) -> bool:
        """
        Infer transparency either via custom prop or from blend method/alpha usage.
        """
        if mat.get("bw_transparent") is not None:
            return bool(mat.get("bw_transparent"))
        # Blender heuristic
        try:
            if hasattr(mat, "blend_method"):
                return mat.blend_method in ('BLEND', 'HASHED')
        except Exception:
            pass
        return False


# ====== Convenience entry for legacy macro style ======
def export_visual_for_object(
    obj: bpy.types.Object,
    output_path: str,
    primitives_path: str,
    ctx: ExportContext,
    opts: MaterialExportOptions,
    expected_group_count: Optional[int] = None,
) -> None:
    """
    Convenience wrapper so Operator can call in one line, aligned with legacy export flow.
    """
    writer = MaterialWriter(ctx, opts)
    writer.write_visual(obj, output_path, primitives_path, expected_group_count)

