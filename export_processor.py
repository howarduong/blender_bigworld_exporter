# File: export_processor.py
# Purpose: 统一导出处理器
# Notes:
# - 基于UI选择动态组合流程
# - 集成公用组件
# - 支持不同的导出类型和模式

import bpy
from typing import List, Optional, Dict, Any
from .core.coordinate_converter import CoordinateConverter
from .utils.file_manager import FileManager
from .utils.logger import Logger
from .core.schema import (
    Primitives, Visual, Model, Skeleton, Animation, 
    ModelAnimation, ExportSettings, ObjectType
)
from .export_builders import (
    PrimitivesBuilder, VisualBuilder, ModelBuilder, 
    SkeletonBuilder, AnimationBuilder
)
from .export_dispatcher import ExportDispatcher
from .builders.model.hardpoint_builder import HardpointBuilder
from .builders.model.action_builder import ActionBuilder
from .config.export_settings import ObjectExportSettings


class ExportProcessor:
    """
    统一导出处理器
    
    基于UI选择动态组合流程，集成所有公用组件
    """
    
    def __init__(self, settings: ExportSettings, logger: Logger, output_dir: str):
        """
        初始化导出处理器
        
        参数:
            settings: 导出设置
            logger: 日志记录器
            output_dir: 输出目录
        """
        self.settings = settings
        self.logger = logger
        self.output_dir = output_dir
        
        # 公用组件
        self.coordinate_converter = CoordinateConverter()
        self.file_manager = FileManager()
        
        # 创建导出调度器
        self.dispatcher = ExportDispatcher(settings, logger, output_dir)
    
    def process_object(self, obj: bpy.types.Object, 
                      export_type: str, 
                      file_options: Dict[str, bool]) -> bool:
        """
        处理单个对象的导出
        
        参数:
            obj: Blender对象
            export_type: 导出类型 (STATIC, SKINNED, CHARACTER)
            file_options: 文件生成选项
        
        返回:
            导出是否成功
        """
        try:
            # 检测Armature
            armature_obj = self._detect_armature(obj)
            
            # 根据导出类型选择处理流程
            if export_type == 'STATIC':
                return self._process_static(obj, file_options)
            elif export_type == 'SKINNED':
                return self._process_skinned(obj, armature_obj, file_options)
            elif export_type == 'CHARACTER':
                return self._process_character(obj, armature_obj, file_options)
            else:
                self.logger.error(f"未知的导出类型: {export_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"处理对象 {obj.name} 失败: {e}")
            return False
    
    def _detect_armature(self, obj: bpy.types.Object) -> Optional[bpy.types.Object]:
        """
        检测对象的Armature
        
        参数:
            obj: Blender对象
        
        返回:
            Armature对象，如果没有则返回None
        """
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                return mod.object
        return None
    
    def _process_static(self, obj: bpy.types.Object, file_options: Dict[str, bool]) -> bool:
        """
        处理静态模型导出
        
        参数:
            obj: Blender对象
            file_options: 文件生成选项
        
        返回:
            导出是否成功
        """
        self.logger.info(f"开始处理静态模型: {obj.name}")
        
        # 构建数据
        resource_id = obj.bigworld_props.resource_id if obj.bigworld_props.resource_id else obj.name
        primitives = PrimitivesBuilder.build(obj, force_static=True)
        visual = VisualBuilder.build(obj, f"{resource_id}.primitives", skeleton=None)
        model = ModelBuilder.build(obj, resource_id, has_skeleton=False)
        
        # 设置资源ID
        model.resource_id = resource_id
        
        # 生成文件
        return self._generate_files(
            object_type=ObjectType.STATIC,
            primitives=primitives,
            visual=visual,
            model=model,
            animations=None,
            file_options=file_options
        )
    
    def _process_skinned(self, obj: bpy.types.Object, armature_obj: Optional[bpy.types.Object], 
                        file_options: Dict[str, bool]) -> bool:
        """
        处理蒙皮模型导出
        
        参数:
            obj: Blender对象
            armature_obj: Armature对象
            file_options: 文件生成选项
        
        返回:
            导出是否成功
        """
        if not armature_obj:
            self.logger.warning(f"导出类型为蒙皮模型，但未检测到 Armature！")
            self.logger.warning(f"将降级为静态模型导出")
            return self._process_static(obj, file_options)
        
        self.logger.info(f"开始处理蒙皮模型: {obj.name}")
        self.logger.info(f"检测到 Armature: {armature_obj.name}")
        
        # 构建数据
        resource_id = obj.bigworld_props.resource_id if obj.bigworld_props.resource_id else obj.name
        skeleton = SkeletonBuilder.build(armature_obj)
        primitives = PrimitivesBuilder.build(obj, force_static=False)
        visual = VisualBuilder.build(obj, f"{resource_id}.primitives", skeleton)
        model = ModelBuilder.build(obj, resource_id, has_skeleton=True)
        
        # 设置资源ID
        model.resource_id = resource_id
        
        # 构建硬点（新增）
        obj_settings = ObjectExportSettings.from_object_properties(obj)
        if obj_settings.hardpoints:
            hardpoints = HardpointBuilder.build_all(obj_settings.hardpoints, skeleton)
            model.hardpoints = hardpoints
            self.logger.info(f"已构建 {len(hardpoints)} 个硬点")
        
        # 生成文件
        return self._generate_files(
            object_type=ObjectType.SKINNED,
            primitives=primitives,
            visual=visual,
            model=model,
            animations=None,
            file_options=file_options
        )
    
    def _process_character(self, obj: bpy.types.Object, armature_obj: Optional[bpy.types.Object], 
                          file_options: Dict[str, bool]) -> bool:
        """
        处理角色动画导出
        
        参数:
            obj: Blender对象
            armature_obj: Armature对象
            file_options: 文件生成选项
        
        返回:
            导出是否成功
        """
        if not armature_obj:
            self.logger.warning(f"导出类型为角色模型，但未检测到 Armature！")
            self.logger.warning(f"将降级为静态模型导出")
            return self._process_static(obj, file_options)
        
        self.logger.info(f"开始处理角色动画: {obj.name}")
        self.logger.info(f"检测到 Armature: {armature_obj.name}")
        
        # 构建数据
        resource_id = obj.bigworld_props.resource_id if obj.bigworld_props.resource_id else obj.name
        skeleton = SkeletonBuilder.build(armature_obj)
        primitives = PrimitivesBuilder.build(obj, force_static=False)
        visual = VisualBuilder.build(obj, f"{resource_id}.primitives", skeleton)
        
        # 构建动画数据
        animations = self._build_animations(armature_obj)
        
        # 构建模型数据（包含动画引用）
        model = ModelBuilder.build(obj, resource_id, has_skeleton=True)
        model.resource_id = resource_id
        
        # 添加动画引用
        if animations:
            model.animations = []
            for anim in animations:
                model_anim = ModelAnimation(
                    name=anim.name,
                    resource=f"{obj.name}/animations/{anim.name}"
                )
                model.animations.append(model_anim)
        
        # 构建硬点（新增）
        obj_settings = ObjectExportSettings.from_object_properties(obj)
        if obj_settings.hardpoints:
            hardpoints = HardpointBuilder.build_all(obj_settings.hardpoints, skeleton)
            model.hardpoints = hardpoints
            self.logger.info(f"已构建 {len(hardpoints)} 个硬点")
        
        # 构建Action（新增）
        if obj_settings.actions and animations:
            # 创建动画名称集合（用于验证）
            animation_names = set(anim.name for anim in animations)
            actions = ActionBuilder.build_all(obj_settings.actions, animation_names)
            model.actions = actions
            self.logger.info(f"已构建 {len(actions)} 个Action")
        
        # 生成文件
        return self._generate_files(
            object_type=ObjectType.CHARACTER,
            primitives=primitives,
            visual=visual,
            model=model,
            animations=animations,
            file_options=file_options
        )
    
    def _build_animations(self, armature_obj: bpy.types.Object) -> List[Animation]:
        """
        构建动画数据
        
        参数:
            armature_obj: Armature对象
        
        返回:
            动画数据列表
        """
        animations = []
        
        if not armature_obj.animation_data or not armature_obj.animation_data.action:
            self.logger.info("未检测到动画数据")
            return animations
        
        # 获取所有Action
        all_actions = []
        for action in bpy.data.actions:
            all_actions.append(action)
        
        self.logger.info(f"检测到 {len(all_actions)} 个动画")
        
        # 构建每个动画
        for action in all_actions:
            try:
                # 设置当前Action
                original_action = armature_obj.animation_data.action
                armature_obj.animation_data.action = action
                
                # 构建动画数据（传入单个action对象，不是列表）
                animation = AnimationBuilder.build(armature_obj, action)
                animations.append(animation)
                
                self.logger.info(f"已构建动画: {animation.name}")
                
                # 恢复原始Action
                armature_obj.animation_data.action = original_action
                
            except Exception as e:
                self.logger.error(f"构建动画 {action.name} 失败: {e}")
        
        return animations
    
    def _generate_files(self, object_type: ObjectType, primitives: Optional[Primitives], 
                       visual: Optional[Visual], model: Optional[Model], 
                       animations: Optional[List[Animation]], 
                       file_options: Dict[str, bool]) -> bool:
        """
        生成文件
        
        参数:
            object_type: 对象类型
            primitives: 几何数据
            visual: 视觉数据
            model: 模型数据
            animations: 动画数据
            file_options: 文件生成选项
        
        返回:
            生成是否成功
        """
        try:
            # 使用ExportDispatcher生成文件
            success = self.dispatcher.dispatch(
                object_type=object_type,
                primitives=primitives,
                visual=visual,
                model=model,
                animations=animations
            )
            
            if success:
                self.logger.info(f"文件生成成功")
            else:
                self.logger.error(f"文件生成失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"文件生成失败: {e}")
            return False
