# File: writers/model_writer.py
# Purpose: 写入 .model 文件（BigWorld DataSection 文本格式）
# Notes:
# - 使用 DataSectionWriter，不是 PackedSectionWriter
# - 格式：<filename.model> 根标签
# - 参考示例：unit_cube.model, axe.model

import os
from ..core.io.xml_writer import (
    DataSectionWriter,
    DataSectionNode,
    create_bbox_node,
    format_vector3,
    format_float,
    format_bool
)
from ..core.schema import Model, ModelAnimation, ModelAction


class ModelWriter:
    """
    ModelWriter
    -----------
    用于写入 BigWorld .model 文件（DataSection 文本格式）。
    
    格式示例：
    <filename.model>
        <nodelessVisual>\tpath/to/visual\t</nodelessVisual>
        <extent>\t5.0\t</extent>
        <visibilityBox>
            <min>\t-1.0 -1.0 -1.0\t</min>
            <max>\t1.0 1.0 1.0\t</max>
        </visibilityBox>
        <metaData>
            ...
        </metaData>
    </filename.model>
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def write(self, model: Model) -> None:
        """
        写入 .model 文件
        
        参数:
            model: Model 数据结构
        """
        # 创建写入器
        writer = DataSectionWriter(self.filepath)
        
        # 根标签使用文件名
        filename = os.path.basename(self.filepath)
        root = writer.create_root(filename)
        
        # 1. parent（如果有）
        if model.parent:
            root.add_child("parent", model.parent)
        
        # 2. visual 引用
        if model.visual:
            # 去掉 .visual 扩展名（BigWorld 格式要求）
            visual_path = model.visual.replace('.visual', '')
            print(f"DEBUG: model.visual = {model.visual}")
            print(f"DEBUG: visual_path = {visual_path}")
            
            # 根据是否有骨骼决定使用 nodelessVisual 还是 nodefullVisual
            if model.has_skeleton:
                root.add_child("nodefullVisual", visual_path)
            else:
                root.add_child("nodelessVisual", visual_path)
        
        # 3. materialNames（通常为空）
        root.add_child("materialNames", "")
        
        # 4. dpvsOccluder（官方格式中的字段）
        dpvs_occluder = getattr(model, 'dpvs_occluder', True)
        root.add_child("dpvsOccluder", format_bool(dpvs_occluder))
        
        # 5. batched（官方格式中的字段）
        batched = getattr(model, 'batched', False)
        root.add_child("batched", format_bool(batched))
        
        # 6. extent (LOD 距离)
        extent = getattr(model, 'extent', 20.0)  # 默认 20 米
        root.add_child("extent", format_float(extent))
        
        # 6. visibilityBox（即 boundingBox）
        bbox_node = create_bbox_node("visibilityBox",
                                      model.bounding_box[0],
                                      model.bounding_box[1])
        root.children.append(bbox_node)
        
        # 6. animation（如果有）
        if model.animations:
            self._write_animations(root, model.animations)
        
        # 7. action（如果有）
        if model.actions:
            self._write_actions(root, model.actions)
        
        # 8. hardpoints（如果有）
        if model.hardpoints:
            self._write_hardpoints(root, model.hardpoints)
        
        # 9. metaData
        self._write_metadata(root, model)
        
        # 保存
        writer.save()
    
    def _write_animations(self, root: DataSectionNode, animations: list) -> None:
        """
        写入动画引用列表
        
        格式（参考官方 base.model）:
        <animation>
            <name>\tm_walk\t</name>
            <frameRate>\t30.000000\t</frameRate>
            <nodes>\tcharacters/avatars/base/animations/m_walk\t</nodes>
        </animation>
        """
        from ..core.io.xml_writer import format_float
        
        for anim in animations:
            anim_node = root.add_child("animation")
            anim_node.add_child("name", anim.name)
            
            # frameRate (如果有)
            if hasattr(anim, 'frame_rate'):
                anim_node.add_child("frameRate", format_float(float(anim.frame_rate)))
            
            # nodes 字段：指向 .animation 文件的路径（相对于 res 根目录）
            # 如果 anim 有 resource 属性，使用它；否则生成默认路径
            if hasattr(anim, 'resource') and anim.resource:
                anim_node.add_child("nodes", anim.resource)
            else:
                # 默认路径（与 .animation 文件的相对路径一致）
                anim_node.add_child("nodes", anim.name)
    
    def _write_actions(self, root: DataSectionNode, actions: list) -> None:
        """
        写入Action定义列表（符合BigWorld官方规范）
        
        格式：
        <action>
            <name>\tWalkForward\t</name>
            <animation>\twalk\t</animation>
            <blended>\ttrue\t</blended>
            <track>\t0\t</track>
        </action>
        """
        for action in actions:
            action_node = root.add_child("action")
            action_node.add_child("name", action.name)
            action_node.add_child("animation", action.animation_ref)
            action_node.add_child("blended", format_bool(action.blended))
            action_node.add_child("track", str(action.track))
    
    def _write_hardpoints(self, root: DataSectionNode, hardpoints: list) -> None:
        """
        写入硬点列表（符合BigWorld官方规范）
        
        格式：
        <hardPoint>
            <name>\tHP_RightHand\t</name>
            <identifier>\tScene Root/biped/biped..R Hand\t</identifier>
            <transform>
                <row0>\t1.0 0.0 0.0\t</row0>
                <row1>\t0.0 1.0 0.0\t</row1>
                <row2>\t0.0 0.0 1.0\t</row2>
                <row3>\t0.0 0.0 0.0\t</row3>
            </transform>
        </hardPoint>
        """
        from ..core.io.xml_writer import format_float
        
        for hp in hardpoints:
            hp_node = root.add_child("hardPoint")
            hp_node.add_child("name", hp.name)
            hp_node.add_child("identifier", hp.identifier)
            
            # 写入4x3变换矩阵
            transform_node = hp_node.add_child("transform")
            for i in range(4):
                row_values = " ".join([format_float(v) for v in hp.transform[i]])
                transform_node.add_child("row{0}".format(i), row_values)
    
    def _write_metadata(self, root: DataSectionNode, model: Model) -> None:
        """
        写入元数据（匹配官方格式）
        
        格式：
        <metaData>
            <sourceFile>\t...\t</sourceFile>
            <computer>\t...\t</computer>
            <created_by>\t...\t</created_by>
            <created_on>\t...\t</created_on>
            <modified_by>\t...\t</modified_by>
            <modified_on>\t...\t</modified_on>
        </metaData>
        """
        import time
        import os
        import getpass
        
        meta_node = root.add_child("metaData")
        
        # 源文件路径（Blender 文件路径）
        source_file = getattr(model, 'source_file', 'Unknown')
        meta_node.add_child("sourceFile", source_file)
        
        # 计算机名
        computer_name = getattr(model, 'computer', getpass.getuser())
        meta_node.add_child("computer", computer_name)
        
        # 创建者
        created_by = getattr(model, 'created_by', getpass.getuser())
        meta_node.add_child("created_by", created_by)
        
        # 创建时间（使用当前时间）
        created_on = getattr(model, 'created_on', int(time.time()))
        meta_node.add_child("created_on", str(created_on))
        
        # 修改者
        modified_by = getattr(model, 'modified_by', 'BlenderExporter')
        meta_node.add_child("modified_by", modified_by)
        
        # 修改时间
        modified_on = int(time.time())
        meta_node.add_child("modified_on", str(modified_on))


def write_model(filepath: str, model: Model) -> None:
    """
    便捷函数：写入 .model 文件
    
    参数:
        filepath: 输出文件路径
        model: Model 数据结构
    """
    writer = ModelWriter(filepath)
    writer.write(model)
