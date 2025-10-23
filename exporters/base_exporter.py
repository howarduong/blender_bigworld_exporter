# -*- coding: utf-8 -*-
"""
基础导出器（抽象类）
定义导出流程模板
"""

from abc import ABC, abstractmethod


class BaseExporter(ABC):
    """
    基础导出器
    使用模板方法模式定义导出流程
    """
    
    def __init__(self, output_dir, logger=None):
        """
        初始化导出器
        
        参数:
            output_dir: str - 输出目录
            logger: Logger - 日志记录器
        """
        self.output_dir = output_dir
        self.logger = logger
    
    def export(self, obj, settings):
        """
        导出流程模板方法
        
        参数:
            obj: bpy.types.Object - Blender对象
            settings: ObjectExportSettings - 导出配置
        
        返回:
            dict - 导出结果信息
        """
        try:
            # 1. 验证
            if not self.validate(obj, settings):
                return {'success': False, 'message': '验证失败'}
            
            # 2. 构建数据
            data = self.build_data(obj, settings)
            
            # 3. 写入文件
            files = self.write_files(data, settings)
            
            # 4. 后处理
            self.post_process(files, settings)
            
            return {
                'success': True,
                'files': files,
                'message': '导出成功'
            }
        
        except Exception as e:
            if self.logger:
                self.logger.error("导出失败: {0}".format(str(e)))
            return {'success': False, 'message': str(e)}
    
    def validate(self, obj, settings):
        """
        验证对象和设置
        
        参数:
            obj: bpy.types.Object
            settings: ObjectExportSettings
        
        返回:
            bool - 是否通过验证
        """
        # 基础验证
        if not obj:
            if self.logger:
                self.logger.error("对象为空")
            return False
        
        if obj.type != 'MESH':
            if self.logger:
                self.logger.error("对象不是网格类型")
            return False
        
        if not settings.resource_id:
            if self.logger:
                self.logger.warning("资源ID为空，将使用对象名")
        
        return True
    
    @abstractmethod
    def build_data(self, obj, settings):
        """
        构建导出数据（子类实现）
        
        参数:
            obj: bpy.types.Object
            settings: ObjectExportSettings
        
        返回:
            数据对象（具体类型由子类定义）
        """
        pass
    
    @abstractmethod
    def write_files(self, data, settings):
        """
        写入文件（子类实现）
        
        参数:
            data: 构建的数据对象
            settings: ObjectExportSettings
        
        返回:
            List[str] - 写入的文件路径列表
        """
        pass
    
    def post_process(self, files, settings):
        """
        后处理（可选，子类可覆盖）
        
        参数:
            files: List[str] - 已写入的文件列表
            settings: ObjectExportSettings
        """
        if self.logger:
            self.logger.info("导出完成，共生成{0}个文件".format(len(files)))

