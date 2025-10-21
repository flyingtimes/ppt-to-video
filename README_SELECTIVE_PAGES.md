# 选择性页面重新制作功能

## 概述

这个功能允许您重新下载、制作指定页面的视频，并智能合并成完整视频。当某些页面的视频生成失败或需要更新时，这个功能特别有用。

## 核心功能

### 🎯 智能页面选择
- 支持多种选择格式：字母、数字、范围
- 混合格式支持：`1,3-5,8`
- 大小写不敏感

### 🔄 完整重新制作流程
1. 解析页面选择
2. 删除现有视频文件
3. 重新提交RunningHub任务
4. 等待任务完成
5. 下载并处理视频
6. Head模式自动组合
7. 智能合并输出

### 📊 详细进度跟踪
- 实时状态更新
- 错误处理和恢复
- 详细的日志记录

## 快速开始

### 1. 基本使用

```bash
# 重新制作第1、2、3页
python redo_pages.py -p "a,b,c"

# 重新制作第1、3、5、6、7、8页
python redo_pages.py -p "1,3,5-8"

# 保留现有文件直接覆盖
python redo_pages.py -p "2,4,6" --no-delete
```

### 2. 页面选择格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 字母列表 | `a,b,c` | 第1、2、3页 |
| 数字列表 | `1,3,5` | 第1、3、5页 |
| 字母范围 | `a-e` | 第1到5页 |
| 数字范围 | `1-5` | 第1到5页 |
| 混合格式 | `1,3-5,8` | 第1、3、4、5、8页 |

### 3. 编程接口

```python
from tools.selective_page_processor import SelectivePageProcessor

# 创建处理器
processor = SelectivePageProcessor()

# 处理选择性页面
success = processor.process_selective_pages(
    selection="a,b,c",      # 页面选择
    delete_existing=True     # 删除现有视频
)

# 只解析页面选择
pages = processor.parse_page_selection("1,3,5-8")  # [1, 3, 5, 6, 7, 8]

# 只合并现有视频
success = processor.merge_selective_videos([1, 3, 5])
```

## 处理流程详解

### 步骤1：页面解析
```
输入: "1,3,5-8"
解析: [1, 3, 5, 6, 7, 8]
验证: 页码在有效范围内且有备注内容
```

### 步骤2：文件清理（可选）
- 删除指定页面的 `.mp4` 视频文件
- 删除相关的 `.png` 字幕文件
- 清理临时文件

### 步骤3：任务重新提交
- 重置任务状态（删除task_id，设为pending）
- 提交新的RunningHub视频生成任务
- 更新JSON配置文件

### 步骤4：任务监控
- 每20秒检查一次任务状态
- 自动处理成功、失败、超时情况
- 实时更新任务进度

### 步骤5：视频下载
- 任务完成后自动下载视频文件
- 验证文件完整性
- 更新文件大小信息

### 步骤6：Head模式处理
对于Head模式页面：
- 查找对应的PPT幻灯片图片
- 创建圆形遮罩
- 组合幻灯片和数字人视频
- 添加字幕

### 步骤7：智能合并
- 收集所有完成的视频文件
- 按页码排序
- 使用FFmpeg合并
- 生成带时间戳的输出文件

## 输出文件

### 文件命名
```
outputs/{project}_pages_{pages}_{timestamp}.mp4
```

### 示例
```
outputs/my_presentation_pages_1_3_5_20241021_143022.mp4
```

## 错误处理

### 常见错误类型
1. **配置文件缺失** - 需要先运行主程序处理PPT
2. **页码超出范围** - 检查PPT总页数
3. **无备注内容** - 该页面没有可生成视频的内容
4. **RunningHub任务失败** - 网络或API问题
5. **视频下载失败** - 文件URL或权限问题

### 错误恢复策略
- **部分失败**：记录失败页面，保留成功页面
- **网络中断**：可重新运行，已完成页面被跳过
- **权限问题**：检查文件和目录权限

## 配置要求

### 必需目录结构
```
ppt-to-video/
├── input/
│   └── *.json           # 任务配置文件
├── outputs/             # 输出目录
├── temp/               # 临时文件目录
└── tools/
    ├── selective_page_processor.py
    └── runninghub_api.py
```

### 环境变量
确保 `.env` 文件包含：
```env
RUNNINGHUB_API_KEY=your_api_key
RUNNINGHUB_WEBAPP_ID=your_webapp_id
CHARACTER_IMAGE_PATH=path/to/character.png
REFERENCE_AUDIO_PATH=path/to/reference.mp3
```

## 最佳实践

### 1. 使用建议
- **小批量处理**：建议一次处理不超过10个页面
- **网络稳定性**：确保网络连接稳定
- **监控进度**：关注日志输出

### 2. 性能优化
- **并发控制**：自动控制RunningHub任务并发数
- **资源管理**：自动清理临时文件
- **缓存复用**：复用现有配置和状态

### 3. 故障排除
1. 查看详细日志：`redo_pages.log`
2. 验证配置文件格式
3. 先用单页测试功能
4. 检查文件权限

## 示例场景

### 场景1：修复失败页面
```bash
# 第3页和第7页视频生成失败
python redo_pages.py -p "3,7"
```

### 场景2：更新内容
```bash
# 更新第1-5页内容
python redo_pages.py -p "1-5"
```

### 场景3：快速测试
```bash
# 只测试第1页
python redo_pages.py -p "a" --no-delete
```

## 技术细节

### 核心组件
- **SelectivePageProcessor**：主处理器
- **页面解析器**：支持多种选择格式
- **任务管理器**：与现有TaskManager集成
- **视频处理器**：复用VideoProcessor功能

### API集成
- **RunningHub API**：视频生成和下载
- **FFmpeg**：视频合并和组合
- **PyMuPDF**：PDF页面处理

### 错误处理
- **异常捕获**：完整的try-catch机制
- **状态恢复**：支持断点续传
- **日志记录**：详细的操作日志

## 版本信息

- **版本**：v1.0.0
- **发布日期**：2024-10-21
- **兼容性**：与现有PPT转视频系统完全兼容

## 支持和帮助

### 查看帮助
```bash
python redo_pages.py -h
```

### 查看日志
```bash
tail -f redo_pages.log
```

### 测试功能
```bash
python test_selective_processor.py
```

---

*这个功能增强了现有PPT转视频系统的灵活性和可维护性，让用户能够更高效地管理和更新视频内容。*