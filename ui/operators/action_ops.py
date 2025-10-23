# -*- coding: utf-8 -*-
"""
Action相关操作符
"""

import bpy
from bpy.types import Operator


class BIGWORLD_OT_action_add(Operator):
    """添加Action"""
    bl_idname = "bigworld.action_add"
    bl_label = "添加Action"
    bl_description = "添加一个新的Action"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        if not obj:
            return {'CANCELLED'}
        
        # 添加新Action
        action = obj.bigworld_actions.add()
        action.name = "Action_{0}".format(len(obj.bigworld_actions))
        action.blended = True
        action.track = 0
        
        # 设置为活动项
        obj.bigworld_actions_index = len(obj.bigworld_actions) - 1
        
        return {'FINISHED'}


class BIGWORLD_OT_action_remove(Operator):
    """删除Action"""
    bl_idname = "bigworld.action_remove"
    bl_label = "删除Action"
    bl_description = "删除选中的Action"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        if not obj or obj.bigworld_actions_index < 0:
            return {'CANCELLED'}
        
        # 删除选中的Action
        obj.bigworld_actions.remove(obj.bigworld_actions_index)
        
        # 调整索引
        if obj.bigworld_actions_index >= len(obj.bigworld_actions):
            obj.bigworld_actions_index = len(obj.bigworld_actions) - 1
        
        return {'FINISHED'}


class BIGWORLD_OT_action_move_up(Operator):
    """上移Action"""
    bl_idname = "bigworld.action_move_up"
    bl_label = "上移"
    bl_description = "将Action向上移动"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        index = obj.bigworld_actions_index
        
        if index > 0:
            obj.bigworld_actions.move(index, index - 1)
            obj.bigworld_actions_index -= 1
        
        return {'FINISHED'}


class BIGWORLD_OT_action_move_down(Operator):
    """下移Action"""
    bl_idname = "bigworld.action_move_down"
    bl_label = "下移"
    bl_description = "将Action向下移动"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        index = obj.bigworld_actions_index
        
        if index < len(obj.bigworld_actions) - 1:
            obj.bigworld_actions.move(index, index + 1)
            obj.bigworld_actions_index += 1
        
        return {'FINISHED'}


# 注册函数
classes = (
    BIGWORLD_OT_action_add,
    BIGWORLD_OT_action_remove,
    BIGWORLD_OT_action_move_up,
    BIGWORLD_OT_action_move_down,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

