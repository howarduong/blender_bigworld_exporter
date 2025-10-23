# -*- coding: utf-8 -*-
"""
硬点数据构建器
从UI配置和Blender场景数据构建Hardpoint数据
"""

import bpy
from ...core.schema import HardPoint
from ...core.coordinate_converter import CoordinateConverter


class HardpointBuilder:
    """硬点构建器"""
    
    @staticmethod
    def build_all(hardpoint_configs, skeleton):
        """
        构建所有硬点
        
        参数:
            hardpoint_configs: List[HardpointConfig] - 硬点配置列表
            skeleton: Skeleton - 骨骼数据（用于查找骨骼路径）
        
        返回:
            List[HardPoint] - 硬点数据列表
        """
        hardpoints = []
        
        for config in hardpoint_configs:
            hardpoint = HardpointBuilder.build(config, skeleton)
            if hardpoint:
                hardpoints.append(hardpoint)
        
        return hardpoints
    
    @staticmethod
    def build(config, skeleton):
        """
        构建单个硬点
        
        参数:
            config: HardpointConfig - 硬点配置
            skeleton: Skeleton - 骨骼数据
        
        返回:
            HardPoint - 硬点数据
        """
        # 获取骨骼完整路径
        bone_identifier = HardpointBuilder._get_bone_identifier(config.bone_name, skeleton)
        
        if not bone_identifier:
            print("WARNING: 硬点 {0} 的骨骼 {1} 未找到，跳过".format(config.name, config.bone_name))
            return None
        
        # 获取变换矩阵
        if config.use_empty and config.target_empty:
            # 从Empty对象获取变换
            transform = HardpointBuilder._get_transform_from_empty(config.target_empty)
        else:
            # 使用单位矩阵（硬点位于骨骼原点）
            transform = [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 0.0, 0.0]
            ]
        
        return HardPoint(
            name=config.name,
            identifier=bone_identifier,
            transform=transform,
            hardpoint_type=config.hardpoint_type
        )
    
    @staticmethod
    def _get_bone_identifier(bone_name, skeleton):
        """
        获取骨骼的完整路径
        
        参数:
            bone_name: str - 骨骼名称
            skeleton: Skeleton - 骨骼数据
        
        返回:
            str - 完整路径（如："Scene Root/biped/biped..Spine/..."）
        """
        if not skeleton or not skeleton.bones:
            return None
        
        # 查找骨骼
        bone = None
        for b in skeleton.bones:
            if b.name == bone_name:
                bone = b
                break
        
        if not bone:
            return None
        
        # 构建从Scene Root到该骨骼的完整路径
        path_parts = ["Scene Root"]
        current_bone = bone
        
        # 收集所有父骨骼
        bone_chain = [current_bone]
        while current_bone.parent_name:
            parent = None
            for b in skeleton.bones:
                if b.name == current_bone.parent_name:
                    parent = b
                    break
            if parent:
                bone_chain.insert(0, parent)
                current_bone = parent
            else:
                break
        
        # 构建路径
        for b in bone_chain:
            path_parts.append(b.name)
        
        return "/".join(path_parts)
    
    @staticmethod
    def _get_transform_from_empty(empty_obj):
        """
        从Empty对象获取变换矩阵
        
        参数:
            empty_obj: bpy.types.Object - Empty对象
        
        返回:
            List[List[float]] - 4x3变换矩阵
        """
        # 获取Empty的局部矩阵
        matrix = empty_obj.matrix_local
        
        # 转换为BigWorld坐标系
        converted_matrix = CoordinateConverter.convert_matrix(matrix)
        
        # 转换为4x3格式
        transform = [
            [converted_matrix[0][0], converted_matrix[0][1], converted_matrix[0][2]],
            [converted_matrix[1][0], converted_matrix[1][1], converted_matrix[1][2]],
            [converted_matrix[2][0], converted_matrix[2][1], converted_matrix[2][2]],
            [converted_matrix[0][3], converted_matrix[1][3], converted_matrix[2][3]]
        ]
        
        return transform

