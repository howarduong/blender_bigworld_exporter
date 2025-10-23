# File: writers/animation_writer.py
# Purpose: 写入 .animation 文件（BinaryFile 格式，根据源码对齐）
# Notes:
# - 不是 PackedSection！是直接的 BinaryFile
# - 格式参考: animation.cpp line 807-816
# - 包含: totalTime + identifier + internalIdentifier + channels
# - Channel 类型: InterpolatedAnimationChannel (type=3, 无压缩)

import struct
from typing import List, Tuple
from ..core.schema import Animation, AnimationChannel


class AnimationWriter:
    """
    AnimationWriter
    ---------------
    用于写入 BigWorld .animation 文件（BinaryFile 格式）。
    
    根据源码 animation.cpp line 807-816:
    (*pbf) << totalTime_ << identifier_ << internalIdentifier_;
    (*pbf) << numChannelBinders;
    for (int i = 0; i < numChannelBinders; ++i)
    {
        (*pbf) << pAC->type();
        pAC->save( *pbf );
    }
    
    使用方式:
        writer = AnimationWriter("output/walk.animation")
        writer.write(animation_data)
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def write(self, animation: Animation) -> None:
        """
        写入 .animation 文件
        
        参数:
            animation: Animation 数据结构
        """
        with open(self.filepath, 'wb') as f:
            # 1. totalTime (float)
            f.write(struct.pack('<f', animation.duration))
            
            # 2. identifier (string with length prefix)
            self._write_string(f, animation.name)
            
            # 3. internalIdentifier (string with length prefix)
            # 通常与 identifier 相同，或为资源路径
            internal_id = getattr(animation, 'internal_identifier', animation.name)
            self._write_string(f, internal_id)
            
            # 4. numChannelBinders (int)
            num_channels = len(animation.channels)
            f.write(struct.pack('<i', num_channels))
            
            # 5. For each channel
            for channel in animation.channels:
                # Channel type (int)
                # Type 3 = INTERPOLATED_ANIMATION_CHANNEL_COMPRESSION_OFF
                f.write(struct.pack('<i', 3))
                
                # Channel data (InterpolatedAnimationChannel)
                self._write_interpolated_channel(f, channel)
    
    def _write_string(self, f, s: str):
        """
        写入带长度前缀的字符串
        
        格式: int32(length) + bytes(string)
        """
        s_bytes = s.encode('utf-8')
        f.write(struct.pack('<i', len(s_bytes)))
        f.write(s_bytes)
    
    def _write_interpolated_channel(self, f, channel: AnimationChannel):
        """
        写入 InterpolatedAnimationChannel
        
        根据 interpolated_animation_channel.cpp 的 save() 方法
        
        格式:
        1. identifier (bone name)
        2. num_scale_keys + [(time, Vector3), ...]
        3. num_position_keys + [(time, Vector3), ...]
        4. num_rotation_keys + [(time, Quaternion), ...]
        """
        # 1. identifier (bone name)
        self._write_string(f, channel.bone_name)
        
        # 2. Scale keys
        f.write(struct.pack('<i', len(channel.keys.scale_keys)))
        for time, scale in channel.keys.scale_keys:
            f.write(struct.pack('<f', time))
            f.write(struct.pack('<fff', scale[0], scale[1], scale[2]))
        
        # 3. Position keys
        f.write(struct.pack('<i', len(channel.keys.position_keys)))
        for time, pos in channel.keys.position_keys:
            f.write(struct.pack('<f', time))
            f.write(struct.pack('<fff', pos[0], pos[1], pos[2]))
        
        # 4. Rotation keys (Quaternion)
        f.write(struct.pack('<i', len(channel.keys.rotation_keys)))
        for time, rot in channel.keys.rotation_keys:
            f.write(struct.pack('<f', time))
            # BigWorld Quaternion format: (x, y, z, w)
            f.write(struct.pack('<ffff', rot[0], rot[1], rot[2], rot[3]))


def write_animation(filepath: str, animation: Animation) -> None:
    """
    便捷函数：写入 .animation 文件
    
    参数:
        filepath: 输出文件路径
        animation: Animation 数据结构
    """
    writer = AnimationWriter(filepath)
    writer.write(animation)

