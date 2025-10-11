# 相对路径: core/hitbox_xml_writer.py
# 功能: 导出 Hitbox 数据，包括:
#   - Hitbox 名称
#   - Hitbox 类型 (box/sphere/capsule/mesh)
#   - 层级 (对象/骨骼)
#   - 绑定骨骼 (可选)
#   - 矩阵/几何数据
#
# 注意:
#   - 输出格式需与原 3ds Max 插件一致 (XML 或二进制块)。
#   - 字段顺序、默认值、对齐方式必须严格对齐。
#   - XML 格式需符合 BigWorld 引擎的 Hitbox 解析规范。

from typing import List, Dict
import xml.etree.ElementTree as ET

from .binsection_writer import BinWriter, SectionWriter


class HitboxXMLWriter:
    """Hitbox 导出器 (XML 格式)"""

    def __init__(self):
        pass

    def write_hitboxes_to_xml(self, hitboxes: List[Dict], filepath: str):
        """
        将 Hitbox 列表导出为 XML 文件。
        参数:
            hitboxes: Hitbox 列表，每个为 dict:
                {
                    "name": str,
                    "type": str,   # box/sphere/capsule/mesh
                    "level": str,  # object/bone
                    "bone": str,   # 可选
                    "matrix": List[float] (4x4)
                }
            filepath: 输出 XML 文件路径
        """
        root = ET.Element("Hitboxes")

        # 遍历每个 Hitbox
        for hb in hitboxes:
            elem = ET.SubElement(root, "Hitbox")

            # 名称
            elem.set("name", hb.get("name", ""))

            # 类型
            elem.set("type", hb.get("type", "box"))

            # 层级
            elem.set("level", hb.get("level", "object"))

            # 绑定骨骼 (可选)
            if hb.get("bone"):
                elem.set("bone", hb.get("bone", ""))

            # 矩阵写出
            mat_elem = ET.SubElement(elem, "Matrix")
            mat = hb.get("matrix", [1.0] * 16)
            mat_elem.text = " ".join(str(float(v)) for v in mat)

        # 写出 XML 文件
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding="utf-8", xml_declaration=True)


class HitboxBinaryWriter:
    """Hitbox 导出器 (二进制块格式)"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    def write_hitboxes(self, hitboxes: List[Dict]):
        """
        将 Hitbox 列表导出为二进制块。
        """
        self.secw.begin_section(section_id=0x8001)  # 示例 ID，需在 schema 固化

        # 写 Hitbox 数量
        self.binw.write_u32(len(hitboxes))

        # 遍历每个 Hitbox
        for hb in hitboxes:
            self._write_single_hitbox(hb)

        self.secw.end_section()

    def _write_single_hitbox(self, hb: Dict):
        """
        导出单个 Hitbox。
        """
        # 名称
        self.binw.write_cstring(hb.get("name", ""))

        # 类型
        self.binw.write_cstring(hb.get("type", "box"))

        # 层级
        self.binw.write_cstring(hb.get("level", "object"))

        # 绑定骨骼
        self.binw.write_cstring(hb.get("bone", ""))

        # 矩阵 (16 个 float32)
        mat = hb.get("matrix", [1.0] * 16)
        for v in mat:
            self.binw.write_f32(float(v))
