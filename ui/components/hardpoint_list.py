# -*- coding: utf-8 -*-
"""
硬点列表UI组件
"""

import bpy
from bpy.types import UIList


class BIGWORLD_UL_hardpoints(UIList):
    """硬点列表UIList"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        """
        绘制硬点列表项
        
        显示格式：
        名称 | 类型 | 绑定位置
        """
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # 硬点名称
            row.prop(item, "name", text="", emboss=False, icon='EMPTY_AXIS')
            
            # 硬点类型（显示图标）
            type_icons = {
                'WEAPON': 'EVENT_W',
                'EQUIPMENT': 'EVENT_E',
                'EFFECT': 'EVENT_F',
                'INTERACT': 'EVENT_I'
            }
            icon = type_icons.get(item.hardpoint_type, 'EMPTY_AXIS')
            row.prop(item, "hardpoint_type", text="", icon=icon)
            
            # 绑定位置
            if item.use_empty and item.target_empty:
                row.label(text="→ {0}".format(item.target_empty.name), icon='LINKED')
            elif item.bone_name:
                row.label(text="→ {0}".format(item.bone_name), icon='BONE_DATA')
            else:
                row.label(text="(未绑定)", icon='ERROR')
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='EMPTY_AXIS')


def register():
    bpy.utils.register_class(BIGWORLD_UL_hardpoints)


def unregister():
    bpy.utils.unregister_class(BIGWORLD_UL_hardpoints)

