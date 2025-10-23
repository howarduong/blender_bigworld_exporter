# File: writers/visual_writer.py
# Purpose: 写入 .visual 文件（BigWorld DataSection 文本格式）
# Notes:
# - 使用 DataSectionWriter，不是 PackedSectionWriter
# - 格式：<filename.visual> 根标签
# - 参考示例：unit_cube.visual

import os
from ..core.io.xml_writer import (
    DataSectionWriter,
    DataSectionNode,
    create_matrix_node,
    create_bbox_node,
    format_vector3,
    format_bool,
    format_int
)
from ..core.schema import Visual, RenderSet, MaterialSlot


class VisualWriter:
    """
    VisualWriter
    ------------
    用于写入 BigWorld .visual 文件（DataSection 文本格式）。
    
    格式示例：
    <filename.visual>
        <node>
            <identifier>\tScene Root\t</identifier>
            <transform>
                <row0>\t1.0 0.0 0.0\t</row0>
                ...
            </transform>
        </node>
        <renderSet>
            ...
        </renderSet>
        <boundingBox>
            <min>\t-1.0 -1.0 -1.0\t</min>
            <max>\t1.0 1.0 1.0\t</max>
        </boundingBox>
    </filename.visual>
    """
    
    def __init__(self, filepath: str, relative_path: str = ""):
        self.filepath = filepath
        self.relative_path = relative_path  # 当前 .visual 文件的相对路径（相对于 res）
    
    def write(self, visual: Visual) -> None:
        """
        写入 .visual 文件
        
        参数:
            visual: Visual 数据结构
        """
        # 创建写入器
        writer = DataSectionWriter(self.filepath)
        
        # 根标签使用文件名
        filename = os.path.basename(self.filepath)
        root = writer.create_root(filename)
        
        # 1. 写入 node（Scene Root，如果有骨骼则嵌套骨骼层级）
        if hasattr(visual, 'skeleton') and visual.skeleton and visual.skeleton.bones:
            # 有骨骼：写入完整的骨骼层级结构
            print(f"DEBUG: 写入骨骼层级，骨骼数量: {len(visual.skeleton.bones)}")
            self._write_skeleton_hierarchy(root, visual)
        elif visual.nodes:
            # 兼容旧版：有nodes列表但没有skeleton对象
            print(f"WARNING: visual.nodes存在但visual.skeleton不存在，只写入Scene Root")
            self._write_scene_root(root)
        else:
            # 无骨骼：只写入 Scene Root
            print(f"DEBUG: 无骨骼，只写入Scene Root")
            self._write_scene_root(root)
        
        # 2. 写入 renderSet
        for render_set in visual.render_sets:
            self._write_render_set(root, render_set)
        
        # 3. 写入 boundingBox
        self._write_bounding_box(root, visual)
        
        # 保存
        writer.save()
    
    def _write_scene_root(self, root: DataSectionNode) -> None:
        """
        写入 Scene Root 节点
        
        格式：
        <node>
            <identifier>\tScene Root\t</identifier>
            <transform>
                <row0>\t1.0 0.0 0.0\t</row0>
                ...
            </transform>
        </node>
        """
        node = root.add_child("node")
        node.add_child("identifier", "Scene Root")
        
        # 单位矩阵
        identity_matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0]
        ]
        transform_node = create_matrix_node("transform", identity_matrix)
        node.children.append(transform_node)
    
    def _write_render_set(self, root: DataSectionNode, render_set: RenderSet) -> None:
        """
        写入 renderSet 节点
        
        格式（来自 axe.visual 示例）：
        <renderSet>
            <treatAsWorldSpaceObject>\tfalse\t</treatAsWorldSpaceObject>
            <node>\tScene Root\t</node>
            <geometry>
                <vertices>\tvertices\t</vertices>
                <primitive>\tindices\t</primitive>
                <primitiveGroup>\t0
                    <material>
                        ...
                    </material>
                </primitiveGroup>
            </geometry>
        </renderSet>
        
        注意：
        - <vertices>vertices</vertices> 是固定值，引用 .primitives 中的 vertices section
        - <primitive>indices</primitive> 是固定值，引用 .primitives 中的 indices section
        - .primitives 文件通过文件名约定自动关联（同名同目录）
        """
        rs_node = root.add_child("renderSet")
        
        # treatAsWorldSpaceObject（固定为 false）
        rs_node.add_child("treatAsWorldSpaceObject", "false")
        
        # node 引用（固定为 Scene Root）
        rs_node.add_child("node", "Scene Root")
        
        # geometry
        geom_node = rs_node.add_child("geometry")
        
        # vertices 和 primitive 引用（固定值，不是文件路径！）
        geom_node.add_child("vertices", "vertices")
        geom_node.add_child("primitive", "indices")
        
        # primitiveGroup（每个材质一个）
        for idx in render_set.primitive_group_indices:
            pg_node = geom_node.add_child("primitiveGroup", str(idx))
            self._write_material(pg_node, render_set.material)
    
    def _write_material(self, parent: DataSectionNode, material: MaterialSlot) -> None:
        """
        写入材质节点
        
        格式：
        <material>
            <identifier>\t材质名\t</identifier>
            <fx>\tshaders/xxx.fx\t</fx>
            <collisionFlags>\t0\t</collisionFlags>
            <materialKind>\t0\t</materialKind>
            <property>\tdiffuseMap
                <Texture>\tpath/to/texture.dds\t</Texture>
            </property>
        </material>
        """
        mat_node = parent.add_child("material")
        
        # identifier
        mat_node.add_child("identifier", material.name if material.name else "Material")
        
        # fx shader
        if material.shader:
            mat_node.add_child("fx", material.shader)
        else:
            mat_node.add_child("fx", "shaders/std_effects/lightonly.fx")
        
        # collision flags 和 materialKind
        mat_node.add_child("collisionFlags", "0")
        # materialKind: 0=默认, 1=透明, 2=不透明材质等
        material_kind = getattr(material, 'material_kind', 2)  # 默认为2（不透明材质）
        mat_node.add_child("materialKind", str(material_kind))
        
        # 纹理属性（转换为相对路径，正斜杠格式）
        if material.base_color:
            prop_node = mat_node.add_child("property", "diffuseMap")
            texture_path = self._convert_texture_path(material.base_color)
            prop_node.add_child("Texture", texture_path)
        
        if material.normal:
            prop_node = mat_node.add_child("property", "normalMap")
            texture_path = self._convert_texture_path(material.normal)
            prop_node.add_child("Texture", texture_path)
        
        if material.specular:
            prop_node = mat_node.add_child("property", "specularMap")
            texture_path = self._convert_texture_path(material.specular)
            prop_node.add_child("Texture", texture_path)
    
    def _write_bounding_box(self, root: DataSectionNode, visual: Visual) -> None:
        """
        写入包围盒
        
        格式：
        <boundingBox>
            <min>\t-1.0 -1.0 -1.0\t</min>
            <max>\t1.0 1.0 1.0\t</max>
        </boundingBox>
        """
        bbox_node = create_bbox_node("boundingBox", 
                                      visual.bounding_box[0],
                                      visual.bounding_box[1])
        root.children.append(bbox_node)
    
    def _write_skeleton_hierarchy(self, root: DataSectionNode, visual: Visual) -> None:
        """
        写入完整的骨骼层级结构
        
        格式（嵌套的层级结构）:
        <node>
            <identifier>Scene Root</identifier>
            <transform>...</transform>
            <node>
                <identifier>Root</identifier>
                <transform>...</transform>
                <node>
                    <identifier>Spine</identifier>
                    <transform>...</transform>
                </node>
            </node>
        </node>
        """
        from ..core.schema import Skeleton
        
        # 创建 Scene Root
        scene_root = root.add_child("node")
        scene_root.add_child("identifier", "Scene Root")
        
        # Scene Root 的变换矩阵（单位矩阵）
        identity_matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0]
        ]
        transform_node = create_matrix_node("transform", identity_matrix)
        scene_root.children.append(transform_node)
        
        # 如果visual有skeleton信息，构建骨骼层级
        if hasattr(visual, 'skeleton') and visual.skeleton:
            skeleton = visual.skeleton
            self._build_bone_hierarchy(scene_root, skeleton)
        elif visual.nodes:
            # 如果只有nodes列表（字符串），暂时跳过
            # 这需要完整的Skeleton数据结构
            pass
    
    def _build_bone_hierarchy(self, parent_node: DataSectionNode, skeleton) -> None:
        """
        递归构建骨骼层级结构
        
        参数:
            parent_node: 父节点（通常是Scene Root）
            skeleton: Skeleton数据结构
        """
        # 构建骨骼索引映射
        bone_map = {bone.name: bone for bone in skeleton.bones}
        
        # 找到所有根骨骼（没有父骨骼的）
        root_bones = [bone for bone in skeleton.bones if bone.parent is None]
        
        print(f"DEBUG: _build_bone_hierarchy - 根骨骼数量: {len(root_bones)}")
        for rb in root_bones:
            print(f"  根骨骼: {rb.name}")
        
        # 递归写入每个根骨骼及其子树
        for root_bone in root_bones:
            print(f"DEBUG: 开始递归写入骨骼树，根: {root_bone.name}")
            self._write_bone_node(parent_node, root_bone, bone_map, skeleton.bones)
    
    def _write_bone_node(self, parent_node: DataSectionNode, bone, bone_map: dict, all_bones: list) -> None:
        """
        递归写入单个骨骼节点及其子骨骼
        
        参数:
            parent_node: 父XML节点
            bone: 当前骨骼
            bone_map: 骨骼名称到骨骼对象的映射
            all_bones: 所有骨骼列表
        """
        # 创建当前骨骼节点
        bone_node = parent_node.add_child("node")
        bone_node.add_child("identifier", bone.name)
        
        # 写入变换矩阵
        transform_node = create_matrix_node("transform", bone.bind_matrix)
        bone_node.children.append(transform_node)
        
        # 递归写入子骨骼
        child_bones = [b for b in all_bones if b.parent == bone.name]
        for child_bone in child_bones:
            self._write_bone_node(bone_node, child_bone, bone_map, all_bones)
    
    def _convert_texture_path(self, texture_path: str) -> str:
        """
        转换纹理路径为 BigWorld 格式（相对于root_path的相对路径，包含扩展名）
        
        参数:
            texture_path: 原始纹理路径（经过VisualBuilder预处理，已去除.fbm等临时文件夹）
        
        返回:
            转换后的相对路径（正斜杠格式，包含扩展名，相对于 res 目录）
        
        示例:
            self.relative_path = "characters/dragon/Box01"
            texture_path = "dragon.dds"
            输出: "characters/dragon/dragon.dds"
        """
        if not texture_path:
            return ""
        
        # 统一为正斜杠
        path = texture_path.replace('\\', '/')
        
        # 如果纹理路径已经包含多层目录（如"textures/dragon.dds"），
        # 并且self.relative_path也有目录，需要智能拼接
        if self.relative_path:
            # self.relative_path 例如: "characters/dragon/Box01"
            # 获取目录部分: "characters/dragon"
            import os
            base_dir = os.path.dirname(self.relative_path).replace('\\', '/')
            
            # 如果纹理路径只是文件名（如"dragon.dds"），直接拼接到base_dir
            if '/' not in path:
                texture_path = f"{base_dir}/{path}" if base_dir else path
            else:
                # 如果纹理路径已经包含目录（如"textures/dragon.dds"），
                # 拼接到base_dir
                texture_path = f"{base_dir}/{path}" if base_dir else path
        else:
            # 如果没有相对路径信息，直接使用清理后的路径
            texture_path = path
        
        # 转换扩展名为 .dds
        if '.' in texture_path:
            name, ext = texture_path.rsplit('.', 1)
            texture_path = f"{name}.dds"
        
        return texture_path


def write_visual(filepath: str, visual: Visual) -> None:
    """
    便捷函数：写入 .visual 文件
    
    参数:
        filepath: 输出文件路径
        visual: Visual 数据结构
    """
    writer = VisualWriter(filepath)
    writer.write(visual)
