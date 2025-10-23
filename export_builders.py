# File: export_builders.py
# Purpose: 从 Blender 对象构建 BigWorld 数据结构
# Notes:
# - 从 Blender Mesh 构建 Primitives
# - 从 Blender Material 构建 Visual
# - 从 Blender Armature/Action 构建 Animation
# - 从 Blender Object 构建 Model

import bpy
import bmesh
import os
from mathutils import Vector, Matrix
from typing import List, Tuple, Optional
from .core.schema import (
    Primitives,
    PrimitiveGroup,
    Visual,
    RenderSet,
    MaterialSlot,
    Model,
    Animation,
    AnimationChannel,
    AnimationKeys,
    Skeleton,
    ObjectType,
    CompressionType
)
from .core.coordinate_converter import CoordinateConverter


class PrimitivesBuilder:
    """
    从 Blender Mesh 构建 Primitives 数据
    """
    
    @staticmethod
    def build(obj: bpy.types.Object, apply_transform: bool = True, unit_scale: float = 1.0, force_static: bool = False) -> Primitives:
        """
        构建 Primitives 数据
        
        参数:
            obj: Blender 网格对象
            apply_transform: 是否应用变换
            unit_scale: 单位缩放（Blender 单位 → 米）
            force_static: 强制静态模式
        
        返回:
            Primitives 数据结构
        """
        if obj.type != 'MESH':
            raise ValueError(f"对象 {obj.name} 不是网格")
        
        # 检测 Armature modifier（蒙皮）
        armature_mod = None
        armature_obj = None
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                armature_mod = mod
                armature_obj = mod.object
                break
        
        # 构建静态数据
        primitives = PrimitivesBuilder._build_static_data(obj, apply_transform, unit_scale)
        
        # 构建蒙皮数据（如果需要）
        if not force_static and armature_obj:
            print(f"DEBUG: 生成蒙皮数据 for {obj.name}")
            PrimitivesBuilder._build_skinning_data(primitives, obj, armature_obj)
        else:
            print(f"DEBUG: 跳过蒙皮数据生成 for {obj.name} (force_static={force_static}, has_armature={armature_obj is not None})")
        
        return primitives
    
    @staticmethod
    def _build_static_data(obj: bpy.types.Object, apply_transform: bool, unit_scale: float) -> Primitives:
        """
        构建静态数据（所有类型公用）
        
        参数:
            obj: Blender 网格对象
            apply_transform: 是否应用变换
            unit_scale: 单位缩放
        
        返回:
            Primitives 数据结构（只包含静态数据）
        """
        # 创建 bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        # 三角化
        bmesh.ops.triangulate(bm, faces=bm.faces)
        
        # 计算法线
        bm.normal_update()
        
        # 获取 UV 层
        uv_layer = bm.loops.layers.uv.active
        
        primitives = Primitives()
        
        # 使用 loop-based 顶点收集（支持 UV 分裂）
        # 这样可以正确处理同一顶点在不同面上有不同 UV 的情况
        loop_to_index = {}  # 记录 loop -> 顶点索引的映射
        
        for face in bm.faces:
            for loop in face.loops:
                # 创建 loop 的唯一标识
                vert = loop.vert
                uv = loop[uv_layer].uv if uv_layer else (0.0, 0.0)
                loop_key = (vert.index, tuple(uv))
                
                # 如果这个 (顶点, UV) 组合已经存在，复用索引
                if loop_key in loop_to_index:
                    primitives.indices.append(loop_to_index[loop_key])
                else:
                    # 创建新的顶点
                    new_index = len(primitives.vertices)
                    loop_to_index[loop_key] = new_index
                    
                    # 位置
                    co = vert.co
                    if apply_transform:
                        co = obj.matrix_world @ co
                    
                    # 转换坐标系：Blender Z-up → BigWorld Y-up
                    converted_pos = CoordinateConverter.convert_position(co)
                    # 应用单位缩放
                    converted_pos = (
                        converted_pos[0] * unit_scale,
                        converted_pos[1] * unit_scale,
                        converted_pos[2] * unit_scale
                    )
                    primitives.vertices.append(converted_pos)
                    
                    # 法线（使用顶点的平滑法线，支持 smooth shading）
                    # 重要：使用 vert.normal 而不是 loop.calc_normal()
                    # vert.normal 包含了平滑着色的信息，使模型更圆润
                    n = vert.normal
                    if apply_transform:
                        n = obj.matrix_world.to_3x3() @ n
                    
                    # 转换法线（不需要缩放）
                    converted_normal = CoordinateConverter.convert_normal(n)
                    primitives.normals.append(converted_normal)
                    
                    # UV
                    primitives.uvs.append((uv[0], 1.0 - uv[1]))  # 翻转 V 坐标（Blender 到 BigWorld）
                    
                    # 蒙皮数据将在_build_skinning_data中处理
                    
                    # 添加索引
                    primitives.indices.append(new_index)
        
        # 构建 PrimitiveGroup（按材质槽分组）
        primitives.groups = PrimitivesBuilder._build_groups(obj, bm, loop_to_index)
        
        # 生成简单的 BSP 数据（占位）
        try:
            primitives.bsp_data = PrimitivesBuilder._generate_bsp_data(obj, bm)
        except AttributeError as e:
            print(f"WARNING: BSP 数据生成方法不存在: {e}")
            primitives.bsp_data = None
        
        
        bm.free()
        
        return primitives
    
    @staticmethod
    def _build_skinning_data(primitives: Primitives, obj: bpy.types.Object, armature_obj: bpy.types.Object) -> None:
        """
        构建蒙皮数据（蒙皮/动画专用）
        
        参数:
            primitives: Primitives 数据结构（已包含静态数据）
            obj: Blender 网格对象
            armature_obj: Armature 对象
        """
        # 创建 bmesh 用于访问顶点
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        # 为每个顶点生成蒙皮数据
        for i, vert in enumerate(bm.verts):
            if i < len(primitives.vertices):
                bone_indices, bone_weights = PrimitivesBuilder._get_vertex_weights(
                    obj, vert, armature_obj
                )
                primitives.bone_indices.append(bone_indices)
                primitives.bone_weights.append(bone_weights)
        
        bm.free()
    
    @staticmethod
    def _build_groups(obj: bpy.types.Object, bm: bmesh.types.BMesh, loop_to_index: dict) -> List[PrimitiveGroup]:
        """
        构建 PrimitiveGroup 列表
        
        注意：loop_to_index 现在是 (vert_index, uv_tuple) -> vertex_index 的映射
        但由于我们已经在主循环中构建了索引数组，这里只需要统计即可
        """
        groups = []
        
        # 如果没有材质槽，创建一个默认组
        if not obj.material_slots:
            group = PrimitiveGroup(
                name="default",
                start_index=0,
                num_primitives=len(bm.faces),
                start_vertex=0,
                num_vertices=len(loop_to_index),  # 使用 loop_to_index 的长度
                material_slot=0
            )
            groups.append(group)
            return groups
        
        # 按材质槽分组
        current_index_offset = 0
        for slot_idx, slot in enumerate(obj.material_slots):
            # 收集该材质的面
            faces = [f for f in bm.faces if f.material_index == slot_idx]
            
            if not faces:
                continue
            
            # 计算索引范围
            num_primitives = len(faces)
            start_index = current_index_offset
            
            # 更新索引偏移（每个三角形 3 个索引）
            current_index_offset += num_primitives * 3
            
            group = PrimitiveGroup(
                name=slot.name if slot.name else f"mat_{slot_idx}",
                start_index=start_index,
                num_primitives=num_primitives,
                start_vertex=0,  # 简化：使用整个顶点缓冲区
                num_vertices=len(loop_to_index),
                material_slot=slot_idx
            )
            groups.append(group)
        
        return groups
    
    @staticmethod
    def _get_vertex_weights(obj: bpy.types.Object, vert: bmesh.types.BMVert, 
                           armature_obj: bpy.types.Object) -> Tuple[Tuple[int, ...], Tuple[float, ...]]:
        """
        获取顶点的骨骼权重（从Blender读取真实数据）
        
        参数:
            obj: 网格对象
            vert: BMesh 顶点
            armature_obj: Armature 对象
        
        返回:
            (bone_indices, bone_weights)
            bone_indices: 3个uint8索引
            bone_weights: 2个uint8权重 (0-255)
        """
        # 收集顶点的所有骨骼权重
        vertex_groups = []
        
        # BMesh顶点需要通过原始mesh的顶点索引来访问权重
        mesh_vert_index = vert.index
        
        # 遍历该顶点的所有顶点组
        if mesh_vert_index < len(obj.data.vertices):
            mesh_vert = obj.data.vertices[mesh_vert_index]
            
            for group in mesh_vert.groups:
                group_idx = group.group
                weight = group.weight
                
                # 获取顶点组名称
                if group_idx < len(obj.vertex_groups):
                    group_name = obj.vertex_groups[group_idx].name
                    
                    # 查找对应的骨骼索引
                    bone_idx = SkeletonBuilder.get_bone_index(armature_obj, group_name)
                    
                    if bone_idx >= 0 and weight > 0.0001:
                        vertex_groups.append((bone_idx, weight))
        
        # 如果没有找到任何权重，绑定到Root骨骼
        if not vertex_groups:
            return ((0, 0, 0), (255, 0))
        
        # 验证骨骼索引范围
        max_bone_count = len(armature_obj.data.bones)
        for bone_idx, weight in vertex_groups:
            if bone_idx >= max_bone_count:
                print(f"WARNING: 骨骼索引 {bone_idx} 超出范围 (最大: {max_bone_count-1})")
                # 将无效索引映射到根骨骼
                vertex_groups = [(0, 1.0), (0, 0.0), (0, 0.0)]
                break
        
        # 按权重排序（降序），取前3个
        vertex_groups.sort(key=lambda x: x[1], reverse=True)
        vertex_groups = vertex_groups[:3]
        
        # 归一化权重
        total_weight = sum(w for _, w in vertex_groups)
        if total_weight < 0.0001:
            # 权重和太小，绑定到Root
            return ((0, 0, 0), (255, 0))
        
        # 转换为uint8 (0-255)
        normalized_weights = []
        for _, w in vertex_groups:
            normalized_weights.append((w / total_weight) * 255.0)
        
        # 填充到3个索引和2个权重
        while len(vertex_groups) < 3:
            vertex_groups.append((0, 0.0))
            normalized_weights.append(0.0)
        
        # 提取索引
        indices = tuple(idx for idx, _ in vertex_groups[:3])
        
        # 提取前2个权重，转换为uint8
        w1 = int(normalized_weights[0])
        w2 = int(normalized_weights[1]) if len(normalized_weights) > 1 else 0
        
        # 确保权重在有效范围内
        w1 = max(0, min(255, w1))
        w2 = max(0, min(255, w2))
        
        # 确保w1 + w2 不超过255（第三个权重会自动计算）
        if w1 + w2 > 255:
            w2 = 255 - w1
        
        weights = (w1, w2)
        
        return (indices, weights)


class VisualBuilder:
    """
    从 Blender Material 构建 Visual 数据
    """
    
    @staticmethod
    def build(obj: bpy.types.Object, primitives_path: str, skeleton: Optional[Skeleton] = None) -> Visual:
        """
        构建 Visual 数据
        
        参数:
            obj: Blender 对象
            primitives_path: .primitives 文件路径
            skeleton: 骨骼数据（可选，蒙皮模型需要）
        
        返回:
            Visual 数据结构
        """
        visual = Visual()
        
        # 构建 RenderSet
        for slot_idx, slot in enumerate(obj.material_slots):
            material = VisualBuilder._build_material(slot.material)
            
            render_set = RenderSet(
                geometry=primitives_path,
                primitive_group_indices=[slot_idx],
                material=material
            )
            
            visual.render_sets.append(render_set)
            visual.materials.append(material)
        
        # 计算包围体
        visual.bounding_box = VisualBuilder._compute_bbox(obj)
        visual.bounding_sphere = VisualBuilder._compute_bsphere(obj)
        
        # 添加骨骼节点（如果有）
        if skeleton and skeleton.bones:
            # 保存完整的Skeleton对象（用于写入层级结构）
            visual.skeleton = skeleton
            # 同时保存简化的字符串列表（兼容旧代码）
            visual.nodes = skeleton.bone_names.copy()
        
        return visual
    
    @staticmethod
    def _build_material(mat: bpy.types.Material) -> MaterialSlot:
        """从 Blender 材质构建 MaterialSlot"""
        if not mat:
            return MaterialSlot(name="default")
        
        material = MaterialSlot(name=mat.name)
        
        # 尝试从节点获取纹理路径
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    # 获取纹理路径并转换为相对路径
                    texture_path = VisualBuilder._normalize_texture_path(node.image.filepath)
                    material.base_color = texture_path
                    break
        
        return material
    
    @staticmethod
    def _normalize_texture_path(blender_path: str) -> str:
        """
        标准化纹理路径为BigWorld格式
        
        将Blender的纹理路径转换为相对于res目录的路径（包含扩展名）
        
        注意：这个方法需要在VisualBuilder中被调用，并传入root_path进行正确的相对路径计算
        这里只做基本的路径清理
        """
        import os
        
        if not blender_path:
            return ""
        
        # 移除Blender的相对路径标记"//"
        if blender_path.startswith("//"):
            blender_path = blender_path[2:]
        
        # 转换为正斜杠
        blender_path = blender_path.replace("\\", "/")
        
        # 移除.fbm等导入文件夹
        if ".fbm/" in blender_path:
            # 只保留文件名
            blender_path = blender_path.split(".fbm/")[-1]
        
        # 移除其他常见的临时文件夹
        for temp_folder in [".blend/", ".obj/", ".max/"]:
            if temp_folder in blender_path:
                blender_path = blender_path.split(temp_folder)[-1]
        
        # 确保使用正斜杠
        blender_path = blender_path.replace("\\", "/")
        
        # 移除开头的斜杠
        blender_path = blender_path.lstrip("/")
        
        return blender_path
    
    @staticmethod
    def _compute_bbox(obj: bpy.types.Object) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """计算包围盒（已应用坐标系转换）"""
        if obj.type != 'MESH':
            return ((0, 0, 0), (0, 0, 0))
        
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        
        min_x = min(v.x for v in bbox)
        min_y = min(v.y for v in bbox)
        min_z = min(v.z for v in bbox)
        
        max_x = max(v.x for v in bbox)
        max_y = max(v.y for v in bbox)
        max_z = max(v.z for v in bbox)
        
        # 应用坐标系转换
        blender_bbox = ((min_x, min_y, min_z), (max_x, max_y, max_z))
        return CoordinateConverter.convert_bbox(blender_bbox)
    
    @staticmethod
    def _compute_bsphere(obj: bpy.types.Object) -> Tuple[Tuple[float, float, float], float]:
        """计算包围球"""
        min_pt, max_pt = VisualBuilder._compute_bbox(obj)
        
        center_x = (min_pt[0] + max_pt[0]) / 2
        center_y = (min_pt[1] + max_pt[1]) / 2
        center_z = (min_pt[2] + max_pt[2]) / 2
        
        radius = ((max_pt[0] - min_pt[0])**2 + 
                  (max_pt[1] - min_pt[1])**2 + 
                  (max_pt[2] - min_pt[2])**2) ** 0.5 / 2
        
        return ((center_x, center_y, center_z), radius)


class ModelBuilder:
    """
    从 Blender Object 构建 Model 数据
    """
    
    @staticmethod
    def build(obj: bpy.types.Object, visual_path: str, has_skeleton: bool = False) -> Model:
        """
        构建 Model 数据
        
        参数:
            obj: Blender 对象
            visual_path: .visual 文件路径
            has_skeleton: 是否有骨骼（决定使用 nodefullVisual 还是 nodelessVisual）
        
        返回:
            Model 数据结构
        """
        model = Model()
        
        # 基础信息
        props = obj.bigworld_props
        model.resource_id = props.resource_id if props.resource_id else obj.name
        # export_type 是字符串形式的枚举值（STATIC, SKINNED, CHARACTER）
        # 不需要转换为ObjectType，因为它们的值是匹配的
        
        # 引用
        model.visual = visual_path
        
        # 标记是否有骨骼（用于 model_writer 判断使用哪个标签）
        model.has_skeleton = has_skeleton
        
        # 包围体
        model.bounding_box = VisualBuilder._compute_bbox(obj)
        
        # 计算 extent (LOD 距离，基于包围盒的最大半径)
        min_pt, max_pt = model.bounding_box
        size_x = max_pt[0] - min_pt[0]
        size_y = max_pt[1] - min_pt[1]
        size_z = max_pt[2] - min_pt[2]
        max_size = max(size_x, size_y, size_z)
        
        # extent 默认为包围盒最大尺寸的 10 倍（经验值）
        # 用户可以在对象属性中自定义
        model.extent = getattr(obj, 'bigworld_lod_distance', max_size * 10.0)
        
        # 读取硬点数据
        from .core.schema import HardPoint
        for hp in obj.bigworld_hardpoints:
            hardpoint = HardPoint(
                name=hp.name,
                type=hp.hardpoint_type
            )
            
            # 如果使用 Empty 对象，从 Empty 获取变换矩阵
            if hp.use_empty_transform and hp.target_empty:
                empty = hp.target_empty
                # 转换为 4x4 矩阵
                matrix = empty.matrix_world
                hardpoint.matrix = [
                    [matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3]],
                    [matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3]],
                    [matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3]],
                    [matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3]]
                ]
            
            model.hardpoints.append(hardpoint)
        
        return model


class AnimationBuilder:
    """
    从 Blender Armature/Action 构建 Animation 数据（占位保留）
    """
    
    @staticmethod
    def build(armature: bpy.types.Object, action: bpy.types.Action) -> Animation:
        """
        构建 Animation 数据
        
        参数:
            armature: Blender 骨架对象
            action: Blender 动作
        
        返回:
            Animation 数据结构
        """
        animation = Animation()
        
        # 基础信息
        animation.name = action.name
        animation.skeleton_ref = armature.name
        animation.duration = (action.frame_range[1] - action.frame_range[0]) / bpy.context.scene.render.fps
        
        # TODO: 采样关键帧
        # 这是一个复杂的过程，需要：
        # 1. 遍历所有骨骼
        # 2. 采样每根骨骼的位置/旋转/缩放
        # 3. 转换坐标系
        
        return animation
    
    @staticmethod
    def _generate_bsp_data(obj: bpy.types.Object, bm: bmesh.types.BMesh) -> Optional[bytes]:
        """
        生成简单的 BSP 数据（占位实现）
        
        注意：这是一个简化的实现，主要用于增加文件大小
        真正的 BSP 数据需要复杂的空间分割算法
        """
        import struct
        
        try:
            # 获取所有三角形
            triangles = []
            for face in bm.faces:
                if len(face.verts) == 3:  # 只处理三角形
                    triangle = []
                    for vert in face.verts:
                        # 转换坐标系
                        pos = CoordinateConverter.convert_position(vert.co)
                        triangle.extend(pos)
                    triangles.append(triangle)
            
            if not triangles:
                return None
            
            # 简化的 BSP 数据结构
            bsp_data = bytearray()
            
            # Header (根据文档 ch30.html)
            magic_number = 0x00505342  # "BSP" + version
            num_triangles = len(triangles)
            max_triangles = num_triangles  # 简化处理
            num_nodes = 1  # 简化处理，只有一个节点
            
            bsp_data.extend(struct.pack("<I", magic_number))
            bsp_data.extend(struct.pack("<I", num_triangles))
            bsp_data.extend(struct.pack("<I", max_triangles))
            bsp_data.extend(struct.pack("<I", num_nodes))
            
            # Triangles
            for triangle in triangles:
                # 每个三角形 3 个 Vector3 (9 floats)
                for i in range(9):
                    bsp_data.extend(struct.pack("<f", triangle[i]))
            
            # 简化的节点（占位）
            node_flags = 0x14  # reserved(5) + flags(3)
            bsp_data.extend(struct.pack("<I", node_flags))
            
            # 平面方程 (normal + d)
            plane_normal = [0.0, 0.0, 1.0]  # 默认平面
            plane_d = 0.0
            for i in range(3):
                bsp_data.extend(struct.pack("<f", plane_normal[i]))
            bsp_data.extend(struct.pack("<f", plane_d))
            
            # 索引数量
            num_indices = min(num_triangles, 65535)  # uint16 限制
            bsp_data.extend(struct.pack("<H", num_indices))
            
            # 三角形索引
            for i in range(num_indices):
                bsp_data.extend(struct.pack("<H", i))
            
            return bytes(bsp_data)
            
        except Exception as e:
            print(f"WARNING: BSP 数据生成失败: {e}")
            return None


class SkeletonBuilder:
    """
    从 Blender Armature 构建骨骼结构
    """
    
    @staticmethod
    def build(armature_obj: bpy.types.Object) -> Skeleton:
        """
        构建骨骼数据
        
        参数:
            armature_obj: Blender Armature 对象
        
        返回:
            Skeleton 数据结构（包含完整的骨骼层级）
        """
        from .core.schema import SkeletonBone
        
        skeleton = Skeleton()
        
        if not armature_obj or armature_obj.type != 'ARMATURE':
            return skeleton
        
        armature = armature_obj.data
        
        # 收集所有骨骼，构建完整的层级结构
        for bone in armature.bones:
            # 获取骨骼的局部变换矩阵
            matrix = SkeletonBuilder._get_bone_local_matrix(bone)
            
            skeleton_bone = SkeletonBone(
                name=bone.name,
                parent=bone.parent.name if bone.parent else None,
                bind_matrix=matrix
            )
            
            skeleton.bones.append(skeleton_bone)
            skeleton.bone_names.append(bone.name)
        
        # 查找根骨骼
        for bone in skeleton.bones:
            if bone.parent is None:
                skeleton.root = bone.name
                break
        
        # 调试输出骨骼层级
        print(f"=== 骨骼层级调试 ===")
        print(f"总骨骼数: {len(skeleton.bones)}")
        root_count = sum(1 for b in skeleton.bones if b.parent is None)
        print(f"根骨骼数量: {root_count}")
        print(f"根骨骼名称: {skeleton.root}")
        # 显示前5个骨骼的父子关系
        for i, bone in enumerate(skeleton.bones[:5]):
            print(f"  骨骼[{i}]: {bone.name} -> 父: {bone.parent if bone.parent else 'None'}")
        if len(skeleton.bones) > 5:
            print(f"  ... (还有{len(skeleton.bones)-5}个骨骼)")
        
        return skeleton
    
    @staticmethod
    def _get_bone_local_matrix(bone: bpy.types.Bone) -> List[List[float]]:
        """
        获取骨骼的局部变换矩阵（相对于父骨骼）
        
        参数:
            bone: Blender Bone
        
        返回:
            4x3矩阵（BigWorld格式，已转换坐标系）
        """
        from mathutils import Matrix
        
        # 获取骨骼的局部矩阵（Blender坐标系）
        if bone.parent:
            # 相对于父骨骼的变换
            local_matrix = bone.parent.matrix_local.inverted() @ bone.matrix_local
        else:
            # 根骨骼，使用世界矩阵
            local_matrix = bone.matrix_local
        
        # 应用坐标系转换：Blender Z-up → BigWorld Y-up
        from .core.coordinate_converter import CoordinateConverter
        
        # 转换完整的4x4矩阵
        converted_matrix_4x4 = CoordinateConverter.convert_matrix(local_matrix)
        
        # BigWorld使用4x3矩阵（3列旋转+1列位移）
        # 注意：Y轴（row3的第二个值）需要反向，因为骨骼和顶点的Y轴处理不同
        matrix_4x3 = [
            [converted_matrix_4x4[0][0], converted_matrix_4x4[0][1], converted_matrix_4x4[0][2]],
            [converted_matrix_4x4[1][0], converted_matrix_4x4[1][1], converted_matrix_4x4[1][2]],
            [converted_matrix_4x4[2][0], converted_matrix_4x4[2][1], converted_matrix_4x4[2][2]],
            [converted_matrix_4x4[0][3], -converted_matrix_4x4[1][3], converted_matrix_4x4[2][3]]  # Y轴反向
        ]
        
        return matrix_4x3
    
    @staticmethod
    def _get_bone_path(bone: bpy.types.Bone) -> str:
        """
        生成 BigWorld 骨骼路径
        
        Blender: Root → Spine → Neck
        BigWorld: "Root..Spine..Neck"
        
        参数:
            bone: Blender Bone
        
        返回:
            BigWorld 格式的骨骼路径
        """
        path_parts = []
        current = bone
        
        # 向上遍历到根骨骼
        while current:
            path_parts.insert(0, current.name)
            current = current.parent
        
        # 使用 .. 连接
        return "..".join(path_parts)
    
    @staticmethod
    def get_bone_index(armature_obj: bpy.types.Object, bone_name: str) -> int:
        """
        获取骨骼在骨架中的索引
        
        参数:
            armature_obj: Armature 对象
            bone_name: 骨骼名称
        
        返回:
            骨骼索引，如果不存在返回 -1
        """
        if not armature_obj or armature_obj.type != 'ARMATURE':
            return -1
        
        bone_names = [bone.name for bone in armature_obj.data.bones]
        try:
            return bone_names.index(bone_name)
        except ValueError:
            return -1


class AnimationBuilder:
    """
    从 Blender Action 构建动画数据
    """
    
    @staticmethod
    def build(armature_obj: bpy.types.Object, action: bpy.types.Action, 
              frame_start: int = None, frame_end: int = None, fps: float = None) -> Animation:
        """
        构建动画数据
        
        参数:
            armature_obj: Armature 对象
            action: Blender Action
            frame_start: 起始帧（None 则使用 action.frame_range）
            frame_end: 结束帧
            fps: 帧率（None 则使用场景设置）
        
        返回:
            Animation 数据结构
        """
        if not armature_obj or armature_obj.type != 'ARMATURE':
            raise ValueError("armature_obj 必须是 ARMATURE 类型")
        
        if not action:
            raise ValueError("action 不能为 None")
        
        # 获取帧范围和帧率
        if frame_start is None or frame_end is None:
            frame_start = int(action.frame_range[0])
            frame_end = int(action.frame_range[1])
        
        if fps is None:
            fps = bpy.context.scene.render.fps
        
        # 创建动画数据
        animation = Animation()
        animation.name = action.name
        animation.duration = (frame_end - frame_start) / fps
        animation.frame_rate = int(fps)
        
        # 保存当前帧
        current_frame = bpy.context.scene.frame_current
        
        # 设置动作到 Armature
        old_action = armature_obj.animation_data.action if armature_obj.animation_data else None
        if not armature_obj.animation_data:
            armature_obj.animation_data_create()
        armature_obj.animation_data.action = action
        
        try:
            # 为每根骨骼采样
            for pose_bone in armature_obj.pose.bones:
                bone_name = SkeletonBuilder._get_bone_path(pose_bone.bone)
                bone_index = SkeletonBuilder.get_bone_index(armature_obj, pose_bone.bone.name)
                
                channel = AnimationChannel(
                    bone_name=bone_name,
                    bone_index=bone_index,
                    keys=AnimationKeys()
                )
                
                # 采样关键帧
                for frame in range(frame_start, frame_end + 1):
                    bpy.context.scene.frame_set(frame)
                    bpy.context.view_layer.update()  # 强制更新
                    
                    time = (frame - frame_start) / fps
                    
                    # 位置（局部空间，相对于父骨骼）
                    pos = pose_bone.location.copy()
                    # 坐标系转换
                    pos_bw = CoordinateConverter.convert_position(pos)
                    channel.keys.position_keys.append((time, pos_bw))
                    
                    # 旋转（四元数）
                    if pose_bone.rotation_mode == 'QUATERNION':
                        rot = pose_bone.rotation_quaternion.copy()
                    else:
                        rot = pose_bone.rotation_euler.to_quaternion()
                    
                    # 坐标系转换（四元数）
                    rot_bw = CoordinateConverter.convert_quaternion(rot)
                    channel.keys.rotation_keys.append((time, rot_bw))
                    
                    # 缩放（通常不需要坐标系转换）
                    scale = pose_bone.scale.copy()
                    channel.keys.scale_keys.append((time, tuple(scale)))
                
                animation.channels.append(channel)
        
        finally:
            # 恢复原始状态
            bpy.context.scene.frame_set(current_frame)
            if old_action:
                armature_obj.animation_data.action = old_action
        
        return animation


