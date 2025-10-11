# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Primitives Writer (strictly aligned)

- Object-driven, no bpy.context.active_object reliance
- Loop-triangle based indexing
- Material buckets => global contiguous index buffer + primitive group table
- Unified axis/unit conversion for positions/normals/tangents
- Per-loop vertex domain (corner attributes) with optional per-vertex fallback
- Top-4 bone weights & indices export
- BinSection controlled layout (IDs, names, alignment delegated to binsection_writer)
- Post-write hard validation & export statistics report

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import bpy
import bmesh

from .binsection_writer import BinSectionWriter, BinaryWriter
from .utils import (
    axis_map_y_up_to_z_up_vec3,
    axis_map_y_up_to_z_up_vec4,
    axis_map_y_up_to_z_up_tangent,
    ensure_posix_lower_relative_path,
)
from .utils import ExportAxis, ExportUnits
from .validators.structure_checker import (
    validate_primitives_topology,
    validate_primitives_groups,
    validate_vertex_streams,
)
from .validators.path_validator import validate_output_path


# ====== Specification constants (placeholders mapped to legacy Max plugin spec) ======
# 这些常量名称与布局需与旧版 Max 插件输出一致。具体 ID/名称通过 binsection_writer 统一控制。
class SPEC:
    # Section IDs / names are controlled by BinSectionWriter; we pass logical keys here.
    SECTION_VERTICES = "PRIM_VERTICES"
    SECTION_INDICES = "PRIM_INDICES"
    VERTEX_FORMAT_NAME_LEN = 64
    INDEX_FORMAT_NAME_LEN = 64
    INDEX_FORMAT_U16 = "list"     # 16-bit
    INDEX_FORMAT_U32 = "list32"   # 32-bit

    # Vertex declaration names to mirror Max plugin (examples; ensure they match legacy)
    # Choose one based on domain and attributes presence.
    VERT_DECL_XYZN_UV = "xyznuv"
    VERT_DECL_XYZN_UV_TB = "xyznuvtb"
    VERT_DECL_SKIN_XYZN_UV_TB = "skin_xyznuvtb"

    # Reserve flags / placeholders (kept for strict alignment even if not used)
    RESERVED_U32 = 0
    RESERVED_U8 = 0


@dataclass
class MeshExportOptions:
    # 控制 winding 翻转、顶点域和 UV 层等
    flip_winding: bool = False
    vertex_domain: str = "LOOP"  # "LOOP" or "VERTEX"
    active_uv_name: Optional[str] = None
    secondary_uv_name: Optional[str] = None
    write_tangents: bool = True
    write_vertex_colors: bool = True
    write_skin_weights: bool = True


@dataclass
class ExportContext:
    # 全局策略：坐标系、单位、输出根目录、日志/报告
    axis: ExportAxis = ExportAxis.Y_UP_TO_Z_UP
    units: ExportUnits = ExportUnits.METERS
    unit_scale: float = 1.0  # 由 preferences 决定
    export_root: str = ""
    report: Dict = field(default_factory=dict)
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None

    def add_report_stat(self, key: str, value):
        if "primitives" not in self.report:
            self.report["primitives"] = {}
        self.report["primitives"][key] = value


# ====== Internal data structures ======
@dataclass
class VertexStreams:
    positions: List[Tuple[float, float, float]] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)
    tangents: List[Tuple[float, float, float, float]] = field(default_factory=list)  # xyz + sign
    uv0: List[Tuple[float, float]] = field(default_factory=list)
    uv1: List[Tuple[float, float]] = field(default_factory=list)
    colors: List[Tuple[float, float, float, float]] = field(default_factory=list)  # normalized 0..1
    bone_indices: List[Tuple[int, int, int, int]] = field(default_factory=list)
    bone_weights: List[Tuple[float, float, float, float]] = field(default_factory=list)

    def count(self) -> int:
        return len(self.positions)


@dataclass
class PrimitiveGroup:
    start_index: int
    num_primitives: int  # triangles count
    start_vertex: int
    num_vertices: int


# ====== Primitives Writer ======
class PrimitivesWriter:

    def __init__(self, ctx: ExportContext, opts: MeshExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    # Public API: strictly object-driven
    def write_object(self, obj: bpy.types.Object, output_path: str) -> None:
        # Validate output path
        validate_output_path(output_path)

        # Evaluate object to mesh with modifiers
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)

        mesh = self._mesh_from_object(obj_eval, depsgraph)

        # Prepare geometry domain
        active_uv_name = self._resolve_active_uv(mesh)
        self._prepare_mesh(mesh, active_uv_name)

        # Build indices (loop-triangle based) and material groups
        lt = mesh.loop_triangles
        buckets = self._bucketize_by_material(mesh, lt)
        indices, groups = self._build_indices_and_groups(buckets)

        if self.opts.flip_winding:
            self._flip_winding(indices)

        # Build vertex streams (LOOP domain by default)
        streams = self._build_vertex_streams(obj, mesh, lt, active_uv_name)

        # Axis & unit conversion
        self._apply_axis_unit(streams)

        # Choose vertex declaration name (aligned with legacy)
        vert_decl = self._choose_vertex_decl(streams)

        # Choose index format
        max_index = max(indices) if indices else 0
        use_u16 = max_index <= 65535
        index_format_name = SPEC.INDEX_FORMAT_U16 if use_u16 else SPEC.INDEX_FORMAT_U32

        # Write BinSections
        with self.ctx.binsection.open(output_path) as secw:
            # Vertex section
            secw.begin_section(SPEC.SECTION_VERTICES)
            self._write_vertex_header(self.ctx.binw, vert_decl, streams.count())
            self._write_vertex_streams(self.ctx.binw, streams, vert_decl)
            secw.end_section()

            # Index section
            secw.begin_section(SPEC.SECTION_INDICES)
            self._write_index_header(self.ctx.binw, index_format_name, len(indices), len(groups))
            self._write_indices(self.ctx.binw, indices, use_u16)
            self._write_primitive_groups(self.ctx.binw, groups)
            secw.end_section()

        # Post validations (hard block upstream if fails)
        validate_vertex_streams(streams)
        validate_primitives_topology(streams, indices)
        validate_primitives_groups(indices, groups, streams.count())

        # Report stats
        self.ctx.add_report_stat("object_name", obj.name)
        self.ctx.add_report_stat("vertex_count", streams.count())
        self.ctx.add_report_stat("index_count", len(indices))
        self.ctx.add_report_stat("primitive_groups", len(groups))
        self.ctx.add_report_stat("index_format", index_format_name)
        self.ctx.add_report_stat("vertex_decl", vert_decl)

        # Cleanup
        bpy.data.meshes.remove(mesh)

    # ====== Mesh preparation and domain helpers ======

    def _mesh_from_object(self, obj_eval: bpy.types.Object, depsgraph) -> bpy.types.Mesh:
        # Create evaluated mesh (preserve all layers)
        mesh = bpy.data.meshes.new_from_object(
            obj_eval,
            preserve_all_data_layers=True,
            depsgraph=depsgraph
        )
        return mesh

    def _resolve_active_uv(self, mesh: bpy.types.Mesh) -> Optional[str]:
        if self.opts.active_uv_name:
            return self.opts.active_uv_name
        if mesh.uv_layers and mesh.uv_layers.active:
            return mesh.uv_layers.active.name
        return mesh.uv_layers[0].name if mesh.uv_layers else None

    def _prepare_mesh(self, mesh: bpy.types.Mesh, active_uv_name: Optional[str]) -> None:
        mesh.calc_loop_triangles()
        mesh.calc_normals_split()
        if self.opts.write_tangents and active_uv_name:
            try:
                mesh.calc_tangents(uvmap=active_uv_name)
            except RuntimeError:
                # Fallback: no tangents if calc failed
                pass

    # ====== Index building with material buckets ======

    def _bucketize_by_material(
        self,
        mesh: bpy.types.Mesh,
        loop_tris: bpy.types.MeshLoopTriangleVertices
    ) -> Dict[int, List[Tuple[int, int, int]]]:
        """
        Returns dictionary: material_index -> list of triangles (indices are vertex indices).
        """
        buckets: Dict[int, List[Tuple[int, int, int]]] = {}
        poly_by_loop = mesh.polygons

        for lt in mesh.loop_triangles:
            # polygon index for material
            poly_idx = lt.polygon_index
            mat_idx = poly_by_loop[poly_idx].material_index if poly_idx >= 0 else 0
            tri = (mesh.loops[lt.loops[0]].vertex_index,
                   mesh.loops[lt.loops[1]].vertex_index,
                   mesh.loops[lt.loops[2]].vertex_index)
            buckets.setdefault(mat_idx, []).append(tri)

        # Stabilize material order by slot index
        return dict(sorted(buckets.items(), key=lambda kv: kv[0]))

    def _build_indices_and_groups(
        self,
        buckets: Dict[int, List[Tuple[int, int, int]]]
    ) -> Tuple[List[int], List[PrimitiveGroup]]:
        """
        Build a single global contiguous index buffer by concatenating per-material triangles,
        and a primitive group table aligned to legacy Max plugin expectations.
        """
        indices: List[int] = []
        groups: List[PrimitiveGroup] = []
        current_start_index = 0

        # For start_vertex / num_vertices, we compute per-bucket ranges from used vertex indices.
        for _, tris in buckets.items():
            # Append indices for this material in order
            for (a, b, c) in tris:
                indices.extend([a, b, c])

            # Compute primitive group for this material
            num_prims = len(tris)
            start_idx = current_start_index
            idx_count = num_prims * 3

            # Vertex range in this group
            used_vertices = set()
            for (a, b, c) in tris:
                used_vertices.update([a, b, c])
            start_v = min(used_vertices) if used_vertices else 0
            num_v = (max(used_vertices) - start_v + 1) if used_vertices else 0

            groups.append(PrimitiveGroup(
                start_index=start_idx,
                num_primitives=num_prims,
                start_vertex=start_v,
                num_vertices=num_v
            ))

            current_start_index += idx_count

        return indices, groups

    def _flip_winding(self, indices: List[int]) -> None:
        """
        Flip triangle winding globally: swap second and third index per triangle.
        """
        for i in range(0, len(indices), 3):
            if i + 2 < len(indices):
                indices[i + 1], indices[i + 2] = indices[i + 2], indices[i + 1]

    # ====== Vertex streams (LOOP domain preferred) ======

    def _build_vertex_streams(
        self,
        obj: bpy.types.Object,
        mesh: bpy.types.Mesh,
        loop_tris,
        active_uv_name: Optional[str]
    ) -> VertexStreams:
        """
        Constructs vertex streams in LOOP domain (corner attributes).
        If vertex domain requested, falls back to vertex attributes packing.
        """
        if self.opts.vertex_domain.upper() == "VERTEX":
            return self._build_vertex_streams_vertex_domain(obj, mesh, active_uv_name)
        else:
            return self._build_vertex_streams_loop_domain(obj, mesh, loop_tris, active_uv_name)

    def _build_vertex_streams_loop_domain(
        self,
        obj: bpy.types.Object,
        mesh: bpy.types.Mesh,
        loop_tris,
        active_uv_name: Optional[str]
    ) -> VertexStreams:
        streams = VertexStreams()

        # Loop-domain expansion: each loop corner becomes one vertex
        # For each triangle corner, collect position, normal, tangent(sign), uv(s), color, weights.
        loops = mesh.loops
        verts = mesh.vertices

        # Map UV layer
        uv_layer = mesh.uv_layers.get(active_uv_name) if active_uv_name else (mesh.uv_layers[0] if mesh.uv_layers else None)
        uv_data = uv_layer.data if uv_layer else None

        uv1_layer = mesh.uv_layers.get(self.opts.secondary_uv_name) if self.opts.secondary_uv_name else None
        uv1_data = uv1_layer.data if uv1_layer else None

        # Vertex color (corner domain)
        color_layer = None
        if self.opts.write_vertex_colors:
            for ca in mesh.color_attributes:
                if ca.domain == 'CORNER' and ca.data_type in ('BYTE_COLOR', 'FLOAT_COLOR'):
                    color_layer = ca.data
                    break

        # Armature weights mapping
        use_skin = self.opts.write_skin_weights and obj.find_armature() is not None
        bone_index_map = {}
        if use_skin:
            arm = obj.find_armature()
            bone_index_map = self._build_bone_index_map(arm)
        vg_by_index = {vg.index: vg for vg in obj.vertex_groups} if use_skin else {}

        # Tangents per loop
        has_tangent = self.opts.write_tangents and hasattr(loops[0], "tangent") if len(loops) > 0 else False

        for lt in mesh.loop_triangles:
            for corner in lt.loops:
                loop = loops[corner]
                v = verts[loop.vertex_index]

                # Position
                pos = tuple(v.co)

                # Normal (split normals per loop)
                nrm = tuple(loop.normal)

                # Tangent
                if has_tangent:
                    tan = tuple(loop.tangent) + (loop.bitangent_sign,)
                else:
                    tan = (0.0, 0.0, 0.0, 1.0)

                # UV0
                if uv_data:
                    uv = uv_data[corner].uv
                    uv0 = (uv.x, uv.y)
                else:
                    uv0 = (0.0, 0.0)

                # UV1
                if uv1_data:
                    uvx = uv1_data[corner].uv
                    uv1 = (uvx.x, uvx.y)
                else:
                    uv1 = (0.0, 0.0)

                # Color
                if color_layer:
                    col = color_layer[corner].color
                    # Normalize to 0..1 float4 regardless of internal storage
                    color = (float(col[0]), float(col[1]), float(col[2]), float(col[3]))
                else:
                    color = (1.0, 1.0, 1.0, 1.0)

                # Skin weights / indices (Top-4)
                if use_skin:
                    idxs, wts = self._collect_top4_weights(v, vg_by_index, bone_index_map)
                else:
                    idxs = (0, 0, 0, 0)
                    wts = (1.0, 0.0, 0.0, 0.0)

                streams.positions.append(pos)
                streams.normals.append(nrm)
                streams.tangents.append(tan)
                streams.uv0.append(uv0)
                streams.uv1.append(uv1)
                streams.colors.append(color)
                streams.bone_indices.append(idxs)
                streams.bone_weights.append(wts)

        return streams

    def _build_vertex_streams_vertex_domain(
        self,
        obj: bpy.types.Object,
        mesh: bpy.types.Mesh,
        active_uv_name: Optional[str]
    ) -> VertexStreams:
        """
        Vertex-domain packing: one vertex per mesh vertex. Corner attributes will be averaged,
        only use this if legacy spec explicitly requires per-vertex attributes.
        """
        streams = VertexStreams()

        verts = mesh.vertices
        loops = mesh.loops
        poly_count = len(mesh.polygons)

        # UV layers
        uv_layer = mesh.uv_layers.get(active_uv_name) if active_uv_name else (mesh.uv_layers[0] if mesh.uv_layers else None)
        uv_data = uv_layer.data if uv_layer else None

        uv1_layer = mesh.uv_layers.get(self.opts.secondary_uv_name) if self.opts.secondary_uv_name else None
        uv1_data = uv1_layer.data if uv1_layer else None

        # Vertex color (vertex domain or averaged corner)
        color_layer_corner = None
        if self.opts.write_vertex_colors:
            for ca in mesh.color_attributes:
                if ca.domain == 'CORNER':
                    color_layer_corner = ca.data
                    break

        # Armature
        use_skin = self.opts.write_skin_weights and obj.find_armature() is not None
        bone_index_map = {}
        if use_skin:
            arm = obj.find_armature()
            bone_index_map = self._build_bone_index_map(arm)
        vg_by_index = {vg.index: vg for vg in obj.vertex_groups} if use_skin else {}

        # Average helpers
        corner_map: Dict[int, List[int]] = {i: [] for i in range(len(verts))}
        for i, loop in enumerate(loops):
            corner_map[loop.vertex_index].append(i)

        for v_idx, v in enumerate(verts):
            pos = tuple(v.co)
            # Average normal from loops that point to this vertex
            acc_n = [0.0, 0.0, 0.0]
            for li in corner_map[v_idx]:
                ln = loops[li].normal
                acc_n[0] += ln.x
                acc_n[1] += ln.y
                acc_n[2] += ln.z
            if len(corner_map[v_idx]) > 0:
                inv = 1.0 / float(len(corner_map[v_idx]))
                nrm = (acc_n[0]*inv, acc_n[1]*inv, acc_n[2]*inv)
            else:
                nrm = (0.0, 0.0, 1.0)

            # Tangents: best effort (average or zeros)
            acc_t = [0.0, 0.0, 0.0]
            acc_sign = 0.0
            for li in corner_map[v_idx]:
                if hasattr(loops[li], "tangent"):
                    lt = loops[li].tangent
                    acc_t[0] += lt.x
                    acc_t[1] += lt.y
                    acc_t[2] += lt.z
                    acc_sign += getattr(loops[li], "bitangent_sign", 1.0)
            if len(corner_map[v_idx]) > 0:
                inv = 1.0 / float(len(corner_map[v_idx]))
                tan = (acc_t[0]*inv, acc_t[1]*inv, acc_t[2]*inv, acc_sign*inv if acc_sign != 0.0 else 1.0)
            else:
                tan = (0.0, 0.0, 0.0, 1.0)

            # UV0 averaged
            if uv_data:
                uacc = [0.0, 0.0]
                for li in corner_map[v_idx]:
                    uv = uv_data[li].uv
                    uacc[0] += uv.x
                    uacc[1] += uv.y
                inv = 1.0 / float(len(corner_map[v_idx])) if len(corner_map[v_idx]) else 1.0
                uv0 = (uacc[0]*inv, uacc[1]*inv)
            else:
                uv0 = (0.0, 0.0)

            # UV1 averaged
            if uv1_data:
                uacc1 = [0.0, 0.0]
                for li in corner_map[v_idx]:
                    uvx = uv1_data[li].uv
                    uacc1[0] += uvx.x
                    uacc1[1] += uvx.y
                inv = 1.0 / float(len(corner_map[v_idx])) if len(corner_map[v_idx]) else 1.0
                uv1 = (uacc1[0]*inv, uacc1[1]*inv)
            else:
                uv1 = (0.0, 0.0)

            # Color averaged from corner
            if color_layer_corner:
                cacc = [0.0, 0.0, 0.0, 0.0]
                for li in corner_map[v_idx]:
                    col = color_layer_corner[li].color
                    cacc[0] += float(col[0])
                    cacc[1] += float(col[1])
                    cacc[2] += float(col[2])
                    cacc[3] += float(col[3])
                inv = 1.0 / float(len(corner_map[v_idx])) if len(corner_map[v_idx]) else 1.0
                color = (cacc[0]*inv, cacc[1]*inv, cacc[2]*inv, cacc[3]*inv)
            else:
                color = (1.0, 1.0, 1.0, 1.0)

            # Skin weights
            if use_skin:
                idxs, wts = self._collect_top4_weights(v, vg_by_index, bone_index_map)
            else:
                idxs = (0, 0, 0, 0)
                wts = (1.0, 0.0, 0.0, 0.0)

            streams.positions.append(pos)
            streams.normals.append(nrm)
            streams.tangents.append(tan)
            streams.uv0.append(uv0)
            streams.uv1.append(uv1)
            streams.colors.append(color)
            streams.bone_indices.append(idxs)
            streams.bone_weights.append(wts)

        return streams

    # ====== Axis / Unit conversion ======

    def _apply_axis_unit(self, streams: VertexStreams) -> None:
        s = self.ctx.unit_scale if self.ctx.units == ExportUnits.METERS else 1.0

        # Positions
        for i, p in enumerate(streams.positions):
            streams.positions[i] = axis_map_y_up_to_z_up_vec3((p[0]*s, p[1]*s, p[2]*s))

        # Normals
        for i, n in enumerate(streams.normals):
            streams.normals[i] = axis_map_y_up_to_z_up_vec3(n)

        # Tangents
        for i, t in enumerate(streams.tangents):
            streams.tangents[i] = axis_map_y_up_to_z_up_tangent(t)

        # UVs: leave as-is (unless spec defines flipping V), reserved hook
        # Colors: leave normalized floats as-is

    # ====== Skin weights helpers ======

    def _build_bone_index_map(self, armature_obj: bpy.types.Object) -> Dict[str, int]:
        """
        Map bone name to index; assumes pose bones order stable or uses enumerated order.
        """
        bone_index_map: Dict[str, int] = {}
        idx = 0
        for bone in armature_obj.data.bones:
            bone_index_map[bone.name] = idx
            idx += 1
        return bone_index_map

    def _collect_top4_weights(
        self,
        v: bpy.types.MeshVertex,
        vg_by_index: Dict[int, bpy.types.VertexGroup],
        bone_index_map: Dict[str, int]
    ) -> Tuple[Tuple[int, int, int, int], Tuple[float, float, float, float]]:
        """
        Collect top-4 weights for a vertex and map to bone indices.
        """
        weights: List[Tuple[int, float]] = []  # (bone_index, weight)

        for g in v.groups:
            vg = vg_by_index.get(g.group)
            if vg is None:
                continue
            # Vertex group name corresponds to bone name
            bone_idx = bone_index_map.get(vg.name, None)
            if bone_idx is None:
                continue
            weights.append((bone_idx, g.weight))

        # Sort and take top-4
        weights.sort(key=lambda x: x[1], reverse=True)
        top = weights[:4]

        # Pad to 4
        while len(top) < 4:
            top.append((0, 0.0))

        # Normalize
        total = sum(w for _, w in top)
        if total <= 1e-8:
            # default to full weight on slot 0
            indices = (top[0][0], top[1][0], top[2][0], top[3][0])
            weights_out = (1.0, 0.0, 0.0, 0.0)
        else:
            inv = 1.0 / total
            indices = (top[0][0], top[1][0], top[2][0], top[3][0])
            weights_out = (top[0][1]*inv, top[1][1]*inv, top[2][1]*inv, top[3][1]*inv)

        return indices, weights_out

    # ====== Vertex/Index writing ======

    def _choose_vertex_decl(self, streams: VertexStreams) -> str:
        # Prefer skin decl if weights present (heuristic)
        has_skin = any(w != (1.0, 0.0, 0.0, 0.0) for w in streams.bone_weights)
        has_tan = self.opts.write_tangents and len(streams.tangents) == streams.count()
        if has_skin and has_tan:
            return SPEC.VERT_DECL_SKIN_XYZN_UV_TB
        if has_tan:
            return SPEC.VERT_DECL_XYZN_UV_TB
        return SPEC.VERT_DECL_XYZN_UV

    def _write_vertex_header(self, binw: BinaryWriter, decl_name: str, num_vertices: int) -> None:
        # 64-byte vertex format name (padded)
        name_bytes = decl_name.encode('utf-8')
        name_padded = name_bytes[:SPEC.VERTEX_FORMAT_NAME_LEN].ljust(SPEC.VERTEX_FORMAT_NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)
        binw.write_u32(num_vertices)

    def _write_vertex_streams(self, binw: BinaryWriter, streams: VertexStreams, decl_name: str) -> None:
        # Write raw vertex data in the order expected by the declaration
        # Positions
        for p in streams.positions:
            binw.write_f32(p[0]); binw.write_f32(p[1]); binw.write_f32(p[2])

        # Normals
        for n in streams.normals:
            binw.write_f32(n[0]); binw.write_f32(n[1]); binw.write_f32(n[2])

        # UV0
        for uv in streams.uv0:
            binw.write_f32(uv[0]); binw.write_f32(uv[1])

        # UV1
        for uv in streams.uv1:
            binw.write_f32(uv[0]); binw.write_f32(uv[1])

        # Tangents (if decl requires)
        if "tb" in decl_name:
            for t in streams.tangents:
                binw.write_f32(t[0]); binw.write_f32(t[1]); binw.write_f32(t[2]); binw.write_f32(t[3])

        # Colors
        for c in streams.colors:
            binw.write_f32(c[0]); binw.write_f32(c[1]); binw.write_f32(c[2]); binw.write_f32(c[3])

        # Skin weights/indices (if skin decl)
        if "skin_" in decl_name:
            for bi in streams.bone_indices:
                binw.write_u16(bi[0]); binw.write_u16(bi[1]); binw.write_u16(bi[2]); binw.write_u16(bi[3])
            for bw in streams.bone_weights:
                binw.write_f32(bw[0]); binw.write_f32(bw[1]); binw.write_f32(bw[2]); binw.write_f32(bw[3])

    def _write_index_header(self, binw: BinaryWriter, format_name: str, num_indices: int, num_groups: int) -> None:
        # 64-byte index format name (padded)
        name_bytes = format_name.encode('utf-8')
        name_padded = name_bytes[:SPEC.INDEX_FORMAT_NAME_LEN].ljust(SPEC.INDEX_FORMAT_NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)
        binw.write_u32(num_indices)
        binw.write_u32(num_groups)

    def _write_indices(self, binw: BinaryWriter, indices: List[int], use_u16: bool) -> None:
        if use_u16:
            for idx in indices:
                binw.write_u16(idx)
        else:
            for idx in indices:
                binw.write_u32(idx)

    def _write_primitive_groups(self, binw: BinaryWriter, groups: List[PrimitiveGroup]) -> None:
        # Each group written as:
        # start_idx (u32), num_of_primtvs (u32), start_vrtx (u32), num_of_vrtcs (u32)
        for g in groups:
            binw.write_u32(g.start_index)
            binw.write_u32(g.num_primitives)
            binw.write_u32(g.start_vertex)
            binw.write_u32(g.num_vertices)


# ====== Convenience operator entry (optional, kept for strict alignment) ======
def export_primitives_for_object(
    obj: bpy.types.Object,
    output_path: str,
    ctx: ExportContext,
    opts: MeshExportOptions
) -> None:
    """
    Convenience wrapper to match legacy Max plugin macro entry style.
    """
    writer = PrimitivesWriter(ctx, opts)
    writer.write_object(obj, output_path)
