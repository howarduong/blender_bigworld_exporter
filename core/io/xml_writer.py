# File: core/xml_writer.py
# Purpose: BigWorld DataSection 文本格式写入器（用于 .visual/.model 等）
# Notes:
# - BigWorld 使用特殊的类 XML 格式（DataSection 文本格式）
# - 格式规则（基于 xml_section.cpp 的 writeToStream 方法）：
#   - 值用 TAB 包围：<tag>\t值\t</tag>
#   - 缩进使用 TAB 字符
#   - 根标签使用文件名（如 <unit_cube.visual>）
#   - 可以混合值和子节点：<tag>\t值\n\t<child>...\n</tag>
#   - 数字格式化为 6 位小数

from typing import Any, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class DataSectionNode:
    """
    DataSection 节点
    
    可以同时有值和子节点（与标准 XML 不同）
    """
    tag: str
    value: Optional[str] = None
    children: List["DataSectionNode"] = field(default_factory=list)
    
    def add_child(self, tag: str, value: Optional[str] = None) -> "DataSectionNode":
        """添加子节点"""
        child = DataSectionNode(tag, value)
        self.children.append(child)
        return child


class DataSectionWriter:
    """
    BigWorld DataSection 文本格式写入器
    
    使用方式:
        writer = DataSectionWriter("test.visual")
        root = writer.create_root("test.visual")
        node = root.add_child("renderSet")
        node.add_child("node", "Scene Root")
        writer.save()
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.root: Optional[DataSectionNode] = None
    
    def create_root(self, tag: str) -> DataSectionNode:
        """创建根节点"""
        self.root = DataSectionNode(tag)
        return self.root
    
    def save(self) -> None:
        """保存到文件"""
        if self.root is None:
            raise ValueError("Root node not created")
        
        with open(self.filepath, 'w', encoding='utf-8', newline='\n') as f:
            self._write_node(f, self.root, level=0)
    
    def _write_node(self, f, node: DataSectionNode, level: int) -> None:
        """
        递归写入节点
        
        格式规则（来自 xml_section.cpp 第 2309 行）：
        1. 缩进用 TAB
        2. 开始标签：<tag>
        3. 如果有值：\t值\t 或 \t值\n
        4. 如果有子节点：\n\t<child>...\n
        5. 结束标签：</tag>\n
        """
        # 缩进
        indent = '\t' * level
        f.write(f"{indent}<{node.tag}>")
        
        # 判断是否有子节点
        has_children = len(node.children) > 0
        has_value = node.value is not None and node.value != ""
        
        if has_value and not has_children:
            # 格式：<tag>\t值\t</tag>
            f.write(f"\t{node.value}\t</{node.tag}>\n")
        
        elif has_value and has_children:
            # 格式：<tag>\t值\n\t<child>...\n</tag>
            f.write(f"\t{node.value}\n")
            for child in node.children:
                self._write_node(f, child, level + 1)
            f.write(f"{indent}</{node.tag}>\n")
        
        elif not has_value and has_children:
            # 格式：<tag>\n\t<child>...\n</tag>
            f.write("\n")
            for child in node.children:
                self._write_node(f, child, level + 1)
            f.write(f"{indent}</{node.tag}>\n")
        
        else:
            # 空标签：<tag>\t</tag>
            f.write(f"\t</{node.tag}>\n")


# ==================== 辅助函数 ====================

def format_float(value: float) -> str:
    """格式化浮点数为 BigWorld 格式（6位小数）"""
    return f"{value:.6f}"


def format_vector2(v: Tuple[float, float]) -> str:
    """格式化 Vector2"""
    return f"{format_float(v[0])} {format_float(v[1])}"


def format_vector3(v: Tuple[float, float, float]) -> str:
    """格式化 Vector3"""
    return f"{format_float(v[0])} {format_float(v[1])} {format_float(v[2])}"


def format_vector4(v: Tuple[float, float, float, float]) -> str:
    """格式化 Vector4"""
    return f"{format_float(v[0])} {format_float(v[1])} {format_float(v[2])} {format_float(v[3])}"


def format_bool(value: bool) -> str:
    """格式化布尔值"""
    return "true" if value else "false"


def format_int(value: int) -> str:
    """格式化整数"""
    return str(value)


def create_matrix_node(tag: str, matrix: List[List[float]]) -> DataSectionNode:
    """
    创建矩阵节点
    
    格式：
    <transform>
        <row0>\t1.0 0.0 0.0\t</row0>
        <row1>\t0.0 1.0 0.0\t</row1>
        <row2>\t0.0 0.0 1.0\t</row2>
        <row3>\t0.0 0.0 0.0\t</row3>
    </transform>
    """
    node = DataSectionNode(tag)
    for i in range(min(4, len(matrix))):
        row = matrix[i]
        # 只取前3列（4x3矩阵）
        row_value = format_vector3((row[0], row[1], row[2]))
        node.add_child(f"row{i}", row_value)
    return node


def create_bbox_node(tag: str, min_pt: Tuple[float, float, float], 
                     max_pt: Tuple[float, float, float]) -> DataSectionNode:
    """
    创建包围盒节点
    
    格式：
    <boundingBox>
        <min>\t-1.0 -1.0 -1.0\t</min>
        <max>\t1.0 1.0 1.0\t</max>
    </boundingBox>
    """
    node = DataSectionNode(tag)
    node.add_child("min", format_vector3(min_pt))
    node.add_child("max", format_vector3(max_pt))
    return node
