# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Animation Writer (strictly aligned)

- Exports skeletal animation tracks per bone with time, loc/rot/scale channels
- Sampling based on Action frame range and a fixed FPS
- Writes Cue Track events section (time, label, param)
- Keeps placeholders and reserved fields for strict alignment with legacy outputs
- Explicit object-driven API; no reliance on implicit context

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import bpy
import mathutils

from .binsection_writer import BinSectionWriter, BinaryWriter
from .utils import (
    axis_map_y_up_to_z_up_vec3,
    axis_map_y_up_to_z_up_quat,
    axis_map_y_up_to_z_up_tangent,
    ExportAxis,
    ExportUnits,
)




# ====== Specification constants (logical keys mapped by BinSectionWriter) ======
class SPEC:
    SECTION_ANIMATION = "ANIM_MAIN"
    SECTION_CUE_TRACK = "ANIM_CUE"

    # Versioning / reserved
    ANIM_VERSION = 3
    RESERVED_U32 = 0
    RESERVED_U8 = 0

    NAME_LEN = 128


@dataclass
class AnimationExportOptions:
    fps: int = 30
    # If per-channel axis/unit mapping is required, enable via these flags and use utils conversions
    map_axis: bool = False
    apply_scene_unit_scale: bool = True
    matrix_row_major: bool = True  # Reserved for future matrix-based channels (not used here)


@dataclass
class ExportContext:
    axis: ExportAxis = ExportAxis.Y_UP_TO_Z_UP
    units: ExportUnits = ExportUnits.METERS
    unit_scale: float = 1.0
    binsection: BinSectionWriter = None
    binw: BinaryWriter = None
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "animation" not in self.report:
            self.report["animation"] = {}
        self.report["animation"][key] = value


# ====== Animation Writer ======
class AnimationWriter:

    def __init__(self, ctx: ExportContext, opts: AnimationExportOptions):
        assert ctx is not None and ctx.binsection is not None and ctx.binw is not None
        self.ctx = ctx
        self.opts = opts

    # Public: write skeletal animation + cue track (optional)
    def write_animation(
        self,
        armature_obj: Optional[bpy.types.Object],
        action: Optional[bpy.types.Action],
        output_path: str,
        cue_events: Optional[List[Dict]] = None
    ) -> None:
        """
        Writes animation sections:
        - ANIM_MAIN: version, anim name, duration, bone count, per-bone tracks (t, loc, rot, scale)
        - ANIM_CUE : events list (time, label, param)

        If armature or action is None, writes empty animation placeholders.
        """
        with self.ctx.binsection.open(output_path) as secw:
            # Main animation section
            secw.begin_section(SPEC.SECTION_ANIMATION)
            self._write_anim_main(self.ctx.binw, armature_obj, action)
            secw.end_section()

            # Cue track section (write events or empty placeholder)
            secw.begin_section(SPEC.SECTION_CUE_TRACK)
            self._write_cue_track(self.ctx.binw, cue_events or [])
            secw.end_section()

        # Report
        anim_name = action.name if action else "EmptyAnim"
        bone_count = len(armature_obj.data.bones) if (armature_obj and armature_obj.type == 'ARMATURE') else 0
        duration = self._compute_duration_seconds(action, self.opts.fps)
        self.ctx.add_report_stat("anim_name", anim_name)
        self.ctx.add_report_stat("bone_count", bone_count)
        self.ctx.add_report_stat("duration_sec", duration)
        self.ctx.add_report_stat("fps", self.opts.fps)
        self.ctx.add_report_stat("cue_event_count", len(cue_events or []))

    # ====== Main animation ======
    def _write_anim_main(
        self,
        binw: BinaryWriter,
        armature_obj: Optional[bpy.types.Object],
        action: Optional[bpy.types.Action]
    ) -> None:
        """
        Layout:
        - version (u32)
        - name (fixed 128 bytes)
        - duration (f32, seconds)
        - bone_count (u32)
        - per-bone:
            - bone name (cstring or fixed? here fixed 128 for strict alignment)
            - key_count (u32)
            - repeated keys:
                - time (f32, seconds)
                - loc (3 * f32)
                - rot (4 * f32, quaternion w,x,y,z)
                - scale (3 * f32)
        - reserved fields (u32, u8)
        """
        binw.write_u32(SPEC.ANIM_VERSION)

        # Name padded
        anim_name = action.name if action else "EmptyAnim"
        name_padded = anim_name.encode('utf-8')[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
        binw.write_bytes(name_padded)

        # Duration
        duration = self._compute_duration_seconds(action, self.opts.fps)
        binw.write_f32(duration)

        # Bones
        bones = []
        if armature_obj and armature_obj.type == 'ARMATURE':
            bones = list(armature_obj.data.bones)
        binw.write_u32(len(bones))

        # Sample per bone
        if action and bones:
            self._sample_action_to_tracks(binw, armature_obj, action, bones, self.opts.fps)
        else:
            # Empty tracks for strict alignment (no bones → no tracks)
            pass

        # Reserved
        binw.write_u32(SPEC.RESERVED_U32)
        binw.write_u8(SPEC.RESERVED_U8)

    def _compute_duration_seconds(self, action: Optional[bpy.types.Action], fps: int) -> float:
        if not action:
            return 0.0
        frame_start, frame_end = action.frame_range
        return float(frame_end - frame_start) / float(fps)

    def _sample_action_to_tracks(
        self,
        binw: BinaryWriter,
        armature_obj: bpy.types.Object,
        action: bpy.types.Action,
        bones: List[bpy.types.Bone],
        fps: int
    ) -> None:
        """
        Samples keys from frame_start..frame_end inclusive at 1 frame per step (fixed FPS).
        Writes per-bone tracks: name (fixed 128), key_count (u32), keys (time, loc, rot, scale).
        """
        frame_start, frame_end = action.frame_range
        frame_start_i = int(frame_start)
        frame_end_i = int(frame_end)
        num_keys = (frame_end_i - frame_start_i) + 1

        # Switch action onto armature for evaluation
        prev_action = armature_obj.animation_data.action if armature_obj.animation_data else None
        if armature_obj.animation_data is None:
            armature_obj.animation_data_create()
        armature_obj.animation_data.action = action

        # Sample each bone
        for b in bones:
            # Bone name padded
            bname_padded = b.name.encode('utf-8')[:SPEC.NAME_LEN].ljust(SPEC.NAME_LEN, b'\x00')
            binw.write_bytes(bname_padded)

            # Key count
            binw.write_u32(num_keys)

            # Pose bone
            pose_bone = armature_obj.pose.bones.get(b.name)

            for f in range(frame_start_i, frame_end_i + 1):
                # Set scene frame for evaluation
                bpy.context.scene.frame_set(f)

                # Time (seconds)
                t = (float(f) - float(frame_start_i)) / float(fps)
                binw.write_f32(t)

                if not pose_bone:
                    # Default identity transform
                    self._write_loc_rot_scale(binw,
                                              loc=mathutils.Vector((0.0, 0.0, 0.0)),
                                              rot=mathutils.Quaternion((1.0, 0.0, 0.0, 0.0)),
                                              scale=mathutils.Vector((1.0, 1.0, 1.0)))
                    continue

                # Extract channels
                loc = pose_bone.location.copy()
                rot = pose_bone.rotation_quaternion.copy() if pose_bone.rotation_mode == 'QUATERNION' else pose_bone.rotation_quaternion.copy()
                scale = pose_bone.scale.copy()

                # Optional axis/unit mapping for channels
                # Optional axis/unit mapping for channels
                if self.opts.map_axis and self.ctx.axis == ExportAxis.Y_UP_TO_Z_UP:
                    # Location
                    loc = axis_map_y_up_to_z_up_vec3((loc.x, loc.y, loc.z))
                    # Rotation: utils returns (x, y, z, w), need to rebuild Blender Quaternion(w, x, y, z)
                    rot_tuple = (rot.x, rot.y, rot.z, rot.w)
                    rot_mapped = axis_map_y_up_to_z_up_quat(rot_tuple)
                    rot = mathutils.Quaternion((rot_mapped[3], rot_mapped[0], rot_mapped[1], rot_mapped[2]))
          

                if self.opts.apply_scene_unit_scale and self.ctx.units == ExportUnits.METERS:
                    s = self.ctx.unit_scale
                    loc = mathutils.Vector((loc.x * s, loc.y * s, loc.z * s))
                    # scale typically dimensionless; keep as-is

                self._write_loc_rot_scale(binw, loc, rot, scale)

        # Restore previous action
        armature_obj.animation_data.action = prev_action

    def _write_loc_rot_scale(
        self,
        binw: BinaryWriter,
        loc: mathutils.Vector,
        rot: mathutils.Quaternion,
        scale: mathutils.Vector
    ) -> None:
        # Location
        binw.write_f32(float(loc.x)); binw.write_f32(float(loc.y)); binw.write_f32(float(loc.z))
        # Rotation (w, x, y, z)
        binw.write_f32(float(rot.w)); binw.write_f32(float(rot.x)); binw.write_f32(float(rot.y)); binw.write_f32(float(rot.z))
        # Scale
        binw.write_f32(float(scale.x)); binw.write_f32(float(scale.y)); binw.write_f32(float(scale.z))

    # ====== Cue Track ======
    def _write_cue_track(self, binw: BinaryWriter, events: List[Dict]) -> None:
        """
        Cue track layout:
        - count (u32)
        - repeated events:
            - time (f32, seconds)
            - label (cstring)
            - param (cstring)
        """
        binw.write_u32(len(events))
        for ev in events:
            self._write_single_event(binw, ev)

    def _write_single_event(self, binw: BinaryWriter, ev: Dict) -> None:
        t = float(ev.get("time", 0.0))
        label = str(ev.get("label", ""))
        param = str(ev.get("param", ""))

        binw.write_f32(t)
        binw.write_cstring(label)
        binw.write_cstring(param)


# ====== Convenience entry (aligned with operator usage) ======
def export_animation(
    armature_obj: Optional[bpy.types.Object],
    action: Optional[bpy.types.Action],
    output_path: str,
    ctx: ExportContext,
    opts: AnimationExportOptions,
    cue_events: Optional[List[Dict]] = None
) -> None:
    writer = AnimationWriter(ctx, opts)
    writer.write_animation(armature_obj, action, output_path, cue_events or [])
