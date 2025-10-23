# -*- coding: utf-8 -*-
"""
BigWorld 常量定义
"""

# BinSection文件格式常量
BINSECTION_MAGIC = 0x42A14E65
BINSECTION_VERSION = 0x01

# 顶点格式常量
VERTEX_FORMAT_STATIC = "xyznuv"  # 静态模型（32字节）
VERTEX_FORMAT_SKINNED = "xyznuviiiww"  # 蒙皮模型（29字节）
VERTEX_FORMAT_TANGENT = "xyznuvtb"  # 带切线（32字节）
VERTEX_FORMAT_SKINNED_TANGENT = "xyznuvtbiiiww"  # 蒙皮+切线（37字节）

# 骨骼常量
MAX_BONE_INDEX = 255  # uint8最大值
MAX_BONE_WEIGHT = 255  # uint8最大值
NUM_BONE_INDICES = 3  # 每顶点骨骼索引数
NUM_BONE_WEIGHTS = 2  # 每顶点权重数（第3个隐式）

# 默认值
DEFAULT_EXTENT = 100.0
DEFAULT_UNIT_SCALE = 1.0
DEFAULT_FPS = 30

# 文件扩展名
EXT_PRIMITIVES = ".primitives"
EXT_VISUAL = ".visual"
EXT_MODEL = ".model"
EXT_ANIMATION = ".animation"
EXT_MANIFEST = "manifest.json"
EXT_AUDIT = "audit.log"

# 固定路径
ANIMATION_SUBDIR = "animations"
SCENE_ROOT_NAME = "Scene Root"

# Visual类型
VISUAL_TYPE_NODELESS = "nodelessVisual"  # 静态模型
VISUAL_TYPE_NODEFULL = "nodefullVisual"  # 蒙皮/动画模型

