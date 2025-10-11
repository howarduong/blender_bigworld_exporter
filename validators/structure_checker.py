# 相对路径: blender_bigworld_exporter/validators/structure_checker.py
# 功能: 严格对齐 Max 插件的结构校验器
# 支持 .model / .visual / .primitives 三类文件

import struct
import os
from typing import Dict, List

class StructureChecker:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

        # .model 文件 schema
        self.model_schema = {
            0x1001: {"name": "Header", "min_size": 24, "alignment": 4, "defaults": {20: 0, 24: 0}},
            0x1002: {"name": "NodeTree", "min_size": 32, "alignment": 4},
            0x1003: {"name": "References", "min_size": 12, "alignment": 4, "defaults": {8: 0}},
            0x1004: {"name": "Skeleton", "min_size": 32, "alignment": 4},
            0x1005: {"name": "Animation", "min_size": 32, "alignment": 4},
            0x1006: {"name": "CueTrack", "min_size": 16, "alignment": 4},
            0x1007: {"name": "Portal", "min_size": 16, "alignment": 4},
            0x1008: {"name": "Collision", "min_size": 32, "alignment": 4},
            0x1009: {"name": "Prefab", "min_size": 16, "alignment": 4},
            0x1010: {"name": "Hitbox", "min_size": 16, "alignment": 4},
        }
        self.model_expected_order = [0x1001, 0x1002, 0x1003]

        # .visual 文件 schema
        self.visual_schema = {
            0x2001: {"name": "Header", "min_size": 16, "alignment": 4},
            0x2002: {"name": "RenderSet", "min_size": 32, "alignment": 4},
            0x2003: {"name": "MaterialList", "min_size": 16, "alignment": 4},
            0x2004: {"name": "ExtraData", "min_size": 8, "alignment": 4, "defaults": {0: 0}},
        }
        self.visual_expected_order = [0x2001, 0x2002, 0x2003]

        # .primitives 文件 schema
        self.primitives_schema = {
            0x3001: {"name": "Header", "min_size": 16, "alignment": 4},
            0x3002: {"name": "VertexBuffer", "min_size": 64, "alignment": 4},
            0x3003: {"name": "IndexBuffer", "min_size": 32, "alignment": 4},
            0x3004: {"name": "GroupTable", "min_size": 16, "alignment": 4},
            0x3005: {"name": "SkinWeights", "min_size": 32, "alignment": 4},
            0x3006: {"name": "ExtraData", "min_size": 8, "alignment": 4, "defaults": {0: 0}},
        }
        self.primitives_expected_order = [0x3001, 0x3002, 0x3003]

    def _check_file(self, filepath: str, schema: Dict[int, Dict], expected_order: List[int]) -> Dict:
        report = {
            "filepath": filepath,
            "sections": [],
            "errors": [],
            "warnings": []
        }

        if not os.path.exists(filepath):
            report["errors"].append(f"文件不存在: {filepath}")
            return report

        with open(filepath, "rb") as f:
            section_index = 0
            while True:
                header = f.read(8)
                if not header or len(header) < 8:
                    break

                section_id, length = struct.unpack("<II", header)
                start_pos = f.tell()
                data = f.read(length)
                end_pos = f.tell()

                section_info = {
                    "id": hex(section_id),
                    "length": length,
                    "start": start_pos,
                    "end": end_pos
                }

                # 顺序检查
                if expected_order:
                    if section_index < len(expected_order):
                        expected_id = expected_order[section_index]
                        if section_id != expected_id:
                            report["errors"].append(
                                f"Section 顺序错误: 期望 {hex(expected_id)}, 实际 {hex(section_id)}"
                            )
                    else:
                        report["warnings"].append(f"多余的 section: {hex(section_id)}")

                # schema 检查
                if section_id not in schema:
                    report["warnings"].append(f"未知 section ID: {hex(section_id)}")
                else:
                    schema_def = schema[section_id]

                    # 长度检查
                    if length < schema_def.get("min_size", 0):
                        report["errors"].append(
                            f"Section {hex(section_id)} 长度 {length} 小于最小值 {schema_def['min_size']}"
                        )

                    # 对齐检查
                    align = schema_def.get("alignment", 4)
                    if (start_pos % align) != 0:
                        report["warnings"].append(
                            f"Section {hex(section_id)} 未按 {align} 字节对齐 (start={start_pos})"
                        )

                    # 默认值检查
                    defaults = schema_def.get("defaults", {})
                    for offset, expected_val in defaults.items():
                        if offset + 4 <= len(data):
                            actual_val = struct.unpack_from("<I", data, offset)[0]
                            if actual_val != expected_val:
                                report["errors"].append(
                                    f"Section {hex(section_id)} 偏移 {offset} 默认值错误: "
                                    f"期望 {expected_val}, 实际 {actual_val}"
                                )

                report["sections"].append(section_info)
                section_index += 1

        return report

    # 三类文件专用校验
    def check_model_file(self, filepath: str) -> Dict:
        return self._check_file(filepath, self.model_schema, self.model_expected_order)

    def check_visual_file(self, filepath: str) -> Dict:
        return self._check_file(filepath, self.visual_schema, self.visual_expected_order)

    def check_primitives_file(self, filepath: str) -> Dict:
        return self._check_file(filepath, self.primitives_schema, self.primitives_expected_order)
