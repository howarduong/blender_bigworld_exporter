# File: writers/primitives_writer.py
# Purpose: 写入 .primitives 文件（BinSection 格式）
# Notes:
# - 使用 BinSectionWriter 写入顶点、索引、PrimitiveGroup
# - 支持 BSP 数据（可选）
# - 严格对齐 BigWorld 源码的字段顺序与字节对齐

from typing import List
from ..core.io.bin_section_writer import BinSectionWriter
from ..core.schema import Primitives, PrimitiveGroup
from ..core.formats.vertex_format import build_vertex_format


class PrimitivesWriter:
    """
    PrimitivesWriter
    ----------------
    用于写入 BigWorld .primitives 文件（BinSection 容器）。
    
    写入顺序:
        1. Header (magic + version + timestamp + num_sections占位)
        2. Vertex Section (vertex_format + num_vertices + raw_vertex_data)
        3. Index Section (index_format + num_indices + num_groups + indices[] + groups[])
        4. BSP Section (可选)
        5. Index Table (回填)
    
    使用方式:
        writer = PrimitivesWriter("output/hero.primitives")
        writer.write(primitives_data)
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def write(self, primitives: Primitives) -> None:
        """
        写入 .primitives 文件
        
        参数:
            primitives: Primitives 数据结构
        """
        # 调试信息
        print(f"DEBUG: 导出 .primitives 文件")
        print(f"  顶点数量: {len(primitives.vertices)}")
        print(f"  索引数量: {len(primitives.indices)}")
        print(f"  PrimitiveGroup 数量: {len(primitives.groups)}")
        print(f"  BSP 数据: {bool(primitives.bsp_data)}")
        print(f"  有法线: {bool(primitives.normals)}")
        print(f"  有UV: {bool(primitives.uvs)}")
        print(f"  有切线: {bool(primitives.tangents)}")
        print(f"  有骨骼索引: {bool(primitives.bone_indices)}")
        print(f"  骨骼索引数量: {len(primitives.bone_indices)}")
        print(f"  骨骼权重数量: {len(primitives.bone_weights)}")
        
        # 检查蒙皮数据内容
        if primitives.bone_indices:
            print(f"  骨骼索引示例: {primitives.bone_indices[0] if primitives.bone_indices else 'None'}")
        if primitives.bone_weights:
            print(f"  骨骼权重示例: {primitives.bone_weights[0] if primitives.bone_weights else 'None'}")
        
        # 检查顶点格式
        if primitives.vertex_format:
            print(f"  预设顶点格式: {primitives.vertex_format.rstrip(chr(0))}")
        else:
            print(f"  预设顶点格式: None (将动态生成)")
        
        # 创建 BinSectionWriter
        bw = BinSectionWriter(self.filepath)
        bw.open()
        
        try:
            # 1. 写入顶点数据块
            self._write_vertex_section(bw, primitives)
            
            # 2. 写入索引数据块
            self._write_index_section(bw, primitives)
            
            # 3. 写入 BSP 数据块（如果有）
            if primitives.bsp_data:
                self._write_bsp_section(bw, primitives)
            
            # 4. 写入 index table 并回填 header
            bw.finalize()
            
            # 调试：文件大小
            import os
            file_size = os.path.getsize(self.filepath)
            print(f"DEBUG: 生成文件大小: {file_size} 字节 ({file_size/1024:.1f} KB)")
        
        except Exception as e:
            # 确保文件被关闭
            if bw.fp:
                try:
                    bw.fp.close()
                except:
                    pass
            
            # 清理失败的文件
            import os
            if os.path.exists(self.filepath):
                try:
                    os.remove(self.filepath)
                except:
                    pass
            
            raise RuntimeError(f"写入 .primitives 文件失败: {e}")
    
    def _write_vertex_section(self, bw: BinSectionWriter, primitives: Primitives) -> None:
        """写入顶点数据块（tag: "vertices"）"""
        bw.begin_section("vertices")
        
        # 1. 写入 vertex_format（64 字节）
        vertex_format = primitives.vertex_format
        if not vertex_format:
            # 动态生成
            vertex_format = build_vertex_format(
                has_normals=bool(primitives.normals),
                has_uv=bool(primitives.uvs),
                has_tangent=bool(primitives.tangents),
                has_color=bool(primitives.colors),
                has_skin=(len(primitives.bone_indices) > 0 and len(primitives.bone_weights) > 0)  # 修复：检查长度而不是bool
            )
        print(f"  生成的顶点格式: {vertex_format.rstrip(chr(0))}")
        bw.write_string(vertex_format, fixed_len=64)
        
        # 2. 写入顶点数量
        num_vertices = len(primitives.vertices)
        bw.write_uint32(num_vertices)
        
        # 3. 写入顶点数据（按 vertex_format 顺序）
        for i in range(num_vertices):
            # 位置 (xyz) - 必须
            bw.write_vector3(primitives.vertices[i])
            
            # 法线 (n) - 如果有
            if primitives.normals:
                # 静态模型使用Vector3 normal_ (12字节)
                # 只有带切线/副切线的模型才使用packed normal (4字节)
                if primitives.tangents:
                    # 带切线/副切线的模型使用packed normal
                    bw.write_packed_normal(primitives.normals[i])
                else:
                    # 静态模型使用Vector3 normal
                    bw.write_vector3(primitives.normals[i])
            
            # UV (uv) - 如果有
            if primitives.uvs:
                bw.write_vector2(primitives.uvs[i])
            
            # 切线/副切线 (tb) - 如果有 (packed uint32, 不是Vector3!)
            if primitives.tangents:
                bw.write_packed_normal(primitives.tangents[i])
                if primitives.binormals:
                    bw.write_packed_normal(primitives.binormals[i])
            
            # 顶点颜色 (c) - 如果有
            if primitives.colors:
                # RGBA 4 floats
                color = primitives.colors[i]
                for c in color:
                    bw.write_float(c)
            
            # 蒙皮数据 (iiiww) - 如果有
            if primitives.bone_indices:
                # 骨骼索引 (3 bytes) - uint8
                # 注意：BigWorld支持的最大骨骼索引是255，如果超过需要重新映射
                indices = primitives.bone_indices[i]
                for j in range(3):
                    bone_idx = int(indices[j])
                    # 确保索引在有效范围内
                    if bone_idx < 0:
                        safe_index = 0  # 无效索引映射到根骨骼
                    elif bone_idx > 255:
                        # 如果骨骼数量超过255，需要重新映射到0-255范围
                        # 这里暂时映射到根骨骼，避免崩溃
                        safe_index = 0
                        print(f"WARNING: 骨骼索引 {bone_idx} 超出范围(0-255)，映射到根骨骼")
                    else:
                        safe_index = bone_idx
                    bw.write_byte(safe_index)
                
                # 骨骼权重 (2 bytes) - uint8 (0-255)
                # 注意：BigWorld使用uint8权重，255=100%
                weights = primitives.bone_weights[i]
                for j in range(2):
                    # 权重应该已经是0-255范围的整数
                    safe_weight = min(max(int(weights[j]), 0), 255)
                    bw.write_byte(safe_weight)
        
        bw.end_section()
    
    def _write_index_section(self, bw: BinSectionWriter, primitives: Primitives) -> None:
        """写入索引数据块（tag: "indices"）"""
        bw.begin_section("indices")
        
        # 1. 写入 index_format
        num_vertices = len(primitives.vertices)
        if num_vertices < 65536:
            index_format = "list"
            use_u32 = False
        else:
            index_format = "list32"
            use_u32 = True
        
        bw.write_string(index_format, fixed_len=64)
        
        # 2. 写入索引数量
        num_indices = len(primitives.indices)
        bw.write_uint32(num_indices)
        
        # 3. 写入 PrimitiveGroup 数量
        num_groups = len(primitives.groups)
        bw.write_uint32(num_groups)
        
        # 4. 写入索引数组
        if use_u32:
            bw.write_indices_u32(primitives.indices)
        else:
            bw.write_indices_u16(primitives.indices)
        
        # 5. 写入 PrimitiveGroup 数组
        for group in primitives.groups:
            bw.write_uint32(group.start_index)
            bw.write_uint32(group.num_primitives)
            bw.write_uint32(group.start_vertex)
            bw.write_uint32(group.num_vertices)
        
        bw.end_section()
    
    def _write_bsp_section(self, bw: BinSectionWriter, primitives: Primitives) -> None:
        """写入 BSP 数据块（占位保留）"""
        bw.begin_section("bsp ")
        # TODO: 实现 BSP 写入逻辑
        # 当前仅写入占位数据
        if primitives.bsp_data:
            bw.fp.write(primitives.bsp_data)
        bw.end_section()


def write_primitives(filepath: str, primitives: Primitives) -> None:
    """
    便捷函数：写入 .primitives 文件
    
    参数:
        filepath: 输出文件路径
        primitives: Primitives 数据结构
    """
    writer = PrimitivesWriter(filepath)
    writer.write(primitives)

