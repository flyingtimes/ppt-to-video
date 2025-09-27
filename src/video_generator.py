"""
数字人视频生成器
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from tools.runninghub_api import RunningHubAPI

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class DigitalHumanVideoGenerator:
    """数字人视频生成器"""
    
    def __init__(self):
        self.api = RunningHubAPI()
        self.config_path = "output/config.json"
        
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
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 创建默认配置
                default_config = {
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
                    "tasks": {
                        "full_videos": [],
                        "head_videos": []
                    },
                    "studio_images": {
                        "full": "",
                        "head": ""
                    },
                    "current_project": "",
                    "last_update": ""
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any] = None):
        """保存配置文件"""
        try:
            if config is None:
                config = self.config
            
            config["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 确保output目录存在
            Path("output").mkdir(exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info("配置文件保存成功")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def _should_generate_studio_image(self, mode: str) -> bool:
        """判断是否需要生成工作室效果图"""
        studio_image_path = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
        return not os.path.exists(studio_image_path)
    
    def _save_studio_image(self, mode: str, image_path: str):
        """保存工作室效果图路径"""
        try:
            if mode == "full":
                self.config["studio_images"]["full"] = image_path
                # 复制文件到models目录
                import shutil
                shutil.copy2(image_path, self.full_studio_image_path)
            else:
                self.config["studio_images"]["head"] = image_path
                # 复制文件到models目录
                import shutil
                shutil.copy2(image_path, self.head_studio_image_path)
            
            self._save_config()
            logger.info(f"工作室效果图已保存: {mode} -> {image_path}")
        except Exception as e:
            logger.error(f"保存工作室效果图失败: {e}")
    
    def _save_task_info(self, mode: str, task_info: Dict[str, Any]):
        """保存任务信息"""
        try:
            task_data = {
                "task_id": task_info.get("task_id"),
                "text": task_info.get("text"),
                "video_path": task_info.get("video_path"),
                "studio_image_path": task_info.get("studio_image_path"),
                "mode": mode,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "completed"
            }
            
            if mode == "full":
                self.config["tasks"]["full_videos"].append(task_data)
            else:
                self.config["tasks"]["head_videos"].append(task_data)
            
            self._save_config()
            logger.info(f"任务信息已保存: {mode} -> {task_info.get('task_id')}")
        except Exception as e:
            logger.error(f"保存任务信息失败: {e}")
    
    def generate_video(self, text: str, mode: str = "head", 
                      output_path: str = None) -> Optional[Dict[str, Any]]:
        """
        生成数字人视频
        
        Args:
            text: 播报文本内容
            mode: 视频模式（full/head）
            output_path: 输出路径（可选）
            
        Returns:
            生成结果信息
        """
        try:
            # 检查输入文件是否存在
            if not os.path.exists(self.character_image_path):
                logger.error(f"人物图片不存在: {self.character_image_path}")
                return None
            
            if not os.path.exists(self.reference_audio_path):
                logger.error(f"参考音频不存在: {self.reference_audio_path}")
                return None
            
            # 判断是否需要生成工作室效果图
            first_time = self._should_generate_studio_image(mode)
            
            logger.info(f"开始生成数字人视频: {mode}模式, 首次生成: {first_time}")
            
            # 生成视频
            result = self.api.generate_digital_human_video_full(
                text=text,
                character_image_path=self.character_image_path,
                reference_audio_path=self.reference_audio_path,
                mode=mode,
                first_time=first_time
            )
            
            if not result:
                logger.error("数字人视频生成失败")
                return None
            
            # 处理工作室效果图
            if first_time and result.get("studio_image_path"):
                self._save_studio_image(mode, result["studio_image_path"])
            
            # 如果指定了输出路径，移动视频文件
            video_path = result.get("video_path")
            if video_path and output_path:
                try:
                    import shutil
                    shutil.move(video_path, output_path)
                    result["video_path"] = output_path
                    logger.info(f"视频文件已移动到: {output_path}")
                except Exception as e:
                    logger.error(f"移动视频文件失败: {e}")
            
            # 保存任务信息
            self._save_task_info(mode, result)
            
            logger.info(f"数字人视频生成完成: {mode}模式")
            return result
            
        except Exception as e:
            logger.error(f"生成数字人视频时发生错误: {e}")
            return None
    
    def generate_videos_for_text(self, texts: Dict[str, str], 
                               output_dir: str) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        为多个文本生成视频
        
        Args:
            texts: 字典，key为页面标识，value为文本内容
            output_dir: 输出目录
            
        Returns:
            生成结果字典
        """
        results = {}
        
        for page_id, text in texts.items():
            logger.info(f"为页面 {page_id} 生成视频")
            
            # 判断模式（根据文本是否以[full]开头）
            mode = "full" if text.strip().startswith('[full]') else "head"
            content = text[6:].strip() if mode == "full" else text.strip()
            
            if not content:
                logger.warning(f"页面 {page_id} 文本内容为空，跳过生成")
                continue
            
            # 生成输出路径
            output_path = os.path.join(output_dir, f"video_{page_id}.mp4")
            
            # 生成视频
            result = self.generate_video(content, mode, output_path)
            results[page_id] = result
            
            # 如果生成失败，使用示例视频
            if not result:
                logger.warning(f"页面 {page_id} 视频生成失败，使用示例视频")
                example_video = "./test/full.mp4" if mode == "full" else "./test/head.mp4"
                if os.path.exists(example_video):
                    import shutil
                    shutil.copy2(example_video, output_path)
                    results[page_id] = {
                        "video_path": output_path,
                        "mode": mode,
                        "status": "fallback_to_example"
                    }
        
        return results
    
    def get_studio_image_path(self, mode: str) -> Optional[str]:
        """获取工作室效果图路径"""
        return self.config["studio_images"].get(mode)
    
    def get_task_history(self, mode: str = None) -> Dict[str, Any]:
        """获取任务历史"""
        if mode:
            return self.config["tasks"].get(f"{mode}_videos", [])
        else:
            return self.config["tasks"]
    
    def set_current_project(self, project_name: str):
        """设置当前项目"""
        self.config["current_project"] = project_name
        self._save_config()
        logger.info(f"当前项目设置为: {project_name}")