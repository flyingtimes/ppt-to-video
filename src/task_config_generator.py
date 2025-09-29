"""
完整的任务配置文件生成器
在处理PDF材料时创建完整的初始配置文件
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskConfigGenerator:
    """任务配置文件生成器"""
    
    def __init__(self):
        self.supported_formats = ['.pptx', '.ppt']
    
    def generate_complete_config(self, ppt_file: str, pdf_file: str, 
                                ppt_content: List[Dict[str, Any]], 
                                pdf_pages: List[str]) -> Dict[str, Any]:
        """
        生成完整的任务配置文件
        
        Args:
            ppt_file: PPT文件路径
            pdf_file: PDF文件路径
            ppt_content: PPT内容列表
            pdf_pages: PDF页面图片路径列表
            
        Returns:
            完整的任务配置字典
        """
        project_name = Path(ppt_file).stem
        
        # 生成任务列表
        tasks = []
        for i, slide_data in enumerate(ppt_content):
            notes = slide_data.get('notes_text', '').strip()
            mode = "full" if slide_data.get('is_full_mode', False) else "head"
            
            task = {
                "page_number": i + 1,
                "notes": notes,
                "mode": mode,
                "task_id": "",
                "status": "pending",
                "video_path": f"outputs/video_page_{i+1:03d}_{mode}.mp4",
                "retry_count": 0,
                "submit_time": "",
                "complete_time": "",
                "pdf_page_path": pdf_pages[i] if i < len(pdf_pages) else "",
                "ppt_slide_path": "",
                "audio_path": "",
                "subtitle_path": "",
                "thumbnail_path": "",
                "error_message": "",
                "processing_time": 0,
                "file_size": 0,
                "resolution": "",
                "duration": 0,
                "runninghub_task_id": "",
                "runninghub_status": "",
                "runninghub_progress": 0,
                "studio_image_used": "",
                "character_position": "",
                "background_color": "",
                "text_overlay": "",
                "watermark": "",
                "metadata": {
                    "created_at": "",
                    "modified_at": "",
                    "processed_by": "",
                    "processing_version": "1.0"
                }
            }
            tasks.append(task)
        
        # 完整的配置结构
        complete_config = {
            "project_info": {
                "project_name": project_name,
                "description": f"基于PPT文件 {project_name} 的数字人视频生成项目",
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat(),
                "version": "1.0",
                "processing_status": "initialized"
            },
            
            "file_paths": {
                "ppt_file": ppt_file,
                "pdf_file": pdf_file,
                "input_directory": str(Path(ppt_file).parent),
                "output_directory": "outputs",
                "temp_directory": "temp",
                "log_file": "ppt_to_video.log",
                "config_file": f"input/{project_name}.json"
            },
            
            "processing_config": {
                "total_pages": len(ppt_content),
                "pages_with_notes": len([t for t in tasks if t["notes"]]),
                "head_mode_tasks": len([t for t in tasks if t["mode"] == "head"]),
                "full_mode_tasks": len([t for t in tasks if t["mode"] == "full"]),
                "batch_size": 1,
                "max_retries": 3,
                "timeout_per_task": 3600,
                "check_interval": 20,
                "combine_videos": True,
                "generate_thumbnails": True,
                "generate_subtitles": True
            },
            
            "tasks": tasks,
            
            "runninghub_config": {
                "api_key": os.getenv('RUNNINGHUB_API_KEY'),
                "base_url": os.getenv('RUNNINGHUB_BASE_URL', 'https://www.runninghub.cn'),
                "webapp_id": os.getenv('RUNNINGHUB_WEBAPP_ID'),
                "endpoint": "/api/v1/video/generate",
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 5
            },
            
            "character_config": {
                "image_path": os.getenv('CHARACTER_IMAGE_PATH', 'characters/man/input.png'),
                "reference_audio_path": os.getenv('REFERENCE_AUDIO_PATH', 'characters/man/reference.mp3'),
                "full_studio_image_path": os.getenv('FULL_STUDIO_IMAGE_PATH', 'models/full_studio_image.png'),
                "head_studio_image_path": os.getenv('HEAD_STUDIO_IMAGE_PATH', 'models/head_studio_image.png'),
                "character_scale": 1.0,
                "character_position": "center",
                "background_blur": 0,
                "lighting_adjustment": 1.0
            },
            
            "studio_images": {
                "full": "",
                "head": "",
                "generated_at": "",
                "image_quality": "high",
                "resolution": "1920x1080",
                "format": "png"
            },
            
            "video_settings": {
                "resolution": "1920x1080",
                "fps": 30,
                "bitrate": "5000k",
                "codec": "h264",
                "audio_codec": "aac",
                "audio_bitrate": "128k",
                "format": "mp4",
                "quality": "high",
                "subtitle_enabled": True,
                "subtitle_font": "Arial",
                "subtitle_size": 24,
                "subtitle_color": "#FFFFFF",
                "subtitle_position": "bottom",
                "watermark_enabled": False,
                "watermark_text": "",
                "watermark_position": "bottom-right",
                "watermark_opacity": 0.5
            },
            
            "output_settings": {
                "final_video_path": f"outputs/{project_name}_final_video.mp4",
                "thumbnail_path": f"outputs/{project_name}_thumbnail.png",
                "preview_path": f"outputs/{project_name}_preview.mp4",
                "metadata_path": f"outputs/{project_name}_metadata.json",
                "log_path": f"outputs/{project_name}_processing.log",
                "backup_enabled": True,
                "backup_path": f"outputs/{project_name}_backup",
                "compression_enabled": True,
                "compression_level": "medium"
            },
            
            "progress_tracking": {
                "total_tasks": len([t for t in tasks if t["notes"]]),
                "completed_tasks": 0,
                "failed_tasks": 0,
                "processing_tasks": 0,
                "pending_tasks": len([t for t in tasks if t["notes"]]),
                "start_time": datetime.now().isoformat(),
                "end_time": "",
                "estimated_completion_time": "",
                "progress_percentage": 0,
                "average_task_time": 0,
                "total_processing_time": 0,
                "last_update": datetime.now().isoformat(),
                "current_task_index": -1,
                "status": "initialized"
            },
            
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 5,
                "timeout_threshold": 3600,
                "error_log_path": f"outputs/{project_name}_errors.log",
                "fallback_strategy": "skip",
                "notification_enabled": False,
                "notification_email": "",
                "notification_webhook": ""
            },
            
            "system_info": {
                "python_version": "",
                "platform": "",
                "cpu_count": 0,
                "memory_total": 0,
                "disk_space_free": 0,
                "gpu_available": False,
                "gpu_memory": 0,
                "dependencies": {
                    "python-pptx": "",
                    "pdf2image": "",
                    "requests": "",
                    "opencv-python": "",
                    "moviepy": "",
                    "pillow": ""
                }
            },
            
            "metadata": {
                "author": "",
                "organization": "",
                "department": "",
                "project_type": "presentation_to_video",
                "content_category": "",
                "target_audience": "",
                "language": "zh-CN",
                "region": "CN",
                "timezone": "Asia/Shanghai",
                "tags": [],
                "keywords": []
            }
        }
        
        return complete_config
    
    def save_config(self, config: Dict[str, Any], config_path: str) -> bool:
        """保存配置文件"""
        try:
            # 确保目录存在
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"💾 保存完整配置文件到: {config_path}")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 配置文件保存成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存配置文件失败: {e}")
            return False
    
    def update_config_progress(self, config: Dict[str, Any], task_index: int, 
                             status: str, additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """更新配置文件的进度"""
        try:
            if task_index < 0 or task_index >= len(config["tasks"]):
                logger.error(f"任务索引超出范围: {task_index}")
                return config
            
            # 更新任务状态
            task = config["tasks"][task_index]
            task["status"] = status
            task["metadata"]["modified_at"] = datetime.now().isoformat()
            
            if additional_info:
                task.update(additional_info)
            
            # 更新总体进度
            progress = config["progress_tracking"]
            completed = len([t for t in config["tasks"] if t["status"] == "completed"])
            failed = len([t for t in config["tasks"] if t["status"] == "failed"])
            processing = len([t for t in config["tasks"] if t["status"] == "processing"])
            pending = len([t for t in config["tasks"] if t["status"] == "pending"])
            
            progress["completed_tasks"] = completed
            progress["failed_tasks"] = failed
            progress["processing_tasks"] = processing
            progress["pending_tasks"] = pending
            progress["progress_percentage"] = (completed / len(config["tasks"])) * 100 if config["tasks"] else 0
            progress["last_update"] = datetime.now().isoformat()
            progress["current_task_index"] = task_index
            
            # 更新项目状态
            if completed == len(config["tasks"]):
                progress["status"] = "completed"
                progress["end_time"] = datetime.now().isoformat()
                config["project_info"]["processing_status"] = "completed"
            elif failed > 0:
                progress["status"] = "partial_completed"
                config["project_info"]["processing_status"] = "partial_completed"
            elif processing > 0:
                progress["status"] = "processing"
                config["project_info"]["processing_status"] = "processing"
            else:
                progress["status"] = "pending"
                config["project_info"]["processing_status"] = "pending"
            
            config["project_info"]["modified_at"] = datetime.now().isoformat()
            
            return config
            
        except Exception as e:
            logger.error(f"❌ 更新配置进度失败: {e}")
            return config