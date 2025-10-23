# -*- coding: utf-8 -*-
"""
四元数处理工具
"""

import math


def normalize_quaternion(x, y, z, w):
    """
    归一化四元数
    
    参数:
        x, y, z, w: 四元数分量
    
    返回:
        (x, y, z, w): 归一化后的四元数
    """
    length = math.sqrt(x*x + y*y + z*z + w*w)
    
    if length < 0.0001:
        return (0.0, 0.0, 0.0, 1.0)
    
    return (x/length, y/length, z/length, w/length)


def quaternion_multiply(q1, q2):
    """
    四元数乘法
    
    参数:
        q1, q2: (x, y, z, w) 四元数元组
    
    返回:
        (x, y, z, w): 乘积四元数
    """
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    
    return (x, y, z, w)


def quaternion_inverse(x, y, z, w):
    """
    四元数共轭（用于求逆）
    
    参数:
        x, y, z, w: 四元数分量
    
    返回:
        (x, y, z, w): 共轭四元数
    """
    # 对于单位四元数，共轭即逆
    length_sq = x*x + y*y + z*z + w*w
    
    if length_sq < 0.0001:
        return (0.0, 0.0, 0.0, 1.0)
    
    return (-x/length_sq, -y/length_sq, -z/length_sq, w/length_sq)

