# File: core/file_manager.py
# Purpose: 统一文件管理系统
# Notes:
# - 目录创建和管理
# - 路径解析和计算
# - 文件操作封装

import os
from pathlib import Path
from typing import Optional


class FileManager:
    """
    文件管理器
    
    提供统一的文件操作接口，所有导出类型公用
    """
    
    @staticmethod
    def ensure_directory(file_path: str) -> None:
        """
        确保目录存在
        
        参数:
            file_path: 文件路径
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def resolve_path(relative_path: str, root_path: str) -> str:
        """
        解析相对路径为绝对路径
        
        参数:
            relative_path: 相对路径
            root_path: 根目录路径
        
        返回:
            绝对路径
        """
        return os.path.normpath(os.path.join(root_path, relative_path))
    
    @staticmethod
    def get_relative_path(file_path: str, root_path: str) -> str:
        """
        计算文件路径相对于根目录的相对路径
        
        参数:
            file_path: 文件绝对路径
            root_path: 根目录路径
        
        返回:
            相对路径（正斜杠分隔）
        """
        try:
            # 统一路径格式
            file_path = os.path.normpath(file_path)
            root_path = os.path.normpath(root_path)
            
            # 计算相对路径
            rel_path = os.path.relpath(file_path, root_path)
            
            # 转换为正斜杠分隔（BigWorld 标准）
            rel_path = rel_path.replace(os.sep, '/')
            
            return rel_path
        except ValueError:
            # 如果路径不在根目录下，返回文件名
            return os.path.basename(file_path)
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        获取文件扩展名
        
        参数:
            file_path: 文件路径
        
        返回:
            扩展名（包含点号）
        """
        return os.path.splitext(file_path)[1]
    
    @staticmethod
    def get_file_name_without_extension(file_path: str) -> str:
        """
        获取不带扩展名的文件名
        
        参数:
            file_path: 文件路径
        
        返回:
            不带扩展名的文件名
        """
        return os.path.splitext(os.path.basename(file_path))[0]
    
    @staticmethod
    def is_file_exists(file_path: str) -> bool:
        """
        检查文件是否存在
        
        参数:
            file_path: 文件路径
        
        返回:
            文件是否存在
        """
        return os.path.exists(file_path)
    
    @staticmethod
    def remove_file(file_path: str) -> bool:
        """
        删除文件
        
        参数:
            file_path: 文件路径
        
        返回:
            是否删除成功
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def create_temp_file(prefix: str = "bw_", suffix: str = ".tmp") -> str:
        """
        创建临时文件
        
        参数:
            prefix: 文件名前缀
            suffix: 文件名后缀
        
        返回:
            临时文件路径
        """
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"{prefix}{os.urandom(8).hex()}{suffix}")
        return temp_file
