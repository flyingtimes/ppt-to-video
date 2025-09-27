"""
测试简单的任务来查看失败原因
"""
import os
import logging
from tools.runninghub_api import RunningHubAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_simple_task():
    """测试简单任务"""
    logger.info("开始测试简单任务")
    
    try:
        api = RunningHubAPI()
        
        # 测试文本
        test_text = "测试"
        
        # 获取文件hash
        character_image = os.getenv('CHARACTER_IMAGE_PATH', 'characters/man/input.png')
        reference_audio = os.getenv('REFERENCE_AUDIO_PATH', 'characters/man/reference.mp3')
        
        image_hash = api._get_file_hash(character_image)
        audio_hash = api._get_file_hash(reference_audio)
        
        logger.info(f"图片hash: {image_hash}")
        logger.info(f"音频hash: {audio_hash}")
        
        # 构建简化的请求
        request_data = {
            "webappId": api.webapp_id,
            "apiKey": api.api_key,
            "nodeInfoList": [
                {
                    "nodeId": "55",
                    "fieldName": "value",
                    "fieldValue": "2",  # 不需要修图
                    "description": "是否需要自动修图"
                },
                {
                    "nodeId": "54",
                    "fieldName": "value",
                    "fieldValue": "2",  # 肖像模式
                    "description": "1:全身 2: 肖像"
                },
                {
                    "nodeId": "48",
                    "fieldName": "image",
                    "fieldValue": image_hash,
                    "description": "人物图片"
                },
                {
                    "nodeId": "47",
                    "fieldName": "audio",
                    "fieldValue": audio_hash,
                    "description": "参考音频"
                },
                {
                    "nodeId": "38",
                    "fieldName": "text",
                    "fieldValue": test_text,
                    "description": "要说的话"
                }
            ]
        }
        
        logger.info("发送简化的请求...")
        logger.info(f"请求数据: {request_data}")
        
        response = requests.post(
            f"{api.base_url}/task/openapi/ai-app/run",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        logger.info(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"响应内容: {result}")
            
            if result.get('code') == 0:
                task_data = result.get('data', {})
                task_id = task_data.get('taskId')
                logger.info(f"任务ID: {task_id}")
                
                # 等待任务完成
                api.wait_for_task_completion(task_id, timeout=120)
            else:
                logger.error(f"请求失败: {result.get('msg')}")
        else:
            logger.error(f"请求失败: {response.text}")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import requests
    test_simple_task()