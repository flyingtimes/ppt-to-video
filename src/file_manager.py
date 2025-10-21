"""
文件管理器
"""
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FileManager:
    """文件管理器"""
    
    def __init__(self):
        self.input_dir = Path("input")
        self.output_dir = Path("outputs")
        self.test_dir = Path("test")
        
        # 确保目录存在
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def get_ppt_files(self) -> List[str]:
        """
        获取输入文件夹中的所有PPT文件

        Returns:
            PPT文件路径列表
        """
        ppt_files = []

        try:
            for file_path in self.input_dir.glob("*.ppt*"):
                if file_path.suffix.lower() in ['.pptx', '.ppt']:
                    # 检查是否有对应的PDF文件
                    pdf_path = file_path.with_suffix('.pdf')
                    if pdf_path.exists():
                        ppt_files.append(str(file_path))
                    else:
                        logger.warning(f"未找到对应的PDF文件: {file_path}")

        except Exception as e:
            logger.error(f"获取PPT文件失败: {e}")

        return ppt_files

    def validate_ppt_file(self, ppt_file: str) -> Dict[str, Any]:
        """
        验证指定的PPT文件

        Args:
            ppt_file: PPT文件路径

        Returns:
            验证结果字典，包含是否有效、文件信息等
        """
        try:
            ppt_path = Path(ppt_file)

            # 检查文件是否存在
            if not ppt_path.exists():
                return {
                    'valid': False,
                    'error': f"文件不存在: {ppt_file}",
                    'file_info': {}
                }

            # 检查文件扩展名
            if ppt_path.suffix.lower() not in ['.pptx', '.ppt']:
                return {
                    'valid': False,
                    'error': f"不支持的文件格式: {ppt_path.suffix}",
                    'file_info': {}
                }

            # 获取文件信息
            file_info = {
                'name': ppt_path.name,
                'size': ppt_path.stat().st_size,
                'path': str(ppt_path.absolute()),
                'directory': str(ppt_path.parent)
            }

            # 检查是否有对应的PDF文件
            pdf_path = ppt_path.with_suffix('.pdf')
            pdf_exists = pdf_path.exists()
            if not pdf_exists:
                logger.warning(f"⚠️ 未找到对应的PDF文件: {pdf_path}")
                logger.warning(f"💡 系统将尝试自动转换PPT为PDF")

            return {
                'valid': True,
                'error': None,
                'file_info': file_info,
                'pdf_exists': pdf_exists,
                'pdf_path': str(pdf_path)
            }

        except Exception as e:
            logger.error(f"验证PPT文件时发生错误: {e}")
            return {
                'valid': False,
                'error': f"验证文件时发生错误: {str(e)}",
                'file_info': {}
            }
    
    def create_work_dir(self, ppt_file: str) -> Path:
        """
        为PPT文件创建工作目录
        
        Args:
            ppt_file: PPT文件路径
            
        Returns:
            工作目录路径
        """
        try:
            ppt_name = Path(ppt_file).stem
            work_dir = self.output_dir / f"work_{ppt_name}"
            work_dir.mkdir(exist_ok=True)
            
            # 创建子目录
            (work_dir / "pages").mkdir(exist_ok=True)
            (work_dir / "videos").mkdir(exist_ok=True)
            
            return work_dir
            
        except Exception as e:
            logger.error(f"创建工作目录失败: {e}")
            return Path("temp_work")
    
    def organize_pages_content(self, ppt_content: Dict[str, Any], work_dir: Path) -> List[Dict[str, Any]]:
        """
        按页码组织内容到工作文件夹
        
        Args:
            ppt_content: PPT内容字典
            work_dir: 工作目录
            
        Returns:
            按页码组织的内容列表
        """
        pages_content = []
        
        try:
            pages_dir = work_dir / "pages"
            
            for i, page_data in enumerate(ppt_content['ppt_content']):
                page_number = i + 1
                
                # 创建页面目录
                page_dir = pages_dir / f"page_{page_number:03d}"
                page_dir.mkdir(exist_ok=True)
                
                # 保存备注文本
                notes_file = page_dir / "notes.txt"
                with open(notes_file, 'w', encoding='utf-8') as f:
                    f.write(page_data['notes_text'])
                
                # 复制PDF页面图片
                if i < len(ppt_content['pdf_pages']):
                    pdf_image = Path(ppt_content['pdf_pages'][i])
                    if pdf_image.exists():
                        shutil.copy2(pdf_image, page_dir / "slide.png")
                
                # 准备视频文件路径
                video_file = page_dir / "video.mp4"
                
                page_content = {
                    'page_number': page_number,
                    'page_dir': page_dir,
                    'notes_text': page_data['notes_text'],
                    'is_full_mode': page_data['is_full_mode'],
                    'slide_image': page_dir / "slide.png",
                    'notes_file': notes_file,
                    'video_file': video_file
                }
                
                pages_content.append(page_content)
                
        except Exception as e:
            logger.error(f"组织页面内容失败: {e}")
        
        return pages_content
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_dir = Path("temp")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")