# 游戏地图/关卡随机生成器组件 SPEC 接口规范文档
## 文档信息
|项|内容|
|----|----|
|文档名称|地图关卡随机生成器组件接口&数据边界SPEC|
|对应PRD|游戏地图/关卡随机生成器组件需求文档|
|版本|V1.0|
|开发语言|通用JSON接口规范（C#/TypeScript均可映射）|
|调用方式|同步调用；支持编辑器调试+游戏运行时调用|

## 一、通用约束说明
### 1.1 通用错误码规范
|错误码|说明|处理策略|
|----|----|----|
|0|成功|正常返回地图结构化数据|
|1001|参数越界（宽高/数量/概率超出边界）|自动截断为合法边界值，打印警告日志|
|1002|种子格式非法|自动生成随机6位数字种子兜底|
|1003|关卡校验失败（连续重试超限）|返回错误+最近一次生成的地图预览数据|
|1004|算法类型不存在|降级使用「房间分割算法」默认兜底|
|1005|模板名称不存在|加载内置默认简单模板|

### 1.2 通用数据边界总约束
1. 所有概率值：`[0,100]` 整数，单位：百分比
2. 所有坐标：非负整数，`X∈[0,MapWidth-1]`，`Y∈[0,MapHeight-1]`
3. 字符串长度：名称/种子/模板名最大长度32位
4. 数组最大长度：怪物、道具、陷阱配置列表最多支持50条配置

## 二、组件全局初始化接口
### 接口1：Init 组件初始化
#### 接口签名
```typescript
function Init(globalConfig: GlobalConfig): Result<null>
```
#### 请求入参 GlobalConfig
```json
{
  "maxRetryTimes": 5,
  "logLevel": "info",
  "enablePreview": true,
  "defaultAlgorithmType": "RoomSplit"
}
```
##### 字段边界约束
|字段|类型|取值范围|默认值|说明|
|----|----|----|----|----|
|maxRetryTimes|int|`[1,20]`|5|关卡校验失败最大重试次数|
|logLevel|string|`debug/info/warn/error`|info|日志级别，非法值默认info|
|enablePreview|bool|true/false|true|是否开启地图预览数据返回|
|defaultAlgorithmType|string|GridRandom/RoomSplit/RecursiveBacktrack/PerlinNoise|RoomSplit|默认生成算法|

#### 返回值
```json
{
  "code": 0,
  "msg": "init success",
  "data": null
}
```

## 三、配置类接口
### 接口2：SetMapBasicConfig 设置地图基础配置
#### 接口签名
```typescript
function SetMapBasicConfig(config: MapBasicConfig): Result<null>
```
#### 请求参数
```json
{
  "width": 50,
  "height": 50,
  "isRandomSize": false,
  "widthRange": [20, 100],
  "heightRange": [20, 100],
  "wallRatio": 30,
  "trapMaxRatio": 15,
  "roomMinCount": 3,
  "roomMaxCount": 15,
  "singleRoomMinW": 4,
  "singleRoomMaxW": 12,
  "singleRoomMinH": 4,
  "singleRoomMaxH": 12,
  "pathWidth": 2,
  "difficultyLevel": 1
}
```
##### 字段边界约束
|字段|边界范围|备注|
|----|----|----|
|width|`[10, 1000]`|固定宽度，isRandomSize=false时生效|
|height|`[10, 1000]`|固定高度|
|isRandomSize|bool|是否随机地图尺寸|
|widthRange[0]|≥10；widthRange[1]≤1000；最小值<最大值|随机宽区间|
|heightRange[0]|≥10；heightRange[1]≤1000；最小值<最大值|随机高区间|
|wallRatio|`[0,60]`|墙壁占地百分比，超过60自动限60|
|trapMaxRatio|`[0,30]`|陷阱地块最大占比|
|roomMinCount|`[1,50]`|最小房间数|
|roomMaxCount|`[roomMinCount,50]`|最大房间数|
|singleRoomMinW|`[2,20]`|单个房间最小宽|
|singleRoomMaxW|`[singleRoomMinW,20]`|单个房间最大宽|
|singleRoomMinH|`[2,20]`|单个房间最小高|
|singleRoomMaxH|`[singleRoomMinH,20]`|单个房间最大高|
|pathWidth|`[1,5]`|通道宽度|
|difficultyLevel|`[1,5]`|1简单~5地狱，超出自动限界|

### 接口3：SetSeed 设置随机种子
#### 接口签名
```typescript
function SetSeed(seed: string | number): Result<null>
```
#### 参数边界
1. 数字类型：`[1, 999999999]`
2. 字符串类型：长度`[1,32]`，仅允许大小写字母+数字，特殊字符自动过滤并重新生成随机种子
3. 入参为空：组件自动生成6位数字随机种子

### 接口4：SaveTemplate / LoadTemplate 模板保存&加载
#### 入参
```json
{
  "templateName": "easy_mode",
  "desc": "新手简单关卡模板"
}
```
#### 边界约束
- templateName：长度`[1,32]`，不可重复命名
- 最多保存50套模板，超出返回错误1006

## 四、内容配置接口（怪物/道具/陷阱）
### 接口5：SetContentConfig 关卡内容权重配置
```json
{
  "monsterList": [
    {
      "monsterId": 1001,
      "weight": 30,
      "minNum": 1,
      "maxNum": 5,
      "isBoss": false,
      "forbidSpawnStart": true,
      "forbidSpawnEnd": true
    }
  ],
  "itemList": [
    {
      "itemId": 2001,
      "weight": 25,
      "minNum": 1,
      "maxNum": 8
    }
  ],
  "chestList": [
    {
      "chestId": 3001,
      "weight": 10,
      "minNum": 1,
      "maxNum": 3
    }
  ],
  "trapList": [
    {
      "trapId": 4001,
      "weight": 15,
      "damage": 10,
      "minNum": 2,
      "maxNum": 10
    }
  ]
}
```
#### 字段边界约束
1. monsterId/itemId/chestId/trapId：正整数 `[1,99999]`
2. weight：`[0,100]`，权重为0则不生成该类型
3. minNum：`[0,100]`；maxNum ∈ [minNum,100]
4. damage：`[0,999]`
5. 每个数组最大长度：50条配置

## 五、核心生成接口
### 接口6：GenerateMap 执行地图生成
#### 接口签名
```typescript
function GenerateMap(algorithmType?: string): Result<MapFullData>
```
#### 入参说明
algorithmType 可选，不传使用全局默认算法
合法枚举：`GridRandom / RoomSplit / RecursiveBacktrack / PerlinNoise`

#### 返回结构体 MapFullData
```json
{
  "seed": "123456",
  "mapWidth": 50,
  "mapHeight": 50,
  "tileLayer": [
    [0,1,1,0,...],
    [...]
  ],
  "startPos": {"x": 2, "y": 2},
  "endPos": {"x": 47, "y": 47},
  "roomList": [
    {
      "roomId": 1,
      "x": 3,
      "y": 3,
      "width": 6,
      "height": 6,
      "roomType": "battle"
    }
  ],
  "monsterData": [
    {"id":1001,"x":10,"y":12,"isBoss":false}
  ],
  "itemData": [
    {"id":2001,"x":15,"y":16}
  ],
  "chestData": [
    {"id":3001,"x":20,"y":22}
  ],
  "trapData": [
    {"id":4001,"x":25,"y":26,"damage":10}
  ],
  "generateCostMs": 36,
  "retryCount": 0,
  "checkPass": true
}
```

### 返回字段边界约束
1. tileLayer 二维数组：
   - 取值枚举：0=可通行地面，1=墙壁，2=水域，3=陷阱地块
   - 数组行数 = mapHeight；每行元素数量 = mapWidth
2. startPos、endPos：必须为可通行地块（tile=0）
3. roomType 枚举：`battle/treasure/rest/boss`
4. generateCostMs：正常范围
   - 小图≤50ms；中图≤200ms；大图≤500ms，超时日志告警
5. retryCount ∈ `[0,maxRetryTimes]`

## 六、数据导出&预览接口
### 接口7：ExportMapData 导出关卡JSON
```typescript
function ExportMapData(savePath: string): Result<string>
```
#### 参数边界
- savePath字符串长度≤256，仅允许合法文件路径字符
- 导出文件大小上限：50MB，超大地图分段告警

### 接口8：GetPreviewImageData 获取预览点阵数据
返回一维灰度点阵数组，尺寸同地图宽高，仅用于编辑器可视化预览。

## 七、内置合法性校验规则（数据边界强约束）
1. **连通性约束**
   起点到终点必须存在至少1条通行路径，封闭孤立房间数允许0个；
2. **起点安全约束**
   起点周围3*3范围内：禁止生成怪物、陷阱、BOSS；
3. **资源下限约束**
   单张地图最少生成≥3个道具，否则判定校验失败触发重试；
4. **物体防重叠约束**
   同一坐标不能同时存在怪物、道具、宝箱、陷阱任意两种实体；
5. **边界越界拦截**
   所有实体坐标必须满足：`0 ≤ X < Width，0 ≤ Y < Height`，越界直接丢弃该生成实体。

## 八、各模块极值边界汇总表
### 8.1 地图尺寸边界
|类型|最小|最大|
|----|----|----|
|固定/随机宽高|10|1000 地块|
|单房间宽高|2|20 地块|
|房间总数量|1|50 间|

### 8.2 概率类边界
- 墙壁占比：0 ~ 60%
- 陷阱总占比：0 ~ 30%
- 所有配置权重：0 ~ 100

### 8.3 实体数量边界
- 单类怪物/道具/陷阱最小0，最大单地图100个
- 配置表单类型最多50条配置项

### 8.4 性能边界（非功能SPEC约束）
1. 100×100地图：生成耗时 ≤ 50ms
2. 300×300地图：生成耗时 ≤ 200ms
3. 1000×1000地图：生成耗时 ≤ 500ms
4. 连续生成1000次无内存泄漏、无死循环、无崩溃

