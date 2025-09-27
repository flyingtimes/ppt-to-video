"""
测试完整的数字人视频生成流程
"""
import os
import logging
import time
from pathlib import Path
from src.video_generator import DigitalHumanVideoGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_complete_video_generation():
    """测试完整的数字人视频生成流程"""
    logger.info("开始测试完整的数字人视频生成流程")
    
    try:
        # 初始化视频生成器
        generator = DigitalHumanVideoGenerator()
        
        # 测试文本
        test_texts = {
            "full": "[full]大家好，今天我来为大家介绍一下这个重要的项目。这个项目能够帮助我们提高工作效率，节省时间和成本。",
            "head": "接下来我们来看一下具体的实施方案。这个方案包含了详细的步骤和时间安排。"
        }
        
        # 测试生成两种模式的视频
        for mode, text in test_texts.items():
            logger.info(f"\n=== 测试{mode.upper()}模式 ===")
            
            # 移除[full]前缀（如果有）
            content = text[6:] if text.startswith('[full]') else text
            
            # 生成视频
            output_path = f"outputs/test_{mode}_video_complete.mp4"
            
            logger.info(f"开始生成{mode}模式视频...")
            result = generator.generate_video(
                text=content,
                mode=mode,
                output_path=output_path
            )
            
            if result:
                logger.info(f"{mode.upper()}模式视频生成成功！")
                logger.info(f"任务ID: {result.get('task_id')}")
                logger.info(f"视频路径: {result.get('video_path')}")
                logger.info(f"工作室效果图: {result.get('studio_image_path')}")
                
                # 检查文件是否存在
                if result.get('video_path') and os.path.exists(result['video_path']):
                    file_size = os.path.getsize(result['video_path'])
                    logger.info(f"视频文件大小: {file_size / 1024 / 1024:.2f} MB")
                
            else:
                logger.warning(f"{mode.upper()}模式视频生成失败")
        
        # 显示工作室效果图状态
        logger.info(f"\n=== 工作室效果图状态 ===")
        
        full_studio = generator.get_studio_image_path("full")
        head_studio = generator.get_studio_image_path("head")
        
        logger.info(f"全身工作室效果图: {full_studio}")
        logger.info(f"头部工作室效果图: {head_studio}")
        
        # 显示任务历史
        logger.info(f"\n=== 任务历史 ===")
        
        full_history = generator.get_task_history("full")
        head_history = generator.get_task_history("head")
        
        logger.info(f"全身模式任务数: {len(full_history)}")
        logger.info(f"头部模式任务数: {len(head_history)}")
        
        if full_history:
            latest_full = full_history[-1]
            logger.info(f"最新全身任务: {latest_full.get('task_id')} - {latest_full.get('timestamp')}")
        
        if head_history:
            latest_head = head_history[-1]
            logger.info(f"最新头部任务: {latest_head.get('task_id')} - {latest_head.get('timestamp')}")
        
        logger.info(f"\n=== 配置文件信息 ===")
        config_info = generator.video_generator.api.__dict__ if hasattr(generator, 'video_generator') else {}
        logger.info(f"API Key: {generator.api.api_key[:10] if generator.api.api_key else '未设置'}...")
        logger.info(f"Base URL: {generator.api.base_url}")
        logger.info(f"WebApp ID: {generator.api.webapp_id}")
        
        logger.info(f"\n测试完成！")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_complete_video_generation()