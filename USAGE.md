# PPT转数字人视频项目 - 使用说明

## 项目概述

本项目能够自动读取PPT或PPTX文件中的备注内容，调用RunningHub的AI应用能力生成数字人视频，并最终形成数字人讲解PPT的完整视频。

## 功能特点

1. **智能模式识别**：
   - 备注以`[full]`开头：生成16:9或4:3比例的满屏数字人播报视频
   - 普通备注：生成包含头部的数字人讲解视频

2. **自动工作流**：
   - 读取PPTX备注内容
   - 调用RunningHub AI生成数字人视频
   - 自动添加字幕（20号字体，黑体，浅黄色）
   - 合成最终视频

3. **工作室效果图管理**：
   - 首次生成时自动创建工作室效果图
   - 后续生成时复用已保存的工作室效果图

## 安装和配置

### 1. 环境要求

- Python 3.8+
- UV包管理器
- FFmpeg（用于视频处理）

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置环境变量

编辑`.env`文件，设置以下参数：

```env
# RunningHub API 配置
RUNNINGHUB_API_KEY=your_api_key_here
RUNNINGHUB_BASE_URL=https://www.runninghub.cn
RUNNINGHUB_WEBAPP_ID=1971965779661025281

# 数字人配置
CHARACTER_IMAGE_PATH=characters/man/input.png
REFERENCE_AUDIO_PATH=characters/man/reference.mp3
FULL_STUDIO_IMAGE_PATH=models/full_studio_image.png
HEAD_STUDIO_IMAGE_PATH=models/head_studio_image.png
```

## 使用方法

### 1. 准备输入文件

将PPTX文件和对应的PDF文件放在`./input`目录下：

```
input/
├── presentation.pptx
└── presentation.pdf
```

### 2. 准备数字人素材

将数字人形象图片和参考音频放在`characters`目录下：

```
characters/
└── man/
    ├── input.png      # 数字人形象图片
    └── reference.mp3  # 参考音频
```

### 3. 运行主程序

```bash
python main.py
```

### 4. 输出结果

程序将在`./outputs`目录下生成以下内容：

```
outputs/
├── config.json                    # 配置文件
├── work_presentation_name/        # 工作目录
│   ├── pages/
│   │   ├── page_001/
│   │   │   ├── notes.txt
│   │   │   ├── slide.png
│   │   │   └── video.mp4
│   │   └── ...
│   ├── circular_mask.png
│   ├── merged_video.mp4           # 最终合并视频
│   └── ...
└── studio_image_*.png           # 工作室效果图
```

## 核心模块说明

### 1. RunningHub API 集成 (`tools/runninghub_api.py`)

- 文件上传功能
- 数字人视频生成
- 任务状态查询
- 结果下载

### 2. 视频生成器 (`src/video_generator.py`)

- 管理工作室效果图
- 协调视频生成流程
- 保存任务信息到配置文件

### 3. 视频处理器 (`src/video_processor.py`)

- 字幕生成（20号字体，黑体，浅黄色）
- 视频组合和合成
- 圆形遮罩创建

### 4. 工作室效果图管理 (`tools/studio_image_manager.py`)

- 生成和管理工作室效果图
- 检查效果图状态
- 重新生成效果图

## 故障排除

### 1. RunningHub API 上传失败

如果遇到401错误，请检查：
- API密钥是否正确
- 网络连接是否正常
- API服务是否可用

### 2. FFmpeg 错误

确保系统已安装FFmpeg：
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# 从 https://ffmpeg.org/download.html 下载
```

### 3. 字体问题

如果中文字幕显示异常，请确保系统安装了中文字体：
- macOS：系统自带
- Windows：确保安装了黑体或微软雅黑
- Linux：安装中文字体包

### 4. 文件权限问题

确保程序对以下目录有读写权限：
- `./input`
- `./outputs`
- `./models`
- `./temp`

## 测试

### 测试数字人视频生成

```bash
python test_video_generation.py
```

### 测试完整流程

```bash
python main.py
```

## 注意事项

1. **首次运行**：首次生成数字人视频时，程序会自动生成工作室效果图，这可能需要一些时间。

2. **API限制**：RunningHub API可能有调用频率限制，请合理使用。

3. **文件格式**：
   - PPTX文件必须包含备注内容
   - PDF文件必须与PPTX文件同名
   - 数字人图片建议使用PNG格式
   - 参考音频建议使用MP3格式

4. **字幕样式**：字幕使用20号黑体字，浅黄色，黑色描边，居中显示。

## 技术支持

如果遇到问题，请检查：
1. 日志文件：`ppt_to_video.log`
2. 配置文件：`output/config.json`
3. 环境变量：`.env`文件

## 扩展功能

项目支持以下扩展：
1. 自定义字幕样式
2. 批量处理多个PPT文件
3. 自定义视频输出参数
4. 更多数字人形象支持