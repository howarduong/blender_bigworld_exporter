# 🔧 MVP集成补丁说明

**目标**: 在现有架构基础上添加Action和Hardpoint功能  
**策略**: 最小改动，最大效果  
**工作量**: 约10个文件，~300行代码修改

---

## 📋 需要修改的文件清单

### 1. UI文件替换（3个文件）

#### ✅ 已准备好的新文件
```
ui/preferences_new.py       → 替换 → ui/preferences_panel.py
ui/object_properties_new.py → 替换 → ui/object_panel.py
```

#### 操作步骤
```bash
# 备份旧文件
mv ui/preferences_panel.py ui/preferences_panel_old.py
mv ui/object_panel.py ui/object_panel_old.py

# 使用新文件
mv ui/preferences_new.py ui/preferences_panel.py
mv ui/object_properties_new.py ui/object_panel.py
```

---

### 2. __init__.py修改（关键！）

#### 需要添加的导入
```python
# 在文件开头添加
from .ui.components.action_list import BIGWORLD_UL_actions
from .ui.components.hardpoint_list import BIGWORLD_UL_hardpoints
from .ui.operators import action_ops
from .ui.operators import hardpoint_ops
from .builders.model.hardpoint_builder import HardpointBuilder
from .builders.model.action_builder import ActionBuilder
from .config.export_settings import ObjectExportSettings
```

#### 需要修改register()函数
```python
def register():
    # 注册UI组件
    action_list.register()
    hardpoint_list.register()
    action_ops.register()
    hardpoint_ops.register()
    
    # ... 原有注册代码 ...
```

#### 需要修改unregister()函数
```python
def unregister():
    # 注销UI组件
    hardpoint_ops.unregister()
    action_ops.unregister()
    hardpoint_list.unregister()
    action_list.unregister()
    
    # ... 原有注销代码 ...
```

---

### 3. export_dispatcher.py修改

#### 在文件开头添加导入
```python
from .builders.model.hardpoint_builder import HardpointBuilder
from .builders.model.action_builder import ActionBuilder
from .config.export_settings import ObjectExportSettings
```

#### 修改_export_skinned方法（添加hardpoint支持）

找到这部分代码：
```python
def _export_skinned(self, obj, ...):
    # ... 现有代码 ...
    
    # 构建Model
    model = ModelBuilder.build(...)
```

在构建Model之前添加：
```python
    # 构建硬点
    obj_settings = ObjectExportSettings.from_object_properties(obj)
    hardpoints = []
    if obj_settings.hardpoints and skeleton:
        hardpoints = HardpointBuilder.build_all(obj_settings.hardpoints, skeleton)
        if self.logger:
            self.logger.info("已构建 {0} 个硬点".format(len(hardpoints)))
    
    # 构建Model（添加hardpoints参数）
    model = ModelBuilder.build(...)
    model.hardpoints = hardpoints  # 添加硬点数据
```

#### 修改_export_character方法（添加action和hardpoint支持）

找到这部分代码（约第260-350行）：
```python
def _export_character(self, obj, ...):
    # ... 现有代码 ...
    
    # 构建Model
    model = ModelBuilder.build(...)
```

在构建Model之前添加：
```python
    # 构建硬点
    obj_settings = ObjectExportSettings.from_object_properties(obj)
    hardpoints = []
    if obj_settings.hardpoints and skeleton:
        hardpoints = HardpointBuilder.build_all(obj_settings.hardpoints, skeleton)
        if self.logger:
            self.logger.info("已构建 {0} 个硬点".format(len(hardpoints)))
    
    # 构建Action
    actions = []
    if obj_settings.actions and animations:
        # 创建动画名称集合
        animation_names = set(anim.name for anim in animations)
        actions = ActionBuilder.build_all(obj_settings.actions, animation_names)
        if self.logger:
            self.logger.info("已构建 {0} 个Action".format(len(actions)))
    
    # 构建Model（添加hardpoints和actions）
    model = ModelBuilder.build(...)
    model.hardpoints = hardpoints
    model.actions = actions
```

---

### 4. ui/components/__init__.py（新建）

```python
# -*- coding: utf-8 -*-
"""UI组件模块"""

from .action_list import BIGWORLD_UL_actions
from .hardpoint_list import BIGWORLD_UL_hardpoints

__all__ = [
    'BIGWORLD_UL_actions',
    'BIGWORLD_UL_hardpoints',
]
```

---

### 5. ui/operators/__init__.py（新建）

```python
# -*- coding: utf-8 -*-
"""UI操作符模块"""

from . import action_ops
from . import hardpoint_ops

__all__ = [
    'action_ops',
    'hardpoint_ops',
]
```

---

### 6. builders/model/__init__.py（更新）

```python
# -*- coding: utf-8 -*-
"""Model构建器模块"""

from .hardpoint_builder import HardpointBuilder
from .action_builder import ActionBuilder

__all__ = [
    'HardpointBuilder',
    'ActionBuilder',
]
```

---

### 7. config/__init__.py（更新）

```python
# -*- coding: utf-8 -*-
"""配置模块"""

from .constants import *
from .export_settings import ExportSettings, ObjectExportSettings, ActionConfig, HardpointConfig

__all__ = [
    'ExportSettings',
    'ObjectExportSettings',
    'ActionConfig',
    'HardpointConfig',
]
```

---

## 🔄 导入路径更新（可选，但推荐）

### 更新bin_section_writer的引用

由于文件移动到了`core/io/`，需要更新引用它的文件：

#### writers/primitives_writer.py
```python
# 旧导入
from ..core.bin_section_writer import BinSectionWriter

# 新导入
from ..core.io.bin_section_writer import BinSectionWriter
```

#### 或者保持兼容（在core/\_\_init\_\_.py中）
```python
# core/__init__.py
from .io.bin_section_writer import BinSectionWriter
from .io.packed_section_writer import PackedSectionWriter
from .io.xml_writer import XMLWriter

# 这样其他文件仍可使用
# from core.bin_section_writer import ...
```

---

## ✅ MVP完成检查清单

完成以下步骤后，Action和Hardpoint功能即可使用：

- [ ] 替换UI文件（preferences_panel.py, object_panel.py）
- [ ] 创建ui/components/__init__.py
- [ ] 创建ui/operators/__init__.py
- [ ] 创建builders/model/__init__.py
- [ ] 创建config/__init__.py
- [ ] 更新__init__.py（添加导入和注册）
- [ ] 更新export_dispatcher.py（集成新Builder）
- [ ] 测试插件加载
- [ ] 测试Action功能
- [ ] 测试Hardpoint功能

---

## 🎯 预期效果

完成MVP后，用户可以：

1. **在N面板中管理Action**
   - 添加/删除Action
   - 配置Action名称、关联动画、混合、轨道
   
2. **在N面板中管理硬点**
   - 添加/删除硬点
   - 配置硬点名称、类型、绑定骨骼

3. **导出角色模型时自动包含**
   - Action数据写入.model文件
   - Hardpoint数据写入.model文件

4. **在BigWorld中使用**
   - Action控制角色动作
   - Hardpoint挂载武器装备

---

**这是最高效的实施方案，是否继续？**

