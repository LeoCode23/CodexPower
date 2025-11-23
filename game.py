import json
import math
import random
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame


# Constants
TILE_SIZE = 32
INITIAL_GRID = 6
MAX_DUST_TILES = 3
DAY_LENGTH_SECONDS = 24 * 60  # 24 minutes in real time
SEASON_LENGTH_SECONDS = DAY_LENGTH_SECONDS / 4
SAVE_FILE = Path("savegame.json")
SMALL_CHOP = 5.0
MEDIUM_CHOP = 7.0
LARGE_CHOP = 10.0
AUTOSAVE_EVERY = 60.0


def make_sprite(pattern: List[str], palette: Dict[str, Tuple[int, int, int, int]], scale: int = 2) -> pygame.Surface:
    height = len(pattern)
    width = len(pattern[0]) if height else 0
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y, line in enumerate(pattern):
        for x, key in enumerate(line):
            color = palette.get(key)
            if color:
                surf.set_at((x, y), color)
    if scale != 1:
        surf = pygame.transform.scale(surf, (width * scale, height * scale))
    return surf


def build_sprite_sheet() -> Dict[str, pygame.Surface]:
    palette_common = {
        ".": None,
        "g": (70, 118, 92, 255),
        "G": (96, 160, 128, 255),
        "d": (224, 204, 156, 255),
        "b": (44, 42, 38, 255),
    }
    sheet: Dict[str, pygame.Surface] = {}

    # Ground tiles by season (spring/summer/autumn/winter)
    ground_patterns = {
        "spring": ["gggggggg", "ggGggGgg", "gggggggg", "gGgggggg", "ggggGggg", "gggggggg", "gGgggggg", "gggggggg"],
        "summer": ["GGGGGGGG", "GGGgGGGG", "GGGGGGGG", "GGGGgGGG", "GGGGGGGG", "GGGgGGGG", "GGGGGGGG", "GGGGGGGG"],
        "autumn": ["gggggggg", "gGgggggg", "gggGGggg", "gggggggg", "gggGGggg", "gggggggg", "gGgggggg", "gggggggg"],
        "winter": ["bbbbbbbb", "bbdbbbdb", "bbbbbbbb", "bbdbbbdb", "bbbbbbbb", "bbdbbbdb", "bbbbbbbb", "bbdbbbdb"],
    }
    ground_palettes = {
        "spring": {**palette_common, "g": (84, 150, 108, 255), "G": (106, 176, 138, 255)},
        "summer": {**palette_common, "G": (110, 186, 126, 255), "g": (96, 158, 114, 255)},
        "autumn": {**palette_common, "g": (148, 112, 72, 255), "G": (190, 140, 82, 255)},
        "winter": {**palette_common, "b": (188, 198, 216, 255), "d": (230, 236, 244, 240)},
    }
    for key, pattern in ground_patterns.items():
        sheet[f"ground_{key}"] = make_sprite(pattern, ground_palettes[key], scale=4)

    # Trees
    tree_pal = {
        "t": (56, 92, 60, 255),
        "T": (82, 138, 86, 255),
        "L": (122, 182, 126, 255),
        "b": (94, 70, 46, 255),
    }
    sheet["tree_small"] = make_sprite(
        ["....TT..", "...TTT..", "..TLTT..", "..TLTT..", "...TT...", "...TT...", "...TT...", "...bb..."],
        tree_pal,
        scale=4,
    )
    sheet["tree_medium"] = make_sprite(
        ["...TTTT.", "..TLTTT.", "..TLTTT.", ".TTLTTT.", ".TLTTTT.", "..TTTT..", "...TT...", "...bb..."],
        tree_pal,
        scale=4,
    )
    sheet["tree_large"] = make_sprite(
        ["..TTTTT.", ".TLTTTTT", ".TLTTTTT", "TLTTTTT.", "TLTTTTT.", "TLTTTTT.", ".TTTTTT.", "..bbbb.."],
        tree_pal,
        scale=4,
    )
    sheet["tree_gold"] = make_sprite(
        ["..YYYY..", ".YYYYYY.", ".YhYYYh.", "YYYYYYYY", "YhYYYhYY", "YYYYYYYY", ".YYYYYY.", "..bbbb.."],
        {
            "Y": (228, 196, 72, 255),
            "h": (244, 220, 120, 255),
            "b": (120, 90, 40, 255),
            ".": None,
        },
        scale=4,
    )

    # Dust
    sheet["dust"] = make_sprite(
        ["..aa....", ".aaaa..", "aaaaaa.", "aaaaaa.", ".aaaa..", "..aa....", "..aa....", "........"],
        {"a": (210, 190, 150, 200), ".": None},
        scale=4,
    )

    # Structures
    sheet["bed"] = make_sprite(
        ["rrrrrr..", "rwwww..", "rwwww..", "rwwww..", "rwwww..", "rwwww..", "rrrrrr..", "rrrrrr.."],
        {"r": (200, 168, 120, 255), "w": (240, 240, 240, 255), ".": None},
        scale=4,
    )
    sheet["pc"] = make_sprite(
        ["BBBB....", "BccB....", "BccB....", "BccB....", "BccB....", "BccB....", "BBBB....", "BBBB...."],
        {
            "B": (120, 180, 220, 255),
            "c": (70, 90, 120, 255),
            ".": None,
        },
        scale=4,
    )

    # Buildables
    sheet["cabin"] = make_sprite(
        ["cccccccc", "cCCcCCc", "cCCcCCc", "cCCcCCc", "cCCcCCc", "cCCcCCc", "cCCcCCc", "bbbbbbbb"],
        {"c": (150, 110, 70, 255), "C": (180, 140, 90, 255), "b": (70, 50, 30, 255), ".": None},
        scale=4,
    )
    sheet["workshop"] = make_sprite(
        ["sssSSsss", "sSSSSSSs", "sSmmSSsS", "sSmmSSsS", "sSSSSSSs", "sSSSSSSs", "sSSSSSSs", "bbbbbbbb"],
        {"s": (90, 110, 120, 255), "S": (120, 150, 160, 255), "m": (210, 190, 120, 255), "b": (70, 60, 40, 255), ".": None},
        scale=4,
    )
    sheet["watch"] = make_sprite(
        ["....TT..", "...TTT..", "..TwwT..", "..TwwT..", "..TwwT..", "..TwwT..", "..TwwT..", "..bbbb.."],
        {"T": (90, 120, 80, 255), "w": (200, 200, 220, 255), "b": (70, 50, 30, 255), ".": None},
        scale=4,
    )

    # Characters
    sheet["lumberjack"] = make_sprite(
        ["...rr...", "..rrrr..", "..rRRr..", "..rRRr..", "..rrrr..", "..bbbb..", ".bbMMbb.", "b..MM..b"],
        {
            "r": (196, 70, 60, 255),
            "R": (220, 120, 110, 255),
            "b": (80, 50, 30, 255),
            "M": (80, 110, 180, 255),
            ".": None,
        },
        scale=4,
    )
    sheet["enemy"] = make_sprite(
        ["...rr...", "..rrrr..", "..rkkk..", "..rkkk..", "..rrrr..", "..bbbb..", ".bbMMbb.", "b..MM..b"],
        {
            "r": (140, 40, 40, 255),
            "k": (60, 60, 60, 255),
            "b": (60, 36, 24, 255),
            "M": (190, 120, 40, 255),
            ".": None,
        },
        scale=4,
    )

    # UI icons (emoji style blocks)
    sheet["icon_buy"] = make_sprite([
        "..GG..",
        ".GggG.",
        "GggggG",
        "GggggG",
        ".GggG.",
        "..GG..",
    ], {"G": (240, 196, 50, 255), "g": (210, 160, 40, 255), ".": None}, scale=6)
    sheet["icon_broom"] = make_sprite([
        "..yy..",
        "..yy..",
        "..yy..",
        "yyyyyy",
        ".yyyy.",
        "..yy..",
    ], {"y": (230, 190, 90, 255), ".": None}, scale=6)
    sheet["icon_build"] = make_sprite([
        "RRRRRR",
        "R....R",
        "R....R",
        "RRRRRR",
        "R....R",
        "RRRRRR",
    ], {"R": (120, 180, 220, 255), ".": None}, scale=6)

    return sheet


@dataclass
class Tile:
    x: int
    y: int
    owned: bool = False
    has_tree: bool = False
    tree_growth: float = 0.0
    tree_type: str = "small"  # small, medium, large
    has_dust: bool = False
    special: Optional[str] = None  # computer or bed
    event: Optional[str] = None  # story or random event
    building: Optional[str] = None  # cabane, atelier, tour
    damage: float = 0.0
    building_progress: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Tile":
        return Tile(**data)


@dataclass
class Task:
    kind: str
    target: Optional[Tuple[int, int]] = None
    weight: float = 1.0
    duration: float = 2.0
    progress: float = 0.0
    assigned: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Task":
        return Task(**data)


@dataclass
class Lumberjack:
    x: float
    y: float
    target: Optional[Tuple[int, int]] = None
    chopping: float = 0.0
    friendly: bool = True
    chop_duration: float = 0.0
    health: int = 3
    task_queue: List["Task"] = field(default_factory=list)
    current_task: Optional["Task"] = None

    def enqueue_task(self, task: "Task") -> None:
        self.task_queue.append(task)

    def next_task(self) -> Optional["Task"]:
        if self.current_task:
            return self.current_task
        if self.task_queue:
            self.current_task = self.task_queue.pop(0)
            return self.current_task
        return None

    def position(self) -> Tuple[int, int]:
        return self.x, self.y


class GameState:
    def __init__(self, screen_size: Tuple[int, int]):
        self.screen_width, self.screen_height = screen_size
        self.tiles: Dict[Tuple[int, int], Tile] = {}
        self.inventory = {"gold": 20, "wood": 0, "dust": 0}
        self.dust_timer = 0.0
        self.day_time = 0.0
        self.season_time = 0.0
        self.weather = "Soleil"
        self.lumberjacks: List[Lumberjack] = [Lumberjack(0.0, 0.0)]
        self.cleaning_tool = False
        self.active_tool = "buy"  # buy, broom, build
        self.build_selection = 0
        self.active_task = "Achat de terrain"
        self.selling_dialog = False
        self.pending_sale: Optional[dict] = None
        self.event_timer = 0.0
        self.task_board: List[Task] = []
        self.load_or_init_tiles()
        self.active_task = "Chargement auto" if SAVE_FILE.exists() else "Nouvelle partie"

    def load_or_init_tiles(self) -> None:
        if SAVE_FILE.exists():
            self.load_game()
            return

        for y in range(INITIAL_GRID):
            for x in range(INITIAL_GRID):
                owned = 1 <= x <= INITIAL_GRID - 2 and 1 <= y <= INITIAL_GRID - 2
                has_tree = owned and random.random() < 0.12
                tree_type = random.choice(["small", "medium"]) if has_tree else "small"
                tile = Tile(x=x, y=y, owned=owned, has_tree=has_tree, tree_growth=1.0, tree_type=tree_type)
                self.tiles[(x, y)] = tile

        # Place special structures
        self.get_tile(0, 0).special = "computer"
        self.get_tile(0, 1).special = "bed"
        self.queue_neighbors()

    def get_tile(self, x: int, y: int, create: bool = True) -> Optional[Tile]:
        tile = self.tiles.get((x, y))
        if tile or not create:
            return tile
        tile = Tile(x=x, y=y)
        self.tiles[(x, y)] = tile
        return tile

    def tiles_with_dust(self) -> List[Tile]:
        return [t for t in self.tiles.values() if t.has_dust]

    def owned_tiles(self) -> List[Tile]:
        return [t for t in self.tiles.values() if t.owned]

    def spawn_dust(self, dt: float) -> None:
        self.dust_timer += dt
        if self.dust_timer < 4:
            return
        self.dust_timer = 0
        dust_tiles = self.tiles_with_dust()
        if len(dust_tiles) >= MAX_DUST_TILES:
            return

        candidates = [t for t in self.owned_tiles() if not t.has_dust]
        if not candidates:
            return
        random.choice(candidates).has_dust = True

    def update_trees(self, dt: float) -> None:
        for tile in self.tiles.values():
            if tile.has_tree or tile.building:
                continue
            if not tile.owned:
                continue
            tile.tree_growth = min(1.0, tile.tree_growth + dt / 60)
            if tile.tree_growth >= 1.0 and random.random() < 0.04:
                tile.has_tree = True
                tile.tree_type = random.choices(["small", "medium", "large"], weights=[0.5, 0.35, 0.15])[0]

    def update_time(self, dt: float) -> None:
        self.day_time = (self.day_time + dt) % DAY_LENGTH_SECONDS
        self.season_time = (self.season_time + dt) % (SEASON_LENGTH_SECONDS * 4)
        if self.season_time % SEASON_LENGTH_SECONDS < dt:
            self.roll_weather()
        self.maintain_buildings(dt)

    def update_events(self, dt: float) -> None:
        self.event_timer += dt
        if self.event_timer < 22:
            return
        self.event_timer = 0.0
        owned = self.owned_tiles()
        if not owned:
            return
        tile = random.choice(owned)
        if tile.building:
            return
        event = random.choice(["ennemi", "ami_bucheron", "arbre_or", "fete", "visite"])
        tile.event = event
        if event == "ami_bucheron":
            self.lumberjacks.append(Lumberjack(tile.x + 0.1, tile.y + 0.1))
        elif event == "ennemi":
            self.lumberjacks.append(Lumberjack(tile.x + 0.1, tile.y + 0.1, friendly=False, health=2))
        elif event == "arbre_or":
            tile.has_tree = True
            tile.tree_type = "large"
        elif event == "fete":
            self.inventory["gold"] += 4
        elif event == "visite":
            self.inventory["wood"] += 2

    def current_day_fraction(self) -> float:
        return self.day_time / DAY_LENGTH_SECONDS

    def current_season(self) -> str:
        index = int(self.season_time // SEASON_LENGTH_SECONDS)
        return ["Printemps", "Été", "Automne", "Hiver"][index]

    def roll_weather(self) -> None:
        options = ["Soleil", "Pluie", "Neige", "Brouillard"]
        self.weather = random.choice(options)

    def maintain_buildings(self, dt: float) -> None:
        for tile in self.tiles.values():
            if not tile.building:
                continue
            decay = dt / 9000
            if tile.has_dust:
                decay += dt / 4000
            tile.damage = min(1.0, tile.damage + decay)
            if tile.damage > 0.4 and random.random() < 0.0008:
                tile.has_dust = True
            if tile.building_progress < 1.0:
                tile.building_progress = min(1.0, tile.building_progress + dt / 120)

    def toggle_cleaner(self) -> None:
        self.cleaning_tool = not self.cleaning_tool

    def clean_tile(self, tile: Tile) -> None:
        if tile.has_dust:
            tile.has_dust = False
            self.inventory["dust"] += 1
            self.active_task = "Balai : nettoyage"

    def chop_tree(self, tile: Tile) -> None:
        tile.has_tree = False
        tile.tree_growth = 0.0
        wood_gain = {"small": 1, "medium": 2, "large": 3}.get(tile.tree_type, 1)
        self.inventory["wood"] += wood_gain
        self.active_task = "Bûcheronnage"

    def place_building(self, tile: Tile, building: str) -> None:
        if tile.has_tree or tile.has_dust or tile.special:
            return
        if not tile.owned:
            return
        if tile.building:
            return
        cost = {"cabane": (5, 8), "atelier": (8, 12), "tour": (10, 14)}  # wood, gold
        need_wood, need_gold = cost.get(building, (0, 0))
        if self.inventory["wood"] < need_wood or self.inventory["gold"] < need_gold:
            return
        self.inventory["wood"] -= need_wood
        self.inventory["gold"] -= need_gold
        tile.building = building
        tile.has_tree = False
        tile.tree_growth = 0.0
        tile.building_progress = 0.35
        self.active_task = f"Construit {building}"

    def sell_resources(self) -> None:
        gained = self.inventory["wood"] * 4 + self.inventory["dust"] * 2
        self.inventory["gold"] += gained
        self.inventory["wood"] = 0
        self.inventory["dust"] = 0
        self.active_task = "Vente confirmée"

    def buy_tile(self, tile: Tile) -> None:
        if tile.owned or self.inventory["gold"] < 10:
            return
        neighbours = [
            self.get_tile(tile.x + dx, tile.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ]
        if any(n and n.owned for n in neighbours):
            self.inventory["gold"] -= 10
            tile.owned = True
            tile.tree_growth = 1.0
            self.active_task = "Achat de terrain"
            self.apply_unlock_event(tile)
            self.queue_neighbors()

    def save_game(self) -> None:
        data = {
            "tiles": [t.to_dict() for t in self.tiles.values()],
            "inventory": self.inventory,
            "day_time": self.day_time,
            "season_time": self.season_time,
            "weather": self.weather,
            "screen": [self.screen_width, self.screen_height],
            "lumberjacks": [self.serialize_lumberjack(l) for l in self.lumberjacks],
            "active_task": self.active_task,
            "active_tool": self.active_tool,
            "build_selection": self.build_selection,
            "task_board": [t.to_dict() for t in self.task_board],
        }
        SAVE_FILE.write_text(json.dumps(data, indent=2))

    def load_game(self) -> None:
        data = json.loads(SAVE_FILE.read_text())
        self.tiles = {(t["x"], t["y"]): Tile.from_dict(t) for t in data["tiles"]}
        self.inventory = data.get("inventory", {"gold": 0, "wood": 0, "dust": 0})
        self.day_time = data.get("day_time", 0.0)
        self.season_time = data.get("season_time", 0.0)
        self.weather = data.get("weather", "Soleil")
        self.screen_width, self.screen_height = data.get("screen", [800, 600])
        lumber_data = data.get("lumberjacks", [])
        if lumber_data:
            self.lumberjacks = [self.deserialize_lumberjack(l) for l in lumber_data]
        else:
            self.lumberjacks = [Lumberjack(0.0, 0.0)]
        self.active_task = data.get("active_task", "Achat de terrain")
        self.active_tool = data.get("active_tool", "buy")
        self.build_selection = data.get("build_selection", 0)
        self.task_board = [Task.from_dict(t) for t in data.get("task_board", [])]
        self.queue_neighbors()

    def serialize_lumberjack(self, lumberjack: Lumberjack) -> dict:
        data = asdict(lumberjack)
        data["task_queue"] = [t.to_dict() for t in lumberjack.task_queue]
        data["current_task"] = lumberjack.current_task.to_dict() if lumberjack.current_task else None
        return data

    def deserialize_lumberjack(self, data: dict) -> Lumberjack:
        task_queue = [Task.from_dict(t) for t in data.get("task_queue", [])]
        current_task = Task.from_dict(data["current_task"]) if data.get("current_task") else None
        known_keys = {"x", "y", "target", "chopping", "friendly", "chop_duration", "health"}
        values = {k: v for k, v in data.items() if k in known_keys}
        lumberjack = Lumberjack(**values)
        lumberjack.task_queue = task_queue
        lumberjack.current_task = current_task
        return lumberjack

    def queue_neighbors(self) -> None:
        # always create a one-tile buffer around owned land for infinite feel
        owned_coords = [(t.x, t.y) for t in self.owned_tiles()]
        for x, y in owned_coords:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                self.get_tile(nx, ny)

    def apply_unlock_event(self, tile: Tile) -> None:
        story_events = {
            (3, 0): "ami_bucheron",
            (-1, 2): "arbre_or",
        }
        tile.event = story_events.get((tile.x, tile.y))
        if not tile.event and random.random() < 0.3:
            tile.event = random.choice(["ennemi", "arbre_or", "ami_bucheron"])

        if tile.event == "ami_bucheron":
            self.lumberjacks.append(Lumberjack(tile.x + 0.2, tile.y + 0.2))
        elif tile.event == "arbre_or":
            tile.has_tree = True
            tile.tree_type = "large"
        elif tile.event == "ennemi":
            tile.has_dust = True
            self.lumberjacks.append(Lumberjack(tile.x + 0.2, tile.y + 0.2, friendly=False))

    def find_storage_tile(self) -> Optional[Tile]:
        for tile in self.tiles.values():
            if tile.special == "computer":
                return tile
        return self.get_tile(0, 0, create=False)

    def refresh_task_board(self) -> None:
        tasks: List[Task] = []
        patrol_targets: List[Tuple[int, int]] = []
        for tile in self.tiles.values():
            if tile.has_tree and not tile.has_dust and tile.owned:
                weight = 1.0 + {"medium": 0.4, "large": 0.8}.get(tile.tree_type, 0.0)
                duration = {"small": SMALL_CHOP, "medium": MEDIUM_CHOP, "large": LARGE_CHOP}.get(
                    tile.tree_type, MEDIUM_CHOP
                )
                tasks.append(Task("chop_tree", (tile.x, tile.y), weight=weight, duration=duration))
            if tile.building and (tile.damage > 0.05 or tile.has_dust):
                tasks.append(Task("repair_building", (tile.x, tile.y), weight=1.5 + tile.damage, duration=3.0))
            if tile.building and tile.building_progress < 0.99:
                tasks.append(
                    Task(
                        "assist_construction",
                        (tile.x, tile.y),
                        weight=1.4 + (1 - tile.building_progress),
                        duration=2.5,
                    )
                )
            if tile.owned and not tile.has_tree and tile.tree_growth < 0.6 and not tile.building:
                tasks.append(
                    Task(
                        "tend_plants",
                        (tile.x, tile.y),
                        weight=0.8 + (0.6 - tile.tree_growth),
                        duration=2.2,
                    )
                )
            if tile.owned:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    neighbor = self.get_tile(tile.x + dx, tile.y + dy, create=False)
                    if not neighbor or not neighbor.owned:
                        patrol_targets.append((tile.x, tile.y))
                        break
        storage = self.find_storage_tile()
        resource_count = self.inventory.get("wood", 0) + self.inventory.get("dust", 0)
        if storage and resource_count >= 4:
            tasks.append(
                Task(
                    "haul_storage",
                    (storage.x, storage.y),
                    weight=1.2 + resource_count * 0.05,
                    duration=3.0,
                )
            )
        for x, y in patrol_targets[:5]:
            tasks.append(Task("patrol_fence", (x, y), weight=0.5, duration=1.2))
        self.task_board = tasks


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Retraite Rustique")
        self.state = GameState((960, 720))
        self.sprites = build_sprite_sheet()
        self.screen = pygame.display.set_mode((self.state.screen_width, self.state.screen_height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 18)
        self.big_font = pygame.font.SysFont("arial", 24)
        self.running = True
        self.last_click: Optional[Tile] = None
        self.pause_menu_open = False
        self.animation_timer = 0.0
        self.autosave_timer = 0.0
        self.state.save_game()

    def adjust_resolution(self, dx: int, dy: int) -> None:
        self.state.screen_width = max(640, self.state.screen_width + dx)
        self.state.screen_height = max(480, self.state.screen_height + dy)
        self.screen = pygame.display.set_mode((self.state.screen_width, self.state.screen_height))

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_p:
                    self.pause_menu_open = not self.pause_menu_open
                if event.key == pygame.K_c:
                    self.state.active_tool = "broom" if self.state.active_tool != "broom" else "buy"
                    self.state.cleaning_tool = self.state.active_tool == "broom"
                    self.state.active_task = "Balai prêt" if self.state.cleaning_tool else "Achat de terrain"
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.state.save_game()
                if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.state.load_game()
                    self.adjust_resolution(0, 0)
                if event.key == pygame.K_F5:
                    self.state.save_game()
                if event.key == pygame.K_F9:
                    self.state.load_game()
                    self.adjust_resolution(0, 0)
                if event.key == pygame.K_b:
                    self.jump_to_morning()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_click(event.pos)

    def handle_click(self, pos: Tuple[int, int]) -> None:
        grid_origin = (20, 120)
        x, y = pos

        if self.pause_menu_open:
            if self.handle_pause_click(pos):
                return

        if self.state.selling_dialog:
            self.handle_sell_click(pos)
            return

        if self.toolbar_rect().collidepoint(pos):
            self.handle_toolbar_click(pos)
            return

        tile_x = (x - grid_origin[0]) // TILE_SIZE
        tile_y = (y - grid_origin[1]) // TILE_SIZE
        tile = self.state.get_tile(tile_x, tile_y, create=False)
        if not tile:
            return

        if tile.special == "computer":
            self.open_sell_dialog()
            return

        if tile.special == "bed":
            self.jump_to_morning()
            return

        if self.state.active_tool == "broom":
            self.state.clean_tile(tile)
            return

        if self.state.active_tool == "build":
            building = ["cabane", "atelier", "tour"][self.state.build_selection % 3]
            self.state.place_building(tile, building)
            return

        if tile.has_tree and not tile.has_dust:
            self.state.chop_tree(tile)
            return

        self.state.buy_tile(tile)
        self.last_click = tile

    def handle_resolution_click(self, pos: Tuple[int, int]) -> None:
        x, y = pos
        base_x = self.state.screen_width - 200
        base_y = 20
        if pygame.Rect(base_x, base_y, 24, 24).collidepoint(pos):
            self.adjust_resolution(-32, 0)
        elif pygame.Rect(base_x + 64, base_y, 24, 24).collidepoint(pos):
            self.adjust_resolution(32, 0)
        elif pygame.Rect(base_x, base_y + 28, 24, 24).collidepoint(pos):
            self.adjust_resolution(0, -32)
        elif pygame.Rect(base_x + 64, base_y + 28, 24, 24).collidepoint(pos):
            self.adjust_resolution(0, 32)

    def jump_to_morning(self) -> None:
        self.state.day_time = 0

    def update(self, dt: float) -> None:
        self.state.spawn_dust(dt)
        self.state.update_trees(dt)
        self.state.update_time(dt)
        self.state.update_events(dt)
        self.state.refresh_task_board()
        self.update_lumberjacks(dt)
        self.animation_timer += dt
        self.autosave_timer += dt
        if self.autosave_timer >= AUTOSAVE_EVERY:
            self.state.save_game()
            self.autosave_timer = 0.0
            self.state.active_task = "Autosave"

    def update_lumberjacks(self, dt: float) -> None:
        enemies = [l for l in self.state.lumberjacks if not l.friendly]
        friends = [l for l in self.state.lumberjacks if l.friendly]
        # friendly units protect first
        for friend in friends:
            if enemies:
                enemy = min(enemies, key=lambda e: abs(e.x - friend.x) + abs(e.y - friend.y))
                dist = math.hypot(enemy.x - friend.x, enemy.y - friend.y)
                if dist < 0.2:
                    enemy.health -= dt * 2
                    if enemy.health <= 0:
                        self.state.lumberjacks.remove(enemy)
                        enemies.remove(enemy)
                        self.state.active_task = "Ennemi neutralisé"
        for lumberjack in self.state.lumberjacks:
            if lumberjack.chopping > 0:
                lumberjack.chopping -= dt
                if lumberjack.chopping <= 0 and lumberjack.target:
                    tile = self.state.get_tile(*lumberjack.target, create=False)
                    if tile:
                        self.handle_chop_result(lumberjack, tile)
                        lumberjack.current_task = None
                continue

            if lumberjack.friendly and enemies:
                target_enemy = min(enemies, key=lambda e: abs(e.x - lumberjack.x) + abs(e.y - lumberjack.y))
                dx = target_enemy.x - lumberjack.x
                dy = target_enemy.y - lumberjack.y
                dist = math.hypot(dx, dy)
                speed = 1.4
                if dist < 0.1:
                    target_enemy.health -= dt * 3
                    if target_enemy.health <= 0:
                        self.state.lumberjacks.remove(target_enemy)
                        enemies.remove(target_enemy)
                        self.state.active_task = "Ennemi neutralisé"
                    continue
                lumberjack.x += (dx / dist) * speed * dt
                lumberjack.y += (dy / dist) * speed * dt
                self.state.active_task = "Patrouille de défense"
                continue

            task = lumberjack.next_task()
            if not task or not self.is_task_valid(task):
                lumberjack.current_task = None
                task = self.assign_task_to_lumberjack(lumberjack)
                if not task:
                    continue

            if task.target:
                target_tile = self.state.get_tile(*task.target, create=False)
                if not target_tile:
                    lumberjack.current_task = None
                    continue
            else:
                target_tile = None

            if task.kind == "chop_tree" and target_tile and not target_tile.has_tree:
                lumberjack.current_task = None
                continue

            tx, ty = task.target if task.target else (lumberjack.x, lumberjack.y)
            dx = tx - lumberjack.x
            dy = ty - lumberjack.y
            dist = math.hypot(dx, dy)
            speed = 1.0 + task.weight * 0.2
            if dist > 0.05:
                lumberjack.x += (dx / max(dist, 0.001)) * speed * dt
                lumberjack.y += (dy / max(dist, 0.001)) * speed * dt
                continue

            self.resolve_task(lumberjack, task, target_tile, dt)

    def handle_chop_result(self, lumberjack: Lumberjack, tile: Tile) -> None:
        if lumberjack.friendly:
            self.state.chop_tree(tile)
        else:
            tile.has_tree = False
            tile.tree_growth = 0.0
            tile.has_dust = True
            tile.damage = min(1.0, tile.damage + 0.4)
            self.state.inventory["gold"] = max(0, self.state.inventory["gold"] - 2)
            self.state.active_task = "Ennemi sabote"

    def assign_task_to_lumberjack(self, lumberjack: Lumberjack) -> Optional[Task]:
        if not self.state.task_board:
            return None
        candidates = [t for t in self.state.task_board if self.is_task_valid(t)]
        if not candidates:
            return None
        def priority(task: Task) -> float:
            tx, ty = task.target if task.target else (lumberjack.x, lumberjack.y)
            dist = math.hypot(tx - lumberjack.x, ty - lumberjack.y)
            return task.weight - dist * 0.05

        best = max(candidates, key=priority)
        task_copy = Task.from_dict(best.to_dict())
        pending = [c for c in candidates if c is not best]
        if not lumberjack.task_queue and pending:
            follow_up = max(pending, key=priority)
            lumberjack.task_queue.append(Task.from_dict(follow_up.to_dict()))
        lumberjack.current_task = task_copy
        lumberjack.target = task_copy.target
        return task_copy

    def is_task_valid(self, task: Task) -> bool:
        if task.kind == "haul_storage":
            return (self.state.inventory.get("wood", 0) + self.state.inventory.get("dust", 0)) > 0
        if not task.target:
            return True
        tile = self.state.get_tile(*task.target, create=False)
        if not tile:
            return False
        if task.kind == "chop_tree":
            return tile.has_tree and tile.owned and not tile.has_dust
        if task.kind == "repair_building":
            return bool(tile.building) and (tile.damage > 0.05 or tile.has_dust)
        if task.kind == "assist_construction":
            return bool(tile.building) and tile.building_progress < 1.0
        if task.kind == "tend_plants":
            return tile.owned and not tile.has_tree and tile.tree_growth < 1.0 and not tile.building
        if task.kind == "patrol_fence":
            return tile.owned
        return True

    def resolve_task(self, lumberjack: Lumberjack, task: Task, tile: Optional[Tile], dt: float) -> None:
        if task.kind == "chop_tree":
            if tile and tile.has_tree:
                lumberjack.chopping = task.duration
                lumberjack.chop_duration = task.duration
                self.state.active_task = "Bûcheronnage assisté"
            else:
                lumberjack.current_task = None
            return

        if task.kind == "haul_storage":
            task.progress += dt
            if task.progress >= task.duration:
                delivered_wood = min(3, self.state.inventory.get("wood", 0))
                delivered_dust = min(2, self.state.inventory.get("dust", 0))
                self.state.inventory["wood"] -= delivered_wood
                self.state.inventory["dust"] -= delivered_dust
                self.state.inventory["gold"] += delivered_wood + delivered_dust
                self.state.active_task = "Ravitaille au dépôt"
                lumberjack.current_task = None
            return

        if task.kind == "repair_building" and tile:
            task.progress += dt
            if task.progress >= task.duration:
                tile.damage = max(0.0, tile.damage - 0.6)
                tile.has_dust = False
                self.state.active_task = "Réparation"
                lumberjack.current_task = None
            return

        if task.kind == "tend_plants" and tile:
            task.progress += dt
            if task.progress >= task.duration:
                tile.tree_growth = min(1.0, tile.tree_growth + 0.35)
                if tile.tree_growth >= 1.0:
                    tile.has_tree = True
                    tile.tree_type = "small"
                self.state.active_task = "Entretien des sols"
                lumberjack.current_task = None
            return

        if task.kind == "patrol_fence":
            task.progress += dt
            if task.progress >= task.duration:
                self.state.active_task = "Patrouille clôture"
                lumberjack.current_task = None
            return

        if task.kind == "assist_construction" and tile:
            task.progress += dt
            if task.progress >= task.duration:
                tile.building_progress = min(1.0, tile.building_progress + 0.4)
                tile.damage = max(0.0, tile.damage - 0.1)
                self.state.active_task = "Aide chantier"
                lumberjack.current_task = None
            return

        lumberjack.current_task = None

    def draw(self) -> None:
        self.screen.fill((40, 44, 52))
        self.draw_background_overlay()
        self.draw_header()
        self.draw_grid()
        self.draw_toolbar()
        if self.state.selling_dialog:
            self.draw_sell_dialog()
        if self.pause_menu_open:
            self.draw_pause_menu()
        pygame.display.flip()

    def draw_background_overlay(self) -> None:
        fraction = self.state.current_day_fraction()
        brightness = 0.4 + 0.6 * (math.sin(fraction * 2 * math.pi - math.pi / 2) * 0.5 + 0.5)
        overlay = pygame.Surface((self.state.screen_width, self.state.screen_height), pygame.SRCALPHA)
        if self.state.weather == "Pluie":
            color = (70, 90, 110, int(120 * brightness))
        elif self.state.weather == "Neige":
            color = (200, 220, 240, int(80 * brightness))
        elif self.state.weather == "Brouillard":
            color = (100, 100, 110, int(160 * brightness))
        else:
            color = (80, 120, 80, int(80 * brightness))
        overlay.fill(color)
        self.screen.blit(overlay, (0, 0))
        # pixel shimmer to show saison/météo ambiance
        noise = pygame.Surface((self.state.screen_width, self.state.screen_height), pygame.SRCALPHA)
        for _ in range(120):
            nx = random.randrange(0, self.state.screen_width)
            ny = random.randrange(0, self.state.screen_height)
            alpha = 40 if self.state.weather in ("Pluie", "Neige") else 20
            noise.set_at((nx, ny), (255, 255, 255, alpha))
        season_color = {
            "Printemps": (140, 200, 140, 30),
            "Été": (200, 220, 120, 25),
            "Automne": (200, 140, 80, 25),
            "Hiver": (180, 200, 220, 25),
        }.get(self.state.current_season(), (200, 200, 200, 20))
        tint = pygame.Surface((self.state.screen_width, self.state.screen_height), pygame.SRCALPHA)
        tint.fill(season_color)
        self.screen.blit(tint, (0, 0))
        self.screen.blit(noise, (0, 0))

    def draw_header(self) -> None:
        bar = pygame.Rect(10, 10, self.state.screen_width - 20, 88)
        pygame.draw.rect(self.screen, (20, 26, 32), bar, border_radius=10)
        pygame.draw.rect(self.screen, (120, 170, 140), bar, 2, border_radius=10)
        gold = self.state.inventory["gold"]
        wood = self.state.inventory["wood"]
        dust = self.state.inventory["dust"]
        friends = len([l for l in self.state.lumberjacks if l.friendly])
        enemies = len([l for l in self.state.lumberjacks if not l.friendly])
        trees = len([t for t in self.state.tiles.values() if t.has_tree and t.owned])
        buildings = len([t for t in self.state.tiles.values() if t.building])
        dust_count = len([t for t in self.state.tiles.values() if t.has_dust])
        rows = [
            [
                ("💰", gold, (246, 216, 120)),
                ("🪵", wood, (190, 164, 130)),
                ("🧹", dust, (210, 200, 170)),
                ("⏱", f"{int(self.state.current_day_fraction()*24)}h", (200, 220, 240)),
                ("☁", self.state.weather, (160, 210, 230)),
                ("🍃", self.state.current_season(), (220, 220, 180)),
            ],
            [
                ("🪓", friends, (200, 230, 200)),
                ("⚔️", enemies, (240, 150, 150)),
                ("🌲", trees, (180, 220, 180)),
                ("🏗️", buildings, (220, 200, 170)),
                ("✨", dust_count, (210, 200, 240)),
                ("⚙", self.state.active_task, (200, 230, 210)),
            ],
        ]
        row_h = 36
        for r, cells in enumerate(rows):
            cell_w = (bar.width - 20) // len(cells)
            for i, (icon, text, color) in enumerate(cells):
                rect = pygame.Rect(bar.x + 10 + i * cell_w, bar.y + 8 + r * (row_h + 4), cell_w - 8, row_h)
                pygame.draw.rect(self.screen, (30, 40, 44), rect, border_radius=8)
                pygame.draw.rect(self.screen, (80, 110, 100), rect, 1, border_radius=8)
                label = self.big_font.render(str(icon), True, color)
                self.screen.blit(label, (rect.x + 4, rect.y + 2))
                value = self.font.render(str(text), True, (235, 235, 235))
                self.screen.blit(value, (rect.x + 36, rect.y + 10))

    def toolbar_rect(self) -> pygame.Rect:
        return pygame.Rect(0, self.state.screen_height - 92, self.state.screen_width, 92)

    def handle_toolbar_click(self, pos: Tuple[int, int]) -> None:
        bar = self.toolbar_rect()
        buttons = [
            ("buy", pygame.Rect(bar.x + 20, bar.y + 16, 72, 60)),
            ("broom", pygame.Rect(bar.x + 112, bar.y + 16, 72, 60)),
            ("build", pygame.Rect(bar.x + 204, bar.y + 16, 72, 60)),
            ("build_next", pygame.Rect(bar.x + 292, bar.y + 16, 44, 60)),
        ]
        for action, rect in buttons:
            if rect.collidepoint(pos):
                if action == "build_next":
                    self.state.build_selection = (self.state.build_selection + 1) % 3
                    return
                self.state.active_tool = action if action != "build_next" else self.state.active_tool
                self.state.cleaning_tool = self.state.active_tool == "broom"
                self.state.active_task = {
                    "buy": "Achat de terrain",
                    "broom": "Balai prêt",
                    "build": "Construction",
                }.get(self.state.active_tool, self.state.active_task)
                return
        # open sell dialog on machine icon area
        shop_rect = pygame.Rect(bar.right - 140, bar.y + 12, 120, 68)
        if shop_rect.collidepoint(pos):
            self.open_sell_dialog()

    def draw_toolbar(self) -> None:
        bar = self.toolbar_rect()
        pygame.draw.rect(self.screen, (18, 22, 24), bar)
        pygame.draw.rect(self.screen, (110, 120, 130), bar, 2)
        labels = [
            ("icon_buy", "Acheter"),
            ("icon_broom", "Balai"),
            ("icon_build", "Construire"),
        ]
        for i, (icon_key, name) in enumerate(labels):
            rect = pygame.Rect(bar.x + 20 + i * 92, bar.y + 16, 72, 60)
            active = (self.state.active_tool == "buy" and i == 0) or (
                self.state.active_tool == "broom" and i == 1
            ) or (self.state.active_tool == "build" and i == 2)
            self.draw_icon_button(rect, self.sprites.get(icon_key), active)

        # build selection info
        build_rect = pygame.Rect(bar.x + 292, bar.y + 16, 44, 60)
        pygame.draw.rect(self.screen, (50, 60, 70), build_rect)
        pygame.draw.rect(self.screen, (150, 170, 190), build_rect, 1)
        build_name = ["Cabane", "Atelier", "Tour"][self.state.build_selection % 3]
        icon = self.font.render("→", True, (230, 230, 230))
        self.screen.blit(icon, (build_rect.centerx - 6, build_rect.y + 6))
        label = self.font.render(build_name, True, (230, 230, 230))
        self.screen.blit(label, (build_rect.x - 8, build_rect.y + 34))

        # selling machine quick access
        shop_rect = pygame.Rect(bar.right - 140, bar.y + 12, 120, 68)
        pygame.draw.rect(self.screen, (70, 110, 90), shop_rect)
        pygame.draw.rect(self.screen, (200, 230, 210), shop_rect, 2)
        shop_label = self.big_font.render("💻", True, (20, 40, 20))
        self.screen.blit(shop_label, (shop_rect.x + 8, shop_rect.y + 6))
        small = self.font.render("Vendre", True, (20, 40, 20))
        self.screen.blit(small, (shop_rect.x + 8, shop_rect.y + 40))

    def draw_icon_button(self, rect: pygame.Rect, icon: Optional[pygame.Surface], active: bool) -> None:
        pygame.draw.rect(self.screen, (60, 70, 80) if not active else (110, 150, 110), rect, border_radius=6)
        pygame.draw.rect(self.screen, (160, 180, 200), rect, 2)
        if icon:
            scaled = pygame.transform.scale(icon, (rect.width - 12, rect.height - 12))
            self.screen.blit(scaled, (rect.x + 6, rect.y + 6))
    def draw_grid(self) -> None:
        origin_x, origin_y = 20, 120
        season_key = self.season_to_key()
        for tile in sorted(self.state.tiles.values(), key=lambda t: (t.y, t.x)):
            rect = pygame.Rect(origin_x + tile.x * TILE_SIZE, origin_y + tile.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            ground = self.sprites.get(f"ground_{season_key}")
            if ground:
                self.screen.blit(ground, rect)
            if not tile.owned:
                neighbours = [
                    self.state.get_tile(tile.x + dx, tile.y + dy, create=False)
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                ]
                frontier = any(n and n.owned for n in neighbours)
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade_color = (32, 70, 60, 140) if frontier else (8, 8, 8, 160)
                shade.fill(shade_color)
                if frontier:
                    pygame.draw.rect(shade, (120, 200, 180, 180), shade.get_rect(), 2)
                self.screen.blit(shade, rect.topleft)
            pygame.draw.rect(self.screen, (30, 30, 30), rect, 1)

            if tile.special == "computer":
                pc = self.sprites.get("pc")
                if pc:
                    self.screen.blit(pc, rect)
            elif tile.special == "bed":
                bed = self.sprites.get("bed")
                if bed:
                    self.screen.blit(bed, rect)

            if tile.building:
                key = "cabin" if tile.building == "cabane" else "workshop" if tile.building == "atelier" else "watch"
                sprite = self.sprites.get(key)
                if sprite:
                    self.screen.blit(sprite, rect)

            if tile.has_tree:
                self.draw_tree(rect, tile)
            elif tile.tree_growth > 0 and tile.owned:
                pygame.draw.rect(self.screen, (90, 120, 80), rect.inflate(-12, -12))

            if tile.has_dust:
                dust = self.sprites.get("dust")
                if dust:
                    self.screen.blit(dust, rect)

            if tile.event:
                self.draw_event_marker(rect, tile.event)

            if tile == self.last_click:
                pygame.draw.rect(self.screen, (230, 200, 80), rect, 2)

        self.draw_lumberjacks(origin_x, origin_y)

    def draw_event_marker(self, rect: pygame.Rect, event: str) -> None:
        if event == "ennemi":
            sprite = self.sprites.get("enemy")
        elif event == "arbre_or":
            sprite = self.sprites.get("tree_gold")
        elif event == "ami_bucheron":
            sprite = self.sprites.get("lumberjack")
        elif event in ("fete", "visite"):
            sprite = self.sprites.get("icon_buy")
        else:
            sprite = None
        if sprite:
            small = pygame.transform.scale(sprite, (rect.width - 8, rect.height - 8))
            self.screen.blit(small, (rect.x + 4, rect.y + 4))

    def draw_lumberjacks(self, origin_x: int, origin_y: int) -> None:
        for lumberjack in self.state.lumberjacks:
            rect = pygame.Rect(
                origin_x + lumberjack.x * TILE_SIZE + 6,
                origin_y + lumberjack.y * TILE_SIZE + 6,
                TILE_SIZE - 12,
                TILE_SIZE - 12,
            )
            sprite_key = "lumberjack" if lumberjack.friendly else "enemy"
            sprite = self.sprites.get(sprite_key)
            task = lumberjack.current_task
            if sprite:
                wobble = 2 if (self.animation_timer % 0.6 < 0.3) else 0
                if task:
                    wobble = 3 if task.kind in ("haul_storage", "patrol_fence") else wobble
                    wobble = 1 if task.kind == "repair_building" else wobble
                jiggle = pygame.Rect(rect.x, rect.y + wobble, rect.width, rect.height)
                self.screen.blit(sprite, jiggle)
            if task:
                icon = {
                    "chop_tree": "🪓",
                    "haul_storage": "📦",
                    "repair_building": "🛠",
                    "tend_plants": "🌱",
                    "patrol_fence": "🛡",
                    "assist_construction": "🏗",
                }.get(task.kind, "⚙")
                bubble = pygame.Rect(rect.x - 2, rect.y - 18, rect.width + 4, 16)
                pygame.draw.rect(self.screen, (28, 34, 40), bubble, border_radius=4)
                pygame.draw.rect(self.screen, (120, 170, 200), bubble, 1, border_radius=4)
                label = self.font.render(icon, True, (230, 230, 230))
                self.screen.blit(label, (bubble.x + 4, bubble.y + 1))
                if task.progress > 0:
                    pct = min(1.0, task.progress / max(task.duration, 0.0001))
                    pygame.draw.rect(
                        self.screen,
                        (120, 200, 150),
                        (bubble.x + 20, bubble.y + 10, int((bubble.width - 24) * pct), 4),
                    )
            if lumberjack.chopping > 0:
                bar = pygame.Rect(rect.x, rect.y - 6, rect.width, 4)
                duration = max(lumberjack.chop_duration, SMALL_CHOP)
                progress = max(0.0, 1 - lumberjack.chopping / duration)
                pygame.draw.rect(self.screen, (30, 30, 30), bar)
                pygame.draw.rect(self.screen, (200, 200, 80), (bar.x, bar.y, bar.width * progress, bar.height))

    def draw_tree(self, rect: pygame.Rect, tile: Tile) -> None:
        key = "tree_large" if tile.tree_type == "large" else "tree_medium" if tile.tree_type == "medium" else "tree_small"
        if tile.event == "arbre_or":
            key = "tree_gold"
        tree = self.sprites.get(key)
        if tree:
            sway = 2 if (self.animation_timer % 0.8 < 0.4) else 0
            self.screen.blit(tree, (rect.x, rect.y - sway))

    def draw_resolution_panel(self) -> None:
        panel = pygame.Rect(self.state.screen_width - 220, 10, 210, 70)
        pygame.draw.rect(self.screen, (30, 30, 30), panel)
        pygame.draw.rect(self.screen, (70, 70, 70), panel, 1)
        label = self.big_font.render("Résolution", True, (220, 220, 220))
        self.screen.blit(label, (panel.x + 10, panel.y + 4))
        base_x = self.state.screen_width - 200
        base_y = 20
        self.draw_button(base_x, base_y, "-")
        self.draw_button(base_x + 64, base_y, "+")
        self.draw_button(base_x, base_y + 28, "-", vertical=True)
        self.draw_button(base_x + 64, base_y + 28, "+", vertical=True)
        size_text = self.font.render(f"{self.state.screen_width} x {self.state.screen_height}", True, (220, 220, 220))
        self.screen.blit(size_text, (panel.x + 100, panel.y + 36))

    def draw_button(self, x: int, y: int, text: str, vertical: bool = False) -> None:
        rect = pygame.Rect(x, y, 24, 24)
        pygame.draw.rect(self.screen, (90, 120, 90), rect)
        pygame.draw.rect(self.screen, (20, 30, 20), rect, 1)
        label = self.font.render(text, True, (10, 20, 10))
        self.screen.blit(label, (rect.x + 7, rect.y + 4))
        hint = "H" if vertical else "L"
        tag = self.font.render(hint, True, (200, 210, 200))
        self.screen.blit(tag, (rect.x + (10 if vertical else -4), rect.y + 16))

    def draw_pause_menu(self) -> None:
        overlay = pygame.Surface((self.state.screen_width, self.state.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        panel = pygame.Rect(self.state.screen_width // 2 - 180, self.state.screen_height // 2 - 100, 360, 200)
        pygame.draw.rect(overlay, (40, 60, 40, 220), panel)
        pygame.draw.rect(overlay, (200, 220, 200, 240), panel, 2)
        title = self.big_font.render("Menu confort", True, (240, 240, 240))
        overlay.blit(title, (panel.x + 20, panel.y + 16))
        body_lines = [
            "Ajustez la résolution sans stopper la partie",
            "C = balai | B = dormir | Clic = actions",
            "Ctrl+S/Ctrl+L = sauvegarder/charger",
        ]
        for i, text in enumerate(body_lines):
            surf = self.font.render(text, True, (230, 230, 230))
            overlay.blit(surf, (panel.x + 20, panel.y + 50 + i * 22))
        # resolution buttons
        base_x = panel.x + 20
        base_y = panel.y + 120
        buttons = [
            ("-H", pygame.Rect(base_x, base_y, 48, 28), (-32, 0)),
            ("+H", pygame.Rect(base_x + 60, base_y, 48, 28), (32, 0)),
            ("-V", pygame.Rect(base_x + 130, base_y, 48, 28), (0, -32)),
            ("+V", pygame.Rect(base_x + 190, base_y, 48, 28), (0, 32)),
        ]
        for label, rect, _ in buttons:
            pygame.draw.rect(overlay, (60, 90, 70), rect)
            pygame.draw.rect(overlay, (200, 220, 200), rect, 1)
            overlay.blit(self.font.render(label, True, (20, 30, 20)), (rect.x + 10, rect.y + 6))
        self.screen.blit(overlay, (0, 0))

    def handle_pause_click(self, pos: Tuple[int, int]) -> bool:
        panel = pygame.Rect(self.state.screen_width // 2 - 180, self.state.screen_height // 2 - 100, 360, 200)
        if not panel.collidepoint(pos):
            return False
        base_x = panel.x + 20
        base_y = panel.y + 120
        buttons = [
            (pygame.Rect(base_x, base_y, 48, 28), (-32, 0)),
            (pygame.Rect(base_x + 60, base_y, 48, 28), (32, 0)),
            (pygame.Rect(base_x + 130, base_y, 48, 28), (0, -32)),
            (pygame.Rect(base_x + 190, base_y, 48, 28), (0, 32)),
        ]
        for rect, delta in buttons:
            if rect.collidepoint(pos):
                self.adjust_resolution(*delta)
                return True
        return True

    def open_sell_dialog(self) -> None:
        self.state.pending_sale = {
            "wood": self.state.inventory.get("wood", 0),
            "dust": self.state.inventory.get("dust", 0),
        }
        self.state.pending_sale["gold"] = self.state.pending_sale["wood"] * 4 + self.state.pending_sale["dust"] * 2
        self.state.selling_dialog = True
        self.state.active_task = "Vente - confirmation"

    def handle_sell_click(self, pos: Tuple[int, int]) -> None:
        dialog = pygame.Rect(self.state.screen_width // 2 - 150, self.state.screen_height // 2 - 80, 300, 160)
        confirm = pygame.Rect(dialog.x + 30, dialog.y + 100, 100, 32)
        cancel = pygame.Rect(dialog.x + 170, dialog.y + 100, 100, 32)
        if confirm.collidepoint(pos):
            self.state.sell_resources()
            self.state.selling_dialog = False
            self.state.pending_sale = None
        elif cancel.collidepoint(pos) or not dialog.collidepoint(pos):
            self.state.selling_dialog = False
            self.state.pending_sale = None

    def draw_sell_dialog(self) -> None:
        dialog = pygame.Surface((320, 180), pygame.SRCALPHA)
        dialog.fill((20, 30, 20, 230))
        pygame.draw.rect(dialog, (200, 220, 200), dialog.get_rect(), 2)
        wood = self.state.pending_sale["wood"] if self.state.pending_sale else 0
        dust = self.state.pending_sale["dust"] if self.state.pending_sale else 0
        gold = self.state.pending_sale["gold"] if self.state.pending_sale else 0
        title = self.big_font.render("Vente au PC", True, (240, 240, 240))
        dialog.blit(title, (20, 16))
        lines = [f"Bois: {wood} (x4)", f"Poussière: {dust} (x2)", f"Total en or: {gold}"]
        for i, text in enumerate(lines):
            surf = self.font.render(text, True, (230, 230, 230))
            dialog.blit(surf, (20, 50 + i * 22))
        confirm = pygame.Rect(20, 120, 120, 36)
        cancel = pygame.Rect(180, 120, 120, 36)
        pygame.draw.rect(dialog, (90, 140, 90), confirm)
        pygame.draw.rect(dialog, (140, 90, 90), cancel)
        dialog.blit(self.font.render("Confirmer", True, (20, 30, 20)), (confirm.x + 8, confirm.y + 8))
        dialog.blit(self.font.render("Annuler", True, (20, 30, 20)), (cancel.x + 20, cancel.y + 8))
        screen_pos = (self.state.screen_width // 2 - 160, self.state.screen_height // 2 - 90)
        overlay = pygame.Surface((self.state.screen_width, self.state.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        self.screen.blit(dialog, screen_pos)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(30) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        self.state.save_game()
        pygame.quit()

    def season_to_key(self) -> str:
        mapping = {
            "Printemps": "spring",
            "Été": "summer",
            "Automne": "autumn",
            "Hiver": "winter",
        }
        return mapping.get(self.state.current_season(), "spring")


if __name__ == "__main__":
    Game().run()
