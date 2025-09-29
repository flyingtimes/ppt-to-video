#!/usr/bin/env python3
"""
分镜头视频合并脚本
使用真实生成的数字人视频，保留圆形遮罩效果
"""
import os
import sys
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from video_processor import VideoProcessor
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    try:
        from pdf2image import convert_from_path
        HAS_FITZ = False
    except ImportError:
        HAS_FITZ = False

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ppt_to_video.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_page_info_from_filename(filename: str) -> Dict[str, Any]:
    """从文件名获取页面信息"""
    # 文件名格式: video_page_XXX_mode.mp4
    base_name = os.path.basename(filename)
    parts = base_name.replace('.mp4', '').split('_')
    
    page_info = {
        'page_number': int(parts[2]),
        'mode': parts[3],  # 'full' 或 'head'
        'video_file': filename,
        'slide_image': '',
        'notes_file': '',
        'notes_text': ''
    }
    
    # 查找对应的幻灯片图片和备注文件
    page_num = page_info['page_number']
    outputs_dir = Path(filename).parent
    
    # 查找幻灯片图片（在temp目录下）
    temp_dir = Path("temp")
    
    # 尝试两种格式：page_5.png 和 page_005.png
    slide_patterns = [
        f"page_{page_num}.png",           # page_5.png
        f"page_{page_num:03d}.png"        # page_005.png
    ]
    
    for pattern in slide_patterns:
        slide_path = temp_dir / pattern
        if slide_path.exists():
            page_info['slide_image'] = str(slide_path)
            break
    
    # 查找备注文件
    notes_pattern = f"page_{page_num:03d}_notes.txt"
    notes_path = outputs_dir / notes_pattern
    if notes_path.exists():
        page_info['notes_file'] = str(notes_path)
        try:
            with open(notes_path, 'r', encoding='utf-8') as f:
                page_info['notes_text'] = f.read().strip()
        except Exception as e:
            logging.warning(f"读取备注文件失败: {e}")
    
    return page_info

def recapture_pdf_page(page_num: int) -> Optional[str]:
    """
    重新截取PDF指定页面的图片

    Args:
        page_num: 页码

    Returns:
        图片文件路径或None
    """
    logger = logging.getLogger(__name__)

    if not HAS_FITZ:
        logger.error("缺少必要的PDF处理库，请安装PyMuPDF: pip install PyMuPDF")
        return None

    try:
        # 查找input目录下的PDF文件
        input_dir = Path("input")
        if not input_dir.exists():
            logger.error("input目录不存在")
            return None

        # 查找PDF文件
        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error("input目录中未找到PDF文件")
            return None

        # 使用第一个找到的PDF文件
        pdf_file = pdf_files[0]
        logger.info(f"使用PDF文件: {pdf_file}")

        # 打开PDF文件
        doc = fitz.open(str(pdf_file))

        # 检查页码是否有效
        if page_num < 1 or page_num > len(doc):
            logger.error(f"页码 {page_num} 超出范围 (1-{len(doc)})")
            doc.close()
            return None

        # 创建temp目录
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        # 获取指定页面
        page = doc[page_num - 1]

        # 渲染页面为图片
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍分辨率

        # 保存图片
        image_path = temp_dir / f"page_{page_num}.png"
        pix.save(str(image_path))

        # 关闭PDF文件
        doc.close()

        logger.info(f"成功保存第{page_num}页幻灯片图片到: {image_path}")
        return str(image_path)

    except Exception as e:
        logger.error(f"重新截取PDF第{page_num}页失败: {e}")
        return None

def merge_videos_with_real_digital_human():
    """使用真实生成的数字人视频合并分镜头视频"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("开始分镜头视频合并流程")
    logger.info("使用真实生成的数字人视频，保留圆形遮罩效果")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # 查找outputs目录中的所有视频文件
        outputs_dir = Path("outputs")
        if not outputs_dir.exists():
            logger.error(f"❌ outputs目录不存在: {outputs_dir}")
            return False
        
        # 查找所有视频文件，按页码排序
        video_files = []
        for video_file in sorted(outputs_dir.glob("video_page_*.mp4")):
            # 检查文件是否存在且大小大于0
            if video_file.exists() and video_file.stat().st_size > 0:
                video_files.append(str(video_file))
            else:
                logger.warning(f"⚠️ 视频文件为空或不存在: {video_file}")
        
        if not video_files:
            logger.error("❌ 在outputs目录中未找到任何视频文件")
            return False
        
        logger.info(f"📹 找到 {len(video_files)} 个分镜头视频文件:")
        
        # 获取每个视频文件的信息
        page_infos = []
        for i, video_file in enumerate(video_files, 1):
            file_size = os.path.getsize(video_file)
            page_info = get_page_info_from_filename(video_file)
            page_infos.append(page_info)
            
            mode_text = "全屏" if page_info['mode'] == 'full' else "头部"
            logger.info(f"   {i}. 第{page_info['page_number']}页 ({mode_text}模式) - {os.path.basename(video_file)} ({file_size/1024/1024:.2f} MB)")
        
        # 创建工作目录
        work_dir = outputs_dir / "merge_temp"
        work_dir.mkdir(exist_ok=True)
        
        # 创建视频处理器
        processor = VideoProcessor()
        
        # 重新处理每个页面，使用真实生成的数字人视频
        logger.info(f"🔄 开始重新处理每个页面...")
        processed_videos = []
        
        for page_info in page_infos:
            page_start = time.time()
            page_num = page_info['page_number']
            is_full_mode = page_info['mode'] == 'full'
            
            logger.info(f"📄 处理第{page_num}页 ({'FULL' if is_full_mode else 'HEAD'}模式)...")
            
            # 生成输出文件路径
            output_file = work_dir / f"processed_page_{page_num:03d}.mp4"
            page_info['video_file'] = str(output_file)
            
            # 查找真实生成的数字人视频
            original_video = None
            for video_file in video_files:
                if f"video_page_{page_num:03d}_{page_info['mode']}" in video_file:
                    original_video = video_file
                    break
            
            if not original_video:
                logger.error(f"❌ 找不到第{page_num}页的原始视频文件")
                continue
            
            # 处理视频组合
            if is_full_mode:
                # Full模式：数字人视频 + 字幕
                success = processor.combine_slide_with_video(
                    "",  # 不需要slide_image
                    original_video,
                    True,  # Full模式
                    str(output_file),
                    work_dir,
                    page_info['notes_text'],
                    page_num
                )
            else:
                # Head模式：组合PPT幻灯片和头部数字人视频 + 字幕
                if not page_info['slide_image']:
                    logger.warning(f"⚠️ 第{page_num}页没有找到幻灯片图片，尝试重新截取PDF...")

                    # 尝试重新截取PDF图片
                    slide_image = recapture_pdf_page(page_num)
                    if slide_image:
                        page_info['slide_image'] = slide_image
                        logger.info(f"✅ 成功重新截取第{page_num}页幻灯片图片")
                    else:
                        logger.error(f"❌ 第{page_num}页重新截取PDF失败，跳过")
                        continue

                success = processor.combine_slide_with_video(
                    page_info['slide_image'],
                    original_video,
                    False,  # Head模式
                    str(output_file),
                    work_dir,
                    page_info['notes_text'],
                    page_num
                )
            
            if success and output_file.exists():
                processed_videos.append(str(output_file))
                page_time = time.time() - page_start
                logger.info(f"✅ 第{page_num}页处理完成，耗时: {page_time:.2f}秒")
            else:
                logger.error(f"❌ 第{page_num}页处理失败")
        
        if not processed_videos:
            logger.error("❌ 没有成功处理任何页面")
            return False
        
        logger.info(f"✅ 成功处理 {len(processed_videos)} 个页面")
        
        # 合并所有处理后的视频
        logger.info(f"🔧 开始合并所有处理后的视频...")
        logger.info(f"📋 待合并视频文件: {processed_videos}")
        merged_video_path = processor.merge_videos(processed_videos, outputs_dir)
        
        if merged_video_path:
            total_time = time.time() - start_time
            file_size = os.path.getsize(merged_video_path)
            
            logger.info("=" * 60)
            logger.info("🎉 视频合并完成！")
            logger.info(f"📁 输出文件: {merged_video_path}")
            logger.info(f"📦 文件大小: {file_size/1024/1024:.2f} MB")
            logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
            logger.info("=" * 60)
            
            # 清理临时文件
            logger.info(f"🧹 清理临时文件...")
            import shutil
            if work_dir.exists():
                shutil.rmtree(work_dir)
                logger.info(f"✅ 临时文件清理完成")
            
            return True
        else:
            logger.error("❌ 视频合并失败")
            return False
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"❌ 合并过程中发生错误: {e}")
        logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
        import traceback
        logger.error(f"📋 错误详情: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    setup_logging()
    
    success = merge_videos_with_real_digital_human()
    
    if success:
        logger = logging.getLogger(__name__)
        logger.info("🎯 视频合并任务成功完成！")
    else:
        logger = logging.getLogger(__name__)
        logger.error("💥 视频合并任务失败！")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)