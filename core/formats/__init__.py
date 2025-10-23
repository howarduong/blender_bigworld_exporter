# -*- coding: utf-8 -*-
"""
格式处理模块
"""

from .vertex_format import build_vertex_format, get_vertex_stride, parse_vertex_format
from .packed_normal import pack_normal, unpack_normal
from .quaternion import normalize_quaternion, quaternion_multiply, quaternion_inverse

__all__ = [
    'build_vertex_format',
    'get_vertex_stride',
    'parse_vertex_format',
    'pack_normal',
    'unpack_normal',
    'normalize_quaternion',
    'quaternion_multiply',
    'quaternion_inverse',
]

