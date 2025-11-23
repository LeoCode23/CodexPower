import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple

import pygame


# Constants
TILE_SIZE = 32
GRID_WIDTH = 6
GRID_HEIGHT = 6
MAX_DUST_TILES = 3
DAY_LENGTH_SECONDS = 24 * 60  # 24 minutes in real time
SEASON_LENGTH_SECONDS = DAY_LENGTH_SECONDS / 4
SAVE_FILE = Path("savegame.json")


@dataclass
class Tile:
    x: int
    y: int
    owned: bool = False
    has_tree: bool = False
    tree_growth: float = 0.0
    has_dust: bool = False
    special: Optional[str] = None  # computer or bed

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Tile":
        return Tile(**data)


@dataclass
class Lumberjack:
    x: int
    y: int
    target: Optional[Tuple[int, int]] = None
    chopping: float = 0.0

    def position(self) -> Tuple[int, int]:
        return self.x, self.y


class GameState:
    def __init__(self, screen_size: Tuple[int, int]):
        self.screen_width, self.screen_height = screen_size
        self.tiles: List[Tile] = []
        self.inventory = {"gold": 20, "wood": 0, "dust": 0}
        self.dust_timer = 0.0
        self.day_time = 0.0
        self.season_time = 0.0
        self.weather = "Soleil"
        self.lumberjack = Lumberjack(0, 0)
        self.cleaning_tool = False
        self.load_or_init_tiles()

    def load_or_init_tiles(self) -> None:
        if SAVE_FILE.exists():
            self.load_game()
            return

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                owned = 1 <= x <= 4 and 1 <= y <= 4
                has_tree = owned and random.random() < 0.25
                tile = Tile(x=x, y=y, owned=owned, has_tree=has_tree, tree_growth=1.0)
                self.tiles.append(tile)

        # Place special structures
        self.get_tile(0, 0).special = "computer"
        self.get_tile(0, 1).special = "bed"

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
            return self.tiles[y * GRID_WIDTH + x]
        return None

    def tiles_with_dust(self) -> List[Tile]:
        return [t for t in self.tiles if t.has_dust]

    def owned_tiles(self) -> List[Tile]:
        return [t for t in self.tiles if t.owned]

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
        for tile in self.tiles:
            if tile.has_tree:
                continue
            if not tile.owned:
                continue
            tile.tree_growth = min(1.0, tile.tree_growth + dt / 20)
            if tile.tree_growth >= 1.0 and random.random() < 0.1:
                tile.has_tree = True

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

    def chop_tree(self, tile: Tile) -> None:
        tile.has_tree = False
        tile.tree_growth = 0.0
        self.inventory["wood"] += 1

    def sell_resources(self) -> None:
        gained = self.inventory["wood"] * 4 + self.inventory["dust"] * 2
        self.inventory["gold"] += gained
        self.inventory["wood"] = 0
        self.inventory["dust"] = 0

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

    def save_game(self) -> None:
        data = {
            "tiles": [t.to_dict() for t in self.tiles],
            "inventory": self.inventory,
            "day_time": self.day_time,
            "season_time": self.season_time,
            "weather": self.weather,
            "screen": [self.screen_width, self.screen_height],
            "lumberjack": asdict(self.lumberjack),
        }
        SAVE_FILE.write_text(json.dumps(data, indent=2))

    def load_game(self) -> None:
        data = json.loads(SAVE_FILE.read_text())
        self.tiles = [Tile.from_dict(t) for t in data["tiles"]]
        self.inventory = data.get("inventory", {"gold": 0, "wood": 0, "dust": 0})
        self.day_time = data.get("day_time", 0.0)
        self.season_time = data.get("season_time", 0.0)
        self.weather = data.get("weather", "Soleil")
        self.screen_width, self.screen_height = data.get("screen", [800, 600])
        lumberjack_data = data.get("lumberjack", {})
        self.lumberjack = Lumberjack(**lumberjack_data)


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
                if event.key == pygame.K_c:
                    self.state.toggle_cleaner()
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
        if res_panel.collidepoint(pos):
            self.handle_resolution_click(pos)
            return

        tile_x = (x - grid_origin[0]) // TILE_SIZE
        tile_y = (y - grid_origin[1]) // TILE_SIZE
        tile = self.state.get_tile(tile_x, tile_y)
        if not tile:
            return

        if tile.special == "computer":
            self.state.sell_resources()
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
        self.update_lumberjack(dt)

    def update_lumberjack(self, dt: float) -> None:
        if self.state.lumberjack.chopping > 0:
            self.state.lumberjack.chopping -= dt
            if self.state.lumberjack.chopping <= 0 and self.last_click:
                self.state.chop_tree(self.last_click)
            return

        targets = [t for t in self.state.tiles if t.has_tree and not t.has_dust and t.owned]
        if not targets:
            return
        target = min(targets, key=lambda t: abs(t.x - self.state.lumberjack.x) + abs(t.y - self.state.lumberjack.y))
        lx, ly = self.state.lumberjack.x, self.state.lumberjack.y
        if (lx, ly) == (target.x, target.y):
            self.state.lumberjack.chopping = 1.5
            self.last_click = target
            return

        if lx < target.x:
            self.state.lumberjack.x += 1
        elif lx > target.x:
            self.state.lumberjack.x -= 1
        elif ly < target.y:
            self.state.lumberjack.y += 1
        elif ly > target.y:
            self.state.lumberjack.y -= 1

    def draw(self) -> None:
        self.screen.fill((40, 44, 52))
        self.draw_background_overlay()
        self.draw_header()
        self.draw_grid()
        self.draw_resolution_panel()
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

    def draw_header(self) -> None:
        gold = self.state.inventory["gold"]
        wood = self.state.inventory["wood"]
        dust = self.state.inventory["dust"]
        texts = [
            f"Or: {gold}",
            f"Bois: {wood}",
            f"Poussière: {dust}",
            f"Saison: {self.state.current_season()} ({self.state.weather})",
            f"Outil: {'Balai' if self.state.cleaning_tool else 'Main'}",
            "Ctrl+S/F5 sauvegarde | Ctrl+L/F9 charge | C balai | B lit",
        ]
        for i, text in enumerate(texts):
            surface = self.font.render(text, True, (230, 230, 230))
            self.screen.blit(surface, (20, 10 + i * 18))

    def draw_grid(self) -> None:
        origin_x, origin_y = 20, 80
        for tile in self.state.tiles:
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
                pygame.draw.rect(self.screen, (60, 140, 80), rect.inflate(-10, -10))
            elif tile.tree_growth > 0 and tile.owned:
                pygame.draw.rect(self.screen, (90, 120, 80), rect.inflate(-12, -12))

            if tile.has_dust:
                dust_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                dust_surf.fill((180, 170, 140, 160))
                self.screen.blit(dust_surf, rect.topleft)

            if tile == self.last_click:
                pygame.draw.rect(self.screen, (230, 200, 80), rect, 2)

        self.draw_lumberjack(origin_x, origin_y)

    def draw_lumberjack(self, origin_x: int, origin_y: int) -> None:
        rect = pygame.Rect(
            origin_x + self.state.lumberjack.x * TILE_SIZE + 8,
            origin_y + self.state.lumberjack.y * TILE_SIZE + 8,
            TILE_SIZE - 16,
            TILE_SIZE - 16,
        )
        pygame.draw.rect(self.screen, (150, 90, 60), rect)
        if self.state.lumberjack.chopping > 0:
            bar = pygame.Rect(rect.x, rect.y - 6, rect.width, 4)
            progress = 1 - self.state.lumberjack.chopping / 1.5
            pygame.draw.rect(self.screen, (30, 30, 30), bar)
            pygame.draw.rect(self.screen, (200, 200, 80), (bar.x, bar.y, bar.width * progress, bar.height))

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

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(30) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
