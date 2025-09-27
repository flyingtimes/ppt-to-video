# RunningHub AI 应用使用文档

## 概述
RunningHub 是一个AI驱动的数字人视频生成平台，能够将文本内容转换为数字人播报视频。

## 支持的视频模式

### 1. Full模式（全屏数字人）
- **标识**：备注以 `[full]` 开头
- **比例**：16:9 或 4:3
- **描述**：生成满屏的数字人播报讲解视频
- **适用场景**：需要突出数字人表现力的内容

### 2. Head模式（头部数字人）
- **标识**：备注不以 `[full]` 开头
- **描述**：仅生成包含头部的数字人讲解视频
- **适用场景**：需要与PPT内容配合展示的内容

## API使用方法

### 认证配置
```python
# 需要在.env文件中配置以下环境变量
RUNNINGHUB_API_KEY=your_api_key_here
RUNNINGHUB_BASE_URL=https://api.runninghub.com/v1
```

### 基本参数
- `text`: 播报文本内容（必填）
- `mode`: 视频模式（full/head，默认head）
- `voice_type`: 声音类型
- `resolution`: 分辨率设置
- `speed`: 语速控制（0.5-2.0）
- `emotion`: 情感表达

### 支持的声音类型
- `male_standard`: 男声标准
- `male_warm`: 男声温暖
- `female_standard`: 女声标准
- `female_sweet`: 女声甜美

### 支持的分辨率
- Full模式：`1920x1080`（16:9）、`1440x1080`（4:3）
- Head模式：`720x720`（方形头像）

### 调用示例
```python
# Full模式调用
response = runninghub_api.generate_video(
    text="您的播报内容",
    mode="full",
    resolution="1920x1080",
    voice_type="male_standard",
    speed=1.0
)

# Head模式调用  
response = runninghub_api.generate_video(
    text="您的播报内容",
    mode="head",
    voice_type="female_standard",
    speed=1.2,
    emotion="happy"
)
```

### 响应格式
```json
{
    "success": true,
    "video_id": "vh_123456789",
    "download_url": "https://storage.runninghub.com/videos/vh_123456789.mp4",
    "duration": 30.5,
    "file_size": 10485760
}
```

## 错误处理
- 网络连接问题：检查网络连接和API服务状态
- API配额限制：检查账户余额和调用次数限制
- 文本内容违规检查：确保文本内容符合平台规范
- 认证失败：检查API密钥是否正确配置

## 限制和注意事项
1. 文本长度限制：建议每页备注文字控制在200字以内，最多500字
2. 支持的语言：中文、英文
3. 生成时间：根据视频长度不同，通常需要1-5分钟
4. 文件格式：输出为MP4格式，H.264编码
5. 账户限制：免费用户每月可生成10分钟视频，付费用户无限制
6. 内容审核：所有文本内容都会经过AI内容审核

## 最佳实践
1. 文本预处理：去除特殊字符，确保标点符号正确
2. 分段处理：长文本建议分段生成后再合并
3. 质量检查：生成后进行视频质量检查
4. 错误重试：网络错误时建议重试机制
5. 缓存管理：相同文本可以缓存结果避免重复调用