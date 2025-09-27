"""
测试数字人视频生成功能
"""
import os
import logging
from pathlib import Path
from src.video_generator import DigitalHumanVideoGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_video_generation():
    """测试视频生成功能"""
    logger.info("开始测试数字人视频生成功能")
    
    try:
        # 初始化视频生成器
        generator = DigitalHumanVideoGenerator()
        
        # 测试文本
        test_text = "大家好，今天我来为大家介绍一下这个项目。这是一个非常重要的项目，它能够帮助我们提高工作效率。"
        
        # 测试生成全身视频
        logger.info("测试生成全身视频...")
        full_result = generator.generate_video(
            text=test_text,
            mode="full",
            output_path="outputs/test_full_video.mp4"
        )
        
        if full_result:
            logger.info(f"全身视频生成成功: {full_result.get('video_path')}")
        else:
            logger.warning("全身视频生成失败")
        
        # 测试生成头部视频
        logger.info("测试生成头部视频...")
        head_result = generator.generate_video(
            text=test_text,
            mode="head",
            output_path="outputs/test_head_video.mp4"
        )
        
        if head_result:
            logger.info(f"头部视频生成成功: {head_result.get('video_path')}")
        else:
            logger.warning("头部视频生成失败")
        
        # 显示工作室效果图状态
        studio_status = generator.get_studio_image_path("full")
        logger.info(f"全身工作室效果图: {studio_status}")
        
        studio_status = generator.get_studio_image_path("head")
        logger.info(f"头部工作室效果图: {studio_status}")
        
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")


if __name__ == "__main__":
    test_video_generation()