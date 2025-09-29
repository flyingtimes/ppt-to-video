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
                    "studio_images": {
                        "full": "",
                        "head": ""
                    },
                    "last_update": ""
                }
                return default_config
        except Exception as e:
            logger.error(f"加载任务状态文件失败: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any] = None):
        """保存配置到任务状态文件"""
        try:
            if config is None:
                config = self.config
            
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
    
    def _should_generate_studio_image(self, mode: str) -> bool:
        """判断是否需要生成工作室效果图"""
        # 首先检查任务状态文件中是否已保存工作室图片路径
        studio_images = self.config.get("studio_images", {})
        logger.info(f"当前配置中的studio_images: {studio_images}")
        
        saved_studio_image = studio_images.get(mode, "")
        logger.info(f"检查{mode}模式的工作室图片: {saved_studio_image}")
        
        if saved_studio_image and os.path.exists(saved_studio_image):
            logger.info(f"✅ 发现已保存的工作室图片: {mode} -> {saved_studio_image}")
            return False
        
        # 检查默认工作室图片路径
        default_studio_image = self.full_studio_image_path if mode == "full" else self.head_studio_image_path
        if os.path.exists(default_studio_image):
            logger.info(f"✅ 发现默认工作室图片: {mode} -> {default_studio_image}")
            return False
        
        logger.info(f"❌ 需要生成工作室图片: {mode}")
        return True
    
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
    
    def _save_task_info(self, mode: str, task_info: Dict[str, Any], page_number: int = None):
        """保存任务信息到JSON配置文件"""
        try:
            task_id = task_info.get("task_id")
            if not task_id:
                logger.warning("任务ID为空，跳过保存")
                return
            
            # 如果没有任务状态文件路径，则无法保存
            if not self.task_status_file_path:
                logger.warning("任务状态文件路径未设置，跳过保存")
                return
            
            # 读取现有配置文件
            if os.path.exists(self.task_status_file_path):
                with open(self.task_status_file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                logger.warning("任务状态文件不存在，跳过保存")
                return
            
            # 查找对应的任务并更新
            task_found = False
            if 'tasks' in config:
                # 如果提供了页码，优先使用页码查找
                if page_number is not None:
                    for task in config['tasks']:
                        if task.get('page_number') == page_number:
                            task['task_id'] = task_id
                            task['runninghub_task_id'] = task_id
                            
                            # 如果任务状态是失败，则保持失败状态
                            if task_info.get('status') == 'failed':
                                task['status'] = 'failed'
                                task['runninghub_status'] = 'failed'
                                task['error_message'] = task_info.get('error_message', '任务执行失败')
                                logger.info(f"✅ 失败任务ID已保存到第{page_number}页任务: {task_id}")
                            else:
                                task['status'] = 'processing'
                                task['runninghub_status'] = 'processing'
                                task['runninghub_progress'] = 0
                                logger.info(f"✅ 任务ID已保存到第{page_number}页任务: {task_id}")
                            
                            task['submit_time'] = task_info.get('submit_time', time.strftime("%Y-%m-%d %H:%M:%S"))
                            
                            # 确保metadata字段存在
                            if 'metadata' not in task:
                                task['metadata'] = {
                                    'created_at': '',
                                    'modified_at': '',
                                    'processed_by': '',
                                    'processing_version': '1.0'
                                }
                            task['metadata']['modified_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                            task_found = True
                            break
                
                # 如果没有找到且任务ID匹配，则更新
                if not task_found:
                    for task in config['tasks']:
                        if task.get('task_id') == task_id or task.get('runninghub_task_id') == task_id:
                            if task_info.get('status') == 'failed':
                                task['status'] = 'failed'
                                task['runninghub_status'] = 'failed'
                                task['error_message'] = task_info.get('error_message', '任务执行失败')
                                logger.info(f"✅ 失败任务ID已更新到现有任务: {task_id}")
                            else:
                                task['status'] = 'processing'
                                task['runninghub_status'] = 'processing'
                                task['runninghub_progress'] = 0
                                logger.info(f"✅ 任务ID已更新到现有任务: {task_id}")
                            
                            task['submit_time'] = task_info.get('submit_time', time.strftime("%Y-%m-%d %H:%M:%S"))
                            
                            # 确保metadata字段存在
                            if 'metadata' not in task:
                                task['metadata'] = {
                                    'created_at': '',
                                    'modified_at': '',
                                    'processed_by': '',
                                    'processing_version': '1.0'
                                }
                            task['metadata']['modified_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                            task_found = True
                            break
            
            if not task_found:
                logger.warning(f"未找到对应的任务来保存ID: {task_id}")
                return
            
            # 更新进度统计
            if 'progress_tracking' in config:
                tasks = config['tasks']
                completed = len([t for t in tasks if t['status'] == 'completed'])
                failed = len([t for t in tasks if t['status'] == 'failed'])
                processing = len([t for t in tasks if t['status'] == 'processing'])
                pending = len([t for t in tasks if t['status'] == 'pending'])
                
                config['progress_tracking'].update({
                    'completed_tasks': completed,
                    'failed_tasks': failed,
                    'processing_tasks': processing,
                    'pending_tasks': pending,
                    'progress_percentage': (completed / len(tasks)) * 100 if tasks else 0,
                    'last_update': time.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 保存更新后的配置
            with open(self.task_status_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 任务ID已立即保存到配置文件: {task_id}")
            
        except Exception as e:
            logger.error(f"保存任务信息失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    def generate_video(self, text: str, mode: str = "head", 
                      output_path: str = None, use_example_video: bool = False, 
                      page_number: int = None) -> Optional[Dict[str, Any]]:
        """
        生成数字人视频
        
        Args:
            text: 播报文本内容
            mode: 视频模式（full/head）
            output_path: 输出路径（可选）
            use_example_video: 是否使用示例视频（仅用于head模式）
            page_number: 页码（用于立即保存任务ID到配置文件）
            
        Returns:
            生成结果信息
        """
        start_time = time.time()
        
        logger.info(f"🎬 开始生成数字人视频")
        logger.info(f"📝 文本长度: {len(text)}字符")
        logger.info(f"🎭 视频模式: {mode.upper()}")
        logger.info(f"📁 输出路径: {output_path}")
        logger.info(f"🎬 使用示例视频: {use_example_video}")
        logger.debug(f"📄 播报内容: {text}")
        
        try:
            # 如果是head模式且指定使用示例视频，直接使用示例视频
            if mode == "head" and use_example_video:
                example_video_path = "test/head.mp4"
                if os.path.exists(example_video_path):
                    logger.info(f"✅ 使用示例视频: {example_video_path}")
                    
                    # 确保输出目录存在
                    if output_path:
                        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                        
                        logger.info(f"📁 复制示例视频到目标路径...")
                        import shutil
                        shutil.copy2(example_video_path, output_path)
                        
                        # 返回模拟的结果
                        result = {
                            "task_id": f"example_{int(time.time())}",
                            "video_path": output_path,
                            "studio_image_path": None,
                            "mode": mode,
                            "text": text
                        }
                        
                        # 保存任务信息
                        self._save_task_info(mode, result, page_number)
                        
                        total_time = time.time() - start_time
                        logger.info(f"✅ 示例视频处理完成！")
                        logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
                        logger.info(f"📁 输出文件: {output_path}")
                        return result
                    else:
                        logger.error("❌ 输出路径未指定")
                        return None
                else:
                    logger.warning(f"⚠️ 示例视频不存在: {example_video_path}，继续使用正常生成流程")
            
            # 检查输入文件是否存在
            logger.info(f"🔍 检查输入文件...")
            if not os.path.exists(self.character_image_path):
                logger.error(f"❌ 人物图片不存在: {self.character_image_path}")
                return None
            
            if not os.path.exists(self.reference_audio_path):
                logger.error(f"❌ 参考音频不存在: {self.reference_audio_path}")
                return None
            
            logger.info(f"✅ 人物图片: {self.character_image_path}")
            logger.info(f"✅ 参考音频: {self.reference_audio_path}")
            
            # 判断是否需要生成工作室效果图
            first_time = self._should_generate_studio_image(mode)
            logger.info(f"🎨 首次生成工作室效果图: {first_time}")
            
            # 创建任务ID保存回调函数
            def save_task_id_callback(task_id, mode):
                """保存任务ID到配置文件的回调函数"""
                callback_result = {
                    "task_id": task_id,
                    "mode": mode,
                    "video_path": output_path,
                    "studio_image_path": None,
                    "text": text
                }
                self._save_task_info(mode, callback_result, page_number)
            
            # 开始API调用
            api_start_time = time.time()
            logger.info(f"🌐 调用RunningHub API生成视频...")
            
            # 生成视频
            result = self.api.generate_digital_human_video_full(
                text=text,
                character_image_path=self.character_image_path,
                reference_audio_path=self.reference_audio_path,
                mode=mode,
                first_time=first_time,
                save_task_id_callback=save_task_id_callback
            )
            
            api_time = time.time() - api_start_time
            logger.info(f"⏱️ API调用耗时: {api_time:.2f}秒")
            
            if not result:
                logger.error("❌ 数字人视频生成失败")
                return None
            
            # 检查任务ID是否已经保存（通过回调函数）
            task_id = result.get("task_id")
            if task_id:
                logger.info(f"✅ 任务ID: {task_id}")
                
                # 检查任务是否失败
                if result.get("task_failed", False):
                    logger.warning(f"⚠️ 任务执行失败，但任务ID已保存")
                    # 更新任务状态为失败
                    result["status"] = "failed"
                    result["error_message"] = result.get("error_message", "任务执行失败")
                    # 保存失败状态
                    self._save_task_info(mode, result, page_number)
                    # 仍然返回结果，让调用者知道任务ID
                    return result
            else:
                logger.warning("⚠️ API返回结果中没有任务ID")
            
            # 处理工作室效果图
            if first_time and result.get("studio_image_path"):
                logger.info(f"🎨 工作室效果图已生成: {result['studio_image_path']}")
                self._save_studio_image(mode, result["studio_image_path"])
            
            # 如果指定了输出路径，移动视频文件
            video_path = result.get("video_path")
            if video_path and output_path and video_path != output_path:
                logger.info(f"📁 移动视频文件到目标路径...")
                logger.info(f"从: {video_path}")
                logger.info(f"到: {output_path}")
                
                try:
                    import shutil
                    shutil.move(video_path, output_path)
                    result["video_path"] = output_path
                    logger.info(f"✅ 视频文件移动完成")
                except Exception as e:
                    logger.error(f"❌ 移动视频文件失败: {e}")
            
            # 如果任务成功完成，更新任务状态
            if not result.get("task_failed", False) and result.get("video_path"):
                result["status"] = "completed"
                self._save_task_info(mode, result, page_number)
            
            total_time = time.time() - start_time
            logger.info(f"✅ 数字人视频生成完成！")
            logger.info(f"📁 最终输出: {result.get('video_path')}")
            logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
            
            # 如果有视频文件，记录文件大小
            if result.get("video_path") and os.path.exists(result["video_path"]):
                file_size = os.path.getsize(result["video_path"])
                logger.info(f"📦 文件大小: {file_size / 1024 / 1024:.2f} MB")
                result["file_size"] = file_size
            
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ 生成数字人视频时发生错误: {e}")
            import traceback
            logger.error(f"📋 错误详情: {traceback.format_exc()}")
            logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
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