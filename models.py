from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Optional,Set


#基础类型枚举
class TerrainType(str,Enum):
    """地形类型定义"""
    PLAIN="plain"           #平原
    FOREST="forest"         #森林
    MOUNTAIN="mountain"     #山地
    RIVER="river"           #河流
    WASTELAND="wasteland"   #荒地
class ActionType(str,Enum):
    """动作类型"""
    BUILD_CITY="build_city"           #新建城市
    BUILD_BUILDING="build_building"   #新建建筑
    RESEARCH="research"               #搜索
    SKIP="skip"                       #跳过
class BuildingType(str,Enum):
    """建筑类型"""
    FARM="farm"                       #农场
    LUMBER_MILL="lumber_mill"         #伐木场
    MINE="mine"                       #矿场
    LIBRARY="library"                 #图书馆
class TechType(str,Enum):
    """科技类型"""
    AGRICULTURE="agriculture"        #农业
    LOGGING="logging"                 #伐木
    MINING="mining"                   #采矿
    EDUCATION="education"             #教育


#地图与资源常量

#命令行渲染时的每类地形的字符
TERRAIN_CHARS:Dict[TerrainType,str]={
    TerrainType.PLAIN: "P",
    TerrainType.FOREST: "F",
    TerrainType.MOUNTAIN: "M",
    TerrainType.RIVER: "R",
    TerrainType.WASTELAND: "W",
}
#允许建城的地形集合
BUILD_TERRAINS:FrozenSet[TerrainType]=frozenset(
    {
        TerrainType.PLAIN,
        TerrainType.FOREST,
        TerrainType.RIVER,
    }
)
#全局资源键
RESOURCE_KEYS=("food","wood","ore","science")
#地形基础产出
TERRAIN_YIELDS:Dict[TerrainType,Dict[str, int]]={
    TerrainType.PLAIN: {"food":1},
    TerrainType.FOREST: {"wood":1},
    TerrainType.MOUNTAIN: {"ore":1},
    TerrainType.RIVER: {"food":1,"science":1},
    TerrainType.WASTELAND: {},
}


#科技与建筑规则

#科技花费
TECH_COST:Dict[TechType,int]={
    TechType.AGRICULTURE: 6,
    TechType.LOGGING: 6,
    TechType.MINING: 8,
    TechType.EDUCATION: 10,
}
#建筑定义：成本+产出+迁至科技
BUILDING_DEFS:Dict[BuildingType,Dict[str, object]]={
    BuildingType.FARM:{
        "cost":{"wood":2},
        "yield_bonus":{"food":1},
        "tech":TechType.AGRICULTURE,
    },
    BuildingType.LUMBER_MILL:{
        "cost":{"wood":2},
        "yield_bonus":{"wood":1},
        "tech":TechType.LOGGING,
    },
    BuildingType.MINE:{
        "cost":{"wood":3},
        "yield_bonus":{"ore":2},
        "tech":TechType.MINING,
    },
    BuildingType.LIBRARY:{
        "cost":{"wood":2,"ore":2},
        "yield_bonus":{"science":2},
        "tech":TechType.EDUCATION,
    },
}

# 建城成本（首都除外）
CITY_BUILD_BASE_COST: Dict[str, int] = {"food": 10, "wood": 8, "ore": 3}
# 递增成本系数
CITY_BUILD_SCALING: Dict[str, int] = {"food": 2, "wood": 1, "ore": 1}
# 建城施工回合
CITY_BUILD_TURNS = 2
# 城市固定产出（每城每回合仅 +1 科技；粮食依赖地形与建筑）
CITY_FIXED_YIELD: Dict[str, int] = {"science": 1}
# 城市维护费
CITY_MAINTENANCE_FOOD = 1

#核心数据结构
@dataclass(frozen=True)
class Action:
    """统一动作结构"""
    type: ActionType  # 动作主类型（必须有）
    x: Optional[int] = None  # 建城动作使用的 x 坐标；其他动作保持 None
    y: Optional[int] = None  # 建城动作使用的 y 坐标；其他动作保持 None
    city_id: Optional[int] = None  # 建造动作使用的城市 id；其他动作保持 None
    building: Optional[BuildingType] = None  # 建造动作的建筑类型；其他动作保持 None
    tech: Optional[TechType] = None  # 研究动作的科技类型；其他动作保持 None
    @staticmethod  # 静态构造器：创建“建城”动作，调用时不依赖实例
    def build_city(x: int, y: int) -> "Action":
        return Action(type=ActionType.BUILD_CITY, x=x, y=y)  # 返回完整建城动作对象
    @staticmethod  # 静态构造器：创建“建造建筑”动作
    def build_building(city_id: int, building: BuildingType) -> "Action":
        return Action(
            type=ActionType.BUILD_BUILDING,  # 动作类型=建造
            city_id=city_id,  # 指定目标城市
            building=building,  # 指定要建造的建筑类型
        )
    @staticmethod  # 静态构造器：创建“研究科技”动作
    def research(tech: TechType) -> "Action":
        return Action(type=ActionType.RESEARCH, tech=tech)  # 仅携带科技字段即可
    @staticmethod  # 静态构造器：创建“跳过回合”动作
    def skip() -> "Action":
        return Action(type=ActionType.SKIP)  # 跳过动作不需要额外参数
@dataclass
class City:
    """城市对象，保存城市位置与已建建筑集合"""
    city_id: int
    x:int
    y:int
    buildings: Set[BuildingType]=field(default_factory=set)#当前城市已建成建筑集合
def empty_resources()->Dict[str,int]:
    return {k: 0 for k in RESOURCE_KEYS}# 每种资源初始值设为 0
