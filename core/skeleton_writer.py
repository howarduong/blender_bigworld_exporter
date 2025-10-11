# 相对路径: core/skeleton_writer.py
# 功能: 导出骨骼数据，包括:
#   - 骨骼层级 (父子关系)
#   - Bind Pose / Inverse Bind Pose 矩阵
#   - 硬点 (HardPoint) 挂点信息
#
# 注意:
#   - 字段顺序、默认值、对齐方式必须与原 3ds Max 插件一致。
#   - 矩阵写出顺序需在 schema_reference.md 固化 (行主/列主)。
#   - 坐标系需从 Blender Y-Up 转换为 BigWorld Z-Up。

from typing import List, Dict
import bpy

from .binsection_writer import BinWriter, SectionWriter
from .utils import axis_map_matrix_y_up_to_z_up_row_major, to_row_major_tuple_4x4


class SkeletonWriter:
    """骨骼导出器"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    # =========================
    # 骨骼写出
    # =========================
    def write_skeleton(self, armature: bpy.types.Object):
        """
        导出骨骼数据。
        参数:
            armature: Blender 骨架对象 (Object.type == 'ARMATURE')
        """
        if not armature or armature.type != 'ARMATURE':
            # 没有骨架时写空
            self.write_empty_skeleton()
            return

        bones = armature.data.bones
        bone_index = {b.name: i for i, b in enumerate(bones)}

        self.secw.begin_section(section_id=0x3001)  # 示例 ID，需在 schema 固化
        self.binw.write_u32(len(bones))

        for bone in bones:
            self._write_single_bone(bone, bone_index)

        self.secw.end_section()

    def _write_single_bone(self, bone: bpy.types.Bone, bone_index_map: Dict[str, int]):
        """
        导出单个骨骼。
        字段顺序:
          1) 名称 (cstring)
          2) 父索引 (i32, -1 表示无父)
          3) Bind Pose 矩阵 (f32x16, 行主序 + 坐标系转换)
          4) Inverse Bind Pose 矩阵 (f32x16, 行主序 + 坐标系转换)
        """
        # 名称
        self.binw.write_cstring(bone.name)

        # 父骨骼索引
        parent_index = -1
        if bone.parent:
            parent_index = bone_index_map.get(bone.parent.name, -1)
        self.binw.write_i32(parent_index)

        # Bind Pose
        mat = bone.matrix_local
        row_major = to_row_major_tuple_4x4(mat)
        mapped = axis_map_matrix_y_up_to_z_up_row_major(row_major)
        for v in mapped:
            self.binw.write_f32(float(v))

        # Inverse Bind Pose
        inv_mat = mat.inverted()
        inv_row_major = to_row_major_tuple_4x4(inv_mat)
        inv_mapped = axis_map_matrix_y_up_to_z_up_row_major(inv_row_major)
        for v in inv_mapped:
            self.binw.write_f32(float(v))

    def write_empty_skeleton(self):
        """写出空骨架 (占位)。"""
        self.secw.begin_section(section_id=0x3001)
        self.binw.write_u32(0)
        self.secw.end_section()

    # =========================
    # 硬点写出
    # =========================
    def write_hardpoints(self, hardpoints: List[Dict]):
        """
        导出硬点 (HardPoint)。
        参数:
            hardpoints: 硬点列表，每个硬点为 dict:
                {
                    "name": str,
                    "type": str,
                    "bone": str,
                    "matrix": List[float] (4x4 行主序)
                }
        """
        if not hardpoints:
            self.write_empty_hardpoints()
            return

        self.secw.begin_section(section_id=0x3002)  # 示例 ID，需在 schema 固化
        self.binw.write_u32(len(hardpoints))

        for hp in hardpoints:
            self._write_single_hardpoint(hp)

        self.secw.end_section()

    def _write_single_hardpoint(self, hp: Dict):
        """
        导出单个硬点。
        字段顺序:
          1) 名称 (cstring)
          2) 类型 (cstring)
          3) 绑定骨骼名称 (cstring)
          4) 矩阵 (f32x16, 行主序 + 坐标系转换)
        """
        # 名称
        self.binw.write_cstring(hp.get("name", ""))

        # 类型
        self.binw.write_cstring(hp.get("type", "weapon"))

        # 绑定骨骼名称
        self.binw.write_cstring(hp.get("bone", ""))

        # 矩阵
        mat = hp.get("matrix", [1.0] * 16)
        mapped = axis_map_matrix_y_up_to_z_up_row_major(mat)
        for v in mapped:
            self.binw.write_f32(float(v))

    def write_empty_hardpoints(self):
        """写出空硬点表 (占位)。"""
        self.secw.begin_section(section_id=0x3002)
        self.binw.write_u32(0)
        self.secw.end_section()
