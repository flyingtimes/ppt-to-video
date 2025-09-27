"""
视频处理器
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class VideoProcessor:
    """视频处理器"""
    
    def __init__(self):
        self.test_full_video = Path("test/full.mp4")
        self.test_head_video = Path("test/head.mp4")
        
        # 检查测试视频文件是否存在
        if not self.test_full_video.exists():
            logger.warning(f"测试全屏视频文件不存在: {self.test_full_video}")
        if not self.test_head_video.exists():
            logger.warning(f"测试头部视频文件不存在: {self.test_head_video}")
    
    def process_page(self, page_data: Dict[str, Any], page_number: int, work_dir: Path) -> Optional[str]:
        """
        处理单个页面，生成视频
        
        Args:
            page_data: 页面数据
            page_number: 页码
            work_dir: 工作目录
            
        Returns:
            生成的视频文件路径
        """
        try:
            # 根据模式选择测试视频
            if page_data['is_full_mode']:
                source_video = self.test_full_video
                logger.info(f"第 {page_number} 页使用Full模式")
            else:
                source_video = self.test_head_video
                logger.info(f"第 {page_number} 页使用Head模式")
            
            if not source_video.exists():
                logger.error(f"源视频文件不存在: {source_video}")
                return None
            
            # 处理视频组合
            if page_data['is_full_mode']:
                # Full模式：直接使用数字人视频
                import shutil
                shutil.copy2(source_video, page_data['video_file'])
            else:
                # Head模式：组合PPT幻灯片和头部数字人视频
                success = self.combine_slide_with_video(
                    str(page_data['slide_image']),
                    str(source_video),
                    False,
                    str(page_data['video_file'])
                )
                if not success:
                    logger.error(f"第 {page_number} 页视频组合失败")
                    return None
            
            logger.info(f"第 {page_number} 页视频生成完成: {page_data['video_file']}")
            return str(page_data['video_file'])
            
        except Exception as e:
            logger.error(f"处理第 {page_number} 页失败: {e}")
            return None
    
    def merge_videos(self, video_files: List[str], work_dir: Path) -> Optional[str]:
        """
        合并多个视频文件
        
        Args:
            video_files: 视频文件路径列表
            work_dir: 工作目录
            
        Returns:
            合并后的视频文件路径
        """
        try:
            if not video_files:
                logger.error("没有视频文件需要合并")
                return None
            
            # 输出文件路径
            output_video = work_dir / "merged_video.mp4"
            
            # 构建ffmpeg命令，使用concat filter
            # 为每个视频文件添加输入参数
            input_args = []
            for video_file in video_files:
                input_args.extend(['-i', video_file])
            
            # 构建filter_complex参数，先统一所有视频的分辨率到1920x1080
            scale_parts = []
            filter_parts = []
            for i in range(len(video_files)):
                scale_parts.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[scaled{i}:v]")
                filter_parts.append(f"[scaled{i}:v][{i}:a]")
            
            scale_complex = ';'.join(scale_parts)
            filter_complex = scale_complex + ';' + ''.join(filter_parts) + f'concat=n={len(video_files)}:v=1:a=1[outv][outa]'
            
            cmd = ['ffmpeg'] + input_args + [
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',  # 覆盖输出文件
                str(output_video)
            ]
            
            logger.info(f"开始合并 {len(video_files)} 个视频文件")
            logger.info(f"FFmpeg命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"视频合并完成: {output_video}")
                return str(output_video)
            else:
                logger.error(f"视频合并失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"合并视频失败: {e}")
            return None
    
    def combine_slide_with_video(self, slide_image: str, video_file: str, is_full_mode: bool, output_file: str) -> bool:
        """
        组合PPT幻灯片和数字人视频
        
        Args:
            slide_image: 幻灯片图片路径
            video_file: 视频文件路径
            is_full_mode: 是否为全屏模式
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            if is_full_mode:
                # Full模式：只使用数字人视频
                import shutil
                shutil.copy2(video_file, output_file)
                return True
            else:
                # Head模式：组合幻灯片和头部视频
                # 幻灯片作为背景，头部视频放在左下角
                cmd = [
                    'ffmpeg',
                    '-i', slide_image,
                    '-i', video_file,
                    '-filter_complex', 
                    '[0:v]scale=1920:1080[bg];[1:v]scale=320:320[fg];[bg][fg]overlay=50:710',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'copy',
                    '-shortest',
                    '-y',  # 覆盖输出文件
                    output_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"FFmpeg命令执行失败: {result.stderr}")
                return result.returncode == 0
                
        except Exception as e:
            logger.error(f"组合幻灯片和视频失败: {e}")
            return False