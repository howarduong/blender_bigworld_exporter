# -*- coding: utf-8 -*-
"""
Action数据构建器
从UI配置构建Action数据
"""

from ...core.schema import ModelAction


class ActionBuilder:
    """Action构建器"""
    
    @staticmethod
    def build_all(action_configs, animations):
        """
        构建所有Action
        
        参数:
            action_configs: List[ActionConfig] - Action配置列表
            animations: List[ModelAnimation] - 已导出的动画列表
        
        返回:
            List[ModelAction] - Action数据列表
        """
        actions = []
        
        # 创建动画名称索引
        animation_names = set(anim.name for anim in animations)
        
        for config in action_configs:
            action = ActionBuilder.build(config, animation_names)
            if action:
                actions.append(action)
        
        return actions
    
    @staticmethod
    def build(config, animation_names):
        """
        构建单个Action
        
        参数:
            config: ActionConfig - Action配置
            animation_names: set - 可用的动画名称集合
        
        返回:
            ModelAction - Action数据
        """
        # 验证关联的动画是否存在
        if config.animation_name not in animation_names:
            print("WARNING: Action {0} 引用的动画 {1} 不存在，跳过".format(
                config.name, config.animation_name))
            return None
        
        return ModelAction(
            name=config.name,
            animation_ref=config.animation_name,
            blended=config.blended,
            track=config.track
        )
    
    @staticmethod
    def validate_action(action, animation_names):
        """
        验证Action配置
        
        参数:
            action: ModelAction - Action数据
            animation_names: set - 可用动画名称
        
        返回:
            bool - 是否有效
        """
        if not action.name:
            return False
        
        if not action.animation_ref:
            return False
        
        if action.animation_ref not in animation_names:
            return False
        
        if action.track < 0 or action.track > 10:
            return False
        
        return True

