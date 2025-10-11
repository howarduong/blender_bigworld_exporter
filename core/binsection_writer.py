# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - BinSection Writer (strictly aligned)

- Centralizes binary writing with explicit endianness and alignment control
- Manages sections: begin/end, logical key -> numeric ID mapping, names
- Provides scalar writers (u8/u16/u32/i32/f32), bytes, fixed-length strings, cstrings
- Ensures consistent structure across all writers (no ad-hoc file layout)
- Keeps placeholders and reserved fields intact (no omissions)

Author: Blender 4.5.3 adaptation team
"""

from __future__ import annotations
import io
import os
import struct
from dataclasses import dataclass
from typing import Optional, Dict, Any, BinaryIO, Iterator, Tuple


# =========================
# Endianness / alignment
# =========================

@dataclass
class BinaryWriter:
    """
    Minimalistic binary writer with explicit endianness and alignment padding.
    """
    stream: BinaryIO
    little_endian: bool = True

    # ---- scalar writers ----
    def write_u8(self, v: int) -> None:
        self.stream.write(struct.pack('<B' if self.little_endian else '>B', v & 0xFF))

    def write_u16(self, v: int) -> None:
        self.stream.write(struct.pack('<H' if self.little_endian else '>H', v & 0xFFFF))

    def write_u32(self, v: int) -> None:
        self.stream.write(struct.pack('<I' if self.little_endian else '>I', v & 0xFFFFFFFF))

    def write_i32(self, v: int) -> None:
        self.stream.write(struct.pack('<i' if self.little_endian else '>i', int(v)))

    def write_f32(self, v: float) -> None:
        self.stream.write(struct.pack('<f' if self.little_endian else '>f', float(v)))

    # ---- bulk writers ----
    def write_bytes(self, data: bytes) -> None:
        self.stream.write(data)

    def write_cstring(self, s: str) -> None:
        """
        Write zero-terminated string (UTF-8). No length prefix.
        """
        self.stream.write(s.encode('utf-8'))
        self.stream.write(b'\x00')

    def align(self, boundary: int) -> None:
        """
        Align to 'boundary' bytes by writing zero padding.
        """
        pos = self.stream.tell()
        pad = (boundary - (pos % boundary)) % boundary
        if pad:
            self.stream.write(b'\x00' * pad)


# =========================
# Section registry and writer
# =========================

class SectionRegistry:
    """
    Logical-key -> numeric ID mapping registry.
    Keep IDs aligned with legacy Max plugin output.
    """
    def __init__(self):
        # Default mapping; adjust per legacy spec if needed.
        self._map: Dict[str, int] = {
            # Primitives
            "PRIM_VERTICES":      0x1001,
            "PRIM_INDICES":       0x1002,

            # Visual
            "VISUAL_HEADER":      0x2001,
            "VISUAL_LOD":         0x2002,
            "VISUAL_MATERIALS":   0x2003,

            # Model
            "MODEL_HEADER":       0x3001,
            "MODEL_NODETREE":     0x3002,
            "MODEL_REFERENCES":   0x3003,

            # Skeleton
            "SKELETON_MAIN":      0x4001,
            "SKELETON_HARDPOINTS":0x4002,

            # Animation
            "ANIM_MAIN":          0x5001,
            "ANIM_CUE":           0x5002,

            # Collision
            "COLLISION_HEADER":   0x6001,
            "COLLISION_MESH":     0x6002,
            "COLLISION_GROUPS":   0x6003,
            "COLLISION_BSP":      0x6004,  # placeholder
            "COLLISION_CONVEX":   0x6005,  # placeholder

            # Prefab
            "PREFAB_MAIN":        0x7001,
        }

    def get_id(self, key: str) -> int:
        if key not in self._map:
            raise KeyError(f"Section key '{key}' not registered in SectionRegistry.")
        return self._map[key]

    def set_id(self, key: str, value: int) -> None:
        """
        Override or add mapping to match exact legacy outputs.
        """
        self._map[key] = int(value)

    def contains(self, key: str) -> bool:
        return key in self._map


class BinSectionWriter:
    """
    Manages file creation and section framing:
    - open(path): returns context manager; ensures file is created and stream ready
    - begin_section(key): writes section header (ID + placeholder size)
    - end_section(): patches section size based on content written
    - Uses BinaryWriter for content serialization within sections
    """

    def __init__(self, registry: Optional[SectionRegistry] = None, little_endian: bool = True, align_boundary: int = 4):
        self.registry = registry or SectionRegistry()
        self.little_endian = little_endian
        self.align_boundary = align_boundary

        # Current file stream and writers
        self._stream: Optional[BinaryIO] = None
        self.binw: Optional[BinaryWriter] = None

        # Section state
        self._section_stack: list[Tuple[int, int]] = []  # [(start_pos, id)]
        self._closed: bool = True

    # ---- file management ----
    def open(self, path: str) -> 'BinSectionWriter':
        """
        Context manager: open file for binary write, set up BinaryWriter.
        Usage:
          with binsection.open(path) as secw:
              secw.begin_section("PRIM_VERTICES")
              ...
              secw.end_section()
        """
        class _Context:
            def __init__(self, outer: BinSectionWriter, target_path: str):
                self._outer = outer
                self._path = target_path

            def __enter__(self):
                self._outer._open_stream(self._path)
                return self._outer

            def __exit__(self, exc_type, exc_val, exc_tb):
                self._outer._close_stream()

        return _Context(self, path)

    def _open_stream(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._stream = open(path, 'wb')
        self.binw = BinaryWriter(self._stream, little_endian=self.little_endian)
        self._closed = False

    def _close_stream(self) -> None:
        # Ensure all sections properly closed
        if self._section_stack:
            raise RuntimeError("Unclosed sections detected on close. Ensure end_section() is called for every begin_section().")
        if self._stream:
            self._stream.flush()
            self._stream.close()
        self._stream = None
        self.binw = None
        self._closed = True

    # ---- section framing ----
    def begin_section(self, key: str) -> None:
        """
        Write section header:
        - u32: section ID
        - u32: section size placeholder (to be patched on end_section)
        Followed by aligned content.
        """
        if self._closed or self._stream is None or self.binw is None:
            raise RuntimeError("Stream not open. Use 'with binsection.open(path) as secw:' to begin sections.")

        sec_id = self.registry.get_id(key)

        # Write header
        self.binw.write_u32(sec_id)
        # Placeholder for size; record position to back-patch
        size_pos = self._stream.tell()
        self.binw.write_u32(0)

        # Align content start if required
        self.binw.align(self.align_boundary)

        # Push state
        self._section_stack.append((size_pos, sec_id))

    def end_section(self) -> None:
        """
        Patch the section size in bytes (from after size field to current position),
        then align to boundary for next section header.
        """
        if not self._section_stack:
            raise RuntimeError("end_section() called without a matching begin_section().")

        # Pop current section
        size_pos, sec_id = self._section_stack.pop()

        cur_pos = self._stream.tell()
        # Section content begins after the placeholder (4 bytes) + alignment padding already applied
        # To compute size: read the position just after size field, then subtract from current.
        # For simplicity, we stored the placeholder position (size_pos). Content starts at:
        content_start = size_pos + 4  # immediately after size field; any internal alignment already occurred

        # Compute size
        size_bytes = cur_pos - content_start

        # Patch size
        # Save current position
        after_pos = self._stream.tell()
        # Seek to size_pos and write size
        self._stream.seek(size_pos)
        self.binw.write_u32(size_bytes)
        # Seek back
        self._stream.seek(after_pos)

        # Align for next section header
        self.binw.align(self.align_boundary)
