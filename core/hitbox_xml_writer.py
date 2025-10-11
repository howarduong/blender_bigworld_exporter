# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Hitbox XML Writer (strictly aligned)

- Exports hitbox definitions to XML (creature_collider.xml-style)
- Box-only implementation per scheme; sphere/capsule/mesh are placeholders (kept fields)
- Explicit object-driven API (no implicit context), supports object/bone-level binding
- Axis/unit conversion hooks kept consistent with global scheme
- Reserved/extension fields retained even if unused

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import bpy
import mathutils
import xml.etree.ElementTree as ET


# ====== Specification constants ======
class SPEC:
    ROOT_TAG = "Hitboxes"
    ITEM_TAG = "Hitbox"

    # Attributes
    ATTR_NAME = "name"
    ATTR_TYPE = "type"       # box/sphere/capsule/mesh
    ATTR_LEVEL = "level"     # object/bone
    ATTR_BONE = "bone"       # optional when level == bone

    # Children
    TAG_MIN = "Min"
    TAG_MAX = "Max"
    TAG_MATRIX = "Matrix"
    TAG_RESERVED = "Reserved"  # Placeholder tag for legacy/unused fields

    # Defaults
    DEFAULT_TYPE = "box"
    DEFAULT_LEVEL = "object"


@dataclass
class HitboxExportOptions:
    # Control axis/unit application on computed AABB or provided matrix
    apply_scene_unit_scale: bool = True
    map_axis_y_to_z: bool = False  # If global scheme requires, enable and use utils mapping
    write_matrix_for_box: bool = False  # Write a transform matrix alongside Min/Max (placeholder)
    name_prefix: str = "_bwhitbox"  # Naming convention for detection


@dataclass
class ExportContext:
    unit_scale: float = 1.0
    report: Dict = field(default_factory=dict)

    def add_report_stat(self, key: str, value):
        if "hitbox" not in self.report:
            self.report["hitbox"] = {}
        self.report["hitbox"][key] = value


# ====== Hitbox XML Writer ======
class HitboxXMLWriter:

    def __init__(self, ctx: ExportContext, opts: HitboxExportOptions):
        self.ctx = ctx
        self.opts = opts

    def write_hitboxes_for_objects(
        self,
        objects: List[bpy.types.Object],
        output_path: str
    ) -> None:
        """
        Scan provided objects for hitbox markers, compute box AABB, and write XML.
        Naming: objects whose name starts with opts.name_prefix or have custom prop 'bw_hitbox=True'.
        """
        hitboxes: List[Dict] = []

        for obj in objects:
            if not self._is_hitbox_object(obj):
                continue

            hb = self._build_box_hitbox_entry(obj)
            if hb:
                hitboxes.append(hb)

        # Build XML
        root = ET.Element(SPEC.ROOT_TAG)
        for hb in hitboxes:
            self._append_hitbox_element(root, hb)

        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

        # Report
        self.ctx.add_report_stat("output_path", output_path)
        self.ctx.add_report_stat("hitbox_count", len(hitboxes))

    # ====== Detection and entry build ======
    def _is_hitbox_object(self, obj: bpy.types.Object) -> bool:
        if bool(obj.get("bw_hitbox", False)):
            return True
        return obj.name.lower().startswith(self.opts.name_prefix.lower())

    def _build_box_hitbox_entry(self, obj: bpy.types.Object) -> Optional[Dict]:
        """
        Build a hitbox entry dict:
        {
          "name": str,
          "type": "box",
          "level": "object" or "bone",
          "bone": str or "",
          "min": (x,y,z),
          "max": (x,y,z),
          "matrix": [16 floats] optional if opts.write_matrix_for_box
        }
        """
        # Compute world-space AABB
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)

        bbox_min, bbox_max = self._compute_world_aabb(obj_eval)

        # Unit scale
        if self.opts.apply_scene_unit_scale:
            s = self.ctx.unit_scale
            bbox_min = (bbox_min[0] * s, bbox_min[1] * s, bbox_min[2] * s)
            bbox_max = (bbox_max[0] * s, bbox_max[1] * s, bbox_max[2] * s)

        # Axis mapping hook (if required by global scheme)
        # if self.opts.map_axis_y_to_z:
        #     bbox_min = axis_map_y_up_to_z_up_vec3(bbox_min)
        #     bbox_max = axis_map_y_up_to_z_up_vec3(bbox_max)

        # Level / bone binding (optional)
        level = SPEC.DEFAULT_LEVEL
        bone_name = ""
        if obj.get("bw_hitbox_level") in ("object", "bone"):
            level = obj["bw_hitbox_level"]
        if level == "bone":
            bone_name = str(obj.get("bw_hitbox_bone", ""))

        entry: Dict = {
            "name": obj.name,
            "type": SPEC.DEFAULT_TYPE,
            "level": level,
            "bone": bone_name,
            "min": bbox_min,
            "max": bbox_max,
        }

        if self.opts.write_matrix_for_box:
            # Provide an identity or object world matrix flattened as placeholder
            mat = obj_eval.matrix_world.copy()
            entry["matrix"] = self._flatten_matrix(mat)

        return entry

    def _compute_world_aabb(self, obj_eval: bpy.types.Object) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Compute world-space AABB of the evaluated object by transforming its local bounding box.
        """
        # Blender's bound_box is 8 local corners; transform to world
        bb = obj_eval.bound_box
        corners = [mathutils.Vector(c) for c in bb]  # local-space
        world_corners = [obj_eval.matrix_world @ c for c in corners]

        xs = [c.x for c in world_corners]
        ys = [c.y for c in world_corners]
        zs = [c.z for c in world_corners]

        min_v = (min(xs), min(ys), min(zs))
        max_v = (max(xs), max(ys), max(zs))
        return min_v, max_v

    def _flatten_matrix(self, mat: mathutils.Matrix) -> List[float]:
        """
        Flatten 4x4 matrix row-major into 16 floats.
        """
        out: List[float] = []
        for r in range(4):
            for c in range(4):
                out.append(float(mat[r][c]))
        return out

    # ====== XML writing ======
    def _append_hitbox_element(self, root: ET.Element, hb: Dict) -> None:
        elem = ET.SubElement(root, SPEC.ITEM_TAG)

        # Attributes
        elem.set(SPEC.ATTR_NAME, str(hb.get("name", "")))
        elem.set(SPEC.ATTR_TYPE, str(hb.get("type", SPEC.DEFAULT_TYPE)))
        elem.set(SPEC.ATTR_LEVEL, str(hb.get("level", SPEC.DEFAULT_LEVEL)))
        if hb.get("bone"):
            elem.set(SPEC.ATTR_BONE, str(hb.get("bone")))

        # Children: Min/Max
        min_e = ET.SubElement(elem, SPEC.TAG_MIN)
        max_e = ET.SubElement(elem, SPEC.TAG_MAX)
        min_v = hb.get("min", (0.0, 0.0, 0.0))
        max_v = hb.get("max", (0.0, 0.0, 0.0))
        min_e.text = f"{float(min_v[0])} {float(min_v[1])} {float(min_v[2])}"
        max_e.text = f"{float(max_v[0])} {float(max_v[1])} {float(max_v[2])}"

        # Optional Matrix (placeholder)
        if "matrix" in hb:
            m_e = ET.SubElement(elem, SPEC.TAG_MATRIX)
            m = hb["matrix"]
            m_e.text = " ".join(f"{float(v)}" for v in m)

        # Reserved placeholder child (kept for strict alignment)
        r_e = ET.SubElement(elem, SPEC.TAG_RESERVED)
        r_e.text = "0"

    # ====== Convenience detection entry ======
    def export_from_scene_selection(
        self,
        output_path: str
    ) -> None:
        """
        Export hitboxes for currently selected objects; explicit call requires
        operator to pass selection, kept here as convenience (no internal context logic).
        """
        objs = list(bpy.context.selected_objects)
        self.write_hitboxes_for_objects(objs, output_path)
