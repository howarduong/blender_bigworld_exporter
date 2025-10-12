# 相对路径: blender_bigworld_exporter/validators/path_validator.py
# 功能: 路径校验与修复，严格对齐 Max 插件风格
# 规则:
#   - 所有路径必须在 textures/ 子目录下
#   - 必须是相对路径，不能是绝对路径
#   - 不存在的路径替换为 textures/default.dds
#   - 分隔符统一为 "/"

from pathlib import Path
from typing import List, Dict


class PathValidator:
    """路径校验与修复器 (Max 插件风格)"""

    def __init__(self, root_dir: str, auto_fix: bool = False):
        """
        参数:
            root_dir: 导出根目录
            auto_fix: 是否启用自动修复
        """
        self.root_dir = Path(root_dir).resolve()
        self.auto_fix = auto_fix
        self.default_path = "textures/default.dds"

    def validate_paths(self, paths: List[str]) -> Dict:
        """
        校验路径列表。
        返回:
            {
                "valid": List[str],
                "fixed": List[str],
                "errors": List[str]
            }
        """
        result = {"valid": [], "fixed": [], "errors": []}

        for p in paths:
            fixed = self._validate_single_path(p)
            if fixed is None:
                result["errors"].append(p)
            elif fixed != p:
                result["fixed"].append(f"{p} -> {fixed}")
                result["valid"].append(fixed)
            else:
                result["valid"].append(p)

        return result

    def _validate_single_path(self, path: str) -> str | None:
        """
        校验并修复单个路径。
        """
        if not path:
            return None

        p = Path(path)

        # 1. 绝对路径 → 转相对路径
        if p.is_absolute():
            try:
                rel = p.relative_to(self.root_dir)
                rel_str = str(rel).replace("\\", "/")
                return self._check_and_fix(rel_str)
            except Exception:
                return self._handle_invalid(path)

        # 2. 相对路径 → 必须在 textures/ 下
        rel_str = str(p).replace("\\", "/")
        if not rel_str.lower().startswith("textures/"):
            return self._handle_invalid(path)

        return self._check_and_fix(rel_str)

    def _check_and_fix(self, rel_str: str) -> str | None:
        """检查路径是否存在，不存在时修复或报错"""
        full = self.root_dir / rel_str
        if full.exists():
            return rel_str
        else:
            if self.auto_fix:
                return self.default_path
            else:
                return None

    def _handle_invalid(self, path: str) -> str | None:
        """处理非法路径"""
        if self.auto_fix:
            return self.default_path
        else:
            return None
   # ====== 独立函数接口，供 Writer 调用 ======

def validate_output_path(path: str, required_ext: str = None) -> bool:
    """
    校验导出文件路径是否合法：
    - 父目录存在且可写
    - 扩展名符合要求（如果指定）
    """
    import os
    if not path or not isinstance(path, str):
        raise ValueError("输出路径无效：必须是字符串")

    parent = os.path.dirname(path)
    if not parent or not os.path.exists(parent):
        raise ValueError(f"输出目录不存在: {parent}")

    if not os.access(parent, os.W_OK):
        raise PermissionError(f"输出目录不可写: {parent}")

    if required_ext and not path.lower().endswith(required_ext.lower()):
        raise ValueError(f"输出文件扩展名必须为 {required_ext}")

    return True

