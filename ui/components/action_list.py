# -*- coding: utf-8 -*-
"""
Action列表UI组件
"""

import bpy
from bpy.types import UIList


class BIGWORLD_UL_actions(UIList):
    """Action列表UIList"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        """
        绘制Action列表项
        
        显示格式：
        名称 | 关联动画 | 混合 | 轨道
        """
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # Action名称
            row.prop(item, "name", text="", emboss=False, icon='ACTION')
            
            # 关联动画
            row.prop(item, "animation_name", text="")
            
            # 混合播放
            row.prop(item, "blended", text="", icon='CHECKBOX_HLT' if item.blended else 'CHECKBOX_DEHLT')
            
            # 轨道索引
            row.label(text="轨道:{0}".format(item.track))
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='ACTION')


def register():
    bpy.utils.register_class(BIGWORLD_UL_actions)


def unregister():
    bpy.utils.unregister_class(BIGWORLD_UL_actions)

