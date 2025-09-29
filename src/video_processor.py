"""
视频处理器
"""
import os
import subprocess
import logging
import time
from PIL import Image, ImageDraw
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.video_generator import DigitalHumanVideoGenerator

logger = logging.getLogger(__name__)


class VideoProcessor:
    """视频处理器"""
    
    # 字幕配置类
    class SubtitleConfig:
        """字幕配置"""
        FONT_SIZE = 20
        TEXT_COLOR = (255, 255, 224, 255)  # 浅黄色
        STROKE_COLOR = (0, 0, 0, 255)  # 黑色描边
        STROKE_WIDTH = 1
        LINE_SPACING = 5
        BOTTOM_MARGIN = 100  # 距离底部边缘的距离
        MAX_WIDTH_RATIO = 0.8  # 文本最大宽度比例
        
        # 字体优先级列表
        FONT_CANDIDATES = [
            "STHeiti Medium.ttc",      # 黑体
            "STHeiti Light.ttc",       # 黑体
            "PingFang.ttc",             # 苹方
            "Songti.ttc",               # 宋体
            "Arial Unicode MS.ttf",    # Arial Unicode
            "Microsoft YaHei.ttf",     # 微软雅黑
            "simhei.ttf",               # Windows黑体
            "simsun.ttf",               # Windows宋体
            "arial.ttf"                 # Arial
        ]
    
    def __init__(self):
        self.test_full_video = Path("test/full.mp4")
        self.test_head_video = Path("test/head.mp4")
        self.video_generator = DigitalHumanVideoGenerator()
        
        # 检查测试视频文件是否存在
        if not self.test_full_video.exists():
            logger.warning(f"测试全屏视频文件不存在: {self.test_full_video}")
        if not self.test_head_video.exists():
            logger.warning(f"测试头部视频文件不存在: {self.test_head_video}")
    
    def create_circular_mask(self, size: int, output_path: str) -> bool:
        """
        创建圆形遮罩图像，支持边缘柔和过渡
        
        Args:
            size: 遮罩大小（正方形边长）
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            # 创建RGBA图像（支持透明度）
            mask = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(mask)
            
            # 绘制多层圆形，实现边缘柔和过渡
            center = size // 2
            max_radius = size // 2
            
            # 外层到内层的渐变
            for i in range(10):
                radius = max_radius - i * 2
                alpha = int(255 - i * 15)  # 渐变透明度
                if alpha > 0 and radius > 0:
                    draw.ellipse([center - radius, center - radius, center + radius, center + radius], 
                                fill=(255, 255, 255, alpha))
            
            # 中心完全不透明
            if max_radius > 20:
                center_radius = max_radius - 20
                draw.ellipse([center - center_radius, center - center_radius, center + center_radius, center + center_radius], 
                            fill=(255, 255, 255, 255))
            
            # 保存遮罩图像
            mask.save(output_path)
            logger.info(f"圆形遮罩已创建: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建圆形遮罩失败: {e}")
            return False
    
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
            # 获取备注文本
            notes_text = ""
            if 'notes_file' in page_data:
                try:
                    with open(page_data['notes_file'], 'r', encoding='utf-8') as f:
                        notes_text = f.read().strip()
                except Exception as e:
                    logger.warning(f"读取备注文件失败: {e}")
            
            # 判断模式
            is_full_mode = page_data['is_full_mode']
            mode = "full" if is_full_mode else "head"
            
            logger.info(f"第 {page_number} 页使用{mode.upper()}模式")
            
            # 创建临时视频文件路径
            temp_video_path = work_dir / f"temp_video_{page_number:03d}.mp4"
            
            # 尝试生成数字人视频
            generated_video = None
            if notes_text:
                try:
                    # 生成数字人视频
                    video_result = self.video_generator.generate_video(
                        text=notes_text,
                        mode=mode,
                        output_path=str(temp_video_path)
                    )
                    
                    if video_result and video_result.get('video_path'):
                        generated_video = video_result['video_path']
                        logger.info(f"第 {page_number} 页数字人视频生成成功")
                    else:
                        logger.warning(f"第 {page_number} 页数字人视频生成失败，使用示例视频")
                except Exception as e:
                    logger.warning(f"第 {page_number} 页数字人视频生成异常: {e}，使用示例视频")
            
            # 如果生成失败，使用示例视频
            if not generated_video:
                source_video = self.test_full_video if is_full_mode else self.test_head_video
                if not source_video.exists():
                    logger.error(f"示例视频文件不存在: {source_video}")
                    return None
                
                # 复制示例视频到临时文件
                import shutil
                shutil.copy2(source_video, temp_video_path)
                generated_video = str(temp_video_path)
                logger.info(f"第 {page_number} 页使用示例视频")
            
            # 处理视频组合和字幕
            if is_full_mode:
                # Full模式：数字人视频 + 字幕
                success = self.combine_slide_with_video(
                    "",  # 不需要slide_image
                    generated_video,
                    True,  # Full模式
                    str(page_data['video_file']),
                    work_dir,
                    notes_text,
                    page_number
                )
            else:
                # Head模式：组合PPT幻灯片和头部数字人视频 + 字幕
                # 强制使用PPT背景 + 数字人前景组合
                success = self.combine_slide_with_video(
                    str(page_data['slide_image']),
                    generated_video,
                    False,
                    str(page_data['video_file']),
                    work_dir,
                    notes_text,
                    page_number
                )
            
            # 删除临时文件
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            
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
        start_time = time.time()
        
        logger.info(f"🎬 开始合并视频文件")
        logger.info(f"📁 待合并视频数量: {len(video_files)}")
        
        try:
            if not video_files:
                logger.error("❌ 没有视频文件需要合并")
                return None
            
            # 统计视频文件信息
            total_size = 0
            for i, video_file in enumerate(video_files):
                if os.path.exists(video_file):
                    size = os.path.getsize(video_file)
                    total_size += size
                    logger.info(f"📹 视频{i+1}: {os.path.basename(video_file)} ({size/1024/1024:.2f} MB)")
                else:
                    logger.warning(f"⚠️ 视频文件不存在: {video_file}")
            
            logger.info(f"📊 总文件大小: {total_size/1024/1024:.2f} MB")
            
            # 输出文件路径
            output_video = work_dir / "merged_video.mp4"
            logger.info(f"📁 输出路径: {output_video}")
            
            # 构建ffmpeg命令，使用concat filter
            logger.info(f"🔧 构建FFmpeg命令...")
            
            # 为每个视频文件添加输入参数
            input_args = []
            for video_file in video_files:
                if os.path.exists(video_file):
                    input_args.extend(['-i', video_file])
            
            # 构建filter_complex参数，先统一所有视频的分辨率到1920x1080
            scale_parts = []
            filter_parts = []
            video_count = len([f for f in video_files if os.path.exists(f)])
            
            for i in range(video_count):
                scale_parts.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[scaled{i}:v]")
                filter_parts.append(f"[scaled{i}:v][{i}:a]")
            
            scale_complex = ';'.join(scale_parts)
            filter_complex = scale_complex + ';' + ''.join(filter_parts) + f'concat=n={video_count}:v=1:a=1[outv][outa]'
            
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
            
            logger.info(f"⚙️ 执行FFmpeg合并命令...")
            logger.debug(f"FFmpeg命令: {' '.join(cmd)}")
            
            # 执行命令
            merge_start = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True)
            merge_time = time.time() - merge_start
            
            if result.returncode == 0:
                total_time = time.time() - start_time
                
                if os.path.exists(output_video):
                    output_size = os.path.getsize(output_video)
                    logger.info(f"✅ 视频合并成功！")
                    logger.info(f"📁 输出文件: {output_video}")
                    logger.info(f"📦 输出大小: {output_size/1024/1024:.2f} MB")
                    logger.info(f"⏱️ 合并耗时: {merge_time:.2f}秒")
                    logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
                    
                    if result.stdout:
                        logger.debug(f"FFmpeg输出: {result.stdout}")
                    
                    return str(output_video)
                else:
                    logger.error(f"❌ 输出文件不存在: {output_video}")
                    return None
            else:
                total_time = time.time() - start_time
                logger.error(f"❌ 视频合并失败")
                logger.error(f"📊 返回码: {result.returncode}")
                logger.error(f"💬 错误信息: {result.stderr}")
                logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
                return None
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ 合并视频时发生错误: {e}")
            logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
            import traceback
            logger.error(f"📋 错误详情: {traceback.format_exc()}")
            return None
    
    def create_subtitle_image(self, text: str, output_path: str, width: int = 1920, height: int = 1080) -> bool:
        """
        创建字幕图像
        
        Args:
            text: 字幕文本
            output_path: 输出文件路径
            width: 图像宽度
            height: 图像高度
            
        Returns:
            是否成功
        """
        try:
            # 创建RGBA图像（透明背景）
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # 使用统一的字幕配置
            config = self.SubtitleConfig
            
            # 设置字体 - 优先使用系统中文字体
            try:
                from PIL import ImageFont
                import matplotlib.font_manager
                
                font = None
                for font_name in config.FONT_CANDIDATES:
                    try:
                        # 尝试系统字体路径
                        for font_path in matplotlib.font_manager.findSystemFonts():
                            if font_name in font_path:
                                font = ImageFont.truetype(font_path, config.FONT_SIZE)
                                logger.info(f"使用字体: {font_path}")
                                break
                        if font:
                            break
                    except (ImportError, OSError):
                        continue
                
                # 如果都没找到，使用默认字体
                if not font:
                    font = ImageFont.load_default()
                    logger.warning("使用默认字体，中文可能显示异常")
                    
            except ImportError:
                # matplotlib未安装，使用基本字体检测
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype("STHeiti Medium.ttc", config.FONT_SIZE)
                except (ImportError, OSError):
                    try:
                        font = ImageFont.truetype("PingFang.ttc", config.FONT_SIZE)
                    except (ImportError, OSError):
                        try:
                            font = ImageFont.truetype("Arial Unicode MS", config.FONT_SIZE)
                        except (ImportError, OSError):
                            font = ImageFont.load_default()
                            logger.warning("使用默认字体，中文可能显示异常")
            
            # 使用统一的颜色配置
            text_color = config.TEXT_COLOR
            stroke_color = config.STROKE_COLOR
            stroke_width = config.STROKE_WIDTH
            
            # 处理长文本换行
            def wrap_text(text, font, max_width):
                """将长文本按最大宽度换行"""
                lines = []
                current_line = ""
                
                # 中文字符按字符处理，英文按单词处理
                i = 0
                while i < len(text):
                    # 尝试添加一个字符
                    test_line = current_line + text[i]
                    
                    # 检查是否为英文单词的一部分
                    if text[i].isalnum() and i > 0 and text[i-1].isalnum():
                        # 继续读取英文单词
                        j = i + 1
                        while j < len(text) and text[j].isalnum():
                            test_line += text[j]
                            j += 1
                        
                        # 测试整个单词
                        try:
                            bbox = draw.textbbox((0, 0), test_line, font=font)
                            test_width = bbox[2] - bbox[0]
                        except AttributeError:
                            test_width = draw.textsize(test_line, font=font)[0]
                        
                        if test_width <= max_width:
                            current_line = test_line
                            i = j
                        else:
                            # 单词太长，按字符分割
                            if current_line:
                                lines.append(current_line)
                                current_line = text[i]
                                i += 1
                            else:
                                # 单个字符就超宽，强制分割
                                lines.append(text[i])
                                current_line = ""
                                i += 1
                    else:
                        # 中文字符或符号
                        try:
                            bbox = draw.textbbox((0, 0), test_line, font=font)
                            test_width = bbox[2] - bbox[0]
                        except AttributeError:
                            test_width = draw.textsize(test_line, font=font)[0]
                        
                        if test_width <= max_width:
                            current_line = test_line
                            i += 1
                        else:
                            if current_line:
                                lines.append(current_line)
                                current_line = text[i]
                                i += 1
                            else:
                                # 单个字符就超宽，强制分割
                                lines.append(text[i])
                                current_line = ""
                                i += 1
                
                if current_line:
                    lines.append(current_line)
                
                return lines
            
            # 使用统一的布局配置
            max_width = int(width * config.MAX_WIDTH_RATIO)
            lines = wrap_text(text, font, max_width)
            
            # 计算总高度
            total_height = 0
            line_heights = []
            for line in lines:
                try:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_height = bbox[3] - bbox[1]
                except AttributeError:
                    line_height = draw.textsize(line, font=font)[1]
                line_heights.append(line_height)
                total_height += line_height
            
            # 使用统一的行间距和边距
            total_height += (len(lines) - 1) * config.LINE_SPACING
            
            # 垂直位置在视频底部上方指定像素
            start_y = height - config.BOTTOM_MARGIN - total_height
            
            # 绘制每一行
            for i, line in enumerate(lines):
                try:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                except AttributeError:
                    line_width = draw.textsize(line, font=font)[0]
                
                y_position = start_y + sum(line_heights[:i]) + i * config.LINE_SPACING
                x_position = (width - line_width) // 2
                
                # 绘制带描边的文字
                try:
                    # 使用PIL的stroke功能
                    draw.text((x_position, y_position), line, font=font, fill=text_color, 
                             stroke_width=stroke_width, stroke_fill=stroke_color)
                except Exception as e:
                    logger.warning(f"Stroke绘制失败: {e}, 使用手动描边")
                    # 手动描边效果
                    offsets = [(-stroke_width,-stroke_width), (-stroke_width,0), (-stroke_width,stroke_width), 
                             (0,-stroke_width), (0,stroke_width), (stroke_width,-stroke_width), 
                             (stroke_width,0), (stroke_width,stroke_width)]
                    for dx, dy in offsets:
                        draw.text((x_position + dx, y_position + dy), line, font=font, fill=stroke_color)
                    # 绘制主文字
                    draw.text((x_position, y_position), line, font=font, fill=text_color)
            
            # 保存图像
            image.save(output_path)
            logger.info(f"字幕图像已创建: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建字幕图像失败: {e}")
            return False
    
    def combine_slide_with_video(self, slide_image: str, video_file: str, is_full_mode: bool, output_file: str, work_dir: Path, subtitle_text: str = "", page_number: int = 1) -> bool:
        """
        组合PPT幻灯片和数字人视频，并添加字幕
        
        Args:
            slide_image: 幻灯片图片路径
            video_file: 视频文件路径
            is_full_mode: 是否为全屏模式
            output_file: 输出文件路径
            work_dir: 工作目录
            subtitle_text: 字幕文本
            
        Returns:
            是否成功
        """
        start_time = time.time()
        
        logger.info(f"🎬 开始组合视频内容")
        logger.info(f"📄 页面编号: 第{page_number}页")
        logger.info(f"🎭 模式: {'FULL' if is_full_mode else 'HEAD'}")
        logger.info(f"📹 视频文件: {os.path.basename(video_file)}")
        logger.info(f"📁 输出文件: {output_file}")
        logger.info(f"📝 字幕长度: {len(subtitle_text)}字符")
        
        try:
            # 如果有字幕文本，创建字幕图像
            subtitle_path = None
            if subtitle_text and subtitle_text.strip():
                logger.info(f"📝 创建字幕图像...")
                subtitle_path = work_dir / f"subtitle_page_{page_number:03d}.png"
                
                subtitle_start = time.time()
                if not self.create_subtitle_image(subtitle_text.strip(), str(subtitle_path)):
                    logger.error(f"❌ 创建字幕图像失败")
                    return False
                subtitle_time = time.time() - subtitle_start
                logger.info(f"✅ 字幕图像创建完成，耗时: {subtitle_time:.2f}秒")
            else:
                logger.info(f"ℹ️ 无字幕文本，跳过字幕创建")
            
            if is_full_mode:
                logger.info(f"🎭 使用Full模式处理...")
                # Full模式：数字人视频 + 字幕
                if subtitle_path:
                    logger.info(f"📝 组合视频和字幕...")
                    cmd = [
                        'ffmpeg',
                        '-i', video_file,
                        '-i', str(subtitle_path),
                        '-filter_complex', 
                        '[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[video];[video][1:v]overlay=format=auto',
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'copy',
                        '-y',  # 覆盖输出文件
                        output_file
                    ]
                else:
                    logger.info(f"ℹ️ 无字幕，直接复制视频文件...")
                    # 没有字幕，直接复制视频
                    import shutil
                    shutil.copy2(video_file, output_file)
                    total_time = time.time() - start_time
                    logger.info(f"✅ Full模式处理完成！")
                    logger.info(f"⏱️ 耗时: {total_time:.2f}秒")
                    return True
            else:
                logger.info(f"🎭 使用Head模式处理...")
                # Head模式：组合幻灯片和头部视频 + 字幕
                
                # 创建圆形遮罩
                logger.info(f"🔲 创建圆形遮罩...")
                mask_path = work_dir / "circular_mask.png"
                
                mask_start = time.time()
                if not self.create_circular_mask(280, str(mask_path)):
                    logger.error(f"❌ 创建圆形遮罩失败")
                    return False
                mask_time = time.time() - mask_start
                logger.info(f"✅ 圆形遮罩创建完成，耗时: {mask_time:.2f}秒")
                
                logger.info(f"🔧 构建FFmpeg命令...")
                if subtitle_path:
                    logger.info(f"📝 组合幻灯片、视频、遮罩和字幕...")
                    # 有字幕的情况 - 优化视频叠加效果
                    cmd = [
                        'ffmpeg',
                        '-i', slide_image,
                        '-i', video_file,
                        '-i', str(mask_path),
                        '-i', str(subtitle_path),
                        '-filter_complex', 
                        '[0:v]scale=1920:1080,format=rgba,colorchannelmixer=aa=1.0[bg];[1:v]scale=280:280[fg];[2:v]alphaextract[mask];[fg][mask]alphamerge[masked_fg];[bg][masked_fg]overlay=1600:720:format=auto[with_person];[with_person][3:v]overlay=format=auto,format=yuv420p',
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'copy',
                        '-y',  # 覆盖输出文件
                        output_file
                    ]
                else:
                    logger.info(f"📐 组合幻灯片、视频和遮罩...")
                    # 没有字幕的情况 - 优化视频叠加效果
                    cmd = [
                        'ffmpeg',
                        '-i', slide_image,
                        '-i', video_file,
                        '-i', str(mask_path),
                        '-filter_complex', 
                        '[0:v]scale=1920:1080,format=rgba,colorchannelmixer=aa=1.0[bg];[1:v]scale=280:280[fg];[2:v]alphaextract[mask];[fg][mask]alphamerge[masked_fg];[bg][masked_fg]overlay=1600:720:format=auto,format=yuv420p',
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'copy',
                        '-y',  # 覆盖输出文件
                        output_file
                    ]
            
            # 执行FFmpeg命令（如果有字幕的话）
            if subtitle_path or not is_full_mode:
                logger.info(f"⚙️ 执行FFmpeg组合命令...")
                logger.debug(f"FFmpeg命令: {' '.join(cmd)}")
                
                ffmpeg_start = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True)
                ffmpeg_time = time.time() - ffmpeg_start
                
                if result.returncode == 0:
                    total_time = time.time() - start_time
                    if os.path.exists(output_file):
                        output_size = os.path.getsize(output_file)
                        logger.info(f"✅ 视频组合成功！")
                        logger.info(f"📁 输出文件: {output_file}")
                        logger.info(f"📦 文件大小: {output_size/1024/1024:.2f} MB")
                        logger.info(f"⏱️ FFmpeg耗时: {ffmpeg_time:.2f}秒")
                        logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
                        
                        if result.stdout:
                            logger.debug(f"FFmpeg输出: {result.stdout}")
                    else:
                        logger.error(f"❌ 输出文件不存在: {output_file}")
                        return False
                else:
                    total_time = time.time() - start_time
                    logger.error(f"❌ FFmpeg命令执行失败")
                    logger.error(f"📊 返回码: {result.returncode}")
                    logger.error(f"💬 错误信息: {result.stderr}")
                    logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
                    return False
            
            return True
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ 组合幻灯片和视频时发生错误: {e}")
            logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
            import traceback
            logger.error(f"📋 错误详情: {traceback.format_exc()}")
            return False