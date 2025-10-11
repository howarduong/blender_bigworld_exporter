# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Skeleton Writer (strictly aligned)

- Exports skeleton section with bones, parent indices, bind pose and inverse bind pose
- Axis mapping unified (Y-up -> Z-up) and matrix flatten order configurable (row/col-major)
- Keeps placeholders and reserved fields to strictly align with legacy Max plugin outputs
- Optional hardpoints writer section retained (aligned placeholders)

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
    SECTION_SKELETON = "SKELETON_MAIN"
    SECTION_HARDPOINTS = "SKELETON_HARDPOINTS"

    # Header / reserved defaults
    SKELETON_VERSION = 3
    RESERVED_U32 = 0
    RESERVED_U8 = 0

    # Name field sizes
    NAME_LEN = 128


@dataclass
class SkeletonExportOptions:
    # Control matrix flatten order and unit scale application
    matrix_row_major: bool = True
    apply_scene_unit_scale: bool = True


@dataclass
class ExportContext:
    axis: ExportAxis = ExportAxis.Y_UP_TO_Z_UP
    units: ExportUnits = ExportUnits.METERS
    unit_scale: float = 1.0
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "skeleton" not in self.report:
            self.report["skeleton"] = {}
        self.report["skeleton"][key] = value


# ====== Skeleton Writer ======
class SkeletonWriter:

    def __init__(self, ctx: ExportContext, opts: SkeletonExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    # Public API: write skeleton for an Armature object
    def write_skeleton(
        self,
        armature_obj: Optional[bpy.types.Object],
        output_path: str,
        hardpoints: Optional[List[Dict]] = None
    ) -> None:
        """
        Write skeleton file sections. If armature is None or not ARMATURE, writes empty skeleton placeholder.
        Also writes hardpoints section (empty if not provided), keeping strict alignment placeholders.
        """
        with self.ctx.binsection.open(output_path) as secw:
            # Skeleton main section
            secw.begin_section(SPEC.SECTION_SKELETON)
            self._write_skeleton_main(self.ctx.binw, armature_obj)
            secw.end_section()

            # Hardpoints section (optional, placeholders retained)
            secw.begin_section(SPEC.SECTION_HARDPOINTS)
            self._write_hardpoints(self.ctx.binw, hardpoints or [])
            secw.end_section()

        # Report
        bone_count = len(armature_obj.data.bones) if (armature_obj and armature_obj.type == 'ARMATURE') else 0
        self.ctx.add_report_stat("armature_name", armature_obj.name if armature_obj else "")
        self.ctx.add_report_stat("bone_count", bone_count)
        self.ctx.add_report_stat("matrix_order", "row-major" if self.opts.matrix_row_major else "col-major")

    # ====== Skeleton main ======
    def _write_skeleton_main(self, binw: BinaryWriter, armature_obj: Optional[bpy.types.Object]) -> None:
        """
        Skeleton layout:
        - version (u32)
        - bone_count (u32)
        - repeated bones:
            - name (fixed 128 bytes)
            - parent_index (i32, -1 if none)
            - bind_pose (16 * f32, axis mapped, row/col-major flattened)
            - inverse_bind_pose (16 * f32, axis mapped, row/col-major flattened)
        - reserved fields (u32, u8)
        """
        binw.write_u32(SPEC.SKELETON_VERSION)

        if armature_obj is None or armature_obj.type != 'ARMATURE':
            # Empty skeleton placeholder
            binw.write_u32(0)
            binw.write_u32(SPEC.RESERVED_U32)
            binw.write_u8(SPEC.RESERVED_U8)
            return

        bones = armature_obj.data.bones
        bone_count = len(bones)
        binw.write_u32(bone_count)

        # Bone index map
        bone_index_map: Dict[str, int] = {b.name: i for i, b in enumerate(bones)}

        # Write bones
        for b in bones:
            self._write_single_bone(binw, b, bone_index_map)

        # Reserved fields
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u8(SPEC.RESERVED_U8)

    def _write_single_bone(self, binw: BinaryWriter, bone: bpy.types.Bone, bone_index_map: Dict[str, int]) -> None:
        # Name padded
        name_bytes = bone.name.encode('utf-8')
        name_padded = name_bytes[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)

        # Parent index
        parent_index = -1
        if bone.parent:
            parent_index = bone_index_map.get(bone.parent.name, -1)
        binw.write_i32(parent_index)

        # Bind pose (matrix_local)
        bind_mat = bone.matrix_local.copy()
        bind_mapped = self._map_axis_and_unit_matrix(bind_mat)
        self._write_matrix(binw, bind_mapped, row_major=self.opts.matrix_row_major)

        # Inverse bind pose
        inv_bind = bind_mat.inverted()
        inv_mapped = self._map_axis_and_unit_matrix(inv_bind)
        self._write_matrix(binw, inv_mapped, row_major=self.opts.matrix_row_major)

    # ====== Axis/unit mapping ======
    def _map_axis_and_unit_matrix(self, mat: mathutils.Matrix) -> mathutils.Matrix:
        """
        Apply axis mapping (Y-up -> Z-up if requested) and unit scale (uniform).
        """
        mat_mapped = axis_map_y_up_to_z_up_matrix(mat) if self.ctx.axis == ExportAxis.Y_UP_TO_Z_UP else mat

        s = self.ctx.unit_scale if (self.opts.apply_scene_unit_scale and self.ctx.units == ExportUnits.METERS) else 1.0
        if abs(s - 1.0) < 1e-8:
            return mat_mapped

        scale_mat = mathutils.Matrix.Scale(s, 4)
        return scale_mat @ mat_mapped

    def _write_matrix(self, binw: BinaryWriter, mat: mathutils.Matrix, row_major: bool) -> None:
        """
        Flatten 4x4 matrix into 16 f32 elements, row-major or col-major, consistent with model/primitives usage.
        """
        if row_major:
            for r in range(4):
                for c in range(4):
                    binw.write_f32(float(mat[r][c]))
        else:
            for c in range(4):
                for r in range(4):
                    binw.write_f32(float(mat[r][c]))

    # ====== Hardpoints section ======
    def _write_hardpoints(self, binw: BinaryWriter, hardpoints: List[Dict]) -> None:
        """
        Hardpoints layout:
        - count (u32)
        - repeated entries:
            - name (fixed 128 bytes)
            - type (fixed 64 bytes)  : reserved/classification (e.g., weapon, fx), default "weapon"
            - bone_name (fixed 128 bytes)
            - matrix (16 * f32)      : axis/unit mapped, flattened row/col-major
        """
        binw.write_u32(len(hardpoints))
        for hp in hardpoints:
            name = str(hp.get("name", ""))
            hp_type = str(hp.get("type", "weapon"))
            bone_name = str(hp.get("bone", ""))

            # Name padded
            name_padded = name.encode('utf-8')[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
            binw.write_bytes(name_padded)

            # Type padded (64)
            type_padded = hp_type.encode('utf-8')[:64].ljust(64, b'\x00')
            binw.write_bytes(type_padded)

            # Bone name padded
            bone_padded = bone_name.encode('utf-8')[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
            binw.write_bytes(bone_padded)

            # Matrix
            mat_list = hp.get("matrix", None)
            if isinstance(mat_list, (list, tuple)) and len(mat_list) == 16:
                # Convert list to Matrix
                mat = mathutils.Matrix(
                    ((mat_list[0], mat_list[1], mat_list[2], mat_list[3]),
                     (mat_list[4], mat_list[5], mat_list[6], mat_list[7]),
                     (mat_list[8], mat_list[9], mat_list[10], mat_list[11]),
                     (mat_list[12], mat_list[13], mat_list[14], mat_list[15]))
                )
            else:
                mat = mathutils.Matrix.Identity(4)

            mapped = self._map_axis_and_unit_matrix(mat)
            self._write_matrix(binw, mapped, row_major=self.opts.matrix_row_major)


# ====== Convenience entry (aligned with operator usage) ======
def export_skeleton(
    armature_obj: Optional[bpy.types.Object],
    output_path: str,
    ctx: ExportContext,
    opts: SkeletonExportOptions,
    hardpoints: Optional[List[Dict]] = None
) -> None:
    writer = SkeletonWriter(ctx, opts)
    writer.write_skeleton(armature_obj, output_path, hardpoints or [])
