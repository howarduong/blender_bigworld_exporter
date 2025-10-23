# -*- coding: utf-8 -*-
"""
BigWorld 对象属性面板（重构版 - 核心功能）
移除所有占位功能，专注于核心导出
"""

import bpy
from bpy.types import Panel, PropertyGroup
from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty,
    IntProperty,
    CollectionProperty,
    PointerProperty
)


# ==================== 属性组 ====================

class BigWorldObjectProperties(PropertyGroup):
    """对象级BigWorld属性（精简核心版）"""
    
    # ===== 基础设置 =====
    export_type: EnumProperty(
        name="导出类型",
        description="BigWorld导出类型",
        items=[
            ('STATIC', '静态模型', '无骨骼、无动画'),
            ('SKINNED', '蒙皮模型', '有骨骼、无动画'),
            ('CHARACTER', '角色动画', '有骨骼、有动画')
        ],
        default='STATIC'
    )
    
    resource_id: StringProperty(
        name="资源ID",
        description="资源唯一标识（默认使用对象名）",
        default=""
    )
    
    parent_model: StringProperty(
        name="父模型",
        description="继承的父模型路径（用于角色组件，如：characters/base）",
        default=""
    )


class BigWorldAction(PropertyGroup):
    """Action属性（角色动画用）"""
    
    name: StringProperty(
        name="Action名称",
        description="游戏中的动作标识（如：WalkForward）",
        default="Action"
    )
    
    animation_name: StringProperty(
        name="关联动画",
        description="Blender中的Action名称",
        default=""
    )
    
    blended: BoolProperty(
        name="混合播放",
        description="是否支持动画混合",
        default=True
    )
    
    track: IntProperty(
        name="动画轨道",
        description="动画播放轨道（0-10）",
        default=0,
        min=0,
        max=10
    )


class BigWorldHardpoint(PropertyGroup):
    """硬点属性"""
    
    name: StringProperty(
        name="硬点名称",
        description="硬点唯一标识（如：HP_RightHand）",
        default="HP_Mount"
    )
    
    hardpoint_type: EnumProperty(
        name="硬点类型",
        description="硬点用途类型",
        items=[
            ('WEAPON', '武器挂载', '武器挂载点（剑、枪等）'),
            ('EQUIPMENT', '装备挂载', '装备挂载点（盾牌、背包等）'),
            ('EFFECT', '特效点', '特效播放位置（光环、粒子等）'),
            ('INTERACT', '交互点', '交互触发点（按钮、开关等）')
        ],
        default='WEAPON'
    )
    
    bone_name: StringProperty(
        name="绑定骨骼",
        description="硬点绑定到的骨骼名称",
        default=""
    )
    
    use_empty: BoolProperty(
        name="使用Empty对象",
        description="从场景中的Empty对象获取位置和旋转",
        default=False
    )
    
    target_empty: PointerProperty(
        name="目标Empty",
        description="用作硬点位置的Empty对象",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'EMPTY'
    )


# ==================== 面板 ====================

class BIGWORLD_PT_object_panel(Panel):
    """BigWorld对象属性面板（重构版）"""
    bl_label = "BigWorld 对象属性"
    bl_idname = "BIGWORLD_PT_object_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BigWorld"
    
    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        
        # 检查属性是否存在
        if not hasattr(obj, 'bigworld_props'):
            layout.label(text="BigWorld属性未初始化", icon='ERROR')
            layout.operator("wm.save_userpref", text="保存设置并重启Blender")
            return
        
        props = obj.bigworld_props
        
        # ========== 基础设置 ==========
        box = layout.box()
        box.label(text="📦 基础设置", icon='OBJECT_DATA')
        box.prop(props, "export_type", text="类型")
        box.prop(props, "resource_id", text="ID")
        
        # 父模型（仅蒙皮和角色动画可用）
        if props.export_type in {'SKINNED', 'CHARACTER'}:
            box.prop(props, "parent_model", text="父模型", icon='LINKED')
        
        # ========== 硬点管理（仅蒙皮和角色动画显示）==========
        if props.export_type in {'SKINNED', 'CHARACTER'} and obj.type == 'MESH':
            # 检查属性是否存在
            if not hasattr(obj, 'bigworld_hardpoints'):
                layout.label(text="硬点属性未初始化", icon='ERROR')
                return
            
            box = layout.box()
            box.label(text="🎯 硬点管理 ({0})".format(len(obj.bigworld_hardpoints)), icon='EMPTY_AXIS')
            
            row = box.row()
            row.template_list(
                "BIGWORLD_UL_hardpoints", "",
                obj, "bigworld_hardpoints",
                obj, "bigworld_hardpoints_index",
                rows=3
            )
            
            col = row.column(align=True)
            col.operator("bigworld.hardpoint_add", icon='ADD', text="")
            col.operator("bigworld.hardpoint_remove", icon='REMOVE', text="")
            
            # 选中硬点的详细设置
            if obj.bigworld_hardpoints and 0 <= obj.bigworld_hardpoints_index < len(obj.bigworld_hardpoints):
                hp = obj.bigworld_hardpoints[obj.bigworld_hardpoints_index]
                
                sub_box = box.box()
                sub_box.label(text="⚙️ 设置: {0}".format(hp.name), icon='SETTINGS')
                sub_box.prop(hp, "name", text="名称")
                sub_box.prop(hp, "hardpoint_type", text="类型")
                sub_box.prop(hp, "bone_name", text="骨骼")
                
                row = sub_box.row()
                row.prop(hp, "use_empty", text="使用Empty")
                if hp.use_empty:
                    sub_box.prop(hp, "target_empty", text="")
        
        # ========== Action管理（仅角色动画显示）==========
        if props.export_type == 'CHARACTER':
            # 检查属性是否存在
            if not hasattr(obj, 'bigworld_actions'):
                layout.label(text="Action属性未初始化", icon='ERROR')
                return
            
            box = layout.box()
            box.label(text="🎬 Action管理 ({0})".format(len(obj.bigworld_actions)), icon='ACTION')
            
            row = box.row()
            row.template_list(
                "BIGWORLD_UL_actions", "",
                obj, "bigworld_actions",
                obj, "bigworld_actions_index",
                rows=3
            )
            
            col = row.column(align=True)
            col.operator("bigworld.action_add", icon='ADD', text="")
            col.operator("bigworld.action_remove", icon='REMOVE', text="")
            col.separator()
            col.operator("bigworld.action_move_up", icon='TRIA_UP', text="")
            col.operator("bigworld.action_move_down", icon='TRIA_DOWN', text="")
            
            # 选中Action的详细设置
            if obj.bigworld_actions and 0 <= obj.bigworld_actions_index < len(obj.bigworld_actions):
                action = obj.bigworld_actions[obj.bigworld_actions_index]
                
                sub_box = box.box()
                sub_box.label(text="⚙️ 设置: {0}".format(action.name), icon='SETTINGS')
                sub_box.prop(action, "name", text="名称")
                sub_box.prop(action, "animation_name", text="动画")
                sub_box.prop(action, "blended", text="混合")
                sub_box.prop(action, "track", text="轨道")
        
        # ========== 材质信息（仅网格对象）==========
        if obj.type == 'MESH':
            box = layout.box()
            row = box.row()
            row.label(text="🎨 材质槽: {0}".format(len(obj.material_slots)), icon='MATERIAL')
            row.label(text="(自动提取)", icon='INFO')
        
        # ========== 导出前检测 ==========
        layout.separator()
        row = layout.row()
        row.scale_y = 1.2
        row.operator("bigworld.validate_object", text="🔍 运行导出前检测", icon='CHECKMARK')


class BIGWORLD_OT_validate_object(bpy.types.Operator):
    """运行导出前检测"""
    bl_idname = "bigworld.validate_object"
    bl_label = "运行导出前检测"
    bl_description = "检测对象是否符合导出要求"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        obj = context.object
        props = obj.bigworld_props
        
        # 基础检查
        if not props.resource_id:
            self.report({'WARNING'}, "资源ID为空，将使用对象名称")
        
        # 骨架检查
        if props.export_type in {'SKINNED', 'CHARACTER'}:
            has_armature = any(mod.type == 'ARMATURE' for mod in obj.modifiers)
            if not has_armature:
                self.report({'ERROR'}, "蒙皮/角色动画类型需要Armature修改器")
                return {'CANCELLED'}
        
        # Action检查
        if props.export_type == 'CHARACTER':
            if len(obj.bigworld_actions) == 0:
                self.report({'WARNING'}, "角色动画类型建议至少添加1个Action")
        
        self.report({'INFO'}, "检测通过")
        return {'FINISHED'}


# ==================== 注册 ====================
# 注意：所有类在 __init__.py 中注册，这里只处理属性绑定

def register():
    # 注册属性到Object（属性绑定必须在这里，因为依赖已注册的类）
    bpy.types.Object.bigworld_props = PointerProperty(type=BigWorldObjectProperties)
    bpy.types.Object.bigworld_actions = CollectionProperty(type=BigWorldAction)
    bpy.types.Object.bigworld_actions_index = IntProperty(default=0)
    bpy.types.Object.bigworld_hardpoints = CollectionProperty(type=BigWorldHardpoint)
    bpy.types.Object.bigworld_hardpoints_index = IntProperty(default=0)


def unregister():
    # 删除属性
    if hasattr(bpy.types.Object, 'bigworld_props'):
        del bpy.types.Object.bigworld_props
    if hasattr(bpy.types.Object, 'bigworld_actions'):
        del bpy.types.Object.bigworld_actions
    if hasattr(bpy.types.Object, 'bigworld_actions_index'):
        del bpy.types.Object.bigworld_actions_index
    if hasattr(bpy.types.Object, 'bigworld_hardpoints'):
        del bpy.types.Object.bigworld_hardpoints
    if hasattr(bpy.types.Object, 'bigworld_hardpoints_index'):
        del bpy.types.Object.bigworld_hardpoints_index


if __name__ == "__main__":
    register()

