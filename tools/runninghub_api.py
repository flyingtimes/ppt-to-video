"""
RunningHub AI API 集成工具
"""
import os
import requests
import json
import logging
import time
import hashlib
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class RunningHubAPI:
    """RunningHub AI API 客户端"""
    
    def __init__(self):
        self.api_key = os.getenv('RUNNINGHUB_API_KEY')
        self.base_url = os.getenv('RUNNINGHUB_BASE_URL', 'https://www.runninghub.cn')
        self.webapp_id = os.getenv('RUNNINGHUB_WEBAPP_ID')
        
        if not self.api_key:
            logger.warning("RUNNINGHUB_API_KEY 未配置")
        
        if not self.webapp_id:
            logger.warning("RUNNINGHUB_WEBAPP_ID 未配置")
    
    def _get_file_hash(self, file_path: str) -> Optional[str]:
        """
        获取文件内容hash值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件hash值，失败返回None
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 读取文件内容并计算SHA256 hash（hex格式）
            with open(file_path, 'rb') as f:
                file_content = f.read()
                sha256_hash = hashlib.sha256(file_content).hexdigest()
            
            # 获取文件扩展名
            file_ext = os.path.splitext(file_path)[1].lower()
            if not file_ext:
                # 如果没有扩展名，根据文件类型推断
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    file_ext = '.png'  # 默认图片格式
                elif file_path.lower().endswith(('.mp3', '.wav', '.aac')):
                    file_ext = '.mp3'  # 默认音频格式
            
            # 拼接hash和扩展名
            file_id = sha256_hash + file_ext
            
            logger.info(f"文件hash计算成功: {file_path} -> {file_id}")
            return file_id
                
        except Exception as e:
            logger.error(f"计算文件hash时发生错误: {e}")
            return None
    
    def generate_digital_human_video(self, text: str, character_image_path: str, 
                                  reference_audio_path: str, mode: str = "head",
                                  first_time: bool = False) -> Optional[Dict[str, Any]]:
        """
        生成数字人视频
        
        Args:
            text: 播报文本内容
            character_image_path: 人物图片路径
            reference_audio_path: 参考音频路径
            mode: 视频模式（full/head）
            first_time: 是否为第一次生成（需要工作室效果图）
            
        Returns:
            API响应结果
        """
        start_time = time.time()
        
        logger.info(f"🚀 RunningHub API - 开始生成数字人视频")
        logger.info(f"🎭 模式: {mode.upper()}")
        logger.info(f"📝 文本长度: {len(text)}字符")
        logger.info(f"👤 人物图片: {character_image_path}")
        logger.info(f"🔊 参考音频: {reference_audio_path}")
        logger.info(f"🎨 首次生成工作室图: {first_time}")
        
        try:
            # 检查配置
            if not self.api_key or not self.webapp_id:
                logger.error("❌ 未配置API密钥或webapp_id")
                logger.error(f"API Key: {'已配置' if self.api_key else '未配置'}")
                logger.error(f"WebApp ID: {'已配置' if self.webapp_id else '未配置'}")
                return None
            
            logger.info(f"✅ API配置检查通过")
            logger.info(f"🌐 API Base URL: {self.base_url}")
            
            # 获取图片和音频文件的hash值
            logger.info(f"🔐 计算文件hash值...")
            
            hash_start = time.time()
            image_hash = self._get_file_hash(character_image_path)
            audio_hash = self._get_file_hash(reference_audio_path)
            hash_time = time.time() - hash_start
            
            logger.info(f"⏱️ 文件hash计算耗时: {hash_time:.2f}秒")
            logger.info(f"🖼️ 图片hash: {image_hash[:20]}...{image_hash[-10:] if image_hash else 'None'}")
            logger.info(f"🔊 音频hash: {audio_hash[:20]}...{audio_hash[-10:] if audio_hash else 'None'}")
            
            if not image_hash or not audio_hash:
                logger.error("❌ 文件hash计算失败")
                return None
            
            # 构建API请求数据
            logger.info(f"📋 构建API请求数据...")
            
            node_info_list = [
                {
                    "nodeId": "55",
                    "fieldName": "value",
                    "fieldValue": "1" if first_time else "2",
                    "description": "是否需要自动修图（1:需要 2:不需要）"
                },
                {
                    "nodeId": "54",
                    "fieldName": "value",
                    "fieldValue": "1" if mode == "full" else "2",
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
                    "fieldValue": text,
                    "description": "要说的话"
                }
            ]
            
            # 构建请求数据
            request_data = {
                "webappId": self.webapp_id,
                "apiKey": self.api_key,
                "nodeInfoList": node_info_list
            }
            
            logger.info(f"📤 发送API请求...")
            logger.debug(f"请求URL: {self.base_url}/task/openapi/ai-app/run")
            logger.debug(f"请求体大小: {len(json.dumps(request_data))}字节")
            
            # 发送请求
            request_start = time.time()
            response = requests.post(
                f"{self.base_url}/task/openapi/ai-app/run",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            request_time = time.time() - request_start
            
            logger.info(f"⏱️ API请求耗时: {request_time:.2f}秒")
            logger.info(f"📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"响应内容: {result}")
                
                if result.get('code') == 0:
                    task_data = result.get('data', {})
                    task_id = task_data.get('taskId')
                    total_time = time.time() - start_time
                    
                    logger.info(f"✅ 数字人视频生成请求成功！")
                    logger.info(f"🆔 任务ID: {task_id}")
                    logger.info(f"⏱️ 总耗时: {total_time:.2f}秒")
                    
                    return task_data
                else:
                    total_time = time.time() - start_time
                    logger.error(f"❌ 数字人视频生成请求失败")
                    logger.error(f"📋 错误码: {result.get('code')}")
                    logger.error(f"💬 错误信息: {result.get('msg')}")
                    logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
                    return None
            else:
                total_time = time.time() - start_time
                logger.error(f"❌ 数字人视频生成请求失败")
                logger.error(f"📊 HTTP状态码: {response.status_code}")
                logger.error(f"💬 响应内容: {response.text[:200]}..." if len(response.text) > 200 else f"💬 响应内容: {response.text}")
                logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
                return None
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ 生成数字人视频时发生错误: {e}")
            logger.error(f"⏱️ 失败时已运行: {total_time:.2f}秒")
            import traceback
            logger.error(f"📋 错误详情: {traceback.format_exc()}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态（QUEUED, RUNNING, FAILED, SUCCESS）
        """
        try:
            request_data = {
                "apiKey": self.api_key,
                "taskId": task_id
            }
            
            response = requests.post(
                f"{self.base_url}/task/openapi/status",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return result.get('data')
                else:
                    logger.error(f"获取任务状态失败: {result.get('msg')}")
                    return None
            else:
                logger.error(f"获取任务状态请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取任务状态时发生错误: {e}")
            return None
    
    def get_task_outputs(self, task_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取任务输出结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            输出结果列表
        """
        try:
            request_data = {
                "apiKey": self.api_key,
                "taskId": task_id
            }
            
            response = requests.post(
                f"{self.base_url}/task/openapi/outputs",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return result.get('data', [])
                else:
                    logger.error(f"获取任务输出失败: {result.get('msg')}")
                    return None
            else:
                logger.error(f"获取任务输出请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"获取任务输出时发生错误: {e}")
            return None
    
    def download_file(self, file_url: str, output_path: str) -> bool:
        """
        下载文件
        
        Args:
            file_url: 文件URL
            output_path: 输出路径
            
        Returns:
            是否下载成功
        """
        try:
            logger.info(f"开始下载文件: {file_url}")
            
            response = requests.get(file_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                # 确保输出目录存在
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存文件
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"文件下载完成: {output_path}")
                return True
            else:
                logger.error(f"文件下载失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"下载文件时发生错误: {e}")
            return False
    
    def wait_for_task_completion(self, task_id: str, timeout: int = 600) -> Optional[bool]:
        """
        等待任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            是否成功完成
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            
            if status == "SUCCESS":
                logger.info(f"任务完成: {task_id}")
                return True
            elif status == "FAILED":
                logger.error(f"任务失败: {task_id}")
                # 尝试获取任务输出以了解失败原因
                outputs = self.get_task_outputs(task_id)
                if outputs:
                    logger.error(f"任务输出: {outputs}")
                return False
            elif status in ["QUEUED", "RUNNING"]:
                logger.info(f"任务进行中: {task_id} - {status}")
                time.sleep(10)  # 等待10秒再检查
            else:
                logger.warning(f"未知状态: {status}")
                time.sleep(10)
        
        logger.error(f"任务超时: {task_id}")
        return False
    
    def generate_digital_human_video_full(self, text: str, character_image_path: str,
                                        reference_audio_path: str, mode: str = "head",
                                        first_time: bool = False, 
                                        save_task_id_callback=None) -> Optional[Dict[str, Any]]:
        """
        生成数字人视频的完整流程
        
        Args:
            text: 播报文本内容
            character_image_path: 人物图片路径
            reference_audio_path: 参考音频路径
            mode: 视频模式（full/head）
            first_time: 是否为第一次生成（需要工作室效果图）
            save_task_id_callback: 保存任务ID的回调函数
            
        Returns:
            包含任务信息和文件路径的字典
        """
        try:
            # 生成视频
            task_data = self.generate_digital_human_video(
                text, character_image_path, reference_audio_path, mode, first_time
            )
            
            if not task_data:
                logger.error("❌ 数字人视频生成请求失败")
                return None
            
            task_id = task_data.get('taskId')
            if not task_id:
                logger.error("❌ 未获取到任务ID")
                return None
            
            logger.info(f"✅ 任务提交成功，任务ID: {task_id}")
            
            # 立即保存任务ID到配置文件（通过回调函数）
            if save_task_id_callback:
                try:
                    logger.info(f"💾 立即保存任务ID到配置文件...")
                    save_task_id_callback(task_id, mode)
                    logger.info(f"✅ 任务ID已保存到配置文件: {task_id}")
                except Exception as e:
                    logger.error(f"❌ 保存任务ID失败: {e}")
                    # 继续执行，不因为保存失败而中断任务
            
            logger.info(f"等待任务完成: {task_id}")
            
            # 等待任务完成
            if not self.wait_for_task_completion(task_id):
                logger.error("❌ 任务执行失败，但任务ID已保存")
                # 返回任务ID信息，即使任务失败
                return {
                    "task_id": task_id,
                    "mode": mode,
                    "text": text,
                    "studio_image_path": None,
                    "video_path": None,
                    "outputs": [],
                    "task_failed": True,
                    "error_message": "任务执行失败"
                }
            
            # 获取输出结果
            outputs = self.get_task_outputs(task_id)
            if not outputs:
                logger.warning("⚠️ 未获取到输出结果，但任务ID已保存")
                # 返回任务ID信息，即使没有输出结果
                return {
                    "task_id": task_id,
                    "mode": mode,
                    "text": text,
                    "studio_image_path": None,
                    "video_path": None,
                    "outputs": [],
                    "task_failed": True,
                    "error_message": "未获取到输出结果"
                }
            
            # 解析输出结果
            result = {
                "task_id": task_id,
                "mode": mode,
                "text": text,
                "studio_image_path": None,
                "video_path": None,
                "outputs": outputs,
                "task_failed": False
            }
            
            # 下载工作室效果图和视频
            for output in outputs:
                file_url = output.get('fileUrl')
                file_type = output.get('fileType')
                node_id = output.get('nodeId')
                
                if not file_url or not file_type:
                    continue
                
                # 生成输出文件名
                timestamp = int(time.time())
                
                if node_id == "60" and first_time:  # 工作室效果图
                    output_path = f"outputs/studio_image_{mode}_{timestamp}.{file_type}"
                    if self.download_file(file_url, output_path):
                        result["studio_image_path"] = output_path
                        logger.info(f"工作室效果图下载完成: {output_path}")
                
                elif node_id == "22":  # 视频文件
                    output_path = f"outputs/video_{mode}_{timestamp}.{file_type}"
                    if self.download_file(file_url, output_path):
                        result["video_path"] = output_path
                        logger.info(f"视频文件下载完成: {output_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 生成数字人视频完整流程时发生错误: {e}")
            import traceback
            logger.error(f"📋 错误详情: {traceback.format_exc()}")
            return None