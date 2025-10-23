# File: core/packed_section_writer.py
# Purpose: 写出 BigWorld PackedSection 文件（.visual/.model/.animation 容器）
# Spec:
# - magic_number: 0x62A14E45
# - version: int8 (通常为 1)
# - string_table: 去重 key，null 结尾，最后一个空字符串
# - data_section: num_children + child_record[] + bin_data
# - child_record: (key_index:int16, data_offset:int32)
# - bin_data: 实际值（int/float/string/Vector/Matrix），整数有压缩优化
#
# 输入: 树形节点结构（PackedNode）
# 输出: PackedSection 二进制文件

import struct
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

MAGIC = 0x62A14E45
VERSION = 1


@dataclass
class PackedNode:
    key: str
    value: Optional[Any] = None
    children: List["PackedNode"] = field(default_factory=list)


class PackedSectionWriter:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.string_table: Dict[str, int] = {}  # key -> index
        self.strings: List[str] = []
        self.root_nodes: List[PackedNode] = []

    # ---------------------------
    # 构建节点树
    # ---------------------------

    def add_node(self, key: str, value: Any = None, children: Optional[List[PackedNode]] = None):
        node = PackedNode(key, value, children or [])
        self.root_nodes.append(node)
        return node

    # ---------------------------
    # 内部工具
    # ---------------------------

    def _add_string(self, s: str) -> int:
        if s not in self.string_table:
            idx = len(self.strings)
            self.string_table[s] = idx
            self.strings.append(s)
        return self.string_table[s]

    def _encode_value(self, v: Any) -> bytes:
        """编码值到 bin_data"""
        if v is None:
            return b""
        if isinstance(v, bool):
            return struct.pack("<B", 1 if v else 0)
        if isinstance(v, int):
            # 压缩优化
            if v == 0:
                return b""
            elif -128 <= v <= 127:
                return struct.pack("<b", v)
            elif -32768 <= v <= 32767:
                return struct.pack("<h", v)
            else:
                return struct.pack("<i", v)
        if isinstance(v, float):
            return struct.pack("<f", v)
        if isinstance(v, str):
            return v.encode("utf-8") + b"\x00"
        if isinstance(v, (list, tuple)):
            # 向量/矩阵
            if all(isinstance(x, (int, float)) for x in v):
                return b"".join(struct.pack("<f", float(x)) for x in v)
        raise TypeError(f"Unsupported value type: {type(v)}")

    # ---------------------------
    # 写入流程
    # ---------------------------

    def write(self):
        with open(self.filepath, "wb") as f:
            # 1. magic + version
            f.write(struct.pack("<I", MAGIC))
            f.write(struct.pack("<B", VERSION))

            # 2. 构建 string_table
            def collect_strings(node: PackedNode):
                self._add_string(node.key)
                for c in node.children:
                    collect_strings(c)
            for n in self.root_nodes:
                collect_strings(n)

            # 写 string_table
            for s in self.strings:
                f.write(s.encode("utf-8") + b"\x00")
            f.write(b"\x00")  # 结束空字符串

            # 3. 写 data_section
            self._write_nodes(f, self.root_nodes)

    def _write_nodes(self, f, nodes: List[PackedNode]):
        # num_children
        f.write(struct.pack("<I", len(nodes)))

        # child_record 占位
        record_pos = f.tell()
        f.write(b"\x00" * (len(nodes) * (2 + 4)))  # key_index:int16 + data_pos:int32

        # bin_data
        data_offsets = []
        bin_start = f.tell()
        for node in nodes:
            data_offsets.append(f.tell() - bin_start)
            # 写 value
            if node.value is not None:
                f.write(self._encode_value(node.value))
            # 写 children
            if node.children:
                self._write_nodes(f, node.children)

        # 回填 child_record
        cur = f.tell()
        f.seek(record_pos)
        for i, node in enumerate(nodes):
            key_idx = self.string_table[node.key]
            f.write(struct.pack("<hI", key_idx, data_offsets[i]))
        f.seek(cur)
