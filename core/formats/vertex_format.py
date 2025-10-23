# -*- coding: utf-8 -*-
# File: core/vertex_format.py
# Purpose: 动态生成 BigWorld .primitives 的顶点格式字符串
# Notes:
# - 根据 mesh 属性（法线、UV、切线、颜色、骨骼权重）生成格式
# - 格式示例: "xyznuv", "xyznuvtb", "xyznuviiiww"
# - 按固定顺序: xyz → n → uv → tb → c → iw
# - 填充到 64 字节（.primitives 规范要求）

from typing import Tuple


def build_vertex_format(
    has_normals: bool = True,
    has_uv: bool = True,
    has_tangent: bool = False,
    has_color: bool = False,
    has_skin: bool = False
) -> str:
    """
    根据 mesh 属性生成顶点格式字符串
    
    参数:
        has_normals: 是否有法线
        has_uv: 是否有 UV
        has_tangent: 是否有切线/副切线（法线贴图用）
        has_color: 是否有顶点颜色
        has_skin: 是否有骨骼权重（蒙皮动画用）
    
    返回:
        64 字节的顶点格式字符串（null 填充）
    
    示例:
        >>> build_vertex_format(has_normals=True, has_uv=True)
        'xyznuv\\x00\\x00...'  # 填充到64字节
        
        >>> build_vertex_format(has_normals=True, has_uv=True, has_tangent=True)
        'xyznuvtb\\x00\\x00...'
    """
    fmt = "xyz"  # 位置坐标总是必须的
    
    if has_normals:
        fmt += "n"
    
    if has_uv:
        fmt += "uv"
    
    if has_tangent:
        fmt += "tb"  # tangent + bitangent
    
    if has_color:
        fmt += "c"
    
    if has_skin:
        fmt += "iiiww"  # 蒙皮格式：3 bone indices (uint8) + 2 weights (uint8)
                        # 注意：权重是归一化的uint8 (0-255)，不是float！
                        # 根据BigWorld源码，这应该是5个连续的uint8
                        # 但格式字符串应该是"iiiww"，对应"xyznuviiiww"
    
    # 填充到 64 字节
    return fmt.ljust(64, '\0')


def parse_vertex_format(format_str: str) -> Tuple[bool, bool, bool, bool, bool]:
    """
    解析顶点格式字符串，返回属性标志
    
    参数:
        format_str: 顶点格式字符串（如 "xyznuvtb"）
    
    返回:
        (has_normals, has_uv, has_tangent, has_color, has_skin)
    """
    # 去除填充的 null 字符
    fmt = format_str.rstrip('\0')
    
    has_normals = 'n' in fmt
    has_uv = 'uv' in fmt
    has_tangent = 'tb' in fmt
    has_color = 'c' in fmt
    has_skin = 'iiiww' in fmt or 'iw' in fmt
    
    return has_normals, has_uv, has_tangent, has_color, has_skin


def get_vertex_stride(format_str: str) -> int:
    """
    计算顶点步长（字节数）
    
    参数:
        format_str: 顶点格式字符串
    
    返回:
        每个顶点占用的字节数
    
    说明:
        - xyz: 3 * 4 = 12 bytes
        - n: 3 * 4 = 12 bytes
        - uv: 2 * 4 = 8 bytes
        - tb: 6 * 4 = 24 bytes (tangent 3 + bitangent 3)
        - c: 4 * 4 = 16 bytes (RGBA)
        - iw: 8 * 4 = 32 bytes (4 indices + 4 weights)
    """
    fmt = format_str.rstrip('\0')
    
    stride = 0
    
    # xyz 总是存在
    stride += 12  # 3 floats
    
    if 'n' in fmt:
        # 静态模型使用Vector3 normal (12字节)
        # 带切线/副切线的模型使用packed normal (4字节)
        if 'tb' in fmt:
            stride += 4  # packed uint32
        else:
            stride += 12  # Vector3 (3 floats)
    
    if 'uv' in fmt:
        stride += 8  # 2 floats
    
    if 'tb' in fmt:
        stride += 8  # 2 packed uint32 (tangent + binormal, 不是6个float!)
    
    if 'c' in fmt:
        stride += 16  # 4 floats (RGBA)
    
    if 'iiiww' in fmt or 'iw' in fmt:
        stride += 5  # 3 bytes (indices) + 2 bytes (weights) = 5 bytes total
    
    return stride


# ==================== 常用格式预定义 ====================

# 静态网格（位置 + 法线 + UV）
FORMAT_STATIC = build_vertex_format(has_normals=True, has_uv=True)

# 带法线贴图的网格（位置 + 法线 + UV + 切线）
FORMAT_NORMAL_MAPPED = build_vertex_format(has_normals=True, has_uv=True, has_tangent=True)

# 顶点色网格（位置 + 法线 + UV + 颜色）
FORMAT_VERTEX_COLOR = build_vertex_format(has_normals=True, has_uv=True, has_color=True)

# 蒙皮网格（位置 + 法线 + UV + 骨骼权重）
FORMAT_SKINNED = build_vertex_format(has_normals=True, has_uv=True, has_skin=True)

# 完整格式（所有属性）
FORMAT_FULL = build_vertex_format(
    has_normals=True,
    has_uv=True,
    has_tangent=True,
    has_color=True,
    has_skin=True
)

