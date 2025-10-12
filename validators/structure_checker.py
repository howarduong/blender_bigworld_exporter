# -*- coding: utf-8 -*-
"""
BigWorld Blender Exporter - Structure Checker
严格对齐 Max 插件的结构与几何校验器
- 二进制结构校验（.model / .visual / .primitives）
- PrimitivesWriter 所需的几何后置校验（validate_*）
"""

from typing import Dict, List
import struct
import os

# ========== 二进制结构校验（文件级） ==========

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


# ========== PrimitivesWriter 几何后置校验（函数式导出） ==========

def validate_vertex_count(mesh, expected_count: int = None) -> bool:
    if mesh is None or not hasattr(mesh, "vertices"):
        raise ValueError("无效的 mesh 对象（缺少 vertices）")
    actual = len(mesh.vertices)
    if expected_count is not None and actual != expected_count:
        raise ValueError(f"顶点数量不匹配: 期望 {expected_count}, 实际 {actual}")
    if actual == 0:
        raise ValueError("顶点数量为 0")
    return True


def validate_index_count(mesh, expected_count: int = None) -> bool:
    if mesh is None or not hasattr(mesh, "polygons"):
        raise ValueError("无效的 mesh 对象（缺少 polygons）")
    actual = sum(len(p.vertices) for p in mesh.polygons)
    if expected_count is not None and actual != expected_count:
        raise ValueError(f"索引数量不匹配: 期望 {expected_count}, 实际 {actual}")
    return True


def validate_material_groups(obj, required_slots: int = None) -> bool:
    if obj is None or not hasattr(obj.data, "materials"):
        raise ValueError("对象没有材质槽")
    actual = len(obj.data.materials)
    if required_slots is not None and actual < required_slots:
        raise ValueError(f"材质槽数量不足: 期望至少 {required_slots}, 实际 {actual}")
    return True


def validate_vertex_streams(streams) -> bool:
    count = streams.count()
    if count == 0:
        raise ValueError("VertexStreams 为空")
    if len(streams.positions) != count:
        raise ValueError("positions 数量与顶点数不一致")
    if len(streams.normals) not in (0, count):
        raise ValueError("normals 数量与顶点数不一致")
    if len(streams.tangents) not in (0, count):
        raise ValueError("tangents 数量与顶点数不一致")
    if len(streams.uv0) not in (0, count):
        raise ValueError("uv0 数量与顶点数不一致")
    if len(streams.uv1) not in (0, count):
        raise ValueError("uv1 数量与顶点数不一致")
    if len(streams.colors) not in (0, count):
        raise ValueError("colors 数量与顶点数不一致")
    # 若使用 skin（非默认全重 1.0 到槽 0）则须对齐数量
    if any(w != (1.0, 0.0, 0.0, 0.0) for w in streams.bone_weights):
        if len(streams.bone_indices) != count or len(streams.bone_weights) != count:
            raise ValueError("skin 顶点数据数量与顶点数不一致")
    return True


def validate_primitives_topology(streams, indices) -> bool:
    if len(indices) % 3 != 0:
        raise ValueError("索引数量不是 3 的倍数，拓扑错误")
    vcount = streams.count()
    if vcount == 0 and len(indices) > 0:
        raise ValueError("存在索引但顶点数为 0")
    if len(indices) > 0:
        if min(indices) < 0:
            raise ValueError("索引存在负值")
        if max(indices) >= vcount:
            raise ValueError("索引引用超出顶点范围")
    return True


def validate_primitives_groups(indices, groups, vertex_count: int) -> bool:
    total_indices = len(indices)
    group_sum = sum(g.num_primitives * 3 for g in groups)
    if group_sum != total_indices:
        raise ValueError(f"PrimitiveGroup 索引数量不匹配: 组内 {group_sum}, 实际 {total_indices}")
    for g in groups:
        if g.start_vertex < 0:
            raise ValueError("PrimitiveGroup start_vertex 为负数")
        if g.num_vertices < 0:
            raise ValueError("PrimitiveGroup num_vertices 为负数")
        if g.start_vertex + g.num_vertices > vertex_count:
            raise ValueError("PrimitiveGroup 顶点范围越界")
        if g.num_primitives < 0:
            raise ValueError("PrimitiveGroup num_primitives 为负数")
        if g.start_index < 0:
            raise ValueError("PrimitiveGroup start_index 为负数")
    return True
