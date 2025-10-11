# 相对路径: core/portal_writer.py
# 功能: 导出门户 (Portal) 数据，包括:
#   - 门户类型 (标准/天堂/出口/无)
#   - 门户标签 (字符串标识)
#   - 门户几何 (对象边界/自定义网格)
#
# 注意:
#   - 字段顺序、默认值、对齐方式必须与原 3ds Max 插件一致。
#   - 门户几何来源需支持两种模式: 自动边界盒、自定义网格。
#   - 门户类型与标签需与 BigWorld 引擎规范对齐。

from typing import List, Dict
import bpy
from mathutils import Vector

from .binsection_writer import BinWriter, SectionWriter


class PortalWriter:
    """门户导出器"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    # =========================
    # 主入口
    # =========================
    def write_portals(self, portals: List[Dict]):
        """
        导出门户列表。
        参数:
            portals: 门户列表，每个门户为 dict:
                {
                    "type": str,       # 门户类型 (standard/heaven/exit/none)
                    "label": str,      # 门户标签
                    "geometry": str,   # "BOUNDING_BOX" 或 "CUSTOM_MESH"
                    "object": bpy.types.Object  # Blender 对象 (可选)
                }
        """
        self.secw.begin_section(section_id=0x6001)  # 示例 ID，需在 schema 固化

        # 写门户数量
        self.binw.write_u32(len(portals))

        # 遍历门户
        for portal in portals:
            self._write_single_portal(portal)

        self.secw.end_section()

    # =========================
    # 单个门户
    # =========================
    def _write_single_portal(self, portal: Dict):
        """
        导出单个门户。
        """
        # 门户类型
        portal_type = portal.get("type", "standard")
        self.binw.write_cstring(portal_type)

        # 门户标签
        portal_label = portal.get("label", "")
        self.binw.write_cstring(portal_label)

        # 门户几何来源
        geom_mode = portal.get("geometry", "BOUNDING_BOX")
        self.binw.write_cstring(geom_mode)

        obj = portal.get("object", None)

        # ========== BOUNDING_BOX 模式 ==========
        if geom_mode == "BOUNDING_BOX" and obj:
            # 自动计算包围盒
            bbox_world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

            # 写顶点数量 (8 个角点)
            self.binw.write_u32(8)

            # 写 8 个顶点
            for v in bbox_world:
                self.binw.write_f32(v.x)
                self.binw.write_f32(v.y)
                self.binw.write_f32(v.z)

            # 占位: 包围盒模式不写索引，保持对齐
            self.binw.write_u32(0)

        # ========== CUSTOM_MESH 模式 ==========
        elif geom_mode == "CUSTOM_MESH" and obj and obj.type == 'MESH':
            mesh = obj.data
            mesh.calc_loop_triangles()

            vertices = [tuple(v.co) for v in mesh.vertices]
            indices: List[int] = []
            for tri in mesh.loop_triangles:
                indices.extend(tri.vertices)

            # 写顶点数量
            self.binw.write_u32(len(vertices))
            for vx in vertices:
                self.binw.write_f32(vx[0])
                self.binw.write_f32(vx[1])
                self.binw.write_f32(vx[2])

            # 写索引数量
            self.binw.write_u32(len(indices))
            for i in indices:
                self.binw.write_u32(int(i))

        # ========== 无几何 ==========
        else:
            # 写顶点数量 0
            self.binw.write_u32(0)
            # 写索引数量 0
            self.binw.write_u32(0)
