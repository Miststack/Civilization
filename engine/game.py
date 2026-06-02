from __future__ import annotations
import copy
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, cast, Callable
from engine import map as map_module
from engine.models import (
    BUILDING_DEFS,
    BUILD_TERRAINS,
    CITY_BUILD_BASE_COST,
    CITY_BUILD_SCALING,
    CITY_BUILD_TURNS,
    CITY_FIXED_YIELD,
    CITY_MAINTENANCE_FOOD,
    RESOURCE_KEYS,
    TECH_COST,
    Action,
    ActionType,
    BuildingType,
    City,
    TechType,
    TerrainType,
    TERRAIN_YIELDS,
    empty_resources,
)

# =========================================================
# 配置层：定义一局游戏的外部参数
# =========================================================
@dataclass
class GameConfig:
    """游戏配置：地图尺寸、总回合数与随机种子。"""
    map_size: int = 10
    total_turns: int = 30
    seed: Optional[int] = None
    def validate(self) -> None:
        """参数合法性检查（对齐题目要求）。"""
        if not (8 <= self.map_size <= 12):
            raise ValueError("map_size 必须在 8~12 之间")
        if self.total_turns <= 0:
            raise ValueError("total_turns 必须 > 0")
# =========================================================
# 状态层：保存当前对局的全部动态信息与规则实现
# =========================================================
class GameState:
    """阶段一完整环境；同时提供 clone 和 legal actions 供阶段二搜索复用。"""
    def __init__(self, config: GameConfig):
        # 1) 参数验证
        config.validate()
        self.config = config
        # 2) 独立随机源，便于通过 seed 复现实验（函数式地图接口会使用）
        self.rng = random.Random(config.seed)
        # 3) 初始化回合与文明状态
        self.turn = 1
        self.resources: Dict[str, int] = empty_resources()
        self.tech_unlocked: Set[TechType] = set()
        # 4) 生成地图并放置首都
        self.grid = self._generate_initial_map()
        self.cities: List[City] = []
        self.pending_city_projects: List[Tuple[int, int, int]] = []
        self._next_city_id = 1
        self._init_capital()
    # ----------------------------- 基础状态接口 -----------------------------
    def clone(self) -> "GameState":
        """深拷贝当前状态（用于阶段二搜索前瞻模拟）。"""
        cloned = copy.deepcopy(self)
        return cloned
    @property

    def size(self) -> int:
        return self.config.map_size

    def is_terminal(self) -> bool:
        """超过总回合即终局。"""
        return self.turn > self.config.total_turns

    def render_map(self) -> str:
        """输出带城市标记的地图文本。"""
        city_positions = [(c.x, c.y) for c in self.cities]
        return self._format_current_map(city_positions)

    def summary(self) -> str:
        """输出当前回合摘要，便于调试与日志记录。"""
        city_count = len(self.cities)
        pending_count = len(self.pending_city_projects)
        building_count = sum(len(c.buildings) for c in self.cities)
        tech_count = len(self.tech_unlocked)
        return (
            f"Turn={self.turn}/{self.config.total_turns} | "
            f"城市={city_count}(在建{pending_count}) 建筑={building_count} 科技={tech_count} | "
            f"资源 food={self.resources['food']} wood={self.resources['wood']} "
            f"ore={self.resources['ore']} science={self.resources['science']}"
        )

    def _generate_initial_map(self) -> List[List[TerrainType]]:
        """生成初始地图"""
        map_generator_cls=getattr(map_module, "MapGenerator",None)
        map_config_cls=getattr(map_module, "MapGenConfig",None) or getattr(map_module, "MapConfig",None)
        if map_generator_cls is not None and map_config_cls is not None:
            map_cfg=map_config_cls(size=self.config.map_size,seed=self.config.seed)
            generator=map_generator_cls(map_cfg)
            generated=generator.generate()
            return generated

        generate_map_fn = getattr(map_module, "generate_map", None)
        if generate_map_fn is None:
            raise RuntimeError("未找到可用的地图生成接口")
        return generate_map_fn(self.config.map_size, self.rng)

    def _format_current_map(self, city_positions: Sequence[Tuple[int, int]]) -> str:
        """渲染地图"""
        # 1) 函数式接口：map_gen.format_map(grid, city_positions)
        format_map_fn = getattr(map_module, "format_map", None)
        if callable(format_map_fn):
            fn = cast(Callable[[list[list[TerrainType]], Sequence[Tuple[int, int]]], str], format_map_fn)
            return fn(self.grid, city_positions)
        # 2) 类式接口：map_gen.MapGenerator.format_map(grid, city_positions)
        map_generator_cls = getattr(map_module, "MapGenerator", None)
        if map_generator_cls is not None:
            formatter = getattr(map_generator_cls, "format_map", None)
            if callable(formatter):
                fn = cast(Callable[[list[list[TerrainType]], list[Tuple[int, int]]], str], formatter)
                return fn(self.grid, list(city_positions))
        raise RuntimeError("未找到可用的地图渲染接口")


    #-----------------------------初始化与地图工具----------------------
    def _init_capital(self) -> None:
        """初始化首都"""
        candidates=self._all_terrain_positions(BUILD_TERRAINS)
        if not candidates:
            raise RuntimeError("地图无可建城池地块")
        best=max(candidates, key=lambda p:self._location_resource_potential(p[0],p[1]))
        self._create_city(best[0],best[1])
        self._ensure_forest_near_first_city()

    def _ensure_forest_near_first_city(self) -> None:
        """保证第一座城市（首都）3×3 范围内至少有一格为森林；若无则改环上优先格为 FOREST。"""
        if not self.cities:
            return
        cap = self.cities[0]
        cells = self._city_area_cells(cap.x, cap.y)
        if any(self.grid[ny][nx] == TerrainType.FOREST for nx, ny in cells):
            return
        ring = [(nx, ny) for nx, ny in cells if not (nx == cap.x and ny == cap.y)]
        for prefer in (
            TerrainType.WASTELAND,
            TerrainType.PLAIN,
            TerrainType.RIVER,
            TerrainType.MOUNTAIN,
        ):
            for nx, ny in ring:
                if self.grid[ny][nx] == prefer:
                    self.grid[ny][nx] = TerrainType.FOREST
                    return
        self.grid[cap.y][cap.x] = TerrainType.FOREST

    def _all_terrain_positions(self, terrains: Iterable[TerrainType]) -> List[Tuple[int, int]]:
        """返回地图上属于指定地形集合的所有坐标"""
        terrain_set=set(terrains)
        out: List[Tuple[int, int]] = []
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[y][x] in terrain_set:
                    out.append((x, y))
        return out

    def _in_bound(self,x:int,y:int)->bool:
        """边界检查"""
        return 0<=x<self.size and 0<=y<self.size

    def _distance_ok(self,x:int,y:int)->bool:
        """判断城市间的距离"""
        for city in self.cities:
            manhattan_distance=abs(x-city.x)+abs(y-city.y)
            if manhattan_distance<3:
                return False
        for px,py,_ in self.pending_city_projects:
            if abs(x-px)+abs(y-py)<3:
                return False
        return True

    def _location_resource_potential(self,x:int,y:int)->float:
        """评估坐标城市资源潜力"""
        score=0.0
        for nx,ny in self._city_area_cells(x,y):
            terrain = self.grid[ny][nx]
            yld = TERRAIN_YIELDS[terrain]
            # 轻量启发式：对不同资源赋予略微不同权重。
            score += yld.get("food", 0) * 1.2
            score += yld.get("wood", 0) * 1.1
            score += yld.get("ore", 0) * 1.0
            score += yld.get("science", 0) * 1.3
        return score

    def _city_area_cells(self, x: int, y: int) -> List[Tuple[int, int]]:
        """城市覆盖范围：中心周围 1 格（最多 3x3 区域）。"""
        cells: List[Tuple[int, int]] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if self._in_bound(nx, ny):
                    cells.append((nx, ny))
        return cells

    def _city_by_id(self, city_id: int) -> Optional[City]:
        """按 id 查询城市对象，不存在返回 None。"""
        for c in self.cities:
            if c.city_id == city_id:
                return c
        return None

    def _create_city(self, x: int, y: int) -> City:
        """创建城市并分配id"""
        city = City(city_id=self._next_city_id, x=x, y=y)
        self._next_city_id += 1
        self.cities.append(city)
        return city
    #--------------------------合法性判断-----------------------------------
    def _next_city_build_cost(self) -> Dict[str,int]:
        """下一座新城的成本"""
        k=len(self.cities)+len(self.pending_city_projects)-1
        k=max(1,k)
        extra=max(0,k-1)
        return {
            "food": CITY_BUILD_BASE_COST["food"] + CITY_BUILD_SCALING["food"] * extra,
            "wood": CITY_BUILD_BASE_COST["wood"] + CITY_BUILD_SCALING["wood"] * extra,
            "ore": CITY_BUILD_BASE_COST["ore"] + CITY_BUILD_SCALING["ore"] * (extra // 2),
        }

    def can_build_city(self,x: int, y: int) -> Tuple[bool, str]:
        """建城合法性检查"""
        if not self._in_bound(x,y):
            return False,"坐标越界"
        if self.grid[y][x] not in BUILD_TERRAINS:
            return False,"该地形不可建城"
        if any(c.x==x and c.y==y for c in self.cities):
            return False,"该位置已有城市"
        if any(px==x and py==y for px,py,_ in self.pending_city_projects):
            return False, "该位置已有城市"
        if not self._distance_ok(x,y):
            return False,"与已有城市距离不足 3 格"
        costs=self._next_city_build_cost()
        for k,v in costs.items():
            if self.resources[k] < v:
                return False,f"资源不足：{k}"
        return True,"OK"

    def can_build_building(self,city_id: int,building:BuildingType) -> Tuple[bool, str]:
        """建筑合法性检查"""
        city = self._city_by_id(city_id)
        if not city:
            return False,"城市不存在"
        if building in city.buildings:
            return False,"同一城市一种建筑只能建造一次"
        definition =BUILDING_DEFS[building]
        need_tech =definition["tech"]
        assert isinstance(need_tech, TechType)
        if need_tech not in self.tech_unlocked:
            return False,f"未解锁科技{need_tech.value}"
        costs=definition["cost"]
        assert isinstance(costs, dict)
        for k,v in costs.items():
            if self.resources[k]<int(v):
                return False,f"资源不足：{k}"
        return True,"OK"

    def can_research(self,tech:TechType)->Tuple[bool, str]:
        """科技研究合法性检查"""
        if tech in self.tech_unlocked:
            return False,"科技已解锁"
        cost=TECH_COST[tech]
        if self.resources["science"]<cost:
            return False,"科技点不足"
        return True,"OK"

    #-----------------------------动作枚举--------------------------

    def legal_actions(self)->List[Action]:
        """
        枚举当前状态下所有合法动作。
        """
        actions: List[Action] = [Action.skip()]
        for y in range(self.size):
            for x in range(self.size):
                # 每个格子都尝试一次建城合法性检查
                ok,_=self.can_build_city(x,y)
                if ok:
                    actions.append(Action.build_city(x,y))
        for city in self.cities:
            for b in BuildingType:
                # 每座城市对每种建筑做合法性帅选
                ok,_=self.can_build_building(city.city_id,b)
                if ok:
                    actions.append(Action.build_building(city.city_id,b))
        for tech in TechType:
            # 每项科技检查一次是否可研究。
            ok, _ = self.can_research(tech)
            if ok:
                actions.append(Action.research(tech))
        return actions

    #-------------------------------------资源系统---------------------------

    def estimate_production(self) -> Dict[str, int]:
        """
        单回合总产出：
        - 地形：各城 3×3 覆盖范围的并集，同一坐标只计一次地形产出（避免城界重叠时重复累加）。
        - 每城固定产出、建筑加成仍按城市分别累计。
        """
        per_turn = empty_resources()
        counted_cells: Set[Tuple[int, int]] = set()
        for city in self.cities:
            for nx, ny in self._city_area_cells(city.x, city.y):
                if (nx, ny) in counted_cells:
                    continue
                counted_cells.add((nx, ny))
                terrain = self.grid[ny][nx]
                for key, value in TERRAIN_YIELDS[terrain].items():
                    per_turn[key] += value
        for city in self.cities:
            for k, v in CITY_FIXED_YIELD.items():
                per_turn[k] += int(v)
            for b in city.buildings:
                bonus = BUILDING_DEFS[b]["yield_bonus"]
                assert isinstance(bonus, dict)
                for k, v in bonus.items():
                    per_turn[k] += int(v)
        return per_turn

    def _collect_resource_phase(self) -> None:
        """
        本回合资源结算（四类资源同一套规则）：
        在 `apply_action` 扣费/付费之后，按 `estimate_production()` 为粮木矿科各加本回合产出；
        每城粮食维护从粮食净增量中一并扣除，最后粮食不低于 0。不因动作类型（跳过/建城/建造/研究）抑制某一类产出。
        """
        delta = self.estimate_production()
        delta["food"] -= len(self.cities) * CITY_MAINTENANCE_FOOD
        for k in RESOURCE_KEYS:
            self.resources[k] += delta[k]
        self.resources["food"] = max(0, self.resources["food"])

    def _progress_city_projects(self) -> List[Tuple[int,int]]:
        """推进建城工程"""
        completed: List[Tuple[int,int]] = []
        next_projects: List[Tuple[int,int,int]] = []
        for x, y, remain in self.pending_city_projects:
            remain-=1
            if remain <= 0:
                self._create_city(x,y)
                completed.append((x,y))
            else:
                next_projects.append((x,y,remain))
        self.pending_city_projects = next_projects
        return completed

    #------------------------------------动作执行------------------------------

    def apply_action(self,action:Action)->str:
        """执行动作"""
        if action.type == ActionType.SKIP:
            return "跳过回合"
        if action.type == ActionType.BUILD_CITY:
            if action.x is None or action.y is None:
                return "建城缺少坐标"
            ok,reason=self.can_build_city(action.x,action.y)
            if not ok:
                return f"非法动作(建城):{reason}"
            costs = self._next_city_build_cost()
            for k,v in costs.items():
                self.resources[k]-=int(v)
            self.pending_city_projects.append((action.x,action.y,CITY_BUILD_TURNS))
            return f"开始建城({action.x},{action.y})，耗时{CITY_BUILD_TURNS}回合"
        if action.type == ActionType.BUILD_BUILDING:
            if action.city_id is None or action.building is None:
                return "建筑参数不完整"
            ok,reason=self.can_build_building(action.city_id,action.building)
            if not ok:
                return f"非法动作(建造): {reason}"
            city=self._city_by_id(action.city_id)
            assert city is not None
            definition =BUILDING_DEFS[action.building]
            costs = definition["cost"]
            assert isinstance(costs, dict)
            for k,v in costs.items():
                self.resources[k]-=int(v)
            city.buildings.add(action.building)
            return f"城市#{city.city_id} 建造 {action.building.value}"
        if action.type == ActionType.RESEARCH:
            if action.tech is None:
                return "科技为空"
            ok,reason=self.can_research(action.tech)
            if not ok:
                return f"非法动作(研究): {reason}"
            # 研究科技：先扣科技点，再写入已解锁集合
            self.resources["science"]-=TECH_COST[action.tech]
            self.tech_unlocked.add(action.tech)
            return f"研究完成 {action.tech.value}"
        return "未知"

    # ----------------------------- 回合推进与评分 -----------------------------

    def do_turn(self, action: Action) -> str:
        # 阶段一规定流程：动作 -> 执行 -> 结算 -> 回合+1
        result = self.apply_action(action)
        self._collect_resource_phase()
        completed = self._progress_city_projects()
        self.turn += 1
        if completed:
            done=",".join(f"({x},{y})"for x,y in completed)
            result=f"{result}|建筑完工：{done}"
        return result

    def score(self) -> int:
        """
        阶段一建议评分函数：
        Score = 20*城市数 + 5*建筑数 + 8*科技数 + floor((food+wood+ore+science)/4)
        """
        city_count = len(self.cities)
        building_count = sum(len(c.buildings) for c in self.cities)
        tech_count = len(self.tech_unlocked)
        resource_part = (self.resources["food"] + self.resources["wood"] + self.resources["ore"] + self.resources["science"]) // 4
        return 20 * city_count + 5 * building_count + 8 * tech_count + resource_part

    def city_positions(self) -> Sequence[Tuple[int, int]]:
        """返回全部城市坐标，主要用于地图渲染。"""
        return [(c.x, c.y) for c in self.cities]