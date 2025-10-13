# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Model Writer (strictly aligned)

- Object-driven export of .model with Header, NodeTree, References sections
- Strict placeholders for legacy/excluded features (kept as empty/default)
- Matrix handling unified with primitives/skeleton (axis/unit, consistent order)
- Relative path normalization and reserved fields preserved
- Portal/HardPoint/Hitbox node markers retained (metadata placeholders)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import bpy
import mathutils

from .binsection_writer import BinSectionWriter, BinaryWriter
from .utils import (
    axis_map_y_up_to_z_up_matrix,
    ensure_posix_lower_relative_path,
)
from .utils import ExportAxis, ExportUnits
from ..validators.path_validator import validate_output_path


# ====== Specification constants (logical keys mapped by BinSectionWriter) ======
class SPEC:
    SECTION_HEADER = "MODEL_HEADER"
    SECTION_NODETREE = "MODEL_NODETREE"
    SECTION_REFERENCES = "MODEL_REFERENCES"

    # Header reserved defaults (kept even if unused)
    HEADER_VERSION = 3           # legacy-compatible model header version (example)
    RESERVED_U32 = 0
    RESERVED_U8 = 0

    # Node flags (bitfield placeholders)
    NODE_FLAG_DEFAULT = 0
    NODE_FLAG_HARDPOINT = 1 << 0
    NODE_FLAG_PORTAL = 1 << 1
    NODE_FLAG_HITBOX = 1 << 2

    # Reference slots (always write, even if empty)
    REF_VISUAL = 0
    REF_PRIMITIVES = 1
    REF_ANIMATION = 2
    REF_COLLISION = 3
    REF_COUNT = 4


@dataclass
class ModelExportOptions:
    # 控制是否写 Portal/HardPoint/Hitbox 标记，以及矩阵展开策略
    write_portals: bool = True
    write_hardpoints: bool = True
    write_hitbox_nodes: bool = True
    matrix_row_major: bool = True   # True: row-major flatten; False: col-major
    apply_scene_unit_scale: bool = True


@dataclass
class ExportContext:
    axis: ExportAxis = ExportAxis.Y_UP_TO_Z_UP
    units: ExportUnits = ExportUnits.METERS
    unit_scale: float = 1.0
    export_root: str = ""
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "model" not in self.report:
            self.report["model"] = {}
        self.report["model"][key] = value


# ====== Model Writer ======
class ModelWriter:

    def __init__(self, ctx: ExportContext, opts: ModelExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    # Public API
    def write_model(
        self,
        root_obj: bpy.types.Object,
        output_path: str,
        references: Dict[str, Optional[str]],
    ) -> None:
        """
        Write a .model file for the given root object.
        references keys (all optional but must be present as placeholders):
          - "visual": path to .visual
          - "primitives": path to .primitives
          - "animation": path to .animation (or supermodel chain), kept even if None
          - "collision": path to collision data
        """
        validate_output_path(output_path)

        with self.ctx.binsection.open(output_path) as secw:
            # Header
            secw.begin_section(SPEC.SECTION_HEADER)
            self._write_header(self.ctx.binw, root_obj)
            secw.end_section()

            # NodeTree (hierarchical)
            secw.begin_section(SPEC.SECTION_NODETREE)
            self._write_node_tree(self.ctx.binw, root_obj)
            secw.end_section()

            # References (paths normalized, placeholders written)
            secw.begin_section(SPEC.SECTION_REFERENCES)
            self._write_references(self.ctx.binw, references)
            secw.end_section()

        # Report
        self.ctx.add_report_stat("root_object", root_obj.name)
        self.ctx.add_report_stat("node_count", self._count_nodes_recursive(root_obj))
        self.ctx.add_report_stat("matrix_order", "row-major" if self.opts.matrix_row_major else "col-major")

    # ====== Header ======

    def _write_header(self, binw: BinaryWriter, root_obj: bpy.types.Object) -> None:
        """
        Header fields (kept aligned with legacy):
        - version (u32)
        - axis_mode (u8)  : 0=identity, 1=Y->Z
        - unit_scale (f32)
        - apply_scene_unit_scale (u8)
        - object_name (fixed 128 bytes utf8, padded)
        - reserved fields
        """
        version = SPEC.HEADER_VERSION
        axis_mode = 1 if self.ctx.axis == ExportAxis.Y_UP_TO_Z_UP else 0
        unit_scale = self.ctx.unit_scale if self.opts.apply_scene_unit_scale and self.ctx.units == ExportUnits.METERS else 1.0
        apply_scale_flag = 1 if (self.opts.apply_scene_unit_scale and self.ctx.units == ExportUnits.METERS) else 0

        binw.write_u32(version)
        binw.write_u8(axis_mode)
        binw.write_f32(unit_scale)
        binw.write_u8(apply_scale_flag)

        # object name padded to 128 bytes
        name_bytes = root_obj.name.encode('utf-8')
        name_padded = name_bytes[:128].ljust(128, b'\x00')
        binw.write_bytes(name_padded)

        # reserved placeholders
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u8(SPEC.RESERVED_U8)

    # ====== Node Tree ======

    def _write_node_tree(self, binw: BinaryWriter, root_obj: bpy.types.Object) -> None:
        """
        NodeTree layout (per node):
        - name (fixed 128 bytes)
        - flags (u32)       : default/hardpoint/portal/hitbox
        - transform (16 * f32) : row-major or col-major flattened after axis/unit mapping
        - child_count (u32)
        - children (recurse)
        """
        nodes = self._collect_hierarchy(root_obj)

        # Write root count (often 1 for a single model root)
        binw.write_u32(len(nodes))

        for node in nodes:
            self._write_single_node(binw, node)

    def _collect_hierarchy(self, root_obj: bpy.types.Object) -> List[bpy.types.Object]:
        """
        Collect a list of root-level nodes (usually the root object itself). If multiple
        selected roots are to be supported, adapt this to a list passed by operator.
        """
        return [root_obj]

    def _write_single_node(self, binw: BinaryWriter, node_obj: bpy.types.Object) -> None:
        # Node name padded
        name_bytes = node_obj.name.encode('utf-8')
        name_padded = name_bytes[:128].ljust(128, b'\x00')
        binw.write_bytes(name_padded)

        # Node flags (metadata from custom props)
        flags = self._compute_node_flags(node_obj)
        binw.write_u32(flags)

        # Transform matrix (axis/unit applied, flattened)
        mat = self._get_world_matrix(node_obj)
        mat_mapped = axis_map_y_up_to_z_up_matrix(mat) if self.ctx.axis == ExportAxis.Y_UP_TO_Z_UP else mat
        mat_scaled = self._apply_unit_matrix(mat_mapped)

        self._write_matrix(binw, mat_scaled, row_major=self.opts.matrix_row_major)

        # Children
        children = [c for c in node_obj.children]
        binw.write_u32(len(children))
        for child in children:
            self._write_single_node(binw, child)

    def _get_world_matrix(self, obj: bpy.types.Object) -> mathutils.Matrix:
        """
        Prefer the evaluated depsgraph for final transforms if needed;
        here we use obj.matrix_world directly (UI/operator ensures correctness).
        """
        return obj.matrix_world.copy()

    def _apply_unit_matrix(self, mat: mathutils.Matrix) -> mathutils.Matrix:
        """
        Apply uniform scale to matrix based on unit settings. Only scale components affected.
        """
        s = self.ctx.unit_scale if (self.opts.apply_scene_unit_scale and self.ctx.units == ExportUnits.METERS) else 1.0
        if abs(s - 1.0) < 1e-8:
            return mat

        scale_mat = mathutils.Matrix.Scale(s, 4)
        return scale_mat @ mat

    def _compute_node_flags(self, obj: bpy.types.Object) -> int:
        """
        Compute flags using custom properties or naming conventions.
        We keep placeholders to strictly align with legacy fields.
        """
        flags = SPEC.NODE_FLAG_DEFAULT

        if self.opts.write_hardpoints and self._is_hardpoint(obj):
            flags |= SPEC.NODE_FLAG_HARDPOINT

        if self.opts.write_portals and self._is_portal(obj):
            flags |= SPEC.NODE_FLAG_PORTAL

        if self.opts.write_hitbox_nodes and self._is_hitbox_node(obj):
            flags |= SPEC.NODE_FLAG_HITBOX

        return flags

    def _is_hardpoint(self, obj: bpy.types.Object) -> bool:
        """
        Legacy naming scheme often uses 'HP_' or custom props.
        We accept either a prop 'bw_hardpoint' == True or name startswith 'HP_'.
        """
        return bool(obj.get("bw_hardpoint", False)) or obj.name.upper().startswith("HP_")

    def _is_portal(self, obj: bpy.types.Object) -> bool:
        """
        Portal markers via custom prop 'bw_portal' or name prefix 'PORTAL_'.
        Values may carry types (Exit/Heaven/Standard/Label) but here we only set the flag.
        """
        return bool(obj.get("bw_portal", False)) or obj.name.upper().startswith("PORTAL_")

    def _is_hitbox_node(self, obj: bpy.types.Object) -> bool:
        """
        Hitbox node marker via prop 'bw_hitbox_node' or name startswith '_bwhitbox'.
        """
        return bool(obj.get("bw_hitbox_node", False)) or obj.name.lower().startswith("_bwhitbox")

    def _write_matrix(self, binw: BinaryWriter, mat: mathutils.Matrix, row_major: bool) -> None:
        """
        Flatten 4x4 matrix into 16 f32 elements, row-major or col-major,
        must be consistent with skeleton/primitives usages.
        """
        if row_major:
            for r in range(4):
                for c in range(4):
                    binw.write_f32(mat[r][c])
        else:
            for c in range(4):
                for r in range(4):
                    binw.write_f32(mat[r][c])

    def _count_nodes_recursive(self, root: bpy.types.Object) -> int:
        cnt = 1
        for c in root.children:
            cnt += self._count_nodes_recursive(c)
        return cnt

    # ====== References ======

    def _write_references(self, binw: BinaryWriter, refs: Dict[str, Optional[str]]) -> None:
        """
        References layout:
        - count (u32) : always SPEC.REF_COUNT
        - For each slot (visual/primitives/animation/collision):
            - path length (u32), path bytes (utf8, lower, posix, relative to export_root)
        Empty references are written as zero-length strings (strict alignment).
        """
        binw.write_u32(SPEC.REF_COUNT)

        # Visual
        self._write_ref_path(binw, refs.get("visual"))

        # Primitives
        self._write_ref_path(binw, refs.get("primitives"))

        # Animation (placeholder even if None)
        self._write_ref_path(binw, refs.get("animation"))

        # Collision (placeholder even if None)
        self._write_ref_path(binw, refs.get("collision"))

        # Reserved for future alignment
        binw.write_u32(SPEC.RESERVED_U32)

    def _write_ref_path(self, binw: BinaryWriter, path: Optional[str]) -> None:
        if not path:
            binw.write_u32(0)
            return

        norm = ensure_posix_lower_relative_path(self.ctx.export_root, path)
        data = norm.encode('utf-8')
        binw.write_u32(len(data))
        binw.write_bytes(data)


# ====== Convenience entry (kept for strict alignment with legacy macro style) ======
def export_model(
    root_obj: bpy.types.Object,
    output_path: str,
    ctx: ExportContext,
    opts: ModelExportOptions,
    references: Dict[str, Optional[str]],
) -> None:
    writer = ModelWriter(ctx, opts)
    writer.write_model(root_obj, output_path, references)
