#!/usr/bin/env python3
"""
视频合并脚本
用于将分镜头视频合并成一个完整的视频文件
"""
import os
import sys
import logging
from pathlib import Path
import time

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from video_processor import VideoProcessor

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

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("🎬 开始视频合并流程")
    logger.info("=" * 50)
    
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
            video_files.append(str(video_file))
        
        if not video_files:
            logger.error("❌ 在outputs目录中未找到任何视频文件")
            return False
        
        logger.info(f"📹 找到 {len(video_files)} 个分镜头视频文件:")
        for i, video_file in enumerate(video_files, 1):
            file_size = os.path.getsize(video_file)
            logger.info(f"   {i}. {os.path.basename(video_file)} ({file_size/1024/1024:.2f} MB)")
        
        # 创建视频处理器
        processor = VideoProcessor()
        
        # 合并视频
        logger.info(f"🔧 开始合并视频...")
        merged_video_path = processor.merge_videos(video_files, outputs_dir)
        
        if merged_video_path:
            total_time = time.time() - start_time
            file_size = os.path.getsize(merged_video_path)
            
            logger.info("=" * 50)
            logger.info("✅ 视频合并完成！")
            logger.info(f"📁 输出文件: {merged_video_path}")
            logger.info(f"📦 文件大小: {file_size/1024/1024:.2f} MB")
            logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
            logger.info("=" * 50)
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

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)