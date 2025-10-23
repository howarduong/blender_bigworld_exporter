# -*- coding: utf-8 -*-
"""
导出配置数据类
将UI属性转换为内部配置对象
"""

from typing import List, Optional


class ExportSettings:
    """全局导出配置"""
    
    def __init__(self):
        self.root_path = ""  # Res根目录（所有相对路径都相对于此计算）
        self.axis_mode = "Z_UP_TO_Y_UP"
        self.unit_scale = 1.0
        self.auto_validate = True
        self.write_audit = True
    
    @classmethod
    def from_preferences(cls, prefs):
        """从Blender偏好设置创建配置对象"""
        settings = cls()
        settings.root_path = prefs.root_path
        settings.axis_mode = prefs.axis_mode
        settings.unit_scale = prefs.unit_scale
        settings.auto_validate = prefs.auto_validate
        settings.write_audit = prefs.write_audit
        return settings


class ActionConfig:
    """Action配置"""
    
    def __init__(self, name, animation_name, blended, track):
        self.name = name
        self.animation_name = animation_name
        self.blended = blended
        self.track = track


class HardpointConfig:
    """硬点配置"""
    
    def __init__(self, name, hardpoint_type, bone_name, use_empty, target_empty):
        self.name = name
        self.hardpoint_type = hardpoint_type
        self.bone_name = bone_name
        self.use_empty = use_empty
        self.target_empty = target_empty


class ObjectExportSettings:
    """对象导出配置"""
    
    def __init__(self):
        self.export_type = "STATIC"  # STATIC / SKINNED / CHARACTER
        self.resource_id = ""
        self.parent_model = None
        self.actions = []  # List[ActionConfig]
        self.hardpoints = []  # List[HardpointConfig]
    
    @classmethod
    def from_object_properties(cls, obj):
        """从Blender对象属性创建配置对象"""
        settings = cls()
        props = obj.bigworld_props
        
        settings.export_type = props.export_type
        settings.resource_id = props.resource_id if props.resource_id else obj.name
        settings.parent_model = props.parent_model if props.parent_model else None
        
        # 提取Action配置
        if hasattr(obj, 'bigworld_actions'):
            for action in obj.bigworld_actions:
                settings.actions.append(ActionConfig(
                    name=action.name,
                    animation_name=action.animation_name,
                    blended=action.blended,
                    track=action.track
                ))
        
        # 提取Hardpoint配置
        if hasattr(obj, 'bigworld_hardpoints'):
            for hp in obj.bigworld_hardpoints:
                settings.hardpoints.append(HardpointConfig(
                    name=hp.name,
                    hardpoint_type=hp.hardpoint_type,
                    bone_name=hp.bone_name,
                    use_empty=hp.use_empty,
                    target_empty=hp.target_empty
                ))
        
        return settings

