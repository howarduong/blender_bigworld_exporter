# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Prefab Assembler (strictly aligned)

- Exports prefab groups and instance transforms into a binary section layout
- Explicit object-driven API, no implicit context usage
- Matrix flatten order configurable (row/col-major), consistent with model/skeleton writers
- Axis/unit conversion hooks retained (apply if required by scheme)
- Reserved/placeholder fields kept for strict alignment with legacy

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import bpy
import mathutils

from .binsection_writer import BinSectionWriter, BinaryWriter
from .utils import (
    axis_map_y_up_to_z_up_matrix,
)
from .utils import ExportAxis, ExportUnits


# ====== Specification constants (logical keys mapped by BinSectionWriter) ======
class SPEC:
    SECTION_PREFABS = "PREFAB_MAIN"

    NAME_LEN_GROUP = 128
    NAME_LEN_ROLE = 64

    RESERVED_U32 = 0
    RESERVED_U8 = 0


@dataclass
class PrefabInstance:
    role: str
    object: Optional[bpy.types.Object] = None
    visible: bool = True
    # Optional override matrix (if provided, used instead of object's world matrix)
    matrix_override: Optional[mathutils.Matrix] = None


@dataclass
class PrefabDefinition:
    group: str
    instances: List[PrefabInstance] = field(default_factory=list)


@dataclass
class PrefabExportOptions:
    matrix_row_major: bool = True       # True: row-major flatten; False: col-major
    apply_scene_unit_scale: bool = True
    axis: ExportAxis = ExportAxis.Y_UP_TO_Z_UP
    units: ExportUnits = ExportUnits.METERS
    unit_scale: float = 1.0             # from preferences/scene


@dataclass
class ExportContext:
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "prefab" not in self.report:
            self.report["prefab"] = {}
        self.report["prefab"][key] = value


# ====== Prefab Assembler ======
class PrefabAssembler:

    def __init__(self, ctx: ExportContext, opts: PrefabExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    def write_prefabs(
        self,
        output_path: str,
        prefabs: List[PrefabDefinition]
    ) -> None:
        """
        Write prefab groups and instances into a single binary file/section.

        Layout:
        - count_groups (u32)
        - per-group:
            - group_name (fixed 128 bytes)
            - count_instances (u32)
            - per-instance:
                - role (fixed 64 bytes)
                - visible_flag (u8) + reserved (u8) + reserved_u32
                - transform_matrix (16 * f32) : axis/unit mapped, row/col-major flattened
        - reserved u32 for alignment
        """
        with self.ctx.binsection.open(output_path) as secw:
            secw.begin_section(SPEC.SECTION_PREFABS)
            self._write_groups(self.ctx.binw, prefabs)
            secw.end_section()

        # Report
        self.ctx.add_report_stat("group_count", len(prefabs))
        self.ctx.add_report_stat("instance_total", sum(len(p.instances) for p in prefabs))

    # ====== Group/Instance writing ======
    def _write_groups(self, binw: BinaryWriter, prefabs: List[PrefabDefinition]) -> None:
        # Group count
        binw.write_u32(len(prefabs))

        for group in prefabs:
            self._write_single_group(binw, group)

        # Reserved (file-level alignment)
        binw.write_u32(SPEC.RESERVED_U32)

    def _write_single_group(self, binw: BinaryWriter, group: PrefabDefinition) -> None:
        # Group name padded
        gbytes = group.group.encode('utf-8')
        gpadded = gbytes[:SPEC.NAME_LEN_GROUP].ljust(SPEC.NAME_LEN_GROUP, b'\x00')
        binw.write_bytes(gpadded)

        # Instance count
        binw.write_u32(len(group.instances))

        for inst in group.instances:
            self._write_single_instance(binw, inst)

    def _write_single_instance(self, binw: BinaryWriter, inst: PrefabInstance) -> None:
        # Role padded
        rbytes = inst.role.encode('utf-8')
        rpadded = rbytes[:SPEC.NAME_LEN_ROLE].ljust(SPEC.NAME_LEN_ROLE, b'\x00')
        binw.write_bytes(rpadded)

        # Visible flag + reserved padding
        vis_flag = 1 if inst.visible else 0
        binw.write_u8(vis_flag)
        binw.write_u8(SPEC.RESERVED_U8)       # reserved
        binw.write_u32(SPEC.RESERVED_U32)     # reserved

        # Transform matrix (object world or override)
        mat = self._resolve_instance_matrix(inst)
        mat_mapped = self._map_axis_and_unit_matrix(mat)
        self._write_matrix(binw, mat_mapped, row_major=self.opts.matrix_row_major)

    # ====== Matrix helpers ======
    def _resolve_instance_matrix(self, inst: PrefabInstance) -> mathutils.Matrix:
        """
        Resolve the transform matrix for the instance:
        - If override provided, use it.
        - Else if object exists, use object.matrix_world.
        - Else return identity.
        """
        if inst.matrix_override is not None:
            return inst.matrix_override.copy()
        if inst.object is not None:
            return inst.object.matrix_world.copy()
        return mathutils.Matrix.Identity(4)

    def _map_axis_and_unit_matrix(self, mat: mathutils.Matrix) -> mathutils.Matrix:
        """
        Apply axis mapping (Y->Z if requested) and unit scale (uniform).
        """
        mapped = axis_map_y_up_to_z_up_matrix(mat) if self.opts.axis == ExportAxis.Y_UP_TO_Z_UP else mat

        s = self.opts.unit_scale if (self.opts.apply_scene_unit_scale and self.opts.units == ExportUnits.METERS) else 1.0
        if abs(s - 1.0) < 1e-8:
            return mapped

        scale_mat = mathutils.Matrix.Scale(s, 4)
        return scale_mat @ mapped

    def _write_matrix(self, binw: BinaryWriter, mat: mathutils.Matrix, row_major: bool) -> None:
        """
        Flatten 4x4 matrix into 16 f32 elements, row-major or col-major,
        consistent with model/skeleton writers.
        """
        if row_major:
            for r in range(4):
                for c in range(4):
                    binw.write_f32(float(mat[r][c]))
        else:
            for c in range(4):
                for r in range(4):
                    binw.write_f32(float(mat[r][c]))


# ====== Convenience entry (aligned with operator usage) ======
def export_prefabs(
    output_path: str,
    ctx: ExportContext,
    opts: PrefabExportOptions,
    prefabs: List[PrefabDefinition]
) -> None:
    assembler = PrefabAssembler(ctx, opts)
    assembler.write_prefabs(output_path, prefabs)
