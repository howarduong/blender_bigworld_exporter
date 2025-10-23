# -*- coding: utf-8 -*-
"""
硬点相关操作符
"""

import bpy
from bpy.types import Operator


class BIGWORLD_OT_hardpoint_add(Operator):
    """添加硬点"""
    bl_idname = "bigworld.hardpoint_add"
    bl_label = "添加硬点"
    bl_description = "添加一个新的硬点"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        if not obj:
            return {'CANCELLED'}
        
        # 添加新硬点
        hp = obj.bigworld_hardpoints.add()
        hp.name = "HP_{0}".format(len(obj.bigworld_hardpoints))
        hp.hardpoint_type = 'WEAPON'
        
        # 设置为活动项
        obj.bigworld_hardpoints_index = len(obj.bigworld_hardpoints) - 1
        
        return {'FINISHED'}


class BIGWORLD_OT_hardpoint_remove(Operator):
    """删除硬点"""
    bl_idname = "bigworld.hardpoint_remove"
    bl_label = "删除硬点"
    bl_description = "删除选中的硬点"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        if not obj or obj.bigworld_hardpoints_index < 0:
            return {'CANCELLED'}
        
        # 删除选中的硬点
        obj.bigworld_hardpoints.remove(obj.bigworld_hardpoints_index)
        
        # 调整索引
        if obj.bigworld_hardpoints_index >= len(obj.bigworld_hardpoints):
            obj.bigworld_hardpoints_index = len(obj.bigworld_hardpoints) - 1
        
        return {'FINISHED'}


# 注册函数
classes = (
    BIGWORLD_OT_hardpoint_add,
    BIGWORLD_OT_hardpoint_remove,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

