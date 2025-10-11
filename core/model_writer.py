# 相对路径: blender_bigworld_exporter/core/model_writer.py
# 功能: 写出 .model 文件，包含文件头、节点树、引用路径
# 风格: 对齐 Max 插件的 writeModel()，保留 flags/reserved 字段，保证空节占位

from .binsection_writer import BinWriter

class ModelWriter:
    def __init__(self,
                 binw: BinWriter,
                 engine_version: str = 'BW3',
                 coord_mode: str = 'MAX_COMPAT',
                 default_scale: float = 1.0,
                 apply_scene_scale: bool = False,
                 verbose: bool = False):
        self.binw = binw
        self.engine_version = engine_version
        self.coord_mode = coord_mode
        self.default_scale = default_scale
        self.apply_scene_scale = apply_scene_scale
        self.verbose = verbose

    # 写文件头（Header 节）
    def write_model_header(self, obj):
        self.binw.begin_section("Header")
        # 固定标识
        self.binw.write_string("BigWorldModel")
        # 版本号
        self.binw.write_uint32(3 if self.engine_version == 'BW3' else 2)
        # 坐标系模式
        self.binw.write_string(self.coord_mode)
        # 默认缩放
        self.binw.write_float32(self.default_scale)
        # 是否应用场景缩放
        self.binw.write_uint8(1 if self.apply_scene_scale else 0)
        # 对象名
        self.binw.write_string(obj.name if obj else "")
        # flags（保留字段）
        self.binw.write_uint32(0)
        # reserved（保留字段）
        self.binw.write_uint32(0)
        self.binw.end_section()

    # 写节点树（NodeTree 节）
    def write_node_tree(self, obj):
        self.binw.begin_section("NodeTree")

        def write_node(o):
            self.binw.begin_section("Node")
            # 节点名
            self.binw.write_string(o.name)
            # 写 transform 矩阵（4x4 float32）
            if hasattr(o, "matrix_world"):
                mat = list(o.matrix_world)
                for row in mat:
                    for val in row:
                        self.binw.write_float32(val)
            else:
                # 空矩阵占位
                for _ in range(16):
                    self.binw.write_float32(0.0)
            # 子节点数量
            children = getattr(o, "children", [])
            self.binw.write_uint32(len(children))
            # 递归写子节点
            for child in children:
                write_node(child)
            self.binw.end_section()

        if obj:
            write_node(obj)
        else:
            # 空节点树占位
            self.binw.write_uint32(0)

        self.binw.end_section()

    # 写引用路径（References 节）
    def write_references(self, visual_filename: str, primitives_filename: str):
        self.binw.begin_section("References")
        # .visual 文件路径
        self.binw.write_string(visual_filename if visual_filename else "")
        # .primitives 文件路径
        self.binw.write_string(primitives_filename if primitives_filename else "")
        # 保留字段（Max 插件里通常会有）
        self.binw.write_uint32(0)
        self.binw.end_section()

    # 统一入口
    def write_model(self, obj, primitives_filename: str, visual_filename: str):
        self.write_model_header(obj)
        self.write_node_tree(obj)
        self.write_references(visual_filename, primitives_filename)
