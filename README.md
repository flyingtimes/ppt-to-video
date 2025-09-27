# PPT转数字人视频工具

这个工具可以自动读取PPT文件中的备注内容，生成数字人讲解视频。

## 功能特性

- 自动提取PPT页面截图和备注文字
- 根据备注内容智能选择视频模式：
  - `[full]` 开头：生成全屏数字人视频
  - 普通：生成头部数字人 + PPT截图的组合视频
- 支持批量处理多个PPT文件
- 集成RunningHub AI数字人生成功能

## 安装依赖

1. 确保已安装Python 3.8+
2. 安装uv包管理器：
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. 安装项目依赖：
   ```bash
   uv sync
   ```

## 系统要求

- Python 3.8+
- ffmpeg（用于视频处理）
- 网络连接（用于RunningHub API调用）

## 配置

1. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```

2. 编辑`.env`文件，配置RunningHub API密钥：
   ```bash
   RUNNINGHUB_API_KEY=your_api_key_here
   ```

## 使用方法

### 命令行使用

```bash
# 处理单个PPT文件
python main.py --input ./input/your_presentation.pptx

# 处理所有PPT文件
python main.py --all

# 生成数字人视频（需要API密钥）
python main.py --input ./input/your_presentation.pptx --generate-humans
```

### 交互式使用

```bash
python main.py
```

程序会列出input目录中的所有PPT文件，让您选择要处理的文件。

## 项目结构

```
ppt-to-video/
├── input/              # 输入PPT文件目录
├── outputs/            # 输出视频目录
├── test/               # 测试视频文件
├── src/                # 源代码目录
│   ├── config.py       # 配置管理
│   ├── models.py       # 数据模型
│   ├── ppt_processor.py    # PPT处理
│   ├── video_processor.py  # 视频处理
│   └── runninghub_client.py # RunningHub API客户端
├── main.py             # 主程序
├── pyproject.toml      # 项目配置
└── RUNNINGHUB.md       # RunningHub API文档
```

## 视频模式说明

### Full模式
- 备注以 `[full]` 开头
- 生成全屏数字人播报视频
- 适用于需要突出数字人表现力的内容

### Head模式
- 备注不以 `[full]` 开头  
- 生成PPT截图 + 左下角头部数字人的组合视频
- 适用于需要与PPT内容配合展示的内容

## 开发说明

项目采用迭代开发方式：

1. **第一阶段**：使用测试视频文件进行视频合成
2. **第二阶段**：实现PPT分页和内容提取
3. **第三阶段**：实现视频组合和合并
4. **第四阶段**：集成RunningHub API生成数字人视频

## 注意事项

- 确保PPT文件中的备注内容清晰完整
- 建议每页备注文字控制在200字以内
- 需要确保ffmpeg已安装并可用
- 数字人视频生成需要网络连接和有效的API密钥

## 日志

程序运行时会生成 `ppt_to_video.log` 日志文件，记录详细的处理信息。