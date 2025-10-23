# File: core/coordinate_converter.py
# Purpose: 坐标系转换（Blender Z-up → BigWorld Y-up）
# Notes:
# - Blender 使用右手坐标系，Z-up
# - BigWorld 使用右手坐标系，Y-up
# - 转换矩阵：X 不变，Y ↔ Z，并调整方向

import mathutils
from mathutils import Vector, Matrix, Quaternion
from typing import Tuple, List


class CoordinateConverter:
    """
    坐标系转换器
    
    Blender (Z-up) → BigWorld (Y-up)
    
    转换规则：
        Blender (X, Y, Z) → BigWorld (X, Z, -Y)
    
    矩阵形式：
        [ 1  0  0 ]
        [ 0  0  1 ]
        [ 0 -1  0 ]
    """
    
    # 转换矩阵：Blender → BigWorld
    CONVERSION_MATRIX = Matrix((
        (1.0,  0.0,  0.0),
        (0.0,  0.0,  1.0),
        (0.0, -1.0,  0.0)
    ))
    
    # 逆转换矩阵：BigWorld → Blender
    INVERSE_CONVERSION_MATRIX = Matrix((
        (1.0,  0.0,  0.0),
        (0.0,  0.0, -1.0),
        (0.0,  1.0,  0.0)
    ))
    
    @staticmethod
    def convert_position(blender_pos: Vector) -> Tuple[float, float, float]:
        """
        转换位置向量
        
        参数:
            blender_pos: Blender 位置 (X, Y, Z)
        
        返回:
            BigWorld 位置 (X, Z, -Y)
        """
        converted = CoordinateConverter.CONVERSION_MATRIX @ blender_pos
        return (converted.x, converted.y, converted.z)
    
    @staticmethod
    def convert_normal(blender_normal: Vector) -> Tuple[float, float, float]:
        """
        转换法线向量（与位置相同的转换）
        
        参数:
            blender_normal: Blender 法线 (X, Y, Z)
        
        返回:
            BigWorld 法线 (X, Z, -Y)
        """
        converted = CoordinateConverter.CONVERSION_MATRIX @ blender_normal
        return (converted.x, converted.y, converted.z)
    
    @staticmethod
    def convert_tangent(blender_tangent: Vector) -> Tuple[float, float, float]:
        """
        转换切线向量
        
        参数:
            blender_tangent: Blender 切线 (X, Y, Z)
        
        返回:
            BigWorld 切线 (X, Z, -Y)
        """
        converted = CoordinateConverter.CONVERSION_MATRIX @ blender_tangent
        return (converted.x, converted.y, converted.z)
    
    @staticmethod
    def convert_matrix(blender_matrix: Matrix) -> List[List[float]]:
        """
        转换 4x4 变换矩阵
        
        参数:
            blender_matrix: Blender 4x4 矩阵
        
        返回:
            BigWorld 4x4 矩阵（列表形式）
        """
        # 转换矩阵 = CONVERSION_MATRIX @ blender_matrix @ INVERSE_CONVERSION_MATRIX
        # 简化：直接转换位置部分和旋转部分
        
        # 提取位置
        translation = blender_matrix.to_translation()
        converted_translation = CoordinateConverter.CONVERSION_MATRIX @ translation
        
        # 提取旋转（3x3）
        rotation_3x3 = blender_matrix.to_3x3()
        converted_rotation = CoordinateConverter.CONVERSION_MATRIX @ rotation_3x3 @ CoordinateConverter.INVERSE_CONVERSION_MATRIX
        
        # 重建 4x4 矩阵
        result = Matrix.Identity(4)
        result[0][:3] = converted_rotation[0]
        result[1][:3] = converted_rotation[1]
        result[2][:3] = converted_rotation[2]
        result[0][3] = converted_translation.x
        result[1][3] = converted_translation.y
        result[2][3] = converted_translation.z
        
        # 转换为列表
        return [
            [result[0][0], result[0][1], result[0][2], result[0][3]],
            [result[1][0], result[1][1], result[1][2], result[1][3]],
            [result[2][0], result[2][1], result[2][2], result[2][3]],
            [result[3][0], result[3][1], result[3][2], result[3][3]]
        ]
    
    @staticmethod
    def convert_quaternion(blender_quat: Quaternion) -> Tuple[float, float, float, float]:
        """
        转换四元数（用于动画旋转）
        
        参数:
            blender_quat: Blender 四元数 (W, X, Y, Z)
        
        返回:
            BigWorld 四元数 (X, Y, Z, W) - 注意：BigWorld 可能使用不同的顺序
        """
        # 将四元数转换为矩阵，再转换坐标系，再转回四元数
        matrix = blender_quat.to_matrix().to_4x4()
        converted_matrix = Matrix(CoordinateConverter.convert_matrix(matrix))
        converted_quat = converted_matrix.to_quaternion()
        
        # 归一化
        converted_quat.normalize()
        
        # BigWorld 四元数顺序：(X, Y, Z, W)
        return (converted_quat.x, converted_quat.y, converted_quat.z, converted_quat.w)
    
    @staticmethod
    def convert_euler(blender_euler: mathutils.Euler) -> Tuple[float, float, float]:
        """
        转换欧拉角（转为四元数再转换，避免万向节锁）
        
        参数:
            blender_euler: Blender 欧拉角
        
        返回:
            BigWorld 四元数 (X, Y, Z, W)
        """
        quat = blender_euler.to_quaternion()
        return CoordinateConverter.convert_quaternion(quat)
    
    @staticmethod
    def convert_scale(blender_scale: Vector) -> Tuple[float, float, float]:
        """
        转换缩放向量
        
        注意：缩放在坐标系转换时，Y 和 Z 需要交换
        
        参数:
            blender_scale: Blender 缩放 (X, Y, Z)
        
        返回:
            BigWorld 缩放 (X, Z, Y)
        """
        # 缩放交换 Y 和 Z
        return (blender_scale.x, blender_scale.z, blender_scale.y)
    
    @staticmethod
    def convert_bbox(blender_bbox: Tuple[Tuple[float, float, float], Tuple[float, float, float]]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        转换包围盒
        
        参数:
            blender_bbox: Blender 包围盒 ((min_x, min_y, min_z), (max_x, max_y, max_z))
        
        返回:
            BigWorld 包围盒 ((min_x, min_y, min_z), (max_x, max_y, max_z))
        """
        min_pt = Vector(blender_bbox[0])
        max_pt = Vector(blender_bbox[1])
        
        converted_min = CoordinateConverter.convert_position(min_pt)
        converted_max = CoordinateConverter.convert_position(max_pt)
        
        # 转换后需要重新计算 min/max（因为 Y 和 Z 交换了）
        final_min = (
            min(converted_min[0], converted_max[0]),
            min(converted_min[1], converted_max[1]),
            min(converted_min[2], converted_max[2])
        )
        
        final_max = (
            max(converted_min[0], converted_max[0]),
            max(converted_min[1], converted_max[1]),
            max(converted_min[2], converted_max[2])
        )
        
        return (final_min, final_max)
    
    @staticmethod
    def apply_unit_scale(value: float, scale: float) -> float:
        """
        应用单位缩放
        
        参数:
            value: 原始值
            scale: 缩放系数（如 1.0 表示米，0.01 表示厘米）
        
        返回:
            缩放后的值
        """
        return value * scale
    
    @staticmethod
    def convert_vertex_batch(vertices: List[Vector], 
                             normals: List[Vector] = None,
                             unit_scale: float = 1.0) -> Tuple[List[Tuple[float, float, float]], 
                                                                 List[Tuple[float, float, float]]]:
        """
        批量转换顶点和法线
        
        参数:
            vertices: Blender 顶点列表
            normals: Blender 法线列表（可选）
            unit_scale: 单位缩放
        
        返回:
            (转换后的顶点列表, 转换后的法线列表)
        """
        converted_vertices = []
        converted_normals = []
        
        for v in vertices:
            converted = CoordinateConverter.convert_position(v)
            # 应用单位缩放
            converted = (
                CoordinateConverter.apply_unit_scale(converted[0], unit_scale),
                CoordinateConverter.apply_unit_scale(converted[1], unit_scale),
                CoordinateConverter.apply_unit_scale(converted[2], unit_scale)
            )
            converted_vertices.append(converted)
        
        if normals:
            for n in normals:
                converted_normals.append(CoordinateConverter.convert_normal(n))
        
        return (converted_vertices, converted_normals)


# ==================== 便捷函数 ====================

def convert_to_bigworld(blender_vector: Vector, 
                        vector_type: str = "position",
                        unit_scale: float = 1.0) -> Tuple[float, float, float]:
    """
    便捷函数：转换 Blender 向量到 BigWorld
    
    参数:
        blender_vector: Blender 向量
        vector_type: 向量类型 ("position", "normal", "tangent", "scale")
        unit_scale: 单位缩放（仅用于 position）
    
    返回:
        BigWorld 向量 (X, Y, Z)
    """
    if vector_type == "position":
        result = CoordinateConverter.convert_position(blender_vector)
        return (
            CoordinateConverter.apply_unit_scale(result[0], unit_scale),
            CoordinateConverter.apply_unit_scale(result[1], unit_scale),
            CoordinateConverter.apply_unit_scale(result[2], unit_scale)
        )
    elif vector_type == "normal":
        return CoordinateConverter.convert_normal(blender_vector)
    elif vector_type == "tangent":
        return CoordinateConverter.convert_tangent(blender_vector)
    elif vector_type == "scale":
        return CoordinateConverter.convert_scale(blender_vector)
    else:
        raise ValueError(f"未知的向量类型: {vector_type}")
    
    @staticmethod
    def convert_quaternion(blender_quat) -> Tuple[float, float, float, float]:
        """
        转换四元数：Blender Z-up → BigWorld Y-up
        
        Blender quaternion: (w, x, y, z) in Z-up coordinate system
        BigWorld quaternion: (x, y, z, w) in Y-up coordinate system
        
        转换规则:
        1. 坐标轴转换: x不变, y→z, z→-y
        2. 顺序转换: Blender (w,x,y,z) → BigWorld (x,y,z,w)
        
        参数:
            blender_quat: Blender Quaternion
        
        返回:
            BigWorld Quaternion (x, y, z, w)
        """
        from mathutils import Quaternion
        
        if isinstance(blender_quat, (tuple, list)):
            w, x, y, z = blender_quat
            blender_quat = Quaternion((w, x, y, z))
        
        # 方法：使用旋转矩阵进行坐标系转换
        # 1. 转为矩阵
        mat = blender_quat.to_matrix().to_4x4()
        
        # 2. 应用坐标系转换
        # Z-up → Y-up: (x, y, z) → (x, z, -y)
        converted_mat = CoordinateConverter.CONVERSION_MATRIX @ mat @ CoordinateConverter.INVERSE_CONVERSION_MATRIX
        
        # 3. 转回四元数
        converted_quat = converted_mat.to_quaternion()
        
        # 4. 返回 BigWorld 格式: (x, y, z, w)
        return (converted_quat.x, converted_quat.y, converted_quat.z, converted_quat.w)

