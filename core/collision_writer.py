# 相对路径: core/collision_writer.py
# 功能: 导出碰撞数据，包括:
#   - 普通碰撞体 (原始几何)
#   - BSP (Binary Space Partitioning) 树
#   - 凸包 (Convex Hull)
#
# 注意:
#   - 字段顺序、默认值、对齐方式必须与原 3ds Max 插件一致。
#   - BSP/凸包的生成逻辑需与旧插件保持一致。
#   - 精度 (float32/float16) 需在 schema_reference.md 固化。

from typing import List, Tuple
import bpy

from .binsection_writer import BinWriter, SectionWriter
from .utils import flip_winding


class CollisionExportOptions:
    """碰撞导出选项"""
    def __init__(self, precision: str = "float32"):
        # 精度模式: "float32" 或 "float16"
        self.precision = precision


class CollisionWriter:
    """碰撞导出器"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    # =========================
    # 普通碰撞体
    # =========================
    def write_collision_mesh(self, mesh: bpy.types.Mesh, opts: CollisionExportOptions):
        """
        导出普通碰撞体 (原始几何)。
        """
        # 复制临时网格，避免污染原始数据
        temp_mesh = mesh.copy()
        temp_mesh.calc_loop_triangles()

        # 收集顶点
        vertices = [tuple(v.co) for v in temp_mesh.vertices]

        # 收集索引
        indices: List[int] = []
        for tri in temp_mesh.loop_triangles:
            indices.extend(tri.vertices)

        # 翻转绕序 (保持与 Max 插件一致)
        indices = flip_winding(indices)

        # 写 section
        self.secw.begin_section(section_id=0x5001)  # 示例 ID，需在 schema 固化

        # 写顶点/索引数量
        self.binw.write_u32(len(vertices))
        self.binw.write_u32(len(indices))

        # 写顶点数据
        for vx in vertices:
            if opts.precision == "float16":
                self.binw.write_f16(vx[0])
                self.binw.write_f16(vx[1])
                self.binw.write_f16(vx[2])
            else:
                self.binw.write_f32(vx[0])
                self.binw.write_f32(vx[1])
                self.binw.write_f32(vx[2])

        # 写索引数据
        for i in indices:
            # TODO: 确认旧插件是否使用 u16，这里先写 u32 占位
            self.binw.write_u32(int(i))

        self.secw.end_section()

        # 清理临时网格
        bpy.data.meshes.remove(temp_mesh)

    # =========================
    # BSP 碰撞体
    # =========================
    def write_bsp(self, mesh: bpy.types.Mesh):
        """
        导出 BSP 碰撞体。
        注意: 这里只是占位，真正的 BSP 构建需实现分割平面与节点树。
        """
        self.secw.begin_section(section_id=0x5002)  # 示例 ID

        # TODO: 实现 BSP 树构建逻辑 (需对照 BigWorld_Make_BSP.mcr)
        self.binw.write_u32(0)  # 占位: 节点数量
        self.binw.write_u32(0)  # 占位: 面数量

        self.secw.end_section()

    # =========================
    # 凸包碰撞体
    # =========================
    def write_convex_hull(self, mesh: bpy.types.Mesh):
        """
        导出凸包 (Convex Hull)。
        注意: 这里只是占位，真正的凸包需调用 Blender 的 bmesh.ops.convex_hull。
        """
        self.secw.begin_section(section_id=0x5003)  # 示例 ID

        # TODO: 实现凸包生成逻辑 (需对照 BigWorld_Make_CustomHull.mcr)
        self.binw.write_u32(0)  # 占位: 顶点数量
        self.binw.write_u32(0)  # 占位: 面数量

        self.secw.end_section()
