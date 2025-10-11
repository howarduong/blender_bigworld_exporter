# 相对路径: ui_panel.py
# 功能: 提供 Blender N 面板 (侧边栏) UI，用于对象/集合参数设置。
# 改造点:
#   - 使用 PropertyGroup 定义所有参数
#   - 使用 PointerProperty 挂载到 Object
#   - 支持折叠/展开小节
#
# 注意:
#   - 所有字段命名需与 export_operator.py 中读取逻辑一致
#   - 默认值需与旧 3ds Max 插件保持一致

import bpy


# -------------------------
# 属性定义
# -------------------------
class BigWorldObjectSettings(bpy.types.PropertyGroup):
    # 折叠开关
    show_transform: bpy.props.BoolProperty(name="展开转换参数", default=True)
    show_group: bpy.props.BoolProperty(name="展开分组与LOD", default=False)
    show_collision: bpy.props.BoolProperty(name="展开碰撞与几何派生", default=False)
    show_hitbox: bpy.props.BoolProperty(name="展开Hitbox", default=False)
    show_portal: bpy.props.BoolProperty(name="展开门户", default=False)
    show_prefab: bpy.props.BoolProperty(name="展开预制与实例", default=False)
    show_hardpoint: bpy.props.BoolProperty(name="展开硬点", default=False)
    show_cue: bpy.props.BoolProperty(name="展开动画事件", default=False)

    # 转换参数
    axis_map: bpy.props.BoolProperty(name="坐标轴映射 (Y→Z)", default=True)
    unit_scale: bpy.props.FloatProperty(name="单位缩放", default=1.0)
    flip_winding: bpy.props.BoolProperty(name="翻转面绕序", default=True)
    rebuild_normals: bpy.props.BoolProperty(name="重建法线/切线", default=True)
    norm_angle: bpy.props.FloatProperty(name="法线阈值(度)", default=45.0)

    # 分组与 LOD
    lod: bpy.props.IntProperty(name="LOD 等级", default=0, min=0, max=5)
    group: bpy.props.IntProperty(name="分组索引", default=0)
    partition: bpy.props.StringProperty(name="分割策略", default="")

    # 碰撞
    is_collider: bpy.props.BoolProperty(name="标记为碰撞体", default=False)
    is_bsp: bpy.props.BoolProperty(name="标记为 BSP", default=False)
    is_hull: bpy.props.BoolProperty(name="标记为 凸包", default=False)
    precision: bpy.props.EnumProperty(
        name="精度",
        items=[('f32', "float32", ""), ('f16', "float16", "")],
        default='f32'
    )

    # Hitbox
    hitbox_name: bpy.props.StringProperty(name="Hitbox 名称", default="")
    hitbox_type: bpy.props.EnumProperty(
        name="Hitbox 类型",
        items=[('box', "Box", ""), ('sphere', "Sphere", ""), ('capsule', "Capsule", ""), ('mesh', "Mesh", "")]
    )
    hitbox_level: bpy.props.EnumProperty(
        name="层级",
        items=[('object', "Object", ""), ('bone', "Bone", "")]
    )

    # 门户
    portal_type: bpy.props.EnumProperty(
        name="门户类型",
        items=[('standard', "Standard", ""), ('heaven', "Heaven", ""), ('exit', "Exit", ""), ('none', "None", "")]
    )
    portal_label: bpy.props.StringProperty(name="门户标签", default="")
    portal_geom: bpy.props.EnumProperty(
        name="几何来源",
        items=[('BOUNDING_BOX', "Bounding Box", ""), ('CUSTOM_MESH', "Custom Mesh", "")]
    )

    # 预制与实例
    prefab_group: bpy.props.StringProperty(name="预制体组", default="")
    instance_role: bpy.props.StringProperty(name="实例角色", default="")
    visibility: bpy.props.BoolProperty(name="可见性", default=True)

    # 硬点
    hp_name: bpy.props.StringProperty(name="硬点名称", default="")
    hp_type: bpy.props.StringProperty(name="硬点类型", default="weapon")
    hp_bone: bpy.props.StringProperty(name="绑定骨骼", default="")

    # 动画事件
    cue_events: bpy.props.StringProperty(name="事件列表(JSON)", default="[]")


# -------------------------
# 面板定义
# -------------------------
class BIGWORLD_PT_sidebar(bpy.types.Panel):
    bl_label = "BigWorld 导出参数"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BigWorld'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        if not obj:
            layout.label(text="请选择一个对象")
            return

        settings = obj.bw_settings

        # 转换参数
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_transform", icon="TRIA_DOWN" if settings.show_transform else "TRIA_RIGHT", emboss=False)
        if settings.show_transform:
            box.prop(settings, "axis_map")
            box.prop(settings, "unit_scale")
            box.prop(settings, "flip_winding")
            box.prop(settings, "rebuild_normals")
            box.prop(settings, "norm_angle")

        # 分组与 LOD
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_group", icon="TRIA_DOWN" if settings.show_group else "TRIA_RIGHT", emboss=False)
        if settings.show_group:
            box.prop(settings, "lod")
            box.prop(settings, "group")
            box.prop(settings, "partition")

        # 碰撞
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_collision", icon="TRIA_DOWN" if settings.show_collision else "TRIA_RIGHT", emboss=False)
        if settings.show_collision:
            box.prop(settings, "is_collider")
            box.prop(settings, "is_bsp")
            box.prop(settings, "is_hull")
            box.prop(settings, "precision")

        # Hitbox
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_hitbox", icon="TRIA_DOWN" if settings.show_hitbox else "TRIA_RIGHT", emboss=False)
        if settings.show_hitbox:
            box.prop(settings, "hitbox_name")
            box.prop(settings, "hitbox_type")
            box.prop(settings, "hitbox_level")

        # 门户
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_portal", icon="TRIA_DOWN" if settings.show_portal else "TRIA_RIGHT", emboss=False)
        if settings.show_portal:
            box.prop(settings, "portal_type")
            box.prop(settings, "portal_label")
            box.prop(settings, "portal_geom")

        # 预制与实例
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_prefab", icon="TRIA_DOWN" if settings.show_prefab else "TRIA_RIGHT", emboss=False)
        if settings.show_prefab:
            box.prop(settings, "prefab_group")
            box.prop(settings, "instance_role")
            box.prop(settings, "visibility")

        # 硬点
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_hardpoint", icon="TRIA_DOWN" if settings.show_hardpoint else "TRIA_RIGHT", emboss=False)
        if settings.show_hardpoint:
            box.prop(settings, "hp_name")
            box.prop(settings, "hp_type")
            box.prop(settings, "hp_bone")

        # 动画事件
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_cue", icon="TRIA_DOWN" if settings.show_cue else "TRIA_RIGHT", emboss=False)
        if settings.show_cue:
            box.prop(settings, "cue_events")


# -------------------------
# 注册
# -------------------------
classes = (
    BigWorldObjectSettings,
    BIGWORLD_PT_sidebar,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.bw_settings = bpy.props.PointerProperty(type=BigWorldObjectSettings)

def unregister():
    del bpy.types.Object.bw_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
