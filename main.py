"""
PPT转视频项目 - 主程序入口
支持RunningHub任务监控和自动视频生成
"""
import os
import json
import time
import logging
import shutil
import tempfile
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from dotenv import load_dotenv

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    try:
        from pdf2image import convert_from_path
        HAS_FITZ = False
    except ImportError:
        HAS_FITZ = False

from src.ppt_reader import PPTReader
from src.video_processor import VideoProcessor
from src.video_generator import DigitalHumanVideoGenerator
from src.file_manager import FileManager
from src.task_config_generator import TaskConfigGenerator
from tools.runninghub_api import RunningHubAPI

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


class TaskManager:
    """任务管理器 - 负责RunningHub任务的提交和监控"""
    
    def __init__(self):
        self.video_generator = DigitalHumanVideoGenerator()
        self.runninghub_api = RunningHubAPI()
        self.task_config_generator = TaskConfigGenerator()
        self.task_status_file = None  # 将在处理PPT文件时设置
        self.check_interval = 20  # 每20秒检查一次
        
        # 确保输出目录存在
        Path("outputs").mkdir(exist_ok=True)
        Path("input").mkdir(exist_ok=True)
        Path("temp").mkdir(exist_ok=True)
        
        # 尝试自动设置任务状态文件
        self._auto_detect_task_status_file()
    
    def _auto_detect_task_status_file(self):
        """自动检测任务状态文件"""
        try:
            input_folder = Path("input")
            if input_folder.exists():
                # 查找input文件夹中的JSON文件
                json_files = list(input_folder.glob("*.json"))
                if json_files:
                    # 找到最新的JSON文件
                    latest_json = max(json_files, key=lambda f: f.stat().st_mtime)
                    self.task_status_file = latest_json
                    logger.info(f"📂 自动检测到任务状态文件: {latest_json}")
        except Exception as e:
            logger.warning(f"⚠️ 自动检测任务状态文件失败: {e}")

    def find_slide_image(self, page_num: int) -> Optional[str]:
        """
        查找指定页码的幻灯片图片

        Args:
            page_num: 页码

        Returns:
            图片文件路径或None
        """
        try:
            # 查找temp目录下的幻灯片图片
            temp_dir = Path("temp")
            if not temp_dir.exists():
                logger.warning(f"temp目录不存在")
                return None

            # 尝试多种文件名格式
            slide_patterns = [
                f"page_{page_num}.png",           # page_2.png
                f"page_{page_num:03d}.png"        # page_002.png
            ]

            for pattern in slide_patterns:
                slide_path = temp_dir / pattern
                if slide_path.exists():
                    logger.info(f"找到幻灯片图片: {slide_path}")
                    return str(slide_path)

            logger.warning(f"未找到第{page_num}页的幻灯片图片")
            return None

        except Exception as e:
            logger.error(f"查找幻灯片图片时发生错误: {e}")
            return None

    def recapture_pdf_page(self, page_num: int) -> Optional[str]:
        """
        重新截取PDF指定页面的图片

        Args:
            page_num: 页码

        Returns:
            图片文件路径或None
        """
        try:
            if not HAS_FITZ:
                logger.error("缺少必要的PDF处理库，请安装PyMuPDF: pip install PyMuPDF")
                return None

            # 查找input目录下的PDF文件
            input_dir = Path("input")
            if not input_dir.exists():
                logger.error("input目录不存在")
                return None

            # 查找PDF文件
            pdf_files = list(input_dir.glob("*.pdf"))
            if not pdf_files:
                logger.error("input目录中未找到PDF文件")
                return None

            # 使用第一个找到的PDF文件
            pdf_file = pdf_files[0]
            logger.info(f"使用PDF文件: {pdf_file}")

            # 打开PDF文件
            doc = fitz.open(str(pdf_file))

            # 检查页码是否有效
            if page_num < 1 or page_num > len(doc):
                logger.error(f"页码 {page_num} 超出范围 (1-{len(doc)})")
                doc.close()
                return None

            # 创建temp目录
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)

            # 获取指定页面
            page = doc[page_num - 1]

            # 渲染页面为图片
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍分辨率

            # 保存图片
            image_path = temp_dir / f"page_{page_num}.png"
            pix.save(str(image_path))

            # 关闭PDF文件
            doc.close()

            logger.info(f"成功重新截取第{page_num}页幻灯片图片到: {image_path}")
            return str(image_path)

        except Exception as e:
            logger.error(f"重新截取PDF第{page_num}页失败: {e}")
            return None

    def load_task_status(self) -> Dict[str, Any]:
        """加载任务状态"""
        try:
            if self.task_status_file and os.path.exists(self.task_status_file):
                logger.info(f"📂 加载任务状态文件: {self.task_status_file}")
                with open(self.task_status_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 检查是否为新的配置文件格式
                if 'progress_tracking' in config:
                    # 新格式：转换为兼容的格式
                    progress = config['progress_tracking']
                    return {
                        'project_name': config.get('project_info', {}).get('project_name', ''),
                        'total_tasks': progress.get('total_tasks', 0),
                        'completed_tasks': progress.get('completed_tasks', 0),
                        'failed_tasks': progress.get('failed_tasks', 0),
                        'tasks': config.get('tasks', []),
                        'last_update': progress.get('last_update', ''),
                        'status': progress.get('status', 'not_started'),
                        'full_config': config  # 保存完整配置
                    }
                else:
                    # 旧格式：直接返回
                    return config
            else:
                logger.info(f"📝 未找到任务状态文件，使用默认状态")
        except Exception as e:
            logger.error(f"❌ 加载任务状态失败: {e}")
        
        return {
            'project_name': '',
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'tasks': [],
            'last_update': '',
            'status': 'not_started'
        }
    
    def save_task_status(self, task_status: Dict[str, Any]):
        """保存任务状态"""
        try:
            task_status['last_update'] = datetime.now().isoformat()
            
            # 确保配置信息存在
            if 'runninghub_config' not in task_status:
                task_status['runninghub_config'] = {
                    'api_key': os.getenv('RUNNINGHUB_API_KEY'),
                    'base_url': os.getenv('RUNNINGHUB_BASE_URL', 'https://www.runninghub.cn'),
                    'webapp_id': os.getenv('RUNNINGHUB_WEBAPP_ID')
                }
            if 'character_config' not in task_status:
                task_status['character_config'] = {
                    'image_path': os.getenv('CHARACTER_IMAGE_PATH', 'characters/man/input.png'),
                    'reference_audio_path': os.getenv('REFERENCE_AUDIO_PATH', 'characters/man/reference.mp3'),
                    'full_studio_image_path': os.getenv('FULL_STUDIO_IMAGE_PATH', 'models/full_studio_image.png'),
                    'head_studio_image_path': os.getenv('HEAD_STUDIO_IMAGE_PATH', 'models/head_studio_image.png')
                }
            if 'studio_images' not in task_status:
                task_status['studio_images'] = {
                    'full': '',
                    'head': ''
                }
            
            if self.task_status_file:
                # 确保input目录存在
                Path(self.task_status_file).parent.mkdir(parents=True, exist_ok=True)
                
                logger.info(f"💾 保存任务状态到: {self.task_status_file}")
                with open(self.task_status_file, 'w', encoding='utf-8') as f:
                    json.dump(task_status, f, ensure_ascii=False, indent=2)
            else:
                logger.warning(f"⚠️ 任务状态文件路径未设置，跳过保存")
        except Exception as e:
            logger.error(f"❌ 保存任务状态失败: {e}")
    
    def _update_task_in_config(self, task: Dict[str, Any]):
        """更新配置文件中的单个任务信息"""
        try:
            if not self.task_status_file:
                logger.warning(f"⚠️ 任务状态文件路径未设置，跳过更新")
                return
            
            # 读取现有配置文件
            with open(self.task_status_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 找到对应的任务并更新
            task_index = task['page_number'] - 1
            if 'tasks' in config and 0 <= task_index < len(config['tasks']):
                # 更新任务信息
                config['tasks'][task_index].update({
                    'task_id': task.get('task_id', ''),
                    'status': task.get('status', 'pending'),
                    'submit_time': task.get('submit_time', ''),
                    'complete_time': task.get('complete_time', ''),
                    'retry_count': task.get('retry_count', 0),
                    'error_message': task.get('error_message', ''),
                    'processing_time': task.get('processing_time', 0),
                    'file_size': task.get('file_size', 0),
                    'resolution': task.get('resolution', ''),
                    'duration': task.get('duration', 0),
                    'runninghub_task_id': task.get('runninghub_task_id', ''),
                    'runninghub_status': task.get('runninghub_status', ''),
                    'runninghub_progress': task.get('runninghub_progress', 0),
                    'studio_image_used': task.get('studio_image_used', ''),
                    'character_position': task.get('character_position', ''),
                    'background_color': task.get('background_color', ''),
                    'text_overlay': task.get('text_overlay', ''),
                    'watermark': task.get('watermark', ''),
                    'metadata': task.get('metadata', {
                        'created_at': '',
                        'modified_at': datetime.now().isoformat(),
                        'processed_by': '',
                        'processing_version': '1.0'
                    })
                })
                
                # 更新进度跟踪信息
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
                        'last_update': datetime.now().isoformat(),
                        'current_task_index': task_index
                    })
                
                # 更新项目状态
                if 'project_info' in config:
                    completed_tasks = config['progress_tracking']['completed_tasks']
                    total_tasks = len(config['tasks'])
                    
                    if completed_tasks == total_tasks:
                        config['project_info']['processing_status'] = 'completed'
                    elif failed > 0:
                        config['project_info']['processing_status'] = 'partial_completed'
                    elif processing > 0:
                        config['project_info']['processing_status'] = 'processing'
                    else:
                        config['project_info']['processing_status'] = 'pending'
                    
                    config['project_info']['modified_at'] = datetime.now().isoformat()
                
                # 保存更新后的配置
                with open(self.task_status_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                logger.debug(f"✅ 任务{task['page_number']}信息已更新到配置文件")
            else:
                logger.error(f"❌ 无法找到任务{task['page_number']}在配置文件中")
                
        except Exception as e:
            logger.error(f"❌ 更新任务到配置文件失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
    
    def extract_tasks_from_ppt(self, ppt_file: str) -> List[Dict[str, Any]]:
        """从PPT文件中提取需要生成的视频任务"""
        logger.info(f"开始分析PPT文件: {ppt_file}")
        
        try:
            # 设置任务状态文件路径（放在input文件夹下，与PPT同名）
            ppt_path = Path(ppt_file)
            input_folder = Path("input")
            self.task_status_file = input_folder / ppt_path.with_suffix('.json').name
            logger.info(f"📝 任务状态文件将保存为: {self.task_status_file}")
            
            # 更新video_generator的配置文件路径
            self.video_generator.task_status_file_path = str(self.task_status_file)
            
            ppt_reader = PPTReader()
            logger.info("正在读取PPT内容...")
            
            ppt_data = ppt_reader.read_ppt(ppt_file)
            
            if not ppt_data:
                logger.error("读取PPT文件失败")
                return []
            
            logger.info(f"PPT读取成功，总页数: {ppt_data.get('total_pages', 0)}")
            
            # 记录PDF基本信息
            pdf_info = ppt_data.get('pdf_info', {})
            if pdf_info:
                logger.info(f"PDF基本信息:")
                logger.info(f"  - 总页数: {pdf_info.get('total_pages', 0)}")
                logger.info(f"  - 文件大小: {pdf_info.get('file_size', 0)} 字节")
                logger.info(f"  - 文件存在: {pdf_info.get('file_exists', False)}")
                logger.info(f"  - 文件可读: {pdf_info.get('is_readable', False)}")
                logger.info(f"  - 转换成功: {pdf_info.get('conversion_successful', False)}")
            
            # 使用配置生成器创建完整的初始配置文件
            logger.info("生成完整的任务配置文件...")
            complete_config = self.task_config_generator.generate_complete_config(
                ppt_file=ppt_data['ppt_file'],
                pdf_file=ppt_data['pdf_file'],
                ppt_content=ppt_data['ppt_content'],
                pdf_pages=ppt_data['pdf_pages']
            )
            
            # 将PDF信息添加到配置中
            complete_config['pdf_info'] = pdf_info
            complete_config['file_info'] = ppt_data.get('file_info', {})
            
            # 保存完整配置文件
            if not self.task_config_generator.save_config(complete_config, str(self.task_status_file)):
                logger.error("保存完整配置文件失败")
                return []
            
            logger.info(f"✅ 完整配置文件已保存到: {self.task_status_file}")
            
            # 提取有备注的页面作为任务列表
            tasks = []
            ppt_content = ppt_data.get('ppt_content', [])
            
            logger.info("开始扫描每页的备注内容...")
            for i, slide_data in enumerate(ppt_content):
                notes = slide_data.get('notes_text', '').strip()
                if notes:
                    # 判断模式
                    mode = "full" if slide_data.get('is_full_mode', False) else "head"
                    content = notes
                    
                    task_info = {
                        'page_number': i + 1,
                        'notes': content,
                        'mode': mode,
                        'task_id': '',
                        'status': 'pending',
                        'video_path': f"outputs/video_page_{i+1:03d}_{mode}.mp4",
                        'retry_count': 0,
                        'submit_time': '',
                        'complete_time': ''
                    }
                    tasks.append(task_info)
                    
                    logger.info(f"第{i+1}页发现需要生成视频的备注 - 模式: {mode}, 内容长度: {len(content)}字符")
                    logger.debug(f"第{i+1}页备注内容预览: {content[:100]}{'...' if len(content) > 100 else ''}")
                else:
                    logger.debug(f"第{i+1}页没有备注，跳过")
            
            logger.info(f"PPT分析完成！共找到 {len(tasks)} 个需要生成视频的任务")
            logger.info(f"任务分布 - Head模式: {len([t for t in tasks if t['mode'] == 'head'])}, Full模式: {len([t for t in tasks if t['mode'] == 'full'])}")
            
            # 更新配置文件中的任务状态
            for task in tasks:
                task_index = task['page_number'] - 1
                if task_index < len(complete_config['tasks']):
                    complete_config['tasks'][task_index].update({
                        'notes': task['notes'],
                        'mode': task['mode'],
                        'status': 'pending',
                        'video_path': task['video_path']
                    })
            
            # 重新保存更新后的配置
            self.task_config_generator.save_config(complete_config, str(self.task_status_file))
            
            return tasks
            
        except Exception as e:
            logger.error(f"从PPT提取任务时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return []
    
    def submit_task(self, task: Dict[str, Any]) -> bool:
        """提交单个任务"""
        page_num = task['page_number']
        content = task['notes']
        mode = task['mode']
        
        logger.info(f"=== 开始检查第{page_num}页任务 ===")
        logger.info(f"页面信息 - 模式: {mode}, 文本长度: {len(content)}字符")
        logger.info(f"输出路径: {task['video_path']}")
        
        # 检查任务是否已经存在（兼容task_id和runninghub_task_id）
        task_id = task.get('task_id') or task.get('runninghub_task_id')
        if task_id and task.get('status') in ['completed', 'processing', 'pending']:
            logger.info(f"⏳ 第{page_num}页任务已存在，跳过提交")
            logger.info(f"任务ID: {task_id}")
            logger.info(f"任务状态: {task['status']}")
            return True
        
        # 检查文本内容是否为空
        if not content or not content.strip():
            logger.info(f"⏭️ 第{page_num}页任务内容为空，跳过提交")
            task['status'] = 'skipped'
            task['error_message'] = '任务内容为空，跳过生成'
            
            # 确保metadata字段存在
            if 'metadata' not in task:
                task['metadata'] = {
                    'created_at': '',
                    'modified_at': '',
                    'processed_by': '',
                    'processing_version': '1.0'
                }
            task['metadata']['modified_at'] = datetime.now().isoformat()
            
            # 保存跳过状态到配置文件
            self._update_task_in_config(task)
            logger.info(f"✅ 第{page_num}页任务跳过状态已保存到配置文件")
            return 'skipped'  # 返回特殊状态标识跳过
        
        logger.info(f"=== 开始提交第{page_num}页任务 ===")
        logger.debug(f"完整播报内容: {content}")
        
        try:
            # 判断是否使用示例视频（根据需求文档，现在两种模式都应生成真实视频）
            use_example_video = False  # 不使用示例视频，生成真实的RunningHub视频
            
            # 记录生成开始时间
            start_time = time.time()
            logger.info(f"开始生成数字人视频...")
            
            # 生成视频
            result = self.video_generator.generate_video(
                text=content,
                mode=mode,
                output_path=task['video_path'],
                use_example_video=use_example_video,
                page_number=page_num
            )
            
            # 记录生成耗时
            generation_time = time.time() - start_time
            logger.info(f"视频生成耗时: {generation_time:.2f}秒")
            
            if result:
                task_id = result.get('task_id')
                
                # 更新任务信息
                task['task_id'] = task_id
                task['runninghub_task_id'] = task_id
                
                # 根据结果状态设置任务状态
                if result.get('status') == 'failed' or result.get('task_failed', False):
                    task['status'] = 'failed'
                    task['runninghub_status'] = 'failed'
                    task['error_message'] = result.get('error_message', '任务执行失败')
                    logger.warning(f"第{page_num}页任务执行失败，但任务ID已保存")
                else:
                    task['status'] = 'processing'
                    task['runninghub_status'] = 'processing'
                    task['runninghub_progress'] = 0
                    logger.info(f"第{page_num}页任务提交成功！")
                
                task['submit_time'] = datetime.now().isoformat()
                
                logger.info(f"任务ID: {task_id}")
                logger.info(f"预计输出路径: {task['video_path']}")
                
                # 更新任务元数据
                # 确保metadata字段存在
                if 'metadata' not in task:
                    task['metadata'] = {
                        'created_at': '',
                        'modified_at': '',
                        'processed_by': '',
                        'processing_version': '1.0'
                    }
                task['metadata']['modified_at'] = datetime.now().isoformat()
                task['metadata']['processed_by'] = 'ppt-to-video'
                
                # 如果是使用示例视频，立即标记为完成
                if use_example_video and task_id and task_id.startswith('example_'):
                    task['status'] = 'completed'
                    task['complete_time'] = datetime.now().isoformat()
                    task['runninghub_status'] = 'completed'
                    task['runninghub_progress'] = 100
                    logger.info(f"第{page_num}页使用示例视频，立即完成")
                    logger.info(f"实际输出路径: {task['video_path']}")
                
                # 更新文件信息
                if result.get('file_size'):
                    task['file_size'] = result['file_size']
                
                # 立即保存任务状态到配置文件
                self._update_task_in_config(task)
                logger.info(f"✅ 第{page_num}页任务信息已保存到配置文件")
                
                return True
            else:
                logger.error(f"第{page_num}页任务提交失败")
                task['status'] = 'failed'
                task['retry_count'] += 1
                task['runninghub_status'] = 'failed'
                task['error_message'] = '视频生成失败'
                
                # 确保metadata字段存在
                if 'metadata' not in task:
                    task['metadata'] = {
                        'created_at': '',
                        'modified_at': '',
                        'processed_by': '',
                        'processing_version': '1.0'
                    }
                task['metadata']['modified_at'] = datetime.now().isoformat()
                
                # 保存失败状态
                self._update_task_in_config(task)
                logger.info(f"⚠️ 第{page_num}页任务失败状态已保存到配置文件")
                
                logger.info(f"重试次数: {task['retry_count']}")
                return False
                
        except Exception as e:
            logger.error(f"提交任务时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            task['status'] = 'failed'
            task['retry_count'] += 1
            task['runninghub_status'] = 'failed'
            
            # 确保metadata字段存在
            if 'metadata' not in task:
                task['metadata'] = {
                    'created_at': '',
                    'modified_at': '',
                    'processed_by': '',
                    'processing_version': '1.0'
                }
            task['metadata']['modified_at'] = datetime.now().isoformat()
            
            # 保存异常状态
            self._update_task_in_config(task)
            logger.info(f"⚠️ 第{page_num}页任务异常状态已保存到配置文件")
            
            return False
    
    def check_task_status(self, task_id: str) -> Optional[str]:
        """检查任务状态"""
        try:
            status = self.runninghub_api.get_task_status(task_id)
            return status
        except Exception as e:
            logger.error(f"检查任务状态时发生错误: {e}")
            return None
    
    def wait_for_task_completion(self, task: Dict[str, Any], timeout: int = 3600) -> bool:
        """等待任务完成"""
        task_id = task['task_id']
        page_num = task['page_number']
        
        logger.info(f"=== 开始监控第{page_num}页任务状态 ===")
        logger.info(f"任务ID: {task_id}")
        logger.info(f"超时设置: {timeout}秒")
        
        # 示例视频逻辑已移除，所有任务都需等待处理
        logger.info(f"第{page_num}页任务开始监控状态")
        
        start_time = time.time()
        last_status = None
        status_check_count = 0
        
        while time.time() - start_time < timeout:
            elapsed_time = int(time.time() - start_time)
            status_check_count += 1
            
            logger.debug(f"第{status_check_count}次检查任务状态，已等待: {elapsed_time}秒")
            
            status = self.check_task_status(task_id)
            
            if status != last_status:
                logger.info(f"状态变化: {last_status} -> {status}")
                last_status = status
            
            if status == "SUCCESS":
                total_time = int(time.time() - start_time)
                logger.info(f"🎉 第{page_num}页任务完成！")
                logger.info(f"总耗时: {total_time}秒")
                logger.info(f"状态检查次数: {status_check_count}")
                
                # 检查输出文件是否存在
                if os.path.exists(task['video_path']):
                    file_size = os.path.getsize(task['video_path'])
                    logger.info(f"输出文件大小: {file_size / 1024 / 1024:.2f} MB")
                    
                    # 如果是head模式，需要进行本地视频组合
                    if task['mode'] == 'head':
                        logger.info(f"🎭 Head模式检测到，开始本地视频组合...")
                        try:
                            from src.video_processor import VideoProcessor
                            video_processor = VideoProcessor()

                            # 获取PPT幻灯片路径 - 使用新的查找逻辑
                            slide_image = task.get('pdf_page_path', '')
                            if not slide_image or not os.path.exists(slide_image):
                                logger.warning(f"⚠️ 配置中的幻灯片图片不存在: {slide_image}")
                                # 尝试查找幻灯片图片
                                slide_image = self.find_slide_image(page_num)
                                if not slide_image:
                                    logger.warning(f"⚠️ 未找到第{page_num}页幻灯片图片，尝试重新截取PDF...")
                                    # 尝试重新截取PDF图片
                                    slide_image = self.recapture_pdf_page(page_num)
                                    if slide_image:
                                        logger.info(f"✅ 成功重新截取第{page_num}页幻灯片图片")
                                    else:
                                        logger.error(f"❌ 第{page_num}页重新截取PDF失败，无法进行Head模式组合")
                                        # 使用原始视频，但标记为部分完成
                                        task['status'] = 'completed'
                                        task['file_size'] = file_size
                                        task['error_message'] = 'Head模式组合失败：缺少幻灯片图片'
                                        return True

                            # 创建临时工作目录
                            work_dir = Path(tempfile.mkdtemp())
                            logger.info(f"📁 临时工作目录: {work_dir}")

                            # 备份原始视频文件
                            original_video = task['video_path']
                            backup_video = str(work_dir / f"original_video_{page_num:03d}.mp4")
                            shutil.copy2(original_video, backup_video)

                            # 使用video_processor组合PPT和数字人视频
                            logger.info(f"🔧 开始组合PPT幻灯片和数字人视频...")
                            success = video_processor.combine_slide_with_video(
                                slide_image=slide_image,
                                video_file=backup_video,
                                is_full_mode=False,  # head模式
                                output_file=original_video,
                                work_dir=work_dir,
                                subtitle_text=task.get('notes', ''),
                                page_number=page_num
                            )

                            if success:
                                # 更新文件大小
                                if os.path.exists(original_video):
                                    new_file_size = os.path.getsize(original_video)
                                    task['file_size'] = new_file_size
                                    logger.info(f"🎉 Head模式本地视频组合完成！")
                                    logger.info(f"新文件大小: {new_file_size / 1024 / 1024:.2f} MB")
                                else:
                                    logger.error(f"❌ 组合后的视频文件不存在: {original_video}")
                                    # 恢复原始文件
                                    shutil.copy2(backup_video, original_video)
                                    task['file_size'] = file_size
                                    task['error_message'] = 'Head模式组合后文件不存在'
                            else:
                                logger.error(f"❌ Head模式本地视频组合失败，使用原始视频")
                                # 恢复原始文件
                                shutil.copy2(backup_video, original_video)
                                task['file_size'] = file_size
                                task['error_message'] = 'Head模式组合失败'

                            # 清理临时目录
                            shutil.rmtree(work_dir, ignore_errors=True)

                        except Exception as e:
                            logger.error(f"❌ Head模式本地视频组合时发生异常: {e}")
                            import traceback
                            logger.error(f"错误详情: {traceback.format_exc()}")
                            # 组合失败，但任务仍然完成，使用原始视频
                            task['file_size'] = file_size
                            task['error_message'] = f'Head模式组合异常: {str(e)}'
                    else:
                        # full模式，直接使用原始视频
                        task['file_size'] = file_size
                else:
                    logger.warning(f"⚠️ 输出文件不存在: {task['video_path']}")
                    task['file_size'] = 0
                
                # 更新任务状态
                task['status'] = 'completed'
                task['complete_time'] = datetime.now().isoformat()
                task['runninghub_status'] = 'completed'
                task['runninghub_progress'] = 100
                task['processing_time'] = total_time
                
                # 保存完成状态到配置文件
                self._update_task_in_config(task)
                logger.info(f"✅ 第{page_num}页任务完成状态已保存到配置文件")
                
                return True
                
            elif status == "FAILED":
                total_time = int(time.time() - start_time)
                logger.error(f"❌ 第{page_num}页任务失败！")
                logger.error(f"失败时间: {total_time}秒后")
                logger.error(f"状态检查次数: {status_check_count}")
                
                # 更新任务状态
                task['status'] = 'failed'
                task['retry_count'] += 1
                task['runninghub_status'] = 'failed'
                task['runninghub_progress'] = 0
                task['processing_time'] = total_time
                task['error_message'] = f"任务在RunningHub失败，状态: {status}"
                
                # 保存失败状态到配置文件
                self._update_task_in_config(task)
                logger.info(f"⚠️ 第{page_num}页任务失败状态已保存到配置文件")
                
                return False
                
            elif status in ["QUEUED", "RUNNING"]:
                if status_check_count % 5 == 0:  # 每5次检查输出一次进度
                    logger.info(f"⏳ 第{page_num}页任务进行中: {status} (已等待: {elapsed_time}秒)")
                    
                    # 更新运行状态到配置文件
                    task['runninghub_status'] = status
                    if status == "RUNNING":
                        task['runninghub_progress'] = min(95, (elapsed_time / 300) * 100)  # 估算进度
                    
                    self._update_task_in_config(task)
                
                time.sleep(self.check_interval)
                
            else:
                logger.warning(f"⚠️ 第{page_num}页任务未知状态: {status}")
                time.sleep(self.check_interval)
        
        total_time = int(time.time() - start_time)
        logger.error(f"⏰ 第{page_num}页任务超时！")
        logger.error(f"超时时间: {total_time}秒 / {timeout}秒")
        logger.error(f"最后状态: {last_status}")
        logger.error(f"状态检查次数: {status_check_count}")
        
        # 更新任务状态
        task['status'] = 'timeout'
        task['runninghub_status'] = 'timeout'
        task['runninghub_progress'] = 0
        task['processing_time'] = total_time
        task['error_message'] = f"任务超时，最后状态: {last_status}"
        
        # 保存超时状态到配置文件
        self._update_task_in_config(task)
        logger.info(f"⚠️ 第{page_num}页任务超时状态已保存到配置文件")
        
        return False
    
    def process_all_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理所有任务"""
        start_time = time.time()
        
        # 统计已完成的任务数量
        completed_tasks = len([t for t in tasks if t['status'] == 'completed'])
        failed_tasks = len([t for t in tasks if t['status'] == 'failed'])
        
        task_status = {
            'project_name': Path(tasks[0]['video_path']).parent.name if tasks else '',
            'total_tasks': len(tasks),
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'tasks': tasks,
            'start_time': datetime.now().isoformat(),
            'status': 'processing'
        }
        
        logger.info(f"🚀 开始处理 {len(tasks)} 个任务")
        logger.info(f"项目名称: {task_status['project_name']}")
        logger.info(f"开始时间: {task_status['start_time']}")
        
        # 统计任务类型
        head_tasks = len([t for t in tasks if t['mode'] == 'head'])
        full_tasks = len([t for t in tasks if t['mode'] == 'full'])
        logger.info(f"任务类型分布 - Head模式: {head_tasks}, Full模式: {full_tasks}")
        
        for i, task in enumerate(tasks):
            task_start_time = time.time()
            
            logger.info(f"\n{'='*50}")
            logger.info(f"📋 处理第 {i+1}/{len(tasks)} 个任务")
            logger.info(f"{'='*50}")
            logger.info(f"页面编号: 第{task['page_number']}页")
            logger.info(f"视频模式: {task['mode'].upper()}")
            logger.info(f"文本长度: {len(task['notes'])}字符")
            
            # 检查任务状态
            task_status_code = task.get('status', 'pending')
            logger.info(f"当前状态: {task_status_code}")
            
            if task_status_code == 'completed':
                logger.info(f"✅ 第{task['page_number']}页任务已完成，跳过")
                continue
            
            elif task_status_code == 'failed':
                logger.info(f"❌ 第{task['page_number']}页任务失败，跳过")
                logger.info(f"重试次数: {task.get('retry_count', 0)}")
                continue
            
            elif task_status_code == 'skipped':
                logger.info(f"⏭️ 第{task['page_number']}页任务已跳过（内容为空），跳过")
                continue
            
            elif task_status_code in ['processing', 'pending']:
                # 检查任务是否已经提交（有task_id或runninghub_task_id）
                task_id = task.get('task_id') or task.get('runninghub_task_id')
                if task_id:
                    logger.info(f"⏳ 第{task['page_number']}页任务已在处理中")
                    logger.info(f"任务ID: {task_id}")
                    
                    # 确保task_id字段存在（兼容性处理）
                    if not task.get('task_id'):
                        task['task_id'] = task_id
                    
                    # 等待任务完成
                    logger.info(f"⏳ 等待任务完成...")
                    if self.wait_for_task_completion(task):
                        task_status['completed_tasks'] += 1
                        success_rate = task_status['completed_tasks'] / (i + 1) * 100
                        logger.info(f"📊 当前进度: {task_status['completed_tasks']}/{len(tasks)} ({success_rate:.1f}%)")
                    else:
                        task_status['failed_tasks'] += 1
                        failure_rate = task_status['failed_tasks'] / (i + 1) * 100
                        logger.warning(f"📊 当前进度: 失败 {task_status['failed_tasks']}/{len(tasks)} ({failure_rate:.1f}%)")
                else:
                    # 如果任务还没有提交，则提交新任务
                    logger.info(f"📤 第{task['page_number']}页任务未提交，正在提交...")
                    submit_result = self.submit_task(task)
                    
                    if submit_result == 'skipped':
                        logger.info(f"⏭️ 第{task['page_number']}页任务已跳过（内容为空）")
                        continue  # 跳过等待完成的步骤
                    elif not submit_result:
                        task_status['failed_tasks'] += 1
                        logger.error(f"任务提交失败，跳过此任务")
                        continue
                    
                    # 等待任务完成
                    logger.info(f"⏳ 等待任务完成...")
                    if self.wait_for_task_completion(task):
                        task_status['completed_tasks'] += 1
                        success_rate = task_status['completed_tasks'] / (i + 1) * 100
                        logger.info(f"📊 当前进度: {task_status['completed_tasks']}/{len(tasks)} ({success_rate:.1f}%)")
                    else:
                        task_status['failed_tasks'] += 1
                        failure_rate = task_status['failed_tasks'] / (i + 1) * 100
                        logger.warning(f"📊 当前进度: 失败 {task_status['failed_tasks']}/{len(tasks)} ({failure_rate:.1f}%)")
            
            # 记录单个任务耗时
            task_time = time.time() - task_start_time
            logger.info(f"⏱️ 第{task['page_number']}页处理耗时: {task_time:.2f}秒")
            
            # 保存状态
            self.save_task_status(task_status)
        
        # 计算总耗时
        total_time = time.time() - start_time
        task_status['status'] = 'completed'
        task_status['end_time'] = datetime.now().isoformat()
        
        logger.info(f"\n{'='*50}")
        logger.info(f"🎉 所有任务处理完成！")
        logger.info(f"{'='*50}")
        logger.info(f"✅ 成功: {task_status['completed_tasks']}/{len(tasks)}")
        logger.info(f"❌ 失败: {task_status['failed_tasks']}/{len(tasks)}")
        logger.info(f"⏱️ 总耗时: {total_time:.2f}秒 ({total_time/60:.1f}分钟)")
        
        if len(tasks) > 0:
            success_rate = task_status['completed_tasks'] / len(tasks) * 100
            avg_time_per_task = total_time / len(tasks)
            logger.info(f"📊 成功率: {success_rate:.1f}%")
            logger.info(f"📊 平均每页耗时: {avg_time_per_task:.2f}秒")
        
        self.save_task_status(task_status)
        return task_status
    
    def download_completed_videos(self, task_status: Dict[str, Any]) -> bool:
        """下载已完成的任务视频文件"""
        try:
            logger.info(f"📥 开始下载已完成的任务视频...")
            
            downloaded_count = 0
            failed_count = 0
            
            for task in task_status['tasks']:
                if task['status'] in ['completed', 'downloading'] and task.get('runninghub_task_id'):
                    task_id = task['runninghub_task_id']
                    video_path = task.get('video_path')
                    
                    # 检查视频文件是否已存在
                    if video_path and os.path.exists(video_path):
                        logger.info(f"✅ 第{task['page_number']}页视频文件已存在: {video_path}")
                        downloaded_count += 1
                        continue
                    
                    logger.info(f"📥 下载第{task['page_number']}页视频...")
                    logger.info(f"任务ID: {task_id}")
                    logger.info(f"目标路径: {video_path}")
                    
                    # 获取任务输出
                    outputs = self.runninghub_api.get_task_outputs(task_id)
                    if not outputs:
                        logger.warning(f"⚠️ 第{task['page_number']}页未获取到输出结果")
                        failed_count += 1
                        continue
                    
                    # 查找视频文件
                    video_downloaded = False
                    for output in outputs:
                        file_url = output.get('fileUrl')
                        file_type = output.get('fileType')
                        node_id = output.get('nodeId')
                        
                        if node_id == "22" and file_url:  # 视频文件
                            # 确保输出目录存在
                            if video_path:
                                output_dir = Path(video_path).parent
                                output_dir.mkdir(parents=True, exist_ok=True)
                                
                                if self.runninghub_api.download_file(file_url, video_path):
                                    logger.info(f"✅ 第{task['page_number']}页视频下载完成")
                                    
                                    # 更新文件大小信息
                                    if os.path.exists(video_path):
                                        file_size = os.path.getsize(video_path)
                                        task['file_size'] = file_size
                                        logger.info(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
                                    
                                    downloaded_count += 1
                                    video_downloaded = True
                                    
                                    # 如果是head模式，需要进行本地视频组合
                                    if task['mode'] == 'head':
                                        logger.info(f"🎭 Head模式检测到，开始本地视频组合...")
                                        try:
                                            from src.video_processor import VideoProcessor
                                            video_processor = VideoProcessor()

                                            # 获取PPT幻灯片路径 - 使用新的查找逻辑
                                            page_num = task['page_number']
                                            slide_image = task.get('pdf_page_path', '')
                                            if not slide_image or not os.path.exists(slide_image):
                                                logger.warning(f"⚠️ 配置中的幻灯片图片不存在: {slide_image}")
                                                # 尝试查找幻灯片图片
                                                slide_image = self.find_slide_image(page_num)
                                                if not slide_image:
                                                    logger.warning(f"⚠️ 未找到第{page_num}页幻灯片图片，尝试重新截取PDF...")
                                                    # 尝试重新截取PDF图片
                                                    slide_image = self.recapture_pdf_page(page_num)
                                                    if slide_image:
                                                        logger.info(f"✅ 成功重新截取第{page_num}页幻灯片图片")
                                                    else:
                                                        logger.error(f"❌ 第{page_num}页重新截取PDF失败，跳过Head模式组合")
                                                        task['error_message'] = 'Head模式组合失败：缺少幻灯片图片'
                                                        continue

                                            # 创建临时工作目录
                                            work_dir = Path(tempfile.mkdtemp())
                                            logger.info(f"📁 临时工作目录: {work_dir}")

                                            # 备份原始视频文件
                                            original_video = video_path
                                            backup_video = str(work_dir / f"original_video_{page_num:03d}.mp4")
                                            shutil.copy2(original_video, backup_video)

                                            # 使用video_processor组合PPT和数字人视频
                                            logger.info(f"🔧 开始组合PPT幻灯片和数字人视频...")
                                            success = video_processor.combine_slide_with_video(
                                                slide_image=slide_image,
                                                video_file=backup_video,
                                                is_full_mode=False,  # head模式
                                                output_file=original_video,
                                                work_dir=work_dir,
                                                subtitle_text=task.get('notes', ''),
                                                page_number=page_num
                                            )

                                            if success:
                                                # 更新文件大小
                                                if os.path.exists(original_video):
                                                    new_file_size = os.path.getsize(original_video)
                                                    task['file_size'] = new_file_size
                                                    logger.info(f"🎉 Head模式本地视频组合完成！")
                                                    logger.info(f"新文件大小: {new_file_size / 1024 / 1024:.2f} MB")
                                                else:
                                                    logger.error(f"❌ 组合后的视频文件不存在: {original_video}")
                                                    # 恢复原始文件
                                                    shutil.copy2(backup_video, original_video)
                                                    task['error_message'] = 'Head模式组合后文件不存在'
                                            else:
                                                logger.error(f"❌ Head模式本地视频组合失败，使用原始视频")
                                                # 恢复原始文件
                                                shutil.copy2(backup_video, original_video)
                                                task['error_message'] = 'Head模式组合失败'

                                            # 清理临时目录
                                            shutil.rmtree(work_dir, ignore_errors=True)

                                        except Exception as e:
                                            logger.error(f"❌ Head模式本地视频组合时发生异常: {e}")
                                            import traceback
                                            logger.error(f"错误详情: {traceback.format_exc()}")
                                            task['error_message'] = f'Head模式组合异常: {str(e)}'
                                    break
                                else:
                                    logger.error(f"❌ 第{task['page_number']}页视频下载失败")
                                    failed_count += 1
                    
                    if not video_downloaded:
                        logger.warning(f"⚠️ 第{task['page_number']}页未找到视频文件")
                        failed_count += 1
                    
                    # 保存更新后的任务状态
                    self._update_task_in_config(task)
            
            logger.info(f"📥 视频下载完成！")
            logger.info(f"✅ 成功下载: {downloaded_count} 个")
            logger.info(f"❌ 下载失败: {failed_count} 个")
            
            return downloaded_count > 0
            
        except Exception as e:
            logger.error(f"下载视频时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False

    def combine_videos(self, task_status: Dict[str, Any]) -> bool:
        """组合所有视频成一个完整视频 - 直接合并所有现有视频文件，不考虑任务状态"""
        try:
            logger.info(f"🎬 开始合并所有现有视频文件...")

            # 初始化视频处理器
            video_processor = VideoProcessor()

            # 扫描outputs目录中的视频文件
            outputs_dir = Path("outputs")
            if not outputs_dir.exists():
                logger.error(f"❌ outputs目录不存在: {outputs_dir}")
                return False

            # 查找所有video_page_开头的mp4文件
            video_files = []
            for video_file in outputs_dir.glob("video_page_*.mp4"):
                if video_file.exists():  # 确保文件存在
                    video_files.append(video_file)

            if not video_files:
                logger.error(f"❌ 在outputs目录中未找到video_page_*.mp4格式的视频文件")
                logger.error(f"💡 请确保存在要合并的视频文件")
                return False

            # 按文件名排序确保顺序正确
            video_files.sort()

            logger.info(f"📊 找到 {len(video_files)} 个视频文件")

            # 显示找到的视频文件信息
            total_size = 0
            video_paths = []
            for i, video_file in enumerate(video_files, 1):
                if video_file.exists():
                    size = video_file.stat().st_size
                    total_size += size
                    video_paths.append(str(video_file))
                    logger.info(f"📹 视频{i}: {video_file.name} ({size / 1024 / 1024:.2f} MB)")
                else:
                    logger.warning(f"⚠️ 视频文件不存在: {video_file}")

            logger.info(f"📊 总文件大小: {total_size / 1024 / 1024:.2f} MB")

            # 生成输出文件名（带时间戳避免覆盖）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = outputs_dir / f"merged_video_{timestamp}.mp4"

            logger.info(f"🎬 开始合并视频文件...")
            logger.info(f"📁 输出路径: {output_path}")

            # 执行视频合并
            result = video_processor.merge_videos(video_paths, outputs_dir)

            if result:
                # 重命名生成的文件
                default_output = outputs_dir / "merged_video.mp4"
                if default_output.exists():
                    default_output.rename(output_path)

                # 获取实际文件大小
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    logger.info(f"🎉 视频合并完成！")
                    logger.info(f"📁 输出文件: {output_path}")
                    logger.info(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")

                    # 更新任务状态（可选）
                    task_status['final_video_path'] = str(output_path)
                    task_status['final_video_size'] = file_size
                    task_status['completion_time'] = datetime.now().isoformat()
                    self.save_task_status(task_status)

                    return True
                else:
                    logger.error(f"❌ 合并后的视频文件不存在: {output_path}")
                    return False
            else:
                logger.error(f"❌ 视频合并失败")
                return False

        except Exception as e:
            logger.error(f"❌ 合并视频时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='PPT转数字人视频处理系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                                 # 运行完整的PPT处理流程（自动扫描input文件夹）
  python main.py -c                              # 仅组合现有视频文件
  python main.py -i input/presentation.pptx     # 处理指定的PPT文件
        """
    )

    parser.add_argument(
        '-c', '--combine',
        action='store_true',
        help='仅组合现有的视频文件，不进行新的PPT处理'
    )

    parser.add_argument(
        '-i', '--input',
        type=str,
        metavar='PPT_FILE',
        help='指定要处理的PPT文件路径（支持.pptx和.ppt文件）'
    )

    return parser.parse_args()


def main():
    """主程序入口"""
    # 解析命令行参数
    args = parse_arguments()

    program_start_time = time.time()

    logger.info(f"🚀 PPT转数字人视频处理系统启动")
    logger.info(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🐍 Python版本: {os.sys.version}")
    logger.info(f"📁 工作目录: {os.getcwd()}")

    # 检查参数冲突
    if args.combine and args.input:
        logger.error(f"❌ 参数冲突：-c/--combine 和 -i/--input 参数不能同时使用")
        logger.error(f"💡 -c/--combine 用于组合现有视频，-i/--input 用于处理新的PPT文件")
        return

    # 如果指定了-c参数，直接运行组合视频功能
    if args.combine:
        logger.info(f"🎬 检测到-c参数，开始按顺序合并所有现有视频文件...")

        try:
            # 初始化视频处理器
            video_processor = VideoProcessor()

            # 扫描outputs目录中的视频文件
            outputs_dir = Path("outputs")
            if not outputs_dir.exists():
                logger.error(f"❌ outputs目录不存在: {outputs_dir}")
                return

            # 查找所有video_page_开头的mp4文件
            video_files = []
            for video_file in outputs_dir.glob("video_page_*.mp4"):
                video_files.append(video_file)

            if not video_files:
                logger.error(f"❌ 在outputs目录中未找到video_page_*.mp4格式的视频文件")
                logger.error(f"💡 请确保存在要合并的视频文件")
                return

            # 按文件名排序确保顺序正确
            video_files.sort()

            logger.info(f"📊 找到 {len(video_files)} 个视频文件")

            # 显示找到的视频文件信息
            total_size = 0
            for i, video_file in enumerate(video_files, 1):
                if video_file.exists():
                    size = video_file.stat().st_size
                    total_size += size
                    logger.info(f"📹 视频{i}: {video_file.name} ({size / 1024 / 1024:.2f} MB)")
                else:
                    logger.warning(f"⚠️ 视频文件不存在: {video_file}")

            logger.info(f"📊 总文件大小: {total_size / 1024 / 1024:.2f} MB")

            # 生成输出文件名（带时间戳避免覆盖）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = outputs_dir / f"merged_video_{timestamp}.mp4"

            logger.info(f"🎬 开始合并视频文件...")
            logger.info(f"📁 输出路径: {output_path}")

            # 执行视频合并
            result = video_processor.merge_videos([str(f) for f in video_files], outputs_dir)

            if result:
                # 重命名生成的文件
                default_output = outputs_dir / "merged_video.mp4"
                if default_output.exists():
                    default_output.rename(output_path)

                # 获取实际文件大小
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    logger.info(f"🎉 视频合并完成！")
                    logger.info(f"📁 输出文件: {output_path}")
                    logger.info(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
                    logger.info(f"💡 使用命令: python -c \"import os; print(f'播放: {output_path}')\"")
                else:
                    logger.error(f"❌ 合并后的视频文件不存在: {output_path}")
            else:
                logger.error(f"❌ 视频合并失败")

        except Exception as e:
            logger.error(f"❌ 合并视频时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

        return
    
    try:
        # 初始化任务管理器
        logger.info(f"⚙️ 初始化任务管理器...")
        task_manager = TaskManager()
        
        # 检查是否有未完成的任务
        logger.info(f"🔍 检查未完成任务...")
        task_status = task_manager.load_task_status()
        
        logger.info(f"🔍 调试信息: task_status['status'] = {task_status.get('status')}")
        logger.info(f"🔍 调试信息: task_status['tasks'] = {len(task_status.get('tasks', []))}")
        
        if task_status['tasks'] and task_status['status'] in ['processing', 'not_started']:
            # 恢复之前的任务
            logger.info(f"🔄 检测到未完成任务，准备恢复...")
            logger.info(f"📊 任务状态: {task_status['status']}")
            logger.info(f"📁 项目名称: {task_status['project_name']}")
            logger.info(f"📋 总任务数: {task_status['total_tasks']}")
            logger.info(f"✅ 已完成: {task_status['completed_tasks']}")
            logger.info(f"❌ 失败: {task_status['failed_tasks']}")
            
            # 继续处理未完成的任务
            remaining_tasks = [task for task in task_status['tasks'] if task['status'] not in ['completed', 'failed']]
            if remaining_tasks:
                logger.info(f"⏳ 继续处理 {len(remaining_tasks)} 个未完成的任务...")
                updated_status = task_manager.process_all_tasks(remaining_tasks)
                
                # 组合视频
                if updated_status['completed_tasks'] > 0:
                    logger.info(f"🎬 开始组合最终视频...")
                    task_manager.combine_videos(updated_status)
            else:
                logger.info(f"✅ 所有任务已完成")
                
                # 检查已完成任务的视频文件是否存在
                logger.info(f"🔍 检查已完成任务的视频文件...")
                completed_tasks = [task for task in task_status['tasks'] if task['status'] in ['completed', 'downloading']]
                missing_videos = []
                
                for task in completed_tasks:
                    video_path = task.get('video_path')
                    if not video_path or not os.path.exists(video_path):
                        missing_videos.append(task)
                        logger.warning(f"⚠️ 第{task['page_number']}页视频文件缺失: {video_path}")
                
                if missing_videos:
                    logger.info(f"📥 发现 {len(missing_videos)} 个已完成任务的视频文件缺失，开始下载...")
                    
                    # 下载缺失的视频文件
                    if task_manager.download_completed_videos(task_status):
                        logger.info(f"✅ 视频文件下载完成")
                        
                        # 重新组合视频
                        logger.info(f"🎬 开始组合最终视频...")
                        task_manager.combine_videos(task_status)
                    else:
                        logger.error(f"❌ 视频文件下载失败")
                else:
                    logger.info(f"✅ 所有已完成任务的视频文件都存在")
                    
                    # 检查是否需要组合视频
                    final_video_path = task_status.get('final_video_path')
                    if not final_video_path or not os.path.exists(final_video_path):
                        logger.info(f"🎬 最终视频文件不存在，开始组合...")
                        task_manager.combine_videos(task_status)
                    else:
                        logger.info(f"✅ 最终视频文件已存在: {final_video_path}")
        elif task_status['tasks'] and task_status['status'] == 'completed':
            # 检查已完成任务的视频文件是否存在
            logger.info(f"🔍 检查已完成任务的视频文件...")
            completed_tasks = [task for task in task_status['tasks'] if task['status'] in ['completed', 'downloading']]
            missing_videos = []
            
            for task in completed_tasks:
                video_path = task.get('video_path')
                if not video_path or not os.path.exists(video_path):
                    missing_videos.append(task)
                    logger.warning(f"⚠️ 第{task['page_number']}页视频文件缺失: {video_path}")
            
            if missing_videos:
                logger.info(f"📥 发现 {len(missing_videos)} 个已完成任务的视频文件缺失，开始下载...")
                
                # 下载缺失的视频文件
                if task_manager.download_completed_videos(task_status):
                    logger.info(f"✅ 视频文件下载完成")
                    
                    # 重新组合视频
                    logger.info(f"🎬 开始组合最终视频...")
                    task_manager.combine_videos(task_status)
                else:
                    logger.error(f"❌ 视频文件下载失败")
            else:
                logger.info(f"✅ 所有已完成任务的视频文件都存在")
                
                # 检查是否需要组合视频
                final_video_path = task_status.get('final_video_path')
                if not final_video_path or not os.path.exists(final_video_path):
                    logger.info(f"🎬 最终视频文件不存在，开始组合...")
                    task_manager.combine_videos(task_status)
                else:
                    logger.info(f"✅ 最终视频文件已存在: {final_video_path}")
                
        else:
            # 开始新的任务
            logger.info(f"🆕 开始新的处理任务...")

            # 初始化文件管理器
            logger.info(f"📁 初始化文件管理器...")
            file_manager = FileManager()

            # 处理指定的PPT文件或扫描input文件夹
            ppt_file = None
            if args.input:
                # 使用指定的PPT文件
                logger.info(f"🔍 验证指定的PPT文件...")
                validation_result = file_manager.validate_ppt_file(args.input)

                if not validation_result['valid']:
                    logger.error(f"❌ PPT文件验证失败: {validation_result['error']}")
                    return

                ppt_file = args.input
                file_info = validation_result['file_info']

                logger.info(f"📄 使用指定的PPT文件: {file_info['name']}")
                logger.info(f"📊 文件大小: {file_info['size']/1024/1024:.2f} MB")
                logger.info(f"📁 文件路径: {file_info['path']}")

                if not validation_result['pdf_exists']:
                    logger.warning(f"⚠️ 未找到对应的PDF文件")
                    logger.warning(f"💡 系统将尝试自动转换PPT为PDF")
            else:
                # 扫描input文件夹中的PPT文件
                logger.info(f"🔍 扫描输入文件夹中的PPT文件...")
                ppt_files = file_manager.get_ppt_files()
                if not ppt_files:
                    logger.error(f"❌ 输入文件夹中没有找到PPT文件")
                    logger.error(f"📁 请检查input文件夹中是否有.pptx或.ppt文件，或使用 -i 参数指定PPT文件")
                    return

                # 处理第一个PPT文件
                ppt_file = ppt_files[0]
                file_size = os.path.getsize(ppt_file) if os.path.exists(ppt_file) else 0
                logger.info(f"📄 在input文件夹中找到PPT文件: {os.path.basename(ppt_file)} ({file_size/1024/1024:.2f} MB)")
            
            # 设置任务状态文件路径
            ppt_path = Path(ppt_file)

            # 如果是指定的PPT文件，将任务状态文件放在input文件夹中
            if args.input:
                # 对于指定的PPT文件，状态文件放在input文件夹中，使用PPT文件名
                input_folder = Path("input")
                task_manager.task_status_file = input_folder / ppt_path.with_suffix('.json').name
                # 确保input文件夹存在
                input_folder.mkdir(exist_ok=True)
            else:
                # 对于input文件夹中的PPT文件，保持原有逻辑
                input_folder = Path("input")
                task_manager.task_status_file = input_folder / ppt_path.with_suffix('.json').name

            logger.info(f"📝 任务状态文件路径: {task_manager.task_status_file}")
            
            # 检查是否已存在任务状态文件
            if os.path.exists(task_manager.task_status_file):
                logger.info(f"📂 发现已存在的任务状态文件: {task_manager.task_status_file}")
                logger.info(f"🔍 读取现有任务状态...")
                
                # 读取现有任务状态
                existing_task_status = task_manager.load_task_status()
                
                # 检查是否有未完成的任务
                if existing_task_status.get('tasks'):
                    # 兼容新旧配置文件格式
                    progress_tracking = existing_task_status.get('progress_tracking', {})
                    processing_status = progress_tracking.get('status', 'not_started')
                    
                    if processing_status != 'completed':
                        logger.info(f"🔄 检测到未完成的任务，继续处理...")
                        logger.info(f"📊 总任务数: {progress_tracking.get('total_tasks', len(existing_task_status['tasks']))}")
                        logger.info(f"✅ 已完成: {progress_tracking.get('completed_tasks', 0)}")
                        logger.info(f"❌ 失败: {progress_tracking.get('failed_tasks', 0)}")
                        
                        # 继续处理未完成的任务
                        remaining_tasks = [task for task in existing_task_status['tasks'] if task['status'] not in ['completed', 'failed']]
                        if remaining_tasks:
                            logger.info(f"⏳ 继续处理 {len(remaining_tasks)} 个未完成的任务...")
                            
                            # 更新video_generator的配置文件路径，确保能访问到工作室图片信息
                            task_manager.video_generator.task_status_file_path = str(task_manager.task_status_file)
                            # 重新加载配置以获取工作室图片信息
                            task_manager.video_generator.config = task_manager.video_generator._load_config()
                            
                            # 使用完整的新格式配置（如果存在）
                            tasks_to_process = existing_task_status.get('full_config', {}).get('tasks', existing_task_status['tasks'])
                            
                            updated_status = task_manager.process_all_tasks(tasks_to_process)
                            
                            # 组合视频
                            if updated_status['completed_tasks'] > 0:
                                logger.info(f"🎬 开始组合最终视频...")
                                task_manager.combine_videos(updated_status)
                        else:
                            logger.info(f"✅ 所有任务已完成")
                            
                            # 检查已完成任务的视频文件是否存在
                            logger.info(f"🔍 检查已完成任务的视频文件...")
                            completed_tasks = [task for task in existing_task_status['tasks'] if task['status'] == 'completed']
                            missing_videos = []
                            
                            for task in completed_tasks:
                                video_path = task.get('video_path')
                                if not video_path or not os.path.exists(video_path):
                                    missing_videos.append(task)
                                    logger.warning(f"⚠️ 第{task['page_number']}页视频文件缺失: {video_path}")
                            
                            if missing_videos:
                                logger.info(f"📥 发现 {len(missing_videos)} 个已完成任务的视频文件缺失，开始下载...")
                                
                                # 下载缺失的视频文件
                                if task_manager.download_completed_videos(existing_task_status):
                                    logger.info(f"✅ 视频文件下载完成")
                                    
                                    # 重新组合视频
                                    logger.info(f"🎬 开始组合最终视频...")
                                    task_manager.combine_videos(existing_task_status)
                                else:
                                    logger.error(f"❌ 视频文件下载失败")
                            else:
                                logger.info(f"✅ 所有已完成任务的视频文件都存在")
                                
                                # 检查是否需要组合视频
                                final_video_path = existing_task_status.get('final_video_path')
                                if not final_video_path or not os.path.exists(final_video_path):
                                    logger.info(f"🎬 最终视频文件不存在，开始组合...")
                                    task_manager.combine_videos(existing_task_status)
                                else:
                                    logger.info(f"✅ 最终视频文件已存在: {final_video_path}")
                else:
                    logger.info(f"📋 任务已完成或没有任务，跳过处理")
            else:
                logger.info(f"📝 未找到任务状态文件，开始新任务...")
                
                # 提取任务
                logger.info(f"📋 开始分析PPT内容...")
                tasks = task_manager.extract_tasks_from_ppt(ppt_file)
                if not tasks:
                    logger.error(f"❌ 没有找到需要生成视频的任务")
                    logger.error(f"💡 请检查PPT文件的备注页是否包含需要播报的内容")
                    return
                
                # 更新video_generator的配置文件路径，确保能访问到工作室图片信息
                task_manager.video_generator.task_status_file_path = str(task_manager.task_status_file)
                # 重新加载配置以获取工作室图片信息
                task_manager.video_generator.config = task_manager.video_generator._load_config()
                
                # 处理所有任务
                logger.info(f"🚀 开始批量处理视频生成任务...")
                task_status = task_manager.process_all_tasks(tasks)
                
                # 组合视频
                if task_status['completed_tasks'] > 0:
                    logger.info(f"🎬 开始组合最终视频...")
                    task_manager.combine_videos(task_status)
                else:
                    logger.warning(f"⚠️ 没有成功完成的任务，跳过视频组合")
        
        program_time = time.time() - program_start_time
        logger.info(f"🎉 PPT转数字人视频处理完成！")
        logger.info(f"⏱️ 总运行时间: {program_time:.2f}秒 ({program_time/60:.1f}分钟)")
        
    except Exception as e:
        program_time = time.time() - program_start_time
        logger.error(f"❌ 处理过程中发生错误: {e}")
        logger.error(f"⏱️ 错误发生时已运行: {program_time:.2f}秒")
        import traceback
        logger.error(f"📋 详细错误信息:")
        logger.error(f"{traceback.format_exc()}")
        
        logger.info(f"💡 如果问题持续存在，请检查：")
        logger.info(f"   1. 网络连接是否正常")
        logger.info(f"   2. API密钥是否配置正确")
        logger.info(f"   3. 输入文件格式是否正确")
        logger.info(f"   4. 磁盘空间是否充足")


if __name__ == "__main__":
    main()