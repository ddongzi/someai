# 游戏地图/关卡随机生成器组件 完整详细技术设计文档（DD V1\.0）

## 0\. 文档总览

### 0\.1 文档目的

本文档为《游戏地图/关卡随机生成器组件》**最终详细技术设计文档（DD）**。用于指导后端/客户端 Python 开发、单元测试、联调、上线、迭代维护。本文档包含：架构设计、模块拆分、类结构、函数逻辑、算法底层实现、数据结构、存储、时序、异常、性能、安全、边界、测试全覆盖。

本文档是 PRD、SPEC 之后的**唯一落地技术依据**，开发必须 100% 严格按照本文实现，不允许私自修改逻辑、边界、默认值、容错策略。

### 0\.2 关联文档

- PRD：游戏地图/关卡随机生成器组件需求文档（业务能力定义）

- SPEC：接口与数据边界规范文档（出入参、错误码、约束）

- DD：本文档（技术落地最终实现规范）

### 0\.3 技术栈与运行环境

- 开发语言：Python 3\.9\+

- 参数校验：Pydantic 2\.x

- 随机算法：原生 random / 自定义噪声实现

- 数据存储：本地 JSON 文件（无数据库依赖）

- 运行环境：Windows / Linux / Mac / 游戏服务端 / 编辑器工具

### 0\.4 设计原则（强制）

- **确定性原则**：同 Seed \+ 同配置 = 100% 相同地图，不允许随机漂移

- **强边界原则**：所有入参、配置、生成数据严格遵从 SPEC 数值边界

- **容错兜底原则**：任何非法输入、算法失败、校验失败均有降级策略

- **模块化解耦**：算法、填充、校验、配置、日志完全解耦

- **可观测原则**：每一次生成可溯源（seed \+ 日志 \+ 耗时 \+ 重试记录）

---

## 1\. 整体系统架构设计（完整版）

### 1\.1 系统分层架构（标准工业级分层）

自上而下 7 层严格分层，单向依赖，禁止跨层乱调用：

```Plain Text
【对外接口层 API】
        ↓
【参数校验与模型层 Pydantic】
        ↓
【全局调度与管理器层 Manager】
        ↓
【核心算法工厂层 Factory】
        ↓
【内容生成填充层 Spawner】
        ↓
【关卡校验容错层 Validator】
        ↓
【数据持久化与日志层 Storage & Log】
```

### 1\.2 每层职责精确定义

- **API 接口层**：对外暴露所有可调用能力，统一返回结构体，捕获顶层异常

- **模型校验层**：拦截所有非法参数、越界、非法枚举、长度超限（SPEC 强约束）

- **调度管理层**：全局单例管理、种子管理、模板管理、配置缓存、重试控制

- **算法工厂层**：统一调度 4 种生成算法，产出标准地块矩阵\+起止点\+房间数据

- **内容填充层**：权重随机生成怪物/道具/宝箱/陷阱，防重叠、防禁区

- **校验容错层**：连通性、安全区、资源、坐标、实体冲突全量校验 \+ 自动重试

- **持久化层**：模板读写、地图导出、日志分级落地、异常快照保存

### 1\.3 核心流程总时序（完整闭环）

初始化 → 参数设置 → 种子锁定 → 算法生成地形 → 实体填充 → 合法性校验 → 成功返回 / 失败重试 → 结果封装导出

---

## 2\. 全局数据模型设计（完整 Pydantic 结构）

本节为系统**全部核心数据结构最终定义**，开发必须完全一致。

### 2\.1 全局枚举定义

```Plain Text
from enum import StrEnum

class LogLevelEnum(StrEnum):
    debug = "debug"
    info = "info"
    warn = "warn"
    error = "error"

class AlgorithmTypeEnum(StrEnum):
    GridRandom = "GridRandom"
    RoomSplit = "RoomSplit"
    RecursiveBacktrack = "RecursiveBacktrack"
    PerlinNoise = "PerlinNoise"

class RoomTypeEnum(StrEnum):
    battle = "battle"
    treasure = "treasure"
    rest = "rest"
    boss = "boss"

class TileType(int):
    GROUND = 0
    WALL = 1
    WATER = 2
    TRAP_TILE = 3
```

### 2\.2 全局配置模型

```Plain Text
from pydantic import BaseModel, Field

class GlobalConfig(BaseModel):
    maxRetryTimes: int = Field(default=5, ge=1, le=20)
    logLevel: LogLevelEnum = Field(default=LogLevelEnum.info)
    enablePreview: bool = True
    defaultAlgorithmType: AlgorithmTypeEnum = Field(default=AlgorithmTypeEnum.RoomSplit)
```

### 2\.3 地图基础配置模型

```Plain Text
class MapBasicConfig(BaseModel):
    width: int = Field(default=50, ge=10, le=1000)
    height: int = Field(default=50, ge=10, le=1000)
    isRandomSize: bool = False
    widthRange: list[int] = Field(default=[20, 100], min_length=2, max_length=2)
    heightRange: list[int] = Field(default=[20, 100], min_length=2, max_length=2)
    wallRatio: int = Field(default=30, ge=0, le=60)
    trapMaxRatio: int = Field(default=15, ge=0, le=30)
    roomMinCount: int = Field(default=3, ge=1, le=50)
    roomMaxCount: int = Field(default=15, ge=1, le=50)
    singleRoomMinW: int = Field(default=4, ge=2, le=20)
    singleRoomMaxW: int = Field(default=12, ge=4, le=20)
    singleRoomMinH: int = Field(default=4, ge=2, le=20)
    singleRoomMaxH: int = Field(default=12, ge=4, le=20)
    pathWidth: int = Field(default=2, ge=1, le=5)
    difficultyLevel: int = Field(default=1, ge=1, le=5)
```

### 2\.4 实体配置模型（怪物/道具/宝箱/陷阱）

```Plain Text
class MonsterConfig(BaseModel):
    monsterId: int = Field(gt=0, le=99999)
    weight: int = Field(ge=0, le=100)
    minNum: int = Field(ge=0, le=100)
    maxNum: int = Field(ge=0, le=100)
    isBoss: bool = False
    forbidSpawnStart: bool = True
    forbidSpawnEnd: bool = True

class ItemConfig(BaseModel):
    itemId: int = Field(gt=0, le=99999)
    weight: int = Field(ge=0, le=100)
    minNum: int = Field(ge=0, le=100)
    maxNum: int = Field(ge=0, le=100)

class ChestConfig(BaseModel):
    chestId: int = Field(gt=0, le=99999)
    weight: int = Field(ge=0, le=100)
    minNum: int = Field(ge=0, le=100)
    maxNum: int = Field(ge=0, le=100)

class TrapConfig(BaseModel):
    trapId: int = Field(gt=0, le=99999)
    weight: int = Field(ge=0, le=100)
    minNum: int = Field(ge=0, le=100)
    maxNum: int = Field(ge=0, le=100)
    damage: int = Field(ge=0, le=999)
```

### 2\.5 内容总配置模型

```Plain Text
class ContentConfig(BaseModel):
    monsterList: list[MonsterConfig] = Field(default=[], max_length=50)
    itemList: list[ItemConfig] = Field(default=[], max_length=50)
    chestList: list[ChestConfig] = Field(default=[], max_length=50)
    trapList: list[TrapConfig] = Field(default=[], max_length=50)
```

### 2\.6 输出结果模型（完全对齐SPEC）

```Plain Text
class PosData(BaseModel):
    x: int
    y: int

class RoomData(BaseModel):
    roomId: int
    x: int
    y: int
    width: int
    height: int
    roomType: RoomTypeEnum

class MonsterSpawnData(BaseModel):
    id: int
    x: int
    y: int
    isBoss: bool

class ItemSpawnData(BaseModel):
    id: int
    x: int
    y: int

class ChestSpawnData(BaseModel):
    id: int
    x: int
    y: int

class TrapSpawnData(BaseModel):
    id: int
    x: int
    y: int
    damage: int

class MapFullData(BaseModel):
    seed: str
    mapWidth: int
    mapHeight: int
    tileLayer: list[list[int]]
    startPos: PosData
    endPos: PosData
    roomList: list[RoomData]
    monsterData: list[MonsterSpawnData]
    itemData: list[ItemSpawnData]
    chestData: list[ChestSpawnData]
    trapData: list[TrapSpawnData]
    generateCostMs: int
    retryCount: int
    checkPass: bool
```

### 2\.7 统一返回模型与错误码

```Plain Text
class ApiResult(BaseModel):
    code: int
    msg: str
    data: dict | None = None

# 错误码常量
SUCCESS = 0
ERR_PARAM_OUT_RANGE = 1001
ERR_SEED_INVALID = 1002
ERR_GENERATE_RETRY_OVER = 1003
ERR_ALGORITHM_INVALID = 1004
ERR_TEMPLATE_NOT_EXIST = 1005
ERR_TEMPLATE_MAX_LIMIT = 1006
```

---

## 3\. 核心模块详细设计（逐模块源码级设计）

### 3\.1 全局单例管理器 MapManager

全局唯一调度中心，缓存所有配置、种子、状态。

#### 核心属性

- global\_config：GlobalConfig

- map\_config：MapBasicConfig

- content\_config：ContentConfig

- current\_seed：str

- retry\_count：int

#### 核心能力

- 初始化全局环境、日志目录、模板目录

- 种子标准化、哈希统一处理（str/int 兼容）

- 配置快照保存（用于重试、回溯）

- 模板数量上限管控（最大50）

### 3\.2 种子管理器 SeedManager 详细设计

解决**确定性复现**核心问题，是本组件最关键模块之一。

#### 规则

- int 种子范围：1 \~ 999999999

- str 种子：长度 1\~32，仅字母数字，非法字符自动清洗

- 非法种子：自动生成 6 位随机数字兜底

- 所有随机行为统一绑定同一个种子，保证全局确定性

#### 标准化算法

字符串种子统一 hash 转为整数种子，避免不同字符串长度导致随机序列不一致。

### 3\.3 算法工厂模块 AlgorithmFactory 完整设计

采用**抽象基类 \+ 工厂模式**，四种算法完全解耦。

#### 基类 BaseGenerator

统一接口：generate\(\) \-\> 输出 tile\_map, start, end, room\_list

#### 四大算法详细技术原理

##### 3\.3\.1 GridRandom 网格随机算法

适用：小型闯关、小游戏地图

逻辑：根据 wallRatio / trapMaxRatio 逐地块随机生成，保证基础通路，最后 BFS 校验通路。

##### 3\.3\.2 RoomSplit 房间分割算法（核心主力算法）

适用：Roguelike、地牢、多层房间关卡

技术步骤：

1. 根据房间数量区间随机生成房间个数

2. 随机分割不重叠矩形房间

3. 房间类型随机分配：战斗/奖励/休息/Boss

4. 生成连通通道（pathWidth 控制宽度）

5. 自动选取起点（首个房间）、终点（Boss房/最后房间）

##### 3\.3\.3 RecursiveBacktrack 递归回溯迷宫算法

适用：纯迷宫、单线闯关

特性：**无死胡同、单连通域、100%可通行**

##### 3\.3\.4 PerlinNoise 柏林噪声地形算法

适用：自然地形、草地、岩石、水域随机地图

通过噪声值区间判定地面/水域/障碍，生成自然随机地形。

### 3\.4 内容填充生成器 SpawnManager 详细设计

所有权重随机、防重叠、禁区规则在此模块实现。

#### 核心执行步骤

1. 获取所有可通行地面坐标池（tile=0）

2. 剔除起点 3\*3 安全禁区

3. 根据权重加权随机选择生成数量

4. 随机坐标采样

5. 全局坐标冲突检测（同一个坐标只能一个实体）

6. 难度系数动态倍率（difficultyLevel 越高怪物/陷阱越多）

#### 硬性边界

- 单类实体最大 100 个

- 配置列表最大 50 条

- 权重 0 直接不生成

### 3\.5 关卡校验器 MapValidator（核心质量保障模块）

所有失败重试均由该模块驱动，是地图“可用性”的最终守门。

#### 五大强制校验规则（100%严格执行）

1. **连通性校验**：BFS 遍历，起点到终点必须通路，无死图

2. **起点安全校验**：起点 3\*3 无怪物、无陷阱、无 Boss

3. **资源下限校验**：整张地图道具数量 ≥3

4. **坐标越界校验**：所有实体坐标必须在地图范围内

5. **实体唯一校验**：坐标不重复、不重叠

#### 重试机制

校验失败 → 重试计数\+1 → 重新全流程生成 → 达到 maxRetryTimes 终止并返回错误

### 3\.6 持久化与日志模块

#### 目录规范

- 模板目录：\./map\_templates/

- 日志目录：\./logs/

- 导出目录：\./export\_maps/

#### 日志分级

debug / info / warn / error，严格根据配置输出，记录每一次：初始化、参数变更、种子、算法、重试、校验结果、耗时。

---

## 4\. 核心业务时序图（文字完整版，可直接绘图）

**完整生成时序**

1. 业务层调用 Init 初始化组件

2. 设置地图基础配置、内容配置

3. 设置/自动生成种子

4. 算法工厂根据算法类型生成原始地形

5. Spawner 填充怪物、道具、宝箱、陷阱

6. Validator 全量校验

7. 校验成功：封装 MapFullData 返回

8. 校验失败：自动重试，直到超限报错

9. 支持导出 JSON、预览点阵数据

---

## 5\. 异常体系完整设计

### 5\.1 异常分类

- 参数异常：Pydantic 拦截，返回 1001

- 种子异常：自动兜底，警告日志

- 算法异常：降级 RoomSplit

- 关卡无效异常：重试耗尽返回 1003

- IO 异常：文件读写失败不中断内存运行

### 5\.2 兜底策略（全部强制落地）

- 任何参数越界 → 自动限界\+警告

- 任何算法异常 → 降级默认算法

- 任何生成失败 → 重试机制兜底

- 任何模板缺失 → 加载默认模板

---

## 6\. 性能指标与优化方案（完全对齐SPEC）

### 6\.1 性能硬指标

- 100\*100 以内地图：≤50ms

- 300\*300 以内地图：≤200ms

- 1000\*1000 以内地图：≤500ms

### 6\.2 性能优化手段

- 预筛选可通行坐标池，避免全图遍历

- BFS 连通性剪枝，跳过墙壁/水域

- 失败地图内存即时释放

- 预览点阵延迟生成，非必要不计算

- 模板懒加载，不常驻内存

---

## 7\. 稳定性设计

- 1000 次连续生成无崩溃、无死循环、无内存泄漏

- 种子确定性 100% 一致

- 所有输入强校验，无任何非法输入可导致崩溃

- 重试次数硬上限，杜绝死循环

---

## 8\. 测试用例设计（完整覆盖）

- 参数边界极值测试（最大/最小/0值）

- 种子一致性回归测试

- 四算法独立生成测试

- 校验失败重试测试

- 模板保存加载测试

- 超大地图性能测试

- 压测：1000 次连续生成稳定性

- 非法参数容错测试

---

## 9\. 版本迭代规划（技术迭代）

### V1\.0

本文档全部能力落地：四算法、种子、校验、重试、模板、导出、日志、完整SPEC边界

### V1\.1

增加自定义规则注入、自定义地块、分层独立生成

### V1\.2

增加联机同步、批量生成工具、可视化编辑器对接

---

## 10\. 开发规范（强制）

- 所有参数必须经过 Pydantic 模型校验，禁止裸参数使用

- 所有随机逻辑必须绑定种子，禁止系统随机

- 所有返回结构必须使用标准 ApiResult / MapFullData

- 所有异常必须捕获并日志记录，禁止抛顶层异常

- 所有数值严格遵从 SPEC 边界，禁止硬编码篡改范围

> （注：部分内容可能由 AI 生成）
