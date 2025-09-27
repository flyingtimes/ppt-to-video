# RunningHub AI 应用使用文档

数字人播报工作流的调用示例如下，节点54代表是full模式的视频还是head模式的视频，节点55为1代表输出自动修图的工作室效果的图片，节点55为2代表不需要。
一般第一次生成全身视频或者第一次生成肖像视频的时候，才需要输出工作室效果图片，并保存起来。后续调用的时候，直接使用全身和肖像工作室效果图生成视频，此时节点55的参数为2
```
curl --location --request POST 'https://www.runninghub.cn/task/openapi/ai-app/run' \
--header 'Host: www.runninghub.cn' \
--header 'Content-Type: application/json' \
--data-raw '{
    "webappId": "1971965779661025281",
    "apiKey": "481e7653f5334058bd642478fdca8ddd",
    "nodeInfoList": [
        {
            "nodeId": "55",
            "fieldName": "value",
            "fieldValue": "1",
            "description": "是否需要自动修图（1:需要 2:不需要）"
        },
        {
            "nodeId": "54",
            "fieldName": "value",
            "fieldValue": "2",
            "description": "1:全身 2: 肖像"
        },
        {
            "nodeId": "48",
            "fieldName": "image",
            "fieldValue": "b6ce68aa6738ff0defde5cfc0ec34c52cd0918d4089fa0ecf74af4c168452eb3.gif",
            "description": "人物图片"
        },
        {
            "nodeId": "47",
            "fieldName": "audio",
            "fieldValue": "007c991b216f73404eead02468903ce7400ad59e6f3971833556eca51ddb24e7.mp3",
            "description": "参考音频"
        },
        {
            "nodeId": "38",
            "fieldName": "text",
            "fieldValue": "我的汇报就到这里",
            "description": "要说的话"
        }
    ]
}'
```
返回的结果示例如下,taskStatus为RUNNING代表人物还没执行完，SUCCESS代表执行完毕，一定要将taskId记录下来供后续获取结果用
```
{
    "code": 0,
    "msg": "success",
    "data": {
        "netWssUrl": "wss://www.runninghub.cn:443/ws/c_instance?c_host=222.186.161.123&c_port=85&clientId=14caa1db2110a81629c101b9bb4cb0ce&workflowId=1876205853438365698&Rh-Comfy-Auth=eyJ1c2VySWQiOiJkZTBkYjZmMjU2NGM4Njk3YjA3ZGY1NWE3N2YwN2JlOSIsInNpZ25FeHBpcmUiOjE3NDQxMTI1MjEyMzYsInRzIjoxNzQzNTA3NzIxMjM2LCJzaWduIjoiZDExOTE0MzkwMjJlNjViMjQ5MjU2YzU2ZmQxYTUwZjUifQ%3D%3D",
        "taskId": "1907035719658053634",
        "clientId": "14caa1db2110a81629c101b9bb4cb0ce",
        "taskStatus": "RUNNING",
        "promptTips": "{\"result\": true, \"error\": null, \"outputs_to_execute\": [\"115\", \"129\", \"124\"], \"node_errors\": {}}"
    }
}
```
查询任务状态和结果的示例如下：
```
curl --location --request POST 'https://www.runninghub.cn/task/openapi/status' \
--header 'Host: www.runninghub.cn' \
--header 'Content-Type: application/json' \
--data-raw '{
    "apiKey": "请输入自己的apiKey",
    "taskId": "1904152026220003329"
}'
```
返回的响应如下，其中data可以是["QUEUED","RUNNING","FAILED","SUCCESS"]
```
{
  "code": 0,
  "msg": "",
  "data": ""
}
```
如果查询到任务的结果是SUCCESS，则可以使用以下示例获取输出结果：
```
curl --location --request POST 'https://www.runninghub.cn/task/openapi/outputs' \
--header 'Host: www.runninghub.cn' \
--header 'Content-Type: application/json' \
--data-raw '{
    "apiKey": "请输入自己的apiKey",
    "taskId": "1904152026220003329"
}'
```
返回的信息如下：
```
{
    "code": 0,
    "msg": "success",
    "data": [
        {
            "fileUrl": "https://rh-images.xiaoyaoyou.com/de0db6f2564c8697b07df55a77f07be9/output/ComfyUI_00033_hpgko_1742822929.png",
            "fileType": "png",
            "taskCostTime": "0",
            "nodeId": "9"
        }
    ]
}
```
在我们这个数字人工作流中，主要是获取nodeId为60的工作室效果的图片，和nodeId为22的输出视频文件，使用下载程序下载fileUrl可以获取结果