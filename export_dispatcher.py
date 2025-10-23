# File: export_dispatcher.py
# Purpose: 导出调度器，根据对象类型选择对应的导出流水线
# Notes:
# - 静态模型: .primitives → .visual → .model → manifest/audit
# - 角色: .primitives → .animation → .visual → .model → manifest/audit
# - 碰撞体: .collision → .model (可选) → manifest/audit ◆ 占位保留
# - 门户: .visual → .model → manifest/audit ◆ 占位保留

from typing import List, Optional
from pathlib import Path
import os
from .core.schema import (
    ExportSettings,
    ObjectSettings,
    ObjectType,
    Primitives,
    Visual,
    Model,
    Animation
)
from .utils.logger import Logger
from .utils.path_resolver import PathResolver
from .writers.audit_writer import AuditLogger, ErrorCode
from .writers.manifest_writer import ManifestWriter
from .builders.model.hardpoint_builder import HardpointBuilder
from .builders.model.action_builder import ActionBuilder
from .config.export_settings import ObjectExportSettings


class ExportDispatcher:
    """
    ExportDispatcher
    ----------------
    导出调度器，负责：
    1. 根据对象类型选择对应的 pipeline
    2. 调用 writers 生成文件
    3. 写入 manifest / audit
    4. 校验与回滚
    
    使用方式:
        dispatcher = ExportDispatcher(export_settings, audit_logger)
        dispatcher.dispatch(object_type, primitives, visual, model, animations)
    """
    
    def __init__(self, settings: ExportSettings, logger: Logger, output_dir: str):
        self.settings = settings
        self.logger = logger
        self.output_dir = output_dir  # 真正的输出目录（文件浏览器选择的目录）
        self.path_resolver = PathResolver(output_dir)  # 基于输出目录计算相对路径
        self.manifest = ManifestWriter(str(Path(output_dir) / "manifest.json"))
    
    def dispatch(self,
                 object_type: ObjectType,
                 primitives: Optional[Primitives] = None,
                 visual: Optional[Visual] = None,
                 model: Optional[Model] = None,
                 animations: Optional[List[Animation]] = None) -> bool:
        """
        调度导出流水线
        
        参数:
            object_type: 对象类型
            primitives: .primitives 数据
            visual: .visual 数据
            model: .model 数据
            animations: .animation 数据列表
        
        返回:
            导出是否成功
        """
        try:
            if object_type == ObjectType.STATIC:
                return self._export_static(primitives, visual, model)
            
            elif object_type == ObjectType.SKINNED:
                return self._export_skinned(primitives, visual, model)
            
            elif object_type == ObjectType.CHARACTER:
                return self._export_character(primitives, visual, model, animations)
            
            elif object_type == ObjectType.COLLISION:
                self.logger.warning("碰撞体导出功能占位保留")
                return False
            
            elif object_type == ObjectType.PORTAL:
                self.logger.warning("门户导出功能占位保留")
                return False
            
            elif object_type == ObjectType.GROUP:
                self.logger.warning("组导出功能占位保留")
                return False
            
            else:
                self.logger.error(f"未知对象类型: {object_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"导出失败: {e}")
            return False
    
    def _export_static(self, 
                       primitives: Optional[Primitives],
                       visual: Optional[Visual],
                       model: Optional[Model]) -> bool:
        """
        导出静态模型
        
        流程: .primitives → .visual → .model → manifest/audit
        """
        self.logger.info("开始导出静态模型")
        self.logger.info(f"输出目录: {self.output_dir}")
        
        # 计算文件路径
        resource_id = model.resource_id
        self.logger.info(f"资源ID: {resource_id}")
        
        # 绝对路径（基于输出目录）
        primitives_abs = os.path.join(self.output_dir, f"{resource_id}.primitives")
        visual_abs = os.path.join(self.output_dir, f"{resource_id}.visual")
        model_abs = os.path.join(self.output_dir, f"{resource_id}.model")
        
        self.logger.info(f"将写入文件:")
        self.logger.info(f"  - {primitives_abs}")
        self.logger.info(f"  - {visual_abs}")
        self.logger.info(f"  - {model_abs}")
        
        # 相对路径（用于文件内引用）
        # 需要计算相对于偏好设置根目录的相对路径
        primitives_rel = f"{resource_id}.primitives"
        
        # 计算 visual 的相对路径（相对于偏好设置根目录）
        # 例如：输出目录 D:\game\res\characters\dragon
        # 偏好设置根目录 D:\game\res\
        # 相对路径应该是 characters/dragon/resource_id
        if self.settings.root_path and os.path.isabs(self.settings.root_path):
            visual_abs_for_rel = os.path.join(self.output_dir, f"{resource_id}.visual")
            visual_rel = self._get_relative_to_root(visual_abs_for_rel, self.settings.root_path)
            # 去掉扩展名
            visual_rel = visual_rel.replace('.visual', '')
        else:
            # 如果没有设置根目录，直接使用resource_id
            visual_rel = resource_id
        
        # 1. 导出 .primitives
        if primitives:
            from .writers.primitives_writer import write_primitives
            try:
                self.path_resolver.ensure_directory(primitives_abs)
                write_primitives(primitives_abs, primitives)
                self.manifest.add_entry(primitives_rel, "primitives", [])
                self.logger.info(f"已写入 {primitives_abs}")
            except Exception as e:
                self.logger.error(f"写入 .primitives 失败: {e}")
                raise
        
        # 2. 导出 .visual
        if visual:
            from .writers.visual_writer import VisualWriter
            
            # 注意：.visual 中的 vertices/primitive 是固定值，不是文件路径
            # BigWorld 通过文件名约定自动关联同名 .primitives 文件
            
            self.path_resolver.ensure_directory(visual_abs)
            writer = VisualWriter(visual_abs, visual_rel)
            writer.write(visual)
            
            self.manifest.add_entry(visual_rel, "visual", [primitives_rel])
            self.logger.info(f"已写入 {visual_abs}")
        
        # 3. 导出 .model
        if model:
            from .writers.model_writer import write_model
            
            # 更新 model 中的 visual 引用为相对路径（去掉扩展名）
            # 例如：从 "models.visual" 改为 "models"
            self.logger.info(f"设置 model.visual = {visual_rel}")
            model.visual = visual_rel
            
            self.path_resolver.ensure_directory(model_abs)
            write_model(model_abs, model)
            
            model_rel = self.path_resolver.to_relative(model_abs, remove_extension=True)
            self.manifest.add_entry(model_rel, "model", [visual_rel])
            self.logger.info(f"已写入 {model_abs}")
        
        # 4. 保存 manifest
        self.manifest.save()
        self.logger.info("已写入 manifest.json")
        
        return True
    
    def _export_skinned(self,
                       primitives: Optional[Primitives],
                       visual: Optional[Visual],
                       model: Optional[Model]) -> bool:
        """
        导出蒙皮模型
        
        流程: .primitives → .visual → .model → manifest/audit
        与静态模型相同，但包含骨骼和蒙皮数据
        """
        self.logger.info("开始导出蒙皮模型")
        self.logger.info(f"输出目录: {self.output_dir}")
        
        # 计算文件路径
        resource_id = model.resource_id
        
        # 绝对路径（基于输出目录）
        primitives_abs = os.path.join(self.output_dir, f"{resource_id}.primitives")
        visual_abs = os.path.join(self.output_dir, f"{resource_id}.visual")
        model_abs = os.path.join(self.output_dir, f"{resource_id}.model")
        
        # 相对路径（用于文件内引用）
        primitives_rel = f"{resource_id}.primitives"
        
        # 计算visual的相对路径
        if self.settings.root_path and os.path.isabs(self.settings.root_path):
            visual_rel = self._get_relative_to_root(visual_abs, self.settings.root_path)
            visual_rel = visual_rel.replace('.visual', '')
        else:
            visual_rel = resource_id
        
        # 1. 导出 .primitives
        if primitives:
            from .writers.primitives_writer import write_primitives
            write_primitives(primitives_abs, primitives)
            self.manifest.add_entry(primitives_rel, "primitives", [])
            self.logger.info(f"已写入 {primitives_abs}")
        
        # 2. 导出 .visual（依赖 .primitives）
        if visual:
            from .writers.visual_writer import VisualWriter
            writer = VisualWriter(visual_abs, visual_rel)
            writer.write(visual)
            
            self.manifest.add_entry(visual_rel, "visual", [primitives_rel])
            self.logger.info(f"已写入 {visual_abs}")
        
        # 3. 导出 .model（依赖 .visual）
        if model:
            from .writers.model_writer import write_model
            
            # 更新model中的visual引用为相对路径
            model.visual = visual_rel
            
            write_model(model_abs, model)
            
            model_rel = self._get_relative_to_root(model_abs, self.settings.root_path)
            model_rel = model_rel.replace('.model', '')
            self.manifest.add_entry(model_rel, "model", [visual_rel])
            self.logger.info(f"已写入 {model_abs}")
        
        # 4. 保存 manifest
        self.manifest.save()
        self.logger.info("已写入 manifest.json")
        
        return True
    
    def _get_relative_to_root(self, filepath: str, root_path: str) -> str:
        """
        计算文件路径相对于根目录的相对路径
        
        参数:
            filepath: 文件绝对路径
            root_path: 根目录路径
        
        返回:
            相对路径（正斜杠分隔）
        """
        # 统一路径格式
        filepath = os.path.normpath(filepath)
        root_path = os.path.normpath(root_path)
        
        # 计算相对路径
        try:
            rel_path = os.path.relpath(filepath, root_path)
            # 统一为正斜杠
            rel_path = rel_path.replace('\\', '/')
            return rel_path
        except ValueError:
            # 如果路径不在根目录下，返回文件名
            return os.path.basename(filepath)
    
    def _export_character(self,
                          primitives: Optional[Primitives],
                          visual: Optional[Visual],
                          model: Optional[Model],
                          animations: Optional[List[Animation]]) -> bool:
        """
        导出角色模型
        
        正确的流程（按依赖关系）:
        1. .primitives  ← 几何数据（独立）
        2. .visual      ← 引用 .primitives
        3. .animation   ← 动画数据（独立）
        4. .model       ← 引用 .visual 和 .animation
        5. manifest     ← 记录所有文件
        """
        self.logger.info("开始导出角色模型")
        
        # 计算文件路径
        resource_id = model.resource_id
        
        # 绝对路径（基于输出目录）
        primitives_abs = os.path.join(self.output_dir, f"{resource_id}.primitives")
        visual_abs = os.path.join(self.output_dir, f"{resource_id}.visual")
        model_abs = os.path.join(self.output_dir, f"{resource_id}.model")
        
        # 相对路径（用于文件内引用）
        primitives_rel = f"{resource_id}.primitives"
        
        # 计算visual的相对路径
        if self.settings.root_path and os.path.isabs(self.settings.root_path):
            visual_rel = self._get_relative_to_root(visual_abs, self.settings.root_path)
            visual_rel = visual_rel.replace('.visual', '')
        else:
            visual_rel = resource_id
        
        # 1. 导出 .primitives
        if primitives:
            from .writers.primitives_writer import write_primitives
            write_primitives(primitives_abs, primitives)
            self.manifest.add_entry(primitives_rel, "primitives", [])
            self.logger.info(f"已写入 {primitives_abs}")
        
        # 2. 导出 .visual（依赖 .primitives）
        if visual:
            from .writers.visual_writer import VisualWriter
            writer = VisualWriter(visual_abs, visual_rel)
            writer.write(visual)
            
            self.manifest.add_entry(visual_rel, "visual", [primitives_rel])
            self.logger.info(f"已写入 {visual_abs}")
        
        # 3. 导出 .animation（到 animations/ 子目录）
        anim_paths = []
        anim_rel_paths = []  # 用于.model引用的相对路径
        if animations:
            from .writers.animation_writer import write_animation
            
            # 创建 animations 子目录
            animations_dir = os.path.join(self.output_dir, "animations")
            os.makedirs(animations_dir, exist_ok=True)
            
            for anim in animations:
                # 动画文件保存到 animations/ 子目录
                anim_filename = f"{anim.name}.animation"
                anim_abs_path = os.path.join(animations_dir, anim_filename)
                
                write_animation(anim_abs_path, anim)
                
                # 计算相对于root_path的路径（用于.model引用）
                anim_rel = self._get_relative_to_root(anim_abs_path, self.settings.root_path)
                anim_rel = anim_rel.replace('.animation', '')  # 去掉扩展名
                
                anim_paths.append(anim_abs_path)
                anim_rel_paths.append(anim_rel)
                
                self.manifest.add_entry(anim_rel, "animation", [])
                self.logger.info(f"已写入 {anim_abs_path}")
                self.logger.info(f"  动画引用路径: {anim_rel}")
        
        # 4. 导出 .model（依赖 .visual 和 .animation）
        if model:
            from .writers.model_writer import write_model
            from .core.schema import ModelAnimation
            
            # 更新 Model 的动画引用列表
            model.animations = []
            for anim_rel in anim_rel_paths:
                model.animations.append(ModelAnimation(
                    name=os.path.basename(anim_rel),  # 动画名
                    resource=anim_rel  # 相对路径（不含扩展名）
                ))
            
            # 更新model中的visual引用为相对路径
            model.visual = visual_rel
            
            write_model(model_abs, model)
            
            model_rel = self._get_relative_to_root(model_abs, self.settings.root_path)
            model_rel = model_rel.replace('.model', '')
            deps = [visual_rel] + anim_rel_paths
            self.manifest.add_entry(model_rel, "model", deps)
            self.logger.info(f"已写入 {model_abs}")
            self.logger.info(f"  包含 {len(model.animations)} 个动画引用")
        
        # 5. 保存 manifest
        self.manifest.save()
        self.logger.info("已写入 manifest.json")
        
        return True
    
    def finalize(self) -> None:
        """完成导出，保存 manifest"""
        self.manifest.save()

