# File: core/path_resolver.py
# Purpose: 路径解析与转换（绝对路径 → 相对路径）
# Notes:
# - BigWorld 文件中所有引用使用相对路径（相对于资源根目录）
# - 统一使用正斜杠 `/`
# - 去掉文件扩展名（.visual 引用时写为 path/to/model，不是 path/to/model.visual）

import os
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Optional


class PathResolver:
    """
    路径解析器
    
    职责：
    1. 绝对路径 → 相对路径（相对于资源根目录）
    2. 统一斜杠为正斜杠 `/`
    3. 去掉文件扩展名（可选）
    
    使用方式:
        resolver = PathResolver(root_path="D:/game/res/")
        rel_path = resolver.to_relative("D:/game/res/models/hero.visual")
        # 返回: "models/hero"（去掉扩展名）
    """
    
    def __init__(self, root_path: str):
        """
        初始化路径解析器
        
        参数:
            root_path: 资源根目录（绝对路径）
        """
        # 统一为绝对路径，使用正斜杠
        self.root_path = self._normalize_path(os.path.abspath(root_path))
    
    def to_relative(self, abs_path: str, remove_extension: bool = True) -> str:
        """
        转换绝对路径为相对路径
        
        参数:
            abs_path: 绝对路径
            remove_extension: 是否去掉扩展名
        
        返回:
            相对路径（正斜杠分隔）
        
        示例:
            root: "D:/game/res/"
            abs:  "D:/game/res/models/hero.visual"
            返回: "models/hero"（去掉扩展名）
        """
        # 统一为绝对路径
        abs_path = self._normalize_path(os.path.abspath(abs_path))
        
        # 检查是否在根目录下
        if not abs_path.startswith(self.root_path):
            raise ValueError(f"路径 {abs_path} 不在资源根目录 {self.root_path} 下")
        
        # 计算相对路径
        rel_path = abs_path[len(self.root_path):]
        
        # 去掉前导斜杠
        if rel_path.startswith('/'):
            rel_path = rel_path[1:]
        
        # 去掉扩展名
        if remove_extension:
            rel_path = os.path.splitext(rel_path)[0]
        
        return rel_path
    
    def to_absolute(self, rel_path: str, extension: str = "") -> str:
        """
        转换相对路径为绝对路径
        
        参数:
            rel_path: 相对路径
            extension: 要添加的扩展名（如 ".visual"）
        
        返回:
            绝对路径（正斜杠分隔）
        """
        # 添加扩展名
        if extension and not rel_path.endswith(extension):
            rel_path = rel_path + extension
        
        # 拼接路径
        abs_path = os.path.join(self.root_path, rel_path)
        
        # 统一为正斜杠
        return self._normalize_path(abs_path)
    
    def _normalize_path(self, path: str) -> str:
        """
        统一路径格式：正斜杠，去掉末尾斜杠
        
        参数:
            path: 原始路径
        
        返回:
            统一格式的路径
        """
        # 统一为正斜杠
        path = path.replace('\\', '/')
        
        # 去掉末尾的斜杠（根目录除外）
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]
        
        return path
    
    def ensure_directory(self, filepath: str) -> None:
        """
        确保文件所在目录存在
        
        参数:
            filepath: 文件路径
        """
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


# ==================== 便捷函数 ====================

def normalize_path(path: str) -> str:
    """
    统一路径格式（正斜杠）
    
    参数:
        path: 原始路径
    
    返回:
        统一格式的路径（正斜杠）
    """
    return path.replace('\\', '/')


def remove_extension(path: str) -> str:
    """
    去掉文件扩展名
    
    参数:
        path: 文件路径
    
    返回:
        去掉扩展名的路径
    """
    return os.path.splitext(path)[0]


def get_relative_path(abs_path: str, root_path: str, remove_ext: bool = True) -> str:
    """
    快捷函数：获取相对路径
    
    参数:
        abs_path: 绝对路径
        root_path: 根目录
        remove_ext: 是否去掉扩展名
    
    返回:
        相对路径（正斜杠）
    """
    resolver = PathResolver(root_path)
    return resolver.to_relative(abs_path, remove_extension=remove_ext)

