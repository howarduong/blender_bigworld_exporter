# File: writers/manifest_writer.py
# Purpose: 生成 manifest.json，记录所有导出产物与依赖关系
# Notes:
# - 记录文件路径、类型、hash、时间戳、依赖关系
# - 用于版本控制、增量构建、CI 校验
# - 格式：JSON

import json
import hashlib
import time
from pathlib import Path
from typing import List
from ..core.schema import Manifest, ManifestEntry


class ManifestWriter:
    """
    ManifestWriter
    --------------
    用于生成 manifest.json 文件，记录所有导出产物与依赖关系。
    
    使用方式:
        writer = ManifestWriter("output/manifest.json")
        writer.add_entry("models/hero.primitives", "primitives", dependencies=[])
        writer.add_entry("models/hero.visual", "visual", dependencies=["models/hero.primitives"])
        writer.add_entry("models/hero.model", "model", dependencies=["models/hero.visual"])
        writer.save()
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.manifest = Manifest(version=1)
    
    def add_entry(self, 
                  file_path: str, 
                  file_type: str, 
                  dependencies: List[str] = None) -> None:
        """
        添加文件条目
        
        参数:
            file_path: 文件路径（相对资源根目录）
            file_type: 文件类型（primitives / visual / model / animation / collision / portal）
            dependencies: 依赖文件列表（相对路径）
        """
        # 计算文件 hash（如果文件存在）
        file_hash = ""
        if Path(file_path).exists():
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
        
        entry = ManifestEntry(
            file=file_path,
            file_type=file_type,
            dependencies=dependencies or [],
            hash=file_hash,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )
        
        self.manifest.entries.append(entry)
    
    def save(self) -> None:
        """保存 manifest.json 到文件"""
        data = {
            "version": self.manifest.version,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "entries": [
                {
                    "file": entry.file,
                    "type": entry.file_type,
                    "dependencies": entry.dependencies,
                    "hash": entry.hash,
                    "timestamp": entry.timestamp
                }
                for entry in self.manifest.entries
            ]
        }
        
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_dependency_graph(self) -> dict:
        """
        获取依赖关系图
        
        返回:
            {文件路径: [依赖文件列表]}
        """
        graph = {}
        for entry in self.manifest.entries:
            graph[entry.file] = entry.dependencies
        return graph
    
    def validate_dependencies(self) -> List[str]:
        """
        校验依赖关系是否有效
        
        返回:
            错误消息列表
        """
        errors = []
        all_files = {entry.file for entry in self.manifest.entries}
        
        for entry in self.manifest.entries:
            for dep in entry.dependencies:
                if dep not in all_files:
                    errors.append(f"文件 {entry.file} 依赖的 {dep} 不在导出清单中")
        
        return errors
    
    def get_files_by_type(self, file_type: str) -> List[str]:
        """
        按类型获取文件列表
        
        参数:
            file_type: primitives / visual / model / animation
        
        返回:
            文件路径列表
        """
        return [entry.file for entry in self.manifest.entries 
                if entry.file_type == file_type]

