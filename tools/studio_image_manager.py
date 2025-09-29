"""
工作室效果图管理工具
"""
import os
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from tools.runninghub_api import RunningHubAPI

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class StudioImageManager:
    """工作室效果图管理器"""
    
    def __init__(self, task_status_file_path: str = None):
        self.api = RunningHubAPI()
        self.task_status_file_path = task_status_file_path
        
        # 从环境变量获取配置
        self.character_image_path = os.getenv('CHARACTER_IMAGE_PATH', 'characters/man/input.png')
        self.reference_audio_path = os.getenv('REFERENCE_AUDIO_PATH', 'characters/man/reference.mp3')
        self.full_studio_image_path = os.getenv('FULL_STUDIO_IMAGE_PATH', 'models/full_studio_image.png')
        self.head_studio_image_path = os.getenv('HEAD_STUDIO_IMAGE_PATH', 'models/head_studio_image.png')
        
        # 确保models目录存在
        Path("models").mkdir(exist_ok=True)
        
        # 加载配置文件
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载任务状态文件"""
        try:
            if self.task_status_file_path and os.path.exists(self.task_status_file_path):
                with open(self.task_status_file_path, 'r', encoding='utf-8') as f:
                    task_status = json.load(f)
                    
                # 如果任务状态文件中没有配置信息，则初始化
                if 'runninghub_config' not in task_status:
                    task_status['runninghub_config'] = {
                        "api_key": os.getenv('RUNNINGHUB_API_KEY'),
                        "base_url": os.getenv('RUNNINGHUB_BASE_URL', 'https://www.runninghub.cn'),
                        "webapp_id": os.getenv('RUNNINGHUB_WEBAPP_ID')
                    }
                if 'character_config' not in task_status:
                    task_status['character_config'] = {
                        "image_path": self.character_image_path,
                        "reference_audio_path": self.reference_audio_path,
                        "full_studio_image_path": self.full_studio_image_path,
                        "head_studio_image_path": self.head_studio_image_path
                    }
                if 'studio_images' not in task_status:
                    task_status['studio_images'] = {
                        "full": "",
                        "head": ""
                    }
                
                return task_status
            else:
                logger.warning("任务状态文件路径未设置，使用内存配置")
                return {
                    "runninghub_config": {
                        "api_key": os.getenv('RUNNINGHUB_API_KEY'),
                        "base_url": os.getenv('RUNNINGHUB_BASE_URL', 'https://www.runninghub.cn'),
                        "webapp_id": os.getenv('RUNNINGHUB_WEBAPP_ID')
                    },
                    "character_config": {
                        "image_path": self.character_image_path,
                        "reference_audio_path": self.reference_audio_path,
                        "full_studio_image_path": self.full_studio_image_path,
                        "head_studio_image_path": self.head_studio_image_path
                    },
                    "studio_images": {
                        "full": "",
                        "head": ""
                    }
                }
        except Exception as e:
            logger.error(f"加载任务状态文件失败: {e}")
            return {}
    
    
    def _save_config(self, config: Dict[str, Any]):
        """保存配置到任务状态文件"""
        try:
            import time
            config["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.task_status_file_path:
                # 确保input目录存在
                Path(self.task_status_file_path).parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.task_status_file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                logger.info(f"任务状态文件保存成功: {self.task_status_file_path}")
            else:
                logger.warning("任务状态文件路径未设置，跳过保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def generate_studio_image(self, mode: str) -> Optional[str]:
        """
        生成工作室效果图
        
        Args:
            mode: 模式（full/head）
            
        Returns:
            工作室效果图路径，失败返回None
        """
        try:
            # 检查输入文件
            if not os.path.exists(self.character_image_path):
                logger.error(f"人物图片不存在: {self.character_image_path}")
                return None
            
            if not os.path.exists(self.reference_audio_path):
                logger.error(f"参考音频不存在: {self.reference_audio_path}")
                return None
            
            logger.info(f"开始生成{mode}模式工作室效果图")
            
            # 生成工作室效果图
            result = self.api.generate_digital_human_video_full(
                text="这是一个测试文本，用于生成工作室效果图。",
                character_image_path=self.character_image_path,
                reference_audio_path=self.reference_audio_path,
                mode=mode,
                first_time=True
            )
            
            if not result:
                logger.error(f"{mode}模式工作室效果图生成失败")
                return None
            
            # 获取工作室效果图路径
            studio_image_path = result.get("studio_image_path")
            if not studio_image_path:
                logger.error(f"未获取到{mode}模式工作室效果图")
                return None
            
            # 复制到models目录
            target_path = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
            shutil.copy2(studio_image_path, target_path)
            
            # 更新配置文件
            self.config["studio_images"][mode] = target_path
            self._save_config(self.config)
            
            logger.info(f"{mode}模式工作室效果图生成完成: {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"生成{mode}模式工作室效果图时发生错误: {e}")
            return None
    
    def generate_all_studio_images(self) -> Dict[str, Optional[str]]:
        """
        生成所有模式的工作室效果图
        
        Returns:
            包含各模式结果的字典
        """
        results = {}
        
        for mode in ["full", "head"]:
            logger.info(f"生成{mode}模式工作室效果图...")
            result = self.generate_studio_image(mode)
            results[mode] = result
            
            # 如果生成失败，检查是否已存在
            if not result:
                existing_path = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
                if os.path.exists(existing_path):
                    logger.info(f"使用已存在的{mode}模式工作室效果图: {existing_path}")
                    results[mode] = existing_path
        
        return results
    
    def get_studio_image_path(self, mode: str) -> Optional[str]:
        """
        获取工作室效果图路径
        
        Args:
            mode: 模式（full/head）
            
        Returns:
            工作室效果图路径，不存在返回None
        """
        target_path = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
        
        if os.path.exists(target_path):
            return target_path
        
        return None
    
    def check_studio_images(self) -> Dict[str, bool]:
        """
        检查工作室效果图是否存在
        
        Returns:
            包含各模式存在状态的字典
        """
        return {
            "full": os.path.exists(self.full_studio_image_path),
            "head": os.path.exists(self.head_studio_image_path)
        }
    
    def regenerate_studio_image(self, mode: str) -> Optional[str]:
        """
        重新生成工作室效果图
        
        Args:
            mode: 模式（full/head）
            
        Returns:
            新的工作室效果图路径，失败返回None
        """
        try:
            # 删除现有的工作室效果图
            target_path = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
            if os.path.exists(target_path):
                os.remove(target_path)
                logger.info(f"删除现有的{mode}模式工作室效果图: {target_path}")
            
            # 生成新的工作室效果图
            return self.generate_studio_image(mode)
            
        except Exception as e:
            logger.error(f"重新生成{mode}模式工作室效果图时发生错误: {e}")
            return None
    
    def get_studio_image_info(self) -> Dict[str, Any]:
        """
        获取工作室效果图信息
        
        Returns:
            包含工作室效果图信息的字典
        """
        info = {
            "config": {
                "full": self.full_studio_image_path,
                "head": self.head_studio_image_path
            },
            "exists": self.check_studio_images(),
            "config_file": self.config_path
        }
        
        # 添加文件大小信息
        for mode in ["full", "head"]:
            path = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
            if os.path.exists(path):
                stat = os.stat(path)
                info[f"{mode}_size"] = stat.st_size
                info[f"{mode}_modified"] = stat.st_mtime
            else:
                info[f"{mode}_size"] = 0
                info[f"{mode}_modified"] = 0
        
        return info