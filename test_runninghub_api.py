"""
测试RunningHub API连接和文件上传功能
"""
import os
import logging
from pathlib import Path
from tools.runninghub_api import RunningHubAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_runninghub_api():
    """测试RunningHub API功能"""
    logger.info("开始测试RunningHub API功能")
    
    try:
        # 初始化API客户端
        api = RunningHubAPI()
        
        # 检查配置
        logger.info(f"API Key: {api.api_key[:10]}..." if api.api_key else "API Key: 未设置")
        logger.info(f"Base URL: {api.base_url}")
        logger.info(f"WebApp ID: {api.webapp_id}")
        
        # 检查必要的文件
        character_image = os.getenv('CHARACTER_IMAGE_PATH', 'characters/man/input.png')
        reference_audio = os.getenv('REFERENCE_AUDIO_PATH', 'characters/man/reference.mp3')
        
        logger.info(f"人物图片路径: {character_image}")
        logger.info(f"参考音频路径: {reference_audio}")
        
        # 检查文件是否存在
        if not os.path.exists(character_image):
            logger.error(f"人物图片不存在: {character_image}")
            return
        
        if not os.path.exists(reference_audio):
            logger.error(f"参考音频不存在: {reference_audio}")
            return
        
        # 测试文件hash计算
        logger.info("测试文件hash计算功能...")
        
        # 计算图片hash
        image_hash = api._get_file_hash(character_image)
        if image_hash:
            logger.info(f"图片hash计算成功: {image_hash}")
        else:
            logger.error("图片hash计算失败")
            return
        
        # 计算音频hash
        audio_hash = api._get_file_hash(reference_audio)
        if audio_hash:
            logger.info(f"音频hash计算成功: {audio_hash}")
        else:
            logger.error("音频hash计算失败")
            return
        
        # 测试生成数字人视频
        logger.info("测试生成数字人视频...")
        
        test_text = "大家好，今天我来为大家介绍一下这个项目。"
        
        result = api.generate_digital_human_video(
            text=test_text,
            character_image_path=character_image,
            reference_audio_path=reference_audio,
            mode="head",
            first_time=True
        )
        
        if result:
            task_id = result.get('taskId')
            logger.info(f"数字人视频生成请求成功，任务ID: {task_id}")
            
            # 测试查询任务状态
            logger.info("测试查询任务状态...")
            status = api.get_task_status(task_id)
            logger.info(f"任务状态: {status}")
            
        else:
            logger.error("数字人视频生成请求失败")
        
        logger.info("API测试完成")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_runninghub_api()