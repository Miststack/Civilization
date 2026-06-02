import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Sequence
from engine.models import BUILD_TERRAINS, TERRAIN_CHARS, TerrainType
@dataclass                     #使用dataclass自动生成初始化和表示方法
class MapGenConfig:
    size: int=10               #地图边长，默认10
    seed: int | None=None      #随机种子
    weights:Dict[TerrainType, int]|None=None #地图权重
    min_buildable_ratio: float=0.45 #可建城地块最小阈值
    min_river_ratio: float=0.06    #河流最小阈值
    min_mountain_ratio: float=0.08 #山地最小阈值
    max_retries:int=100            #地图生成重试上限
    smooth_rounds:int=1            #平滑迭代轮数，0为不平滑
    def validate(self)->None:
        """配置合法性检查"""
        if not (8<=self.size<=12):
            raise ValueError("size必须在8到12之间")
        if not(0<=self.min_buildable_ratio<=1):
            raise ValueError("min_buildable_ratio非法")
        if not(0<=self.min_river_ratio<=1):
            raise ValueError("min_river_ratio非法")
        if not(0<=self.min_mountain_ratio<=1):
            raise ValueError("min_mountain_ratio非法")
        if self.max_retries <= 0:
            raise ValueError("max_retries 必须为正整数")
class MapGenerator:#地图生成器类
    def __init__(self, config: MapGenConfig):
        config.validate() #先校验配置合法性
        self.cfg = config #保存配置到实例
        self.rng=random.Random(config.seed)#建立独立随机元
        self.weights=config.weights or{#如果未传权重则使用默认权重
            TerrainType.PLAIN: 28,
            TerrainType.FOREST: 24,
            TerrainType.MOUNTAIN: 18,
            TerrainType.RIVER: 18,
            TerrainType.WASTELAND: 12,
        }
    def generate(self)->List[List[TerrainType]]: #返回二维地形数组
        for _ in range(self.cfg.max_retries):#最多尝试max_retries次
            grid=self._generate_raw() #先生成一张原始随机地图
            for _ in range(self.cfg.smooth_rounds):#进行平滑
                grid=self._smooth_once(grid)
            if self._check_constraints(grid):
                return grid
        raise RuntimeError("地图生成失败")
    def _generate_raw(self)->List[List[TerrainType]]:#仅按权重采样生成地图
        """生成随机地图"""
        terrains=list(self.weights.keys())       #提取所有候选地形
        probs=[self.weights[t] for t in terrains]#与地形顺序一一对应的权重列表
        size=self.cfg.size                       #读取地图尺寸
        return [ #返回二维列表
            [self.rng.choices(terrains,weights=probs,k=1)[0] for _ in range(size)]
            for _ in range(size)
        ]
    def _smooth_once(self,grid:List[List[TerrainType]]) -> List[List[TerrainType]]:
        """单轮平滑 """
        size=self.cfg.size #读取尺寸
        new_grid=[[grid[y][x] for x in range(size)] for y in range(size)] #先深拷贝
        for y in range(size):
            for x in range(size):
                neighbors =self.neighbors(grid,x,y) #取当前格子的领域地形
                count:Dict[TerrainType,int]={}      #统计邻域地形频次
                for t in neighbors:
                    count[t]=count.get(t,0)+1
                major=max(count.items(),key=lambda kv:kv[1])[0]#找到出现次数最多的地形
                if self.rng.random()<0.35:
                    new_grid[y][x]=major #替换当前地形
        return new_grid #返回平滑后的新地图
    def neighbors(self,grid:List[List[TerrainType]],x:int,y:int) -> List[TerrainType]:
        """取邻域列表"""
        size=self.cfg.size #读取尺寸
        out:List[TerrainType]=[] #邻域地形结果列表
        for dy in (-1,0,1):      #邻域y偏移
            for dx in (-1,0,1):  #邻域x偏移
                if dx==0 and dy==0:#跳过中心点本身
                    continue
                nx,ny=x+dx,y+dy  #计算邻居坐标
                if 0<=nx<size and 0<=ny<size:#边界检查
                    out.append(grid[ny][nx]) #收集合法邻居地形
        return out #返回邻域列表
    def _check_constraints(self,grid:List[List[TerrainType]]) -> bool:
        """地图质量检查"""
        size = self.cfg.size  #读取地图尺寸
        total = size * size   #总地块数
        buildable = 0  #可建城地块计数器
        river = 0      #河流地块计数器
        mountain = 0   #山地地块计数器
        for row in grid:   #遍历每一行
            for t in row:  #遍历行内每个地形
                if t in BUILD_TERRAINS:    #若为可建城地形
                    buildable += 1             #可建城计数 +1
                if t == TerrainType.RIVER:     #若为河流
                    river += 1                 #河流计数 +1
                if t == TerrainType.MOUNTAIN:  #若为山地
                    mountain += 1              #山地计数 +1
        buildable_ratio = buildable / total    #计算可建城占比
        river_ratio = river / total            #计算河流占比
        mountain_ratio = mountain / total      #计算山地占比
        if buildable_ratio < self.cfg.min_buildable_ratio:
            return False  #不通过约束
        if river_ratio < self.cfg.min_river_ratio:
            return False  #不通过约束
        if mountain_ratio < self.cfg.min_mountain_ratio:
            return False  #不通过约束
        return True       #所有约束都满足
    #地图渲染
    @staticmethod         #说明这是静态方法
    def format_map(grid:List[List[TerrainType]],city_positions:List[Tuple[int,int]])->str:
        city_positions=city_positions or []
        city_set=set(city_positions)
        size=len(grid)
        lines=["  "+" ".join(f"{i:02d}"for i in range(size))]
        for y in range(size):
            row=[]
            for x in range(size):
                row.append("C" if (x, y) in city_set else TERRAIN_CHARS[grid[y][x]])
            lines.append(f"{y:02d}"+"  ".join(row))
        lines.append("图例：C=城市，P=平原，F=森林，M=山地，R=河流，W=荒地")
        return "\n".join(lines)
#兼容函数式接口
def generate_map(size:int,rng:random.Random)->List[List[TerrainType]]:
    cfg = MapGenConfig(size=size, seed=None)
    gen = MapGenerator(cfg)
    gen.rng = rng
    return gen._generate_raw()

def format_map(grid:List[List[TerrainType]],city_positions:Sequence[Tuple[int,int]])->str:
    return MapGenerator.format_map(grid,list(city_positions))