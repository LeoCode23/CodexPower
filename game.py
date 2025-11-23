import json
import math
import random
from dataclasses import dataclass, asdict
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

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Tile":
        return Tile(**data)


@dataclass
class Lumberjack:
    x: float
    y: float
    target: Optional[Tuple[int, int]] = None
    chopping: float = 0.0
    friendly: bool = True
    chop_duration: float = 0.0

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
        self.active_task = "Achat de terrain"
        self.selling_dialog = False
        self.pending_sale: Optional[dict] = None
        self.load_or_init_tiles()

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

    def get_tile(self, x: int, y: int) -> Tile:
        tile = self.tiles.get((x, y))
        if tile:
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
            if tile.has_tree:
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

    def current_day_fraction(self) -> float:
        return self.day_time / DAY_LENGTH_SECONDS

    def current_season(self) -> str:
        index = int(self.season_time // SEASON_LENGTH_SECONDS)
        return ["Printemps", "Été", "Automne", "Hiver"][index]

    def roll_weather(self) -> None:
        options = ["Soleil", "Pluie", "Neige", "Brouillard"]
        self.weather = random.choice(options)

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
            "lumberjacks": [asdict(l) for l in self.lumberjacks],
            "active_task": self.active_task,
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
            self.lumberjacks = [Lumberjack(**l) for l in lumber_data]
        else:
            self.lumberjacks = [Lumberjack(0.0, 0.0)]
        self.active_task = data.get("active_task", "Achat de terrain")
        self.queue_neighbors()

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


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Retraite Rustique")
        self.state = GameState((960, 720))
        self.screen = pygame.display.set_mode((self.state.screen_width, self.state.screen_height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 18)
        self.big_font = pygame.font.SysFont("arial", 24)
        self.running = True
        self.last_click: Optional[Tile] = None
        self.pause_menu_open = False
        self.animation_timer = 0.0

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
                    self.state.toggle_cleaner()
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
                if event.key == pygame.K_LEFTBRACKET:
                    self.adjust_resolution(-32, 0)
                if event.key == pygame.K_RIGHTBRACKET:
                    self.adjust_resolution(32, 0)
                if event.key == pygame.K_SEMICOLON:
                    self.adjust_resolution(0, -32)
                if event.key == pygame.K_QUOTE:
                    self.adjust_resolution(0, 32)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_click(event.pos)

    def handle_click(self, pos: Tuple[int, int]) -> None:
        grid_origin = (20, 80)
        x, y = pos
        # Resolution panel buttons
        res_panel = pygame.Rect(self.state.screen_width - 220, 10, 210, 60)
        if res_panel.collidepoint(pos) or (self.pause_menu_open and self.handle_pause_click(pos)):
            self.handle_resolution_click(pos)
            return

        if self.state.selling_dialog:
            self.handle_sell_click(pos)
            return

        tile_x = (x - grid_origin[0]) // TILE_SIZE
        tile_y = (y - grid_origin[1]) // TILE_SIZE
        tile = self.state.get_tile(tile_x, tile_y)
        if not tile:
            return

        if tile.special == "computer":
            self.open_sell_dialog()
            return

        if tile.special == "bed":
            self.jump_to_morning()
            return

        if self.state.cleaning_tool:
            self.state.clean_tile(tile)
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
        self.update_lumberjacks(dt)
        self.animation_timer += dt

    def update_lumberjacks(self, dt: float) -> None:
        targets = [t for t in self.state.tiles.values() if t.has_tree and not t.has_dust and t.owned]
        for lumberjack in self.state.lumberjacks:
            if lumberjack.chopping > 0:
                lumberjack.chopping -= dt
                if lumberjack.chopping <= 0 and lumberjack.target:
                    tile = self.state.get_tile(*lumberjack.target)
                    self.state.chop_tree(tile)
                continue

            if lumberjack.target and not self.state.get_tile(*lumberjack.target).has_tree:
                lumberjack.target = None

            if not lumberjack.target:
                if not targets:
                    continue
                target_tile = min(targets, key=lambda t: abs(t.x - lumberjack.x) + abs(t.y - lumberjack.y))
                lumberjack.target = (target_tile.x, target_tile.y)
                continue

            tx, ty = lumberjack.target
            dx = tx - lumberjack.x
            dy = ty - lumberjack.y
            dist = math.hypot(dx, dy)
            speed = 1.2  # tiles per second
            if dist < 0.05:
                tile = self.state.get_tile(tx, ty)
                chop_time = {"small": SMALL_CHOP, "medium": MEDIUM_CHOP, "large": LARGE_CHOP}.get(tile.tree_type, MEDIUM_CHOP)
                lumberjack.chopping = chop_time
                lumberjack.chop_duration = chop_time
                continue
            lumberjack.x += (dx / dist) * speed * dt
            lumberjack.y += (dy / dist) * speed * dt

    def draw(self) -> None:
        self.screen.fill((40, 44, 52))
        self.draw_background_overlay()
        self.draw_header()
        self.draw_grid()
        self.draw_resolution_panel()
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
        gold = self.state.inventory["gold"]
        wood = self.state.inventory["wood"]
        dust = self.state.inventory["dust"]
        texts = [
            f"Or: {gold}",
            f"Bois: {wood}",
            f"Poussière: {dust}",
            f"Saison: {self.state.current_season()} ({self.state.weather})",
            f"Tâche: {self.state.active_task}",
            f"Outil: {'Balai' if self.state.cleaning_tool else 'Main'}",
            "Ctrl+S/F5 sauvegarde | Ctrl+L/F9 charge | C balai | B lit | P menu",
        ]
        for i, text in enumerate(texts):
            surface = self.font.render(text, True, (230, 230, 230))
            self.screen.blit(surface, (20, 10 + i * 18))

    def draw_grid(self) -> None:
        origin_x, origin_y = 20, 80
        for tile in sorted(self.state.tiles.values(), key=lambda t: (t.y, t.x)):
            rect = pygame.Rect(origin_x + tile.x * TILE_SIZE, origin_y + tile.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            base_color = (70, 100, 70) if tile.owned else (50, 60, 50)
            pygame.draw.rect(self.screen, base_color, rect)
            pygame.draw.rect(self.screen, (40, 40, 40), rect, 1)

            if tile.special == "computer":
                pygame.draw.rect(self.screen, (120, 180, 220), rect.inflate(-8, -8))
                label = self.font.render("PC", True, (10, 30, 50))
                self.screen.blit(label, (rect.x + 6, rect.y + 8))
            elif tile.special == "bed":
                pygame.draw.rect(self.screen, (200, 170, 120), rect.inflate(-8, -8))
                label = self.font.render("Lit", True, (70, 50, 20))
                self.screen.blit(label, (rect.x + 6, rect.y + 8))

            if tile.has_tree:
                self.draw_tree(rect, tile)
            elif tile.tree_growth > 0 and tile.owned:
                pygame.draw.rect(self.screen, (90, 120, 80), rect.inflate(-12, -12))

            if tile.has_dust:
                dust_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                dust_surf.fill((180, 170, 140, 160))
                self.screen.blit(dust_surf, rect.topleft)

            if tile.event:
                self.draw_event_marker(rect, tile.event)

            if tile == self.last_click:
                pygame.draw.rect(self.screen, (230, 200, 80), rect, 2)

        self.draw_lumberjacks(origin_x, origin_y)

    def draw_event_marker(self, rect: pygame.Rect, event: str) -> None:
        palette = {
            "ami_bucheron": (120, 180, 240),
            "arbre_or": (240, 200, 60),
            "ennemi": (200, 80, 80),
        }
        color = palette.get(event, (220, 220, 220))
        pygame.draw.rect(self.screen, color, rect.inflate(-16, -16))

    def draw_lumberjacks(self, origin_x: int, origin_y: int) -> None:
        for lumberjack in self.state.lumberjacks:
            rect = pygame.Rect(
                origin_x + lumberjack.x * TILE_SIZE + 6,
                origin_y + lumberjack.y * TILE_SIZE + 6,
                TILE_SIZE - 12,
                TILE_SIZE - 12,
            )
            wobble = int(math.sin(self.animation_timer * 6) * 2)
            color = (150 + wobble, 90, 60)
            pygame.draw.rect(self.screen, color, rect)
            axe_flash = pygame.Rect(rect.x + rect.width - 6, rect.y + 2, 4, 8)
            pygame.draw.rect(self.screen, (220, 220, 180), axe_flash)
            if lumberjack.chopping > 0:
                bar = pygame.Rect(rect.x, rect.y - 6, rect.width, 4)
                duration = max(lumberjack.chop_duration, SMALL_CHOP)
                progress = max(0.0, 1 - lumberjack.chopping / duration)
                pygame.draw.rect(self.screen, (30, 30, 30), bar)
                pygame.draw.rect(self.screen, (200, 200, 80), (bar.x, bar.y, bar.width * progress, bar.height))

    def draw_tree(self, rect: pygame.Rect, tile: Tile) -> None:
        colors = {"small": (70, 160, 90), "medium": (80, 150, 100), "large": (90, 140, 110)}
        pygame.draw.rect(self.screen, colors.get(tile.tree_type, (70, 140, 90)), rect.inflate(-10, -10))
        if self.animation_timer % 0.6 < 0.3:
            sway = pygame.Rect(rect.x + 6, rect.y + 4, rect.width - 12, 6)
            pygame.draw.rect(self.screen, (120, 180, 120), sway)

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
        self.screen.blit(overlay, (0, 0))

    def handle_pause_click(self, pos: Tuple[int, int]) -> bool:
        panel = pygame.Rect(self.state.screen_width // 2 - 180, self.state.screen_height // 2 - 100, 360, 200)
        return panel.collidepoint(pos)

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
        pygame.quit()


if __name__ == "__main__":
    Game().run()
