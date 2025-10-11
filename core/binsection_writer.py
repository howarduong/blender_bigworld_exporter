# 相对路径: core/binsection_writer.py
# 功能: 提供二进制写出基础能力，包括大小端控制、类型写出、
#       对齐（4/8/16）、块写出（开始/回填长度/结束）、字符串与数组写出。

from __future__ import annotations
from typing import BinaryIO, Iterable, Optional, Tuple
import struct


class BinWriter:
    """二进制写出器：控制大小端、对齐与常用类型写出"""

    def __init__(self, f: BinaryIO, little_endian: bool = True, default_align: int = 4):
        self.f = f
        self.le = little_endian
        self.default_align = default_align

    # =========================
    # 位置与对齐
    # =========================
    def tell(self) -> int:
        return self.f.tell()

    def seek(self, pos: int):
        self.f.seek(pos)

    def pad_align(self, boundary: Optional[int] = None):
        boundary = boundary or self.default_align
        pos = self.tell()
        pad = (-pos) % boundary
        if pad:
            self.f.write(b"\x00" * pad)

    # =========================
    # 原始写入
    # =========================
    def write_bytes(self, data: bytes):
        self.f.write(data)

    # =========================
    # 基础类型写出
    # =========================
    def _fmt(self, code: str) -> str:
        return ("<" if self.le else ">") + code

    def write_u8(self, v: int):
        self.f.write(struct.pack(self._fmt("B"), v & 0xFF))

    def write_i8(self, v: int):
        self.f.write(struct.pack(self._fmt("b"), v))

    def write_u16(self, v: int):
        self.f.write(struct.pack(self._fmt("H"), v & 0xFFFF))

    def write_i16(self, v: int):
        self.f.write(struct.pack(self._fmt("h"), v))

    def write_u32(self, v: int):
        self.f.write(struct.pack(self._fmt("I"), v & 0xFFFFFFFF))

    def write_i32(self, v: int):
        self.f.write(struct.pack(self._fmt("i"), v))

    def write_u64(self, v: int):
        self.f.write(struct.pack(self._fmt("Q"), v & 0xFFFFFFFFFFFFFFFF))

    def write_i64(self, v: int):
        self.f.write(struct.pack(self._fmt("q"), v))

    def write_f16(self, v: float):
        f32 = struct.pack(self._fmt("f"), float(v))
        f32_i = struct.unpack(self._fmt("I"), f32)[0]
        sign = (f32_i >> 31) & 0x1
        exp = (f32_i >> 23) & 0xFF
        frac = f32_i & 0x7FFFFF
        if exp == 0:
            h_exp = 0
            h_frac = 0
        elif exp == 0xFF:
            h_exp = 0x1F
            h_frac = 0
        else:
            h_exp = max(0, min(0x1F, exp - 127 + 15))
            h_frac = frac >> (23 - 10)
        h = (sign << 15) | (h_exp << 10) | h_frac
        self.f.write(struct.pack(self._fmt("H"), h))

    def write_f32(self, v: float):
        self.f.write(struct.pack(self._fmt("f"), float(v)))

    def write_f64(self, v: float):
        self.f.write(struct.pack(self._fmt("d"), float(v)))

    # =========================
    # 复合类型写出
    # =========================
    def write_vec2f(self, v: Tuple[float, float]):
        self.write_f32(v[0])
        self.write_f32(v[1])

    def write_vec3f(self, v: Tuple[float, float, float]):
        self.write_f32(v[0])
        self.write_f32(v[1])
        self.write_f32(v[2])

    def write_vec4f(self, v: Tuple[float, float, float, float]):
        self.write_f32(v[0])
        self.write_f32(v[1])
        self.write_f32(v[2])
        self.write_f32(v[3])

    def write_quatf(self, q: Tuple[float, float, float, float]):
        self.write_f32(q[0])
        self.write_f32(q[1])
        self.write_f32(q[2])
        self.write_f32(q[3])

    def write_mat3x3f(self, m: Iterable[float]):
        for x in m:
            self.write_f32(float(x))

    def write_mat4x4f(self, m: Iterable[float]):
        for x in m:
            self.write_f32(float(x))

    # =========================
    # 字符串写出
    # =========================
    def write_cstring(self, s: str, encoding: str = "utf-8"):
        b = s.encode(encoding)
        self.write_bytes(b)
        self.write_bytes(b"\x00")

    def write_pascal_string(self, s: str, encoding: str = "utf-8"):
        b = s.encode(encoding)
        self.write_u32(len(b))
        self.write_bytes(b)

    # =========================
    # 数组写出
    # =========================
    def write_u16_array(self, arr: Iterable[int]):
        for v in arr:
            self.write_u16(int(v))

    def write_u32_array(self, arr: Iterable[int]):
        for v in arr:
            self.write_u32(int(v))

    def write_f32_array(self, arr: Iterable[float]):
        for v in arr:
            self.write_f32(float(v))


class SectionWriter:
    """块写出器"""

    def __init__(self, binw: BinWriter, align: Optional[int] = None):
        self.binw = binw
        self.align = align
        self._len_pos_stack = []
        self._start_pos_stack = []

    def begin_section(self, section_id: int):
        self.binw.write_u32(section_id)
        len_pos = self.binw.tell()
        self.binw.write_u32(0xDEADBEEF)
        start_pos = self.binw.tell()
        self._len_pos_stack.append(len_pos)
        self._start_pos_stack.append(start_pos)

    def end_section(self):
        if not self._len_pos_stack or not self._start_pos_stack:
            raise RuntimeError("end_section called without matching begin_section")

        current_pos = self.binw.tell()
        start_pos = self._start_pos_stack.pop()
        len_pos = self._len_pos_stack.pop()

        total_len = current_pos - start_pos

        back = self.binw.tell()
        self.binw.seek(len_pos)
        self.binw.write_u32(total_len)
        self.binw.seek(back)

        self.binw.pad_align(self.align or self.binw.default_align)


class BWHeaderWriter:
    """BigWorld 文件头写出助手"""

    def __init__(self, binw: BinWriter):
        self.binw = binw

    def write_header(self, magic: bytes, version: int):
        if not isinstance(magic, (bytes, bytearray)):
            raise TypeError("magic must be bytes")
        self.binw.write_bytes(magic)
        self.binw.write_u32(int(version))
