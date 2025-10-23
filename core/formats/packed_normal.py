# -*- coding: utf-8 -*-
"""
Packed Normal 处理
基于BigWorld官方源码 moo_math.hpp
"""

import math


def pack_normal(nx, ny, nz):
    """
    打包法线为uint32（11-11-10位格式）
    
    参数:
        nx, ny, nz: 法线分量 (范围 -1.0 到 1.0)
    
    返回:
        uint32: 打包后的法线
    
    位布局:
        位 31-22: Z (10位, 0-511)
        位 21-11: Y (11位, 0-1023)
        位 10-0:  X (11位, 0-1023)
    """
    # 归一化
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length > 0.0001:
        nx = max(-1.0, min(1.0, nx / length))
        ny = max(-1.0, min(1.0, ny / length))
        nz = max(-1.0, min(1.0, nz / length))
    else:
        nx, ny, nz = 0.0, 0.0, 1.0
    
    # 按照BigWorld源码的方式：直接乘以511/1023
    x_packed = int(nx * 1023.0) & 0x7ff  # 11位掩码
    y_packed = int(ny * 1023.0) & 0x7ff  # 11位掩码
    z_packed = int(nz * 511.0) & 0x3ff   # 10位掩码
    
    # 打包成uint32 (z << 22 | y << 11 | x)
    packed = (z_packed << 22) | (y_packed << 11) | x_packed
    
    return packed


def unpack_normal(packed):
    """
    解包uint32为法线向量
    
    参数:
        packed: uint32打包的法线
    
    返回:
        (nx, ny, nz): 法线向量
    """
    # 提取各分量
    x_packed = packed & 0x7ff
    y_packed = (packed >> 11) & 0x7ff
    z_packed = (packed >> 22) & 0x3ff
    
    # 转换回浮点数
    nx = float(x_packed) / 1023.0
    ny = float(y_packed) / 1023.0
    nz = float(z_packed) / 511.0
    
    return (nx, ny, nz)

