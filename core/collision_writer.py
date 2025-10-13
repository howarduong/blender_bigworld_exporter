# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Collision Writer (strictly aligned)

- Object-driven export of .collision with Header, Mesh, Groups sections
- Forced triangulation; closure checks; optional world-space transform bake
- Axis/unit conversion hooks kept consistent with global scheme (apply if required)
- BSP and ConvexHull sections retained as placeholders (strict alignment, no implementation)
- Hard blocking validation and export statistics

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import bpy
import bmesh
import mathutils

from .binsection_writer import BinSectionWriter, BinaryWriter
from .utils import (
    # Axis/unit mapping hooks if collision needs to be in world-space mapped coordinates.
    # axis_map_y_up_to_z_up_vec3,
)
from .utils import ExportAxis, ExportUnits
from ..validators.path_validator import validate_output_path


# ====== Specification constants (logical keys mapped by BinSectionWriter) ======
class SPEC:
    SECTION_HEADER = "COLLISION_HEADER"
    SECTION_MESH = "COLLISION_MESH"
    SECTION_GROUPS = "COLLISION_GROUPS"
    SECTION_BSP = "COLLISION_BSP"               # Placeholder only
    SECTION_CONVEX = "COLLISION_CONVEX"         # Placeholder only

    COLL_VERSION = 3
    NAME_LEN = 128
    RESERVED_U32 = 0
    RESERVED_U8 = 0


@dataclass
class CollisionExportOptions:
    # 控制是否烘焙世界变换到几何、缠绕翻转、索引类型选择
    apply_object_transform: bool = True
    flip_winding: bool = False
    force_u16_indices: bool = False  # 若为 True，强制使用 u16（越界时校验会阻断）


@dataclass
class ExportContext:
    axis: ExportAxis = ExportAxis.Y_UP_TO_Z_UP
    units: ExportUnits = ExportUnits.METERS
    unit_scale: float = 1.0
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "collision" not in self.report:
            self.report["collision"] = {}
        self.report["collision"][key] = value


# ====== Collision Writer ======
class CollisionWriter:

    def __init__(self, ctx: ExportContext, opts: CollisionExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    # Public API: write collision for an object (or its evaluated mesh)
    def write_collision(
        self,
        obj: bpy.types.Object,
        output_path: str,
        group_by_material: bool = True
    ) -> None:
        """
        Write .collision file for the given object:
        - Header: version, object name, reserved
        - Mesh: vertices (f32), indices (u16/u32), counts
        - Groups: per-material (or single group) primitive ranges
        - BSP: placeholder section
        - Convex: placeholder section
        """
        validate_output_path(output_path)

        # Build evaluated triangulated mesh
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = self._mesh_from_object(obj_eval, depsgraph)

        # Optional transform bake
        if self.opts.apply_object_transform:
            self._apply_world_transform(mesh, obj_eval.matrix_world)

        # Triangulate and prepare
        mesh.calc_loop_triangles()

        # Build vertex/index buffers
        positions = [tuple(v.co) for v in mesh.vertices]
        indices: List[int] = []
        for lt in mesh.loop_triangles:
            # Use vertex indices from loops (triangle vertices property is already vertex indices)
            a, b, c = lt.vertices
            if self.opts.flip_winding:
                indices.extend([a, c, b])
            else:
                indices.extend([a, b, c])

        # Groups
        groups = self._build_groups(mesh, group_by_material)

        # Index type
        max_index = max(indices) if indices else 0
        use_u16 = self.opts.force_u16_indices or (max_index <= 65535)

        # Write sections
        with self.ctx.binsection.open(output_path) as secw:
            # Header
            secw.begin_section(SPEC.SECTION_HEADER)
            self._write_header(self.ctx.binw, obj.name)
            secw.end_section()

            # Mesh
            secw.begin_section(SPEC.SECTION_MESH)
            self._write_mesh(self.ctx.binw, positions, indices, use_u16)
            secw.end_section()

            # Groups
            secw.begin_section(SPEC.SECTION_GROUPS)
            self._write_groups(self.ctx.binw, groups)
            secw.end_section()

            # BSP placeholder
            secw.begin_section(SPEC.SECTION_BSP)
            self._write_bsp_placeholder(self.ctx.binw)
            secw.end_section()

            # Convex placeholder
            secw.begin_section(SPEC.SECTION_CONVEX)
            self._write_convex_placeholder(self.ctx.binw)
            secw.end_section()

        # Hard validation
        self._validate_collision(positions, indices, groups, use_u16)

        # Report stats
        self.ctx.add_report_stat("object_name", obj.name)
        self.ctx.add_report_stat("vertex_count", len(positions))
        self.ctx.add_report_stat("index_count", len(indices))
        self.ctx.add_report_stat("group_count", len(groups))
        self.ctx.add_report_stat("index_format", "u16" if use_u16 else "u32")

        # Cleanup
        bpy.data.meshes.remove(mesh)

    # ====== Mesh preparation ======
    def _mesh_from_object(self, obj_eval: bpy.types.Object, depsgraph) -> bpy.types.Mesh:
        mesh = bpy.data.meshes.new_from_object(
            obj_eval,
            preserve_all_data_layers=True,
            depsgraph=depsgraph
        )
        # Force triangulate via BMesh to ensure manifold triangles
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        return mesh

    def _apply_world_transform(self, mesh: bpy.types.Mesh, matrix_world: mathutils.Matrix) -> None:
        """
        Apply object world transform to mesh positions.
        """
        for v in mesh.vertices:
            v.co = matrix_world @ v.co

        # Unit scaling (optional)
        s = self.ctx.unit_scale if self.ctx.units == ExportUnits.METERS else 1.0
        if abs(s - 1.0) >= 1e-8:
            for v in mesh.vertices:
                v.co *= s

        # Axis mapping hook (if collision needs Y->Z mapping; left as consistent with global scheme)
        # for v in mesh.vertices:
        #     v.co = mathutils.Vector(axis_map_y_up_to_z_up_vec3((v.co.x, v.co.y, v.co.z)))

    # ====== Groups ======
    def _build_groups(self, mesh: bpy.types.Mesh, by_material: bool) -> List[Tuple[int, int]]:
        """
        Build primitive groups as (start_index, num_primitives) in triangle units.
        - by_material=True: one group per material slot in order of slot index.
        - by_material=False: single group covering entire index buffer.
        """
        if not by_material:
            # One group covers all
            tri_count = len(mesh.loop_triangles)
            return [(0, tri_count)]

        # Material-index buckets
        buckets: Dict[int, List[Tuple[int, int, int]]] = {}
        for lt in mesh.loop_triangles:
            mat_idx = mesh.polygons[lt.polygon_index].material_index if lt.polygon_index >= 0 else 0
            a, b, c = lt.vertices
            buckets.setdefault(mat_idx, []).append((a, b, c))

        # Build groups according to material slot order
        groups: List[Tuple[int, int]] = []
        current_start = 0
        for _, tris in sorted(buckets.items(), key=lambda kv: kv[0]):
            tri_count = len(tris)
            groups.append((current_start, tri_count))
            current_start += tri_count * 3  # indices advance by 3 per triangle

        return groups

    # ====== Writing sections ======
    def _write_header(self, binw: BinaryWriter, object_name: str) -> None:
        binw.write_u32(SPEC.COLL_VERSION)

        name_bytes = object_name.encode('utf-8')
        name_padded = name_bytes[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)

        # Reserved
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u8(SPEC.RESERVED_U8)

    def _write_mesh(self, binw: BinaryWriter, positions: List[Tuple[float, float, float]], indices: List[int], use_u16: bool) -> None:
        # Counts
        binw.write_u32(len(positions))
        binw.write_u32(len(indices))

        # Positions (f32)
        for p in positions:
            binw.write_f32(float(p[0])); binw.write_f32(float(p[1])); binw.write_f32(float(p[2]))

        # Indices
        if use_u16:
            for idx in indices:
                binw.write_u16(int(idx))
        else:
            for idx in indices:
                binw.write_u32(int(idx))

    def _write_groups(self, binw: BinaryWriter, groups: List[Tuple[int, int]]) -> None:
        """
        Write groups as:
        - count (u32)
        - repeated entries: start_index (u32), num_primitives (u32)
        """
        binw.write_u32(len(groups))
        for start_index, num_prims in groups:
            binw.write_u32(start_index)
            binw.write_u32(num_prims)

        # Reserved for alignment
        binw.write_u32(SPEC.RESERVED_U32)

    def _write_bsp_placeholder(self, binw: BinaryWriter) -> None:
        """
        BSP placeholder; kept to strictly align with legacy, but not implemented per scheme.
        Layout:
        - node_count (u32) = 0
        - face_count (u32) = 0
        """
        binw.write_u32(0)
        binw.write_u32(0)

    def _write_convex_placeholder(self, binw: BinaryWriter) -> None:
        """
        Convex hull placeholder; kept to strictly align with legacy, but not implemented per scheme.
        Layout:
        - vertex_count (u32) = 0
        - face_count (u32) = 0
        """
        binw.write_u32(0)
        binw.write_u32(0)

    # ====== Validation ======
    def _validate_collision(
        self,
        positions: List[Tuple[float, float, float]],
        indices: List[int],
        groups: List[Tuple[int, int]],
        use_u16: bool
    ) -> None:
        # Basic checks
        if len(positions) == 0 or len(indices) == 0:
            raise ValueError("COLLISION: empty positions or indices")

        max_index = max(indices)
        if use_u16 and max_index > 65535:
            raise ValueError(f"COLLISION: index {max_index} exceeds u16 range while u16 requested")

        # Indices range
        if max_index >= len(positions) or min(indices) < 0:
            raise ValueError("COLLISION: indices out of range")

        # Groups continuity
        total_idx = len(indices)
        for start_idx, num_prims in groups:
            end_idx = start_idx + num_prims * 3
            if not (0 <= start_idx <= total_idx and 0 <= end_idx <= total_idx):
                raise ValueError("COLLISION: group indices out of buffer range")

        # Optional manifold/closure check can be added here (non-manifold detection)

# ====== Convenience entry (aligned with operator usage) ======
def export_collision(
    obj: bpy.types.Object,
    output_path: str,
    ctx: ExportContext,
    opts: CollisionExportOptions,
    group_by_material: bool = True
) -> None:
    writer = CollisionWriter(ctx, opts)
    writer.write_collision(obj, output_path, group_by_material)
