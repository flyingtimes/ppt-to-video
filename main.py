"""
PPT转视频项目 - 主程序入口
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from src.ppt_reader import PPTReader
from src.video_processor import VideoProcessor
from src.file_manager import FileManager

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ppt_to_video.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主程序入口"""
    logger.info("开始PPT转视频处理")
    
    # 初始化文件管理器
    file_manager = FileManager()
    
    # 获取输入文件夹中的PPT文件
    ppt_files = file_manager.get_ppt_files()
    if not ppt_files:
        logger.error("输入文件夹中没有找到PPT文件")
        return
    
    # 初始化PPT读取器
    ppt_reader = PPTReader()
    
    # 初始化视频处理器
    video_processor = VideoProcessor()
    
    # 处理每个PPT文件
    for ppt_file in ppt_files:
        logger.info(f"开始处理文件: {ppt_file}")
        
        try:
            # 读取PPT和PDF内容
            ppt_content = ppt_reader.read_ppt(ppt_file)
            if not ppt_content:
                logger.error(f"无法读取PPT文件: {ppt_file}")
                continue
            
            # 创建工作文件夹
            work_dir = file_manager.create_work_dir(ppt_file)
            
            # 按页码组织内容
            pages_content = file_manager.organize_pages_content(ppt_content, work_dir)
            
            # 生成每一页的视频
            page_videos = []
            for page_num, page_data in enumerate(pages_content, 1):
                logger.info(f"处理第 {page_num} 页")
                
                # 生成单页视频
                page_video = video_processor.process_page(page_data, page_num, work_dir)
                if page_video:
                    page_videos.append(page_video)
            
            # 合并所有页面视频
            if page_videos:
                output_video = video_processor.merge_videos(page_videos, work_dir)
                if output_video:
                    logger.info(f"视频生成完成: {output_video}")
            
        except Exception as e:
            logger.error(f"处理文件 {ppt_file} 时出错: {e}")
            continue
    
    logger.info("PPT转视频处理完成")


if __name__ == "__main__":
    main()