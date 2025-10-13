# -*- coding: utf-8 -*-
# 相对路径: core/utils.py
# 功能: 提供通用工具函数，保持与 3ds Max 插件功能对齐
# 注意: 本文件集中实现 AxisMap 工具函数 (vec3, quat, matrix)，
#       所有 Writer (Mesh, Skeleton, Animation, Collision) 必须调用这里的函数。

"""
BigWorld Blender Exporter - Utils (strictly aligned, centralized)

- Centralized axis mapping (Y-up -> Z-up), unit scaling, matrix flatten
- Path normalization: relative to export root, lowercase, POSIX separators
- Index winding flip; normals/tangents placeholder rebuild (for legacy alignment)
- Object custom property helpers
- Enums for axis/units to keep context consistent across writers

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import List, Tuple, Sequence, Optional


# ====== Enums / constants ======
class ExportAxis:
    IDENTITY = 0
    Y_UP_TO_Z_UP = 1


class ExportUnits:
    METERS = 0
    IDENTITY = 1  # When unit scaling should be disabled


# =========================
# Axis mapping (vectors)
# =========================

def axis_map_y_up_to_z_up_vec3(vec3: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Coordinate system conversion: Blender Y-Up -> BigWorld Z-Up
    Mapping rule (legacy-aligned):
      (x, y, z) -> (x, z, -y)
    """
    x, y, z = vec3
    return (x, z, -y)


def axis_map_y_up_to_z_up_vec4(vec4: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Vector4 mapping; w kept as-is. Tangent sign or quaternion w can be preserved.
    """
    x, y, z, w = vec4
    return (x, z, -y, w)


def axis_map_y_up_to_z_up_tangent(tan4: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Tangent mapping (xyz + sign), consistent with vec4 mapping for xyz; sign preserved.
    """
    x, y, z, sign = tan4
    return (x, z, -y, sign)


# =========================
# Axis mapping (matrix)
# =========================

def axis_map_y_up_to_z_up_matrix_row_major(m: Sequence[float]) -> Tuple[float, ...]:
    """
    Matrix conversion: 4x4 row-major matrix Y-Up -> Z-Up.
    Applies M' = A * M * B where A/B perform basis change.
    """
    A = (
        1, 0, 0, 0,
        0, 0, 1, 0,
        0,-1, 0, 0,
        0, 0, 0, 1,
    )
    B = A  # symmetric for this basis change

    def matmul_row_major(a: Sequence[float], b: Sequence[float]) -> Tuple[float, ...]:
        out = [0.0] * 16
        for r in range(4):
            for c in range(4):
                s = 0.0
                for k in range(4):
                    s += a[r*4 + k] * b[k*4 + c]
                out[r*4 + c] = s
        return tuple(out)

    M = tuple(m)
    AM = matmul_row_major(A, M)
    AMB = matmul_row_major(AM, B)
    return AMB


def to_row_major_tuple_4x4(mat) -> Tuple[float, ...]:
    """
    Blender Matrix -> row-major 16-tuple
    """
    return tuple(v for row in mat for v in row)


def axis_map_y_up_to_z_up_matrix(mat) -> Tuple[Tuple[float, float, float, float], ...]:
    """
    Blender Matrix -> Blender Matrix with Y->Z mapping applied by left/right basis change.
    Provided for callers that prefer matrix × matrix rather than flatten-first.
    """
    # Convert to row-major, apply mapping, then rebuild 4x4
    rm = to_row_major_tuple_4x4(mat)
    mapped = axis_map_y_up_to_z_up_matrix_row_major(rm)
    return (
        (mapped[0], mapped[1], mapped[2], mapped[3]),
        (mapped[4], mapped[5], mapped[6], mapped[7]),
        (mapped[8], mapped[9], mapped[10], mapped[11]),
        (mapped[12], mapped[13], mapped[14], mapped[15]),
    )


# =========================
# Unit scaling
# =========================

def apply_unit_scale_vec3(vec3: Tuple[float, float, float], scale: float) -> Tuple[float, float, float]:
    """
    Apply uniform unit scale to a 3-vector.
    """
    return (vec3[0] * scale, vec3[1] * scale, vec3[2] * scale)


def scene_unit_to_meters(unit_scale: float) -> float:
    """
    Blender scene unit factor -> meters ratio.
    Kept simple: caller passes the factor directly (e.g., 0.01 for cm).
    """
    return float(unit_scale)


# =========================
# Path normalization
# =========================

def ensure_posix_lower_relative_path(root: str, target: str) -> str:
    """
    Normalize a path:
      - relative to 'root'
      - lowercase
      - POSIX separators ('/')
    If relative conversion fails, still force lowercase + POSIX separators for target.
    """
    try:
        rp = Path(root).resolve()
        tp = Path(target).resolve()
        rel = tp.relative_to(rp)
        return str(rel).replace("\\", "/").lower()
    except Exception:
        return str(target).replace("\\", "/").lower()


def make_relative_path(root: str, target: str) -> str:
    """
    Deprecated wrapper kept for strict alignment; use ensure_posix_lower_relative_path.
    """
    return ensure_posix_lower_relative_path(root, target)


# =========================
# Index winding / ranges
# =========================

def flip_winding(indices: List[int]) -> List[int]:
    """
    Flip triangle winding: (i0, i1, i2) -> (i0, i2, i1)
    """
    flipped: List[int] = []
    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i:i+3]
        flipped += [i0, i2, i1]
    return flipped


# =========================
# Normals / tangents rebuild (placeholders)
# =========================

def rebuild_normals(vertices: List[Tuple[float, float, float]],
                    indices: List[int],
                    angle_threshold_degrees: float = 45.0) -> List[Tuple[float, float, float]]:
    """
    Normal rebuild (placeholder implementation).
    TODO: align with legacy Max 'Munge Normals' macro (smoothing groups, angle threshold).
    """
    V = len(vertices)
    acc = [(0.0, 0.0, 0.0) for _ in range(V)]
    counts = [0] * V

    def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
    def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    def norm(a):
        l = math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]) or 1.0
        return (a[0]/l, a[1]/l, a[2]/l)

    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i:i+3]
        p0, p1, p2 = vertices[i0], vertices[i1], vertices[i2]
        n = cross(sub(p1, p0), sub(p2, p0))
        n = norm(n)
        for idx in (i0, i1, i2):
            ax, ay, az = acc[idx]
            acc[idx] = (ax+n[0], ay+n[1], az+n[2])
            counts[idx] += 1

    out: List[Tuple[float, float, float]] = []
    for i in range(V):
        n = acc[i]
        out.append(norm(n) if counts[i] else (0.0, 0.0, 1.0))
    return out


def rebuild_tangents(vertices: List[Tuple[float, float, float]],
                     indices: List[int],
                     uvs: List[Tuple[float, float]]) -> List[Tuple[float, float, float]]:
    """
    Tangent rebuild (placeholder implementation).
    TODO: align with legacy Max plugin's tangent space construction.
    """
    V = len(vertices)
    tx = [(0.0, 0.0, 0.0) for _ in range(V)]

    def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
    def norm(a):
        l = math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]) or 1.0
        return (a[0]/l, a[1]/l, a[2]/l)

    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i:i+3]
        p0, p1, p2 = vertices[i0], vertices[i1], vertices[i2]
        uv0, uv1, uv2 = uvs[i0], uvs[i1], uvs[i2]

        dp1 = sub(p1, p0)
        dp2 = sub(p2, p0)
        duv1 = (uv1[0]-uv0[0], uv1[1]-uv0[1])
        duv2 = (uv2[0]-uv0[0], uv2[1]-uv0[1])

        denom = (duv1[0]*duv2[1] - duv2[0]*duv1[1]) or 1.0
        t = (
            (dp1[0]*duv2[1] - dp2[0]*duv1[1]) / denom,
            (dp1[1]*duv2[1] - dp2[1]*duv1[1]) / denom,
            (dp1[2]*duv2[1] - dp2[2]*duv1[1]) / denom,
        )
        t = norm(t)

        for idx in (i0, i1, i2):
            ax, ay, az = tx[idx]
            tx[idx] = (ax+t[0], ay+t[1], az+t[2])

    out: List[Tuple[float, float, float]] = []
    for i in range(V):
        out.append(norm(tx[i]))
    return out


# =========================
# Custom properties helpers
# =========================

def get_obj_prop(obj, key: str, default=None):
    """
    Read object custom property.
    """
    try:
        return obj.get(key, default)
    except Exception:
        return default


def set_obj_prop(obj, key: str, value):
    """
    Write object custom property.
    """
    try:
        obj[key] = value
    except Exception:
        pass


# =========================
# Optional quaternion mapping (placeholder)
# =========================

def axis_map_y_up_to_z_up_quat(quat4: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Quaternion mapping: Blender Y-Up -> BigWorld Z-Up.
    Implemented via quaternion conjugation with a = Rot(+90° around X),
    which performs the same basis change as matrix M' = A * M * A^{-1}.
    Input/Output order: (x, y, z, w).
    """
    # Helper operations for (x, y, z, w) quaternions
    def quat_mul(q1: Tuple[float, float, float, float],
                 q2: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        x1, y1, z1, w1 = q1
        x2, y2, z2, w2 = q2
        x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        return (x, y, z, w)

    def quat_conjugate(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        x, y, z, w = q
        return (-x, -y, -z, w)

    # a = rotation of +90 degrees around X axis
    half = math.pi * 0.5 * 0.5  # theta/2 with theta = +90°
    sin_h = math.sin(half)
    cos_h = math.cos(half)
    a = (sin_h, 0.0, 0.0, cos_h)       # (x, y, z, w)
    a_inv = quat_conjugate(a)          # unit quaternion inverse equals conjugate

    # Conjugation: q' = a ⊗ q ⊗ a^{-1}
    q = quat4
    return quat_mul(quat_mul(a, q), a_inv)


# =========================
# Module exports
# =========================

__all__ = [
    "ExportAxis",
    "ExportUnits",
    "axis_map_y_up_to_z_up_vec3",
    "axis_map_y_up_to_z_up_vec4",
    "axis_map_y_up_to_z_up_tangent",
    "axis_map_y_up_to_z_up_matrix_row_major",
    "axis_map_y_up_to_z_up_matrix",
    "axis_map_y_up_to_z_up_quat",
    "to_row_major_tuple_4x4",
    "apply_unit_scale_vec3",
    "scene_unit_to_meters",
    "ensure_posix_lower_relative_path",
    "make_relative_path",
    "flip_winding",
    "rebuild_normals",
    "rebuild_tangents",
    "get_obj_prop",
    "set_obj_prop",
]
