# File: core/bin_section_writer.py
# Purpose: 提供 BinSectionWriter 类，用于写入 BigWorld 的 .primitives 文件容器。
# 主要功能：
# - 写入 BinSection 格式（严格按照文档 ch03.html 和源码 bin_section.cpp）
# - 格式：<MagicNumber><ChildSectionData>*<IndexTable>
# - IndexTable: <DataSectionEntry>*<IndexTableLength>
# - DataSectionEntry: <BlobLength><ReservedData(16字节)><TagLength><TagValue(4字节对齐)>
# - 确保所有 section 4 字节对齐

import struct
import time
from typing import List, Tuple, Optional

# 常量定义（来自 bin_section.cpp）
BINSECTION_MAGIC = 0x42A14E65


class BinSectionWriter:
    """
    BinSectionWriter
    ----------------
    用于生成 BigWorld BinSection 文件（例如 .primitives）。
    
    格式（来自文档和源码）：
    1. Magic Number (4 bytes): 0x42A14E65
    2. Child Section Data (每个 section 的二进制数据，4字节对齐)
    3. Index Table:
       - DataSectionEntry* (每个 section 一个条目)
       - Index Table Length (4 bytes)
    
    DataSectionEntry 格式：
    - BlobLength (4 bytes): section 数据长度
    - ReservedData (16 bytes): preloadLen(4) + version(4) + modified(8)
    - TagLength (4 bytes): tag 字符串长度
    - TagValue (变长，4字节对齐): tag 字符串
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fp = None
        self.sections: List[Tuple[str, int, int]] = []  # (tag, offset, length)
        self._curr_tag: Optional[str] = None
        self._start_offset: int = 0
        self._data_start_offset: int = 0  # 数据区起始位置

    # --- 生命周期控制 ---
    def open(self) -> None:
        """打开文件并写入 magic number"""
        if self.fp is not None:
            raise RuntimeError("BinSectionWriter already opened")
        self.fp = open(self.filepath, "wb")
        
        # 仅写入 magic number（4 bytes）
        self.fp.write(struct.pack("<I", BINSECTION_MAGIC))
        self._data_start_offset = self.fp.tell()

    def finalize(self) -> None:
        """写入 index table 并保存文件"""
        if self.fp is None:
            raise RuntimeError("BinSectionWriter not opened")
        
        # 记录 index table 开始位置
        index_table_start = self.fp.tell()
        
        # 写入所有 DataSectionEntry
        for tag, offset, length in self.sections:
            # 1. BlobLength (4 bytes)
            self.fp.write(struct.pack("<I", length))
            
            # 2. ReservedData (16 bytes) - 根据BigWorld源码，应该全部为0
            self.fp.write(b"\x00" * 16)
            
            # 3. TagLength (4 bytes)
            tag_bytes = tag.encode("ascii")
            self.fp.write(struct.pack("<I", len(tag_bytes)))
            
            # 4. TagValue (变长，4字节对齐)
            self.fp.write(tag_bytes)
            # 对齐到 4 字节
            while self.fp.tell() % 4 != 0:
                self.fp.write(b"\x00")
        
        # 5. IndexTableLength (4 bytes) - index table 的长度（不包括这4字节）
        index_table_length = self.fp.tell() - index_table_start
        self.fp.write(struct.pack("<I", index_table_length))
        
        self.fp.close()
        self.fp = None

    # --- section 控制 ---
    def begin_section(self, tag: str) -> None:
        """开始一个新的 section"""
        if self.fp is None:
            raise RuntimeError("BinSectionWriter not opened")
        if self._curr_tag is not None:
            raise RuntimeError("Previous section not ended")
        self._curr_tag = tag
        self._start_offset = self.fp.tell()

    def end_section(self) -> None:
        """结束当前 section 并记录到列表"""
        if self.fp is None or self._curr_tag is None:
            raise RuntimeError("No section to end")
        
        end_offset = self.fp.tell()
        length = end_offset - self._start_offset
        
        # 记录 section 信息（tag, offset, length）
        self.sections.append((
            self._curr_tag,
            self._start_offset - self._data_start_offset,  # 相对于数据区的偏移
            length
        ))
        
        # 对齐到 4 字节
        while self.fp.tell() % 4 != 0:
            self.fp.write(b"\x00")
        
        self._curr_tag = None
        self._start_offset = 0

    # --- 写入工具函数 ---
    def write_string(self, s: str, fixed_len: Optional[int] = None) -> None:
        """写入字符串（可选固定长度）"""
        bs = s.encode("utf-8")
        if fixed_len is None:
            self.fp.write(bs + b"\x00")
        else:
            if len(bs) > fixed_len:
                bs = bs[:fixed_len]
            self.fp.write(bs + b"\x00" * (fixed_len - len(bs)))

    def write_uint32(self, v: int) -> None:
        """写入 uint32"""
        self.fp.write(struct.pack("<I", int(v)))

    def write_uint16(self, v: int) -> None:
        """写入 uint16"""
        self.fp.write(struct.pack("<H", int(v)))

    def write_float(self, v: float) -> None:
        """写入 float"""
        self.fp.write(struct.pack("<f", float(v)))

    def write_vector2(self, uv) -> None:
        """写入 2D 向量"""
        self.fp.write(struct.pack("<ff", float(uv[0]), float(uv[1])))

    def write_vector3(self, v) -> None:
        """写入 3D 向量"""
        self.fp.write(struct.pack("<fff", float(v[0]), float(v[1]), float(v[2])))

    def write_indices_u16(self, indices) -> None:
        """写入 uint16 索引数组"""
        for i in indices:
            self.fp.write(struct.pack("<H", int(i)))

    def write_indices_u32(self, indices) -> None:
        """写入 uint32 索引数组"""
        for i in indices:
            self.fp.write(struct.pack("<I", int(i)))
    
    def write_bytes(self, data: bytes) -> None:
        """写入原始字节数据"""
        self.fp.write(data)
    
    def write_byte(self, v: int) -> None:
        """写入单个字节"""
        self.fp.write(struct.pack("<B", int(v)))
    
    def write_packed_normal(self, v: tuple) -> None:
        """
        写入packed法线/切线（uint32，11-11-10位）
        
        根据BigWorld引擎源码 moo_math.hpp packNormal函数：
        - x: 11位 (无符号，范围0到1023，对应-1.0到1.0)
        - y: 11位 (无符号，范围0到1023，对应-1.0到1.0)  
        - z: 10位 (无符号，范围0到511，对应-1.0到1.0)
        
        注意：BigWorld直接将[-1,1]映射到[0,1023/511]，使用无符号整数
        """
        # 归一化并clamp到[-1, 1]
        import math
        length = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
        if length > 0.0001:
            nx = max(-1.0, min(1.0, v[0] / length))
            ny = max(-1.0, min(1.0, v[1] / length))
            nz = max(-1.0, min(1.0, v[2] / length))
        else:
            nx, ny, nz = 0.0, 0.0, 1.0
        
        # 按照BigWorld源码的方式：直接乘以511/1023
        # 注意：BigWorld期望法线在[-1,1]范围内
        x_packed = int(nx * 1023.0) & 0x7ff  # 11位掩码
        y_packed = int(ny * 1023.0) & 0x7ff  # 11位掩码
        z_packed = int(nz * 511.0) & 0x3ff   # 10位掩码
        
        # 打包成uint32 (11-11-10位格式)
        # 按照BigWorld源码的顺序：z << 22 | y << 11 | x
        packed = (z_packed << 22) | (y_packed << 11) | x_packed
        
        self.write_uint32(packed)
