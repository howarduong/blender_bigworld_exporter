# 相对路径: core/primitives_writer.py
# 主要功能: 导出网格数据 (Mesh)，包括:
#   - 顶点位置
#   - 法线/切线
#   - UV 坐标（至少两层：UV0、UV1；无则用默认值）
#   - 顶点颜色（无则默认 1,1,1,1）
#   - 骨骼权重（Top-4 归一化）和骨骼索引（无骨架则全 0）
#   - 三角形索引（按顶点数动态选择 u16/u32）
#   - 材质分组信息（material_id, start_index, index_count）
#
# 注意:
#   - 字段顺序、默认值、对齐方式需与旧 3ds Max 插件一致（最终以 schema_reference.md 固化为准）。
#   - 法线/切线重建逻辑需对照 BigWorld_Munge_Normals.mcr（当前采用占位/简化实现）。
#   - 索引类型 (u16/u32) 依据顶点数量选择（<=65535 用 u16，否则 u32）。
#
# 开发前必读参考:
# BigWorld_MAXScripts GitHub 仓库：
# https://github.com/howarduong/BigWorld_MAXScripts/tree/1b7eb719e475c409afa319877f4550cf5accbafc/BigWorld_MacroScripts

from typing import List, Tuple, Dict
import bpy
import bmesh

from .binsection_writer import BinWriter, SectionWriter
from .utils import flip_winding, rebuild_normals, rebuild_tangents


class MeshExportOptions:
    """网格导出选项"""
    def __init__(self,
                 flip_winding_enabled: bool = True,
                 rebuild_normals_enabled: bool = True,
                 normals_angle_threshold: float = 45.0,
                 apply_scene_scale: bool = True,
                 default_scale: float = 1.0):
        self.flip_winding_enabled = flip_winding_enabled
        self.rebuild_normals_enabled = rebuild_normals_enabled
        self.normals_angle_threshold = normals_angle_threshold
        self.apply_scene_scale = apply_scene_scale
        self.default_scale = default_scale



class PrimitivesWriter:
    """网格导出器 (.primitives 内容写出)"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    def write_mesh(self, mesh: bpy.types.Mesh, opts: MeshExportOptions):
        """
        导出一个 Mesh 对象的数据，字段顺序如下：
          1) 顶点数量 (u32)
          2) 索引数量 (u32)
          3) 顶点属性块（逐顶点顺序写出）：
             - 位置 (f32x3)
             - 法线 (f32x3)
             - 切线 (f32x3)
             - UV0 (f32x2)
             - UV1 (f32x2)
             - 颜色 (u8x4)  // 如需 f32x4，请在 schema 固化后切换
             - 权重 (f32x4)
             - 骨骼索引 (u16x4)
          4) 索引位宽标记 (u8: 16 或 32)
          5) 索引数据（u16 或 u32）
          6) 材质分组表：
             - 分组数量 (u32)
             - 每组: material_id (u16), start_index (u32), index_count (u32)
        """
        # 1) 确保 mesh 已评估并三角化（统一来源数据）
        temp_mesh = self._make_triangulated_mesh(mesh)

        # 2) 收集顶点位置（按顶点域）
        vertices = [(v.co.x, v.co.y, v.co.z) for v in temp_mesh.vertices]
        vert_count = len(vertices)

        # 3) 收集索引（来自 polygon 顶点序）
        indices: List[int] = []
        for poly in temp_mesh.polygons:
            if len(poly.vertices) == 3:
                i0, i1, i2 = poly.vertices
                indices.extend([i0, i1, i2])
        if opts.flip_winding_enabled:
            indices = flip_winding(indices)

        # 4) UV 层（按 loop 聚合到顶点：平均）
        uv0 = self._collect_uv_layer(temp_mesh, layer_index=0, vert_count=vert_count)
        uv1 = self._collect_uv_layer(temp_mesh, layer_index=1, vert_count=vert_count)

        # 5) 顶点颜色（按 loop 聚合到顶点：平均；无则默认 1,1,1,1）
        colors = self._collect_vertex_colors(temp_mesh, vert_count=vert_count)

        # 6) 法线/切线
        if opts.rebuild_normals_enabled:
            normals = rebuild_normals(vertices, indices, opts.normals_angle_threshold)
        else:
            normals = [(v.normal.x, v.normal.y, v.normal.z) for v in temp_mesh.vertices]
        tangents = rebuild_tangents(vertices, indices, uv0)

        # 7) 骨骼权重/索引（Top-4；若无骨架默认权重 [1,0,0,0]、索引 [0,0,0,0]）
        weights, bone_indices = self._collect_skin_weights(temp_mesh)

        # 8) 索引类型（u16/u32）
        use_u16 = (vert_count <= 65535)

        # --- 写出数据块（保持你的单 section 结构） ---
        self.secw.begin_section(section_id=0x1001)  # 示例 ID，需在 schema_reference.md 固化

        # 顶点/索引数量
        self.binw.write_u32(vert_count)
        self.binw.write_u32(len(indices))

        # 顶点属性：逐顶点顺序写出（严格顺序）
        for i in range(vert_count):
            # 位置 (f32x3)
            vx, vy, vz = vertices[i]
            self.binw.write_f32(vx); self.binw.write_f32(vy); self.binw.write_f32(vz)
            # 法线 (f32x3)
            nx, ny, nz = normals[i] if i < len(normals) else (0.0, 0.0, 1.0)
            self.binw.write_f32(nx); self.binw.write_f32(ny); self.binw.write_f32(nz)
            # 切线 (f32x3)
            tx, ty, tz = tangents[i] if i < len(tangents) else (1.0, 0.0, 0.0)
            self.binw.write_f32(tx); self.binw.write_f32(ty); self.binw.write_f32(tz)
            # UV0 (f32x2)
            u0, v0 = uv0[i] if i < len(uv0) else (0.0, 0.0)
            self.binw.write_f32(u0); self.binw.write_f32(v0)
            # UV1 (f32x2)
            u1, v1 = uv1[i] if i < len(uv1) else (0.0, 0.0)
            self.binw.write_f32(u1); self.binw.write_f32(v1)
            # 颜色 (u8x4) —— 更贴近旧插件；如需改为 f32x4 请在 schema 固化后统一切换
            r, g, b, a = colors[i] if i < len(colors) else (1.0, 1.0, 1.0, 1.0)
            self.binw.write_u8(int(max(0, min(255, round(r * 255)))))
            self.binw.write_u8(int(max(0, min(255, round(g * 255)))))
            self.binw.write_u8(int(max(0, min(255, round(b * 255)))))
            self.binw.write_u8(int(max(0, min(255, round(a * 255)))))
            # 权重 (f32x4)
            w0, w1, w2, w3 = weights[i] if i < len(weights) else (1.0, 0.0, 0.0, 0.0)
            self.binw.write_f32(w0); self.binw.write_f32(w1); self.binw.write_f32(w2); self.binw.write_f32(w3)
            # 骨骼索引 (u16x4)
            b0, b1, b2, b3 = bone_indices[i] if i < len(bone_indices) else (0, 0, 0, 0)
            self.binw.write_u16(b0); self.binw.write_u16(b1); self.binw.write_u16(b2); self.binw.write_u16(b3)

        # 索引位宽标记 (u8: 16 或 32)
        self.binw.write_u8(16 if use_u16 else 32)

        # 索引数据
        if use_u16:
            for idx in indices:
                self.binw.write_u16(int(idx))
        else:
            for idx in indices:
                self.binw.write_u32(int(idx))

        # 材质分组信息（material_id, start_index, index_count）
        groups = self._build_material_groups(temp_mesh)
        self.binw.write_u32(len(groups))
        for g in groups:
            self.binw.write_u16(g["material_id"])
            self.binw.write_u32(g["start_index"])
            self.binw.write_u32(g["index_count"])

        self.secw.end_section()

        # 清理临时 mesh
        bpy.data.meshes.remove(temp_mesh)

    # -------------------------
    # Helpers
    # -------------------------

    def _make_triangulated_mesh(self, src_mesh: bpy.types.Mesh) -> bpy.types.Mesh:
        """评估并三角化得到临时 mesh，确保数据统一、可遍历。"""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = bpy.context.active_object.evaluated_get(depsgraph)
        temp_mesh = bpy.data.meshes.new_from_object(obj_eval, preserve_all_data_layers=True, depsgraph=depsgraph)

        bm = bmesh.new()
        bm.from_mesh(temp_mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.to_mesh(temp_mesh)
        bm.free()

        # Blender 4.x API 替代
         # Blender 4.x: 法线会自动更新，不需要 calc_normals()
        # 如果需要切线，调用 calc_tangents 并指定 UV 层
        if temp_mesh.uv_layers:
           uv_layer_name = temp_mesh.uv_layers.active.name if temp_mesh.uv_layers.active else temp_mesh.uv_layers[0].name
           temp_mesh.calc_tangents(uvmap=uv_layer_name)

        return temp_mesh

    def _collect_uv_layer(self, mesh: bpy.types.Mesh, layer_index: int, vert_count: int) -> List[Tuple[float, float]]:
        """将指定 UV 层从 loop 聚合到顶点（平均）。无该层时返回全 0。"""
        uvs = [(0.0, 0.0)] * vert_count
        if not mesh.uv_layers or layer_index >= len(mesh.uv_layers):
            return uvs
        uv_layer = mesh.uv_layers[layer_index]

        sums = [[0.0, 0.0, 0] for _ in range(vert_count)]
        for poly in mesh.polygons:
            for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
                v_idx = mesh.loops[li].vertex_index
                uv = uv_layer.data[li].uv
                sums[v_idx][0] += uv.x
                sums[v_idx][1] += uv.y
                sums[v_idx][2] += 1

        for i in range(vert_count):
            cnt = sums[i][2]
            if cnt > 0:
                uvs[i] = (sums[i][0] / cnt, sums[i][1] / cnt)
        return uvs

    def _collect_vertex_colors(self, mesh: bpy.types.Mesh, vert_count: int) -> List[Tuple[float, float, float, float]]:
        """从第一个颜色层聚合到顶点（平均），无则默认 1,1,1,1。"""
        cols = [(1.0, 1.0, 1.0, 1.0)] * vert_count
        # Blender 4.x 推荐使用 color_attributes
        layer = None
        if hasattr(mesh, "color_attributes") and mesh.color_attributes:
            for ca in mesh.color_attributes:
                if ca.domain == 'CORNER':
                    layer = ca
                    break
        elif hasattr(mesh, "vertex_colors") and mesh.vertex_colors.active:
            layer = mesh.vertex_colors.active

        if not layer:
            return cols

        data = getattr(layer, "data", None)
        if data is None:
            return cols

        sums = [[0.0, 0.0, 0.0, 0.0, 0] for _ in range(vert_count)]
        for poly in mesh.polygons:
            for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
                v_idx = mesh.loops[li].vertex_index
                c = data[li].color
                r, g, b = float(c[0]), float(c[1]), float(c[2])
                a = float(c[3]) if len(c) > 3 else 1.0
                sums[v_idx][0] += r
                sums[v_idx][1] += g
                sums[v_idx][2] += b
                sums[v_idx][3] += a
                sums[v_idx][4] += 1

        for i in range(vert_count):
            cnt = sums[i][4]
            if cnt > 0:
                cols[i] = (
                    sums[i][0] / cnt,
                    sums[i][1] / cnt,
                    sums[i][2] / cnt,
                    sums[i][3] / cnt,
                )
        return cols

    def _collect_skin_weights(self, mesh: bpy.types.Mesh):
        """收集顶点骨骼权重与索引（Top-4 + 归一化），无骨架则返回默认值。"""
        obj = bpy.context.active_object
        weights = [(1.0, 0.0, 0.0, 0.0)] * len(mesh.vertices)
        bone_indices = [(0, 0, 0, 0)] * len(mesh.vertices)

        arm_obj = obj.find_armature() if obj else None
        if not arm_obj or arm_obj.type != 'ARMATURE':
            return weights, bone_indices

        # 骨骼名 -> 索引
        bone_name_to_index: Dict[str, int] = {b.name: i for i, b in enumerate(arm_obj.data.bones)}

        # 顶点组索引 -> 组名
        vg_index_to_name: Dict[int, str] = {vg.index: vg.name for vg in obj.vertex_groups}

        for v in mesh.vertices:
            pairs = []
            for g in v.groups:
                vg_name = vg_index_to_name.get(g.group)
                if not vg_name:
                    continue
                bi = bone_name_to_index.get(vg_name, 0)
                pairs.append((bi, float(g.weight)))
            if not pairs:
                weights[v.index] = (1.0, 0.0, 0.0, 0.0)
                bone_indices[v.index] = (0, 0, 0, 0)
                continue
            pairs.sort(key=lambda x: x[1], reverse=True)
            pairs = pairs[:4]
            total = sum(p[1] for p in pairs) or 1.0
            ws = [p[1] / total for p in pairs]
            bis = [p[0] for p in pairs]
            while len(ws) < 4:
                ws.append(0.0)
            while len(bis) < 4:
                bis.append(0)
            weights[v.index] = (ws[0], ws[1], ws[2], ws[3])
            bone_indices[v.index] = (bis[0], bis[1], bis[2], bis[3])

        return weights, bone_indices

    def _build_material_groups(self, mesh: bpy.types.Mesh) -> List[Dict]:
        """
        构建材质分组表：
          material_id: 对应 obj.material_slots 的索引（通过 polygon.material_index 取得）
          start_index: 在全局索引缓冲中的起始位置（单位：索引数）
          index_count: 属于该材质的索引数量（单位：索引数，3 * 三角形数）
        """
        # 遍历面，统计每个材质的三角数量，并按写入顺序合并为一个连续段。
        obj = bpy.context.active_object
        # 统计：材质 -> 三角数量
        tri_count_per_mat: Dict[int, int] = {}
        current_global_index = 0
        first_start_per_mat: Dict[int, int] = {}

        for poly in mesh.polygons:
            if len(poly.vertices) != 3:
                continue
            mat_id = int(poly.material_index) if poly.material_index is not None else 0
            tri_count_per_mat[mat_id] = tri_count_per_mat.get(mat_id, 0) + 1
            if mat_id not in first_start_per_mat:
                first_start_per_mat[mat_id] = current_global_index
            current_global_index += 3

        groups = []
        for mat_id in sorted(tri_count_per_mat.keys()):
            tri_cnt = tri_count_per_mat[mat_id]
            start_idx = first_start_per_mat.get(mat_id, 0)
            groups.append({
                "material_id": mat_id,
                "start_index": start_idx,
                "index_count": tri_cnt * 3,
            })
        return groups
