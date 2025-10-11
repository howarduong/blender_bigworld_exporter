# 相对路径: core/utils.py
# 功能: 提供通用工具函数，保持与 3ds Max 插件功能对齐
# 原则: 保留占位，不精简合并，逐项展开，方便后续对照 Max 插件补齐

import math
from pathlib import Path
from typing import List, Tuple, Sequence


# =========================
# 坐标/矩阵相关
# =========================

def axis_map_y_up_to_z_up(vec3: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """坐标系转换: Blender Y-Up → BigWorld Z-Up"""
    x, y, z = vec3
    return (x, z, -y)


def axis_map_matrix_y_up_to_z_up_row_major(m: Sequence[float]) -> Tuple[float, ...]:
    """矩阵转换: 4x4 行主序矩阵 Y-Up → Z-Up"""
    A = (
        1, 0,  0, 0,
        0, 0,  1, 0,
        0,-1,  0, 0,
        0, 0,  0, 1,
    )
    B = A

    def matmul_row_major(a, b):
        out = [0.0]*16
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
    """Blender Matrix → 行主序 16 元组"""
    return tuple(v for row in mat for v in row)


def apply_unit_scale(vec3: Tuple[float, float, float], scale: float) -> Tuple[float, float, float]:
    """应用单位缩放"""
    return (vec3[0] * scale, vec3[1] * scale, vec3[2] * scale)


def scene_unit_to_meters(unit_scale: float) -> float:
    """Blender 场景单位 → 米比例"""
    return float(unit_scale)


# =========================
# 索引/绕序相关
# =========================

def flip_winding(indices: List[int]) -> List[int]:
    """翻转三角形绕序 (i0,i1,i2) → (i0,i2,i1)"""
    flipped = []
    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i:i+3]
        flipped += [i0, i2, i1]
    return flipped


# =========================
# 法线/切线相关
# =========================

def rebuild_normals(vertices: List[Tuple[float, float, float]],
                    indices: List[int],
                    angle_threshold_degrees: float = 45.0) -> List[Tuple[float, float, float]]:
    """
    法线重建 (占位实现)。
    TODO: 对齐 BigWorld_Munge_Normals.mcr 的平滑组/角度阈值逻辑。
    """
    V = len(vertices)
    acc = [(0.0, 0.0, 0.0) for _ in range(V)]
    counts = [0]*V

    def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
    def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    def norm(a):
        l = math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]) or 1.0
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

    out = []
    for i in range(V):
        n = acc[i]
        out.append(norm(n) if counts[i] else (0.0, 0.0, 1.0))
    return out


def rebuild_tangents(vertices: List[Tuple[float, float, float]],
                     indices: List[int],
                     uvs: List[Tuple[float, float]]) -> List[Tuple[float, float, float]]:
    """
    切线重建 (占位实现)。
    TODO: 对齐 Max 插件的切线空间构建逻辑。
    """
    V = len(vertices)
    tx = [(0.0, 0.0, 0.0) for _ in range(V)]

    def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
    def norm(a):
        l = math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]) or 1.0
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

    out = []
    for i in range(V):
        out.append(norm(tx[i]))
    return out


# =========================
# 路径处理
# =========================

def make_relative_path(root: str, target: str) -> str:
    """
    转换为相对路径，小写化。
    TODO: 对齐 Max 插件路径规则 (统一 / 分隔符)。
    """
    try:
        rp = Path(root).resolve()
        tp = Path(target).resolve()
        rel = str(tp.relative_to(rp)).replace("\\", "/")
        return rel.lower()
    except Exception:
        return target.replace("\\", "/").lower()


# =========================
# 自定义属性读写
# =========================

def get_obj_prop(obj, key: str, default=None):
    """读取对象自定义属性 (占位)"""
    try:
        return obj.get(key, default)
    except Exception:
        return default


def set_obj_prop(obj, key: str, value):
    """设置对象自定义属性 (占位)"""
    try:
        obj[key] = value
    except Exception:
        pass
