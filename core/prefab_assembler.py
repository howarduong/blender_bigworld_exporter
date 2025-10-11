# 相对路径: core/prefab_assembler.py
# 功能: 导出预制体 (Prefab) 与实例表 (Instances)
#   - 预制体组名
#   - 实例角色 (角色主体/武器/饰品等)
#   - 对象变换矩阵 (位置/旋转/缩放)
#   - 可见性标记
#
# 注意:
#   - 字段顺序、默认值、对齐方式必须与原 3ds Max 插件一致。
#   - 预制体机制需与 BigWorld 引擎的 SuperModel/Prefab 系统保持一致。
#   - 矩阵写出顺序 (行主/列主) 必须在 schema_reference.md 固化。

from typing import List, Dict
import bpy

from .binsection_writer import BinWriter, SectionWriter


class PrefabAssembler:
    """预制体导出器"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    # =========================
    # 主入口
    # =========================
    def write_prefabs(self, prefabs: List[Dict]):
        """
        导出预制体列表。
        参数:
            prefabs: 预制体列表，每个预制体为 dict:
                {
                    "group": str,        # 预制体组名
                    "instances": List[{
                        "role": str,     # 实例角色
                        "object": bpy.types.Object,  # Blender 对象
                        "visible": bool  # 可见性
                    }]
                }
        """
        self.secw.begin_section(section_id=0x7001)  # 示例 ID，需在 schema 固化

        # 写预制体数量
        self.binw.write_u32(len(prefabs))

        # 遍历预制体
        for prefab in prefabs:
            self._write_single_prefab(prefab)

        self.secw.end_section()

    # =========================
    # 单个预制体
    # =========================
    def _write_single_prefab(self, prefab: Dict):
        """
        导出单个预制体。
        """
        # 写组名
        group_name = prefab.get("group", "")
        self.binw.write_cstring(group_name)

        # 写实例数量
        instances = prefab.get("instances", [])
        self.binw.write_u32(len(instances))

        # 遍历实例
        for inst in instances:
            self._write_single_instance(inst)

    # =========================
    # 单个实例
    # =========================
    def _write_single_instance(self, inst: Dict):
        """
        导出单个实例。
        """
        obj = inst.get("object", None)

        # 实例角色
        role = inst.get("role", "")
        self.binw.write_cstring(role)

        # 可见性
        visible_flag = 1 if inst.get("visible", True) else 0
        self.binw.write_u32(visible_flag)

        # 对象变换矩阵
        if obj:
            mat = obj.matrix_world
            # 转换为 16 元组
            # 注意: 这里使用 col 展开，需确认与 Max 插件一致的行主/列主顺序
            mat_tuple = tuple(sum(mat.col, ()))
            for v in mat_tuple:
                self.binw.write_f32(float(v))
        else:
            # 占位单位矩阵
            for i in range(16):
                if i % 5 == 0:
                    self.binw.write_f32(1.0)
                else:
                    self.binw.write_f32(0.0)
