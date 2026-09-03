import pygame
import random
import sys
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 900
GRID_SIZE = 30
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE
FPS = 5
DEFAULT_RENDER_FPS = 10
MIN_RENDER_FPS = 5
MAX_RENDER_FPS = 60
MIN_GRID_WIDTH = 4
MAX_GRID_WIDTH = 30
MIN_GRID_HEIGHT = 8
MAX_GRID_HEIGHT = 40
GRAVITY_INTERVAL = 1 / FPS

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
PURPLE = (128, 0, 128)
RED = (255, 0, 0)

# Tetris Shapes
class Shape(Enum):
    I = 0  # Cyan
    O = 1  # Yellow
    T = 2  # Purple
    S = 3  # Green
    Z = 4  # Red
    J = 5  # Blue
    L = 6  # Orange

SHAPES = {
    Shape.I: [[(0, 0), (1, 0), (2, 0), (3, 0)],
              [(1, 0), (1, 1), (1, 2), (1, 3)]],
    Shape.O: [[(0, 0), (1, 0), (0, 1), (1, 1)]],
    Shape.T: [[(1, 0), (0, 1), (1, 1), (2, 1)],
              [(1, 0), (1, 1), (0, 1), (1, 2)],
              [(0, 1), (1, 1), (2, 1), (1, 2)],
              [(0, 0), (0, 1), (1, 1), (0, 2)]],
    Shape.S: [[(1, 0), (2, 0), (0, 1), (1, 1)],
              [(0, 0), (0, 1), (1, 1), (1, 2)]],
    Shape.Z: [[(0, 0), (1, 0), (1, 1), (2, 1)],
              [(1, 0), (0, 1), (1, 1), (0, 2)]],
    Shape.J: [[(0, 0), (0, 1), (1, 1), (2, 1)],
              [(0, 0), (1, 0), (0, 1), (0, 2)],
              [(0, 0), (1, 0), (2, 0), (2, 1)],
              [(1, 0), (1, 1), (0, 2), (1, 2)]],
    Shape.L: [[(2, 0), (0, 1), (1, 1), (2, 1)],
              [(0, 0), (0, 1), (0, 2), (1, 2)],
              [(0, 0), (1, 0), (2, 0), (0, 1)],
              [(0, 0), (1, 0), (1, 1), (1, 2)]]
}

SHAPE_COLORS = {
    Shape.I: CYAN,
    Shape.O: YELLOW,
    Shape.T: PURPLE,
    Shape.S: GREEN,
    Shape.Z: RED,
    Shape.J: BLUE,
    Shape.L: ORANGE
}

class Tetromino:
    def __init__(self, shape, grid_width=GRID_WIDTH):
        self.shape = shape
        self.rotation = 0
        self.x = random.randint(0, max(0, grid_width - 4))
        self.y = 0
        self.color = SHAPE_COLORS[shape]

    def get_blocks(self):
        """Return the blocks of the current tetromino"""
        rotations = SHAPES[self.shape]
        blocks = rotations[self.rotation % len(rotations)]
        return [(self.x + dx, self.y + dy) for dx, dy in blocks]

    def rotate(self):
        """Rotate the tetromino"""
        self.rotation = (self.rotation + 1) % len(SHAPES[self.shape])

    def move_down(self):
        """Move tetromino down"""
        self.y += 1

    def move_left(self):
        """Move tetromino left"""
        self.x -= 1

    def move_right(self):
        """Move tetromino right"""
        self.x += 1

class TetrisGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris")
        pygame.key.set_repeat(0)
        self.held_keys = set()
        self.grid_width = GRID_WIDTH
        self.grid_height = GRID_HEIGHT
        self.render_fps = DEFAULT_RENDER_FPS
        self.fall_timer = 0.0
        self.paused = False
        self.debug_visible = False
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.reset_game()

    def reset_game(self):
        """Initialize or reset the game"""
        self.grid = [[None for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        self.current_tetromino = Tetromino(random.choice(list(Shape)), self.grid_width)
        self.next_tetromino = Tetromino(random.choice(list(Shape)), self.grid_width)
        self.score = 0
        self.game_over = False
        self.fall_timer = 0.0

    def resize_grid(self, width, height):
        """Resize the board and restart with dimensions that fit the window."""
        self.grid_width = max(MIN_GRID_WIDTH, min(MAX_GRID_WIDTH, width))
        self.grid_height = max(MIN_GRID_HEIGHT, min(MAX_GRID_HEIGHT, height))
        self.screen = pygame.display.set_mode(
            (self.grid_width * GRID_SIZE, self.grid_height * GRID_SIZE)
        )
        self.held_keys.clear()
        self.reset_game()

    def adjust_render_fps(self, amount):
        """Change render smoothness without changing gravity speed."""
        self.render_fps = max(MIN_RENDER_FPS, min(MAX_RENDER_FPS, self.render_fps + amount))

    def is_valid_position(self, tetromino):
        """Check if tetromino position is valid"""
        for x, y in tetromino.get_blocks():
            if x < 0 or x >= self.grid_width or y >= self.grid_height:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock_tetromino(self):
        """Lock the tetromino in place"""
        for x, y in self.current_tetromino.get_blocks():
            if 0 <= y < self.grid_height and 0 <= x < self.grid_width:
                self.grid[y][x] = self.current_tetromino.color
        self.score += 10

    def clear_lines(self):
        """Clear completed lines and return score"""
        lines_cleared = 0
        y = self.grid_height - 1
        while y >= 0:
            if all(self.grid[y][x] is not None for x in range(self.grid_width)):
                del self.grid[y]
                self.grid.insert(0, [None for _ in range(self.grid_width)])
                lines_cleared += 1
            else:
                y -= 1
        return lines_cleared * 50

    def get_current_fps(self):
        """Return the display rate selected in the debug controls."""
        return self.render_fps

    def handle_input(self):
        """Handle user input"""
        pressed_this_frame = set()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.WINDOWFOCUSLOST:
                self.held_keys.clear()
                continue
            if event.type == pygame.KEYUP:
                self.held_keys.discard(event.key)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_p:
                    if not self.debug_visible:
                        self.paused = not self.paused
                    self.held_keys.clear()
                    continue
                if event.key == pygame.K_z:
                    self.debug_visible = not self.debug_visible
                    self.paused = self.debug_visible
                    self.held_keys.clear()
                    continue
                if self.debug_visible:
                    if event.key == pygame.K_w:
                        self.resize_grid(self.grid_width + 1, self.grid_height)
                    elif event.key == pygame.K_s:
                        self.resize_grid(self.grid_width - 1, self.grid_height)
                    elif event.key == pygame.K_e:
                        self.resize_grid(self.grid_width, self.grid_height + 1)
                    elif event.key == pygame.K_d:
                        self.resize_grid(self.grid_width, self.grid_height - 1)
                    elif event.key == pygame.K_LEFTBRACKET:
                        self.adjust_render_fps(-5)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self.adjust_render_fps(5)
                    if event.key in (pygame.K_w, pygame.K_s, pygame.K_e, pygame.K_d,
                                     pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                        continue
                if self.paused:
                    continue
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN):
                    self.held_keys.add(event.key)
                    pressed_this_frame.add(event.key)
                    if event.key == pygame.K_LEFT:
                        self.current_tetromino.move_left()
                        if not self.is_valid_position(self.current_tetromino):
                            self.current_tetromino.move_right()
                    elif event.key == pygame.K_RIGHT:
                        self.current_tetromino.move_right()
                        if not self.is_valid_position(self.current_tetromino):
                            self.current_tetromino.move_left()
                    else:
                        self.current_tetromino.move_down()
                        if not self.is_valid_position(self.current_tetromino):
                            self.current_tetromino.y -= 1
                elif event.key == pygame.K_UP:
                    previous_rotation = self.current_tetromino.rotation
                    self.current_tetromino.rotate()
                    if not self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.rotation = previous_rotation
                elif event.key == pygame.K_SPACE:
                    # Hard drop - move down until we can't move anymore
                    while self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.move_down()
                    # Move back up to the last valid position (undo last move)
                    self.current_tetromino.y -= 1
                elif event.key == pygame.K_r:
                    if self.game_over:
                        self.reset_game()

        if not self.game_over and not self.paused:
            if (pygame.K_LEFT in self.held_keys
                    and pygame.K_LEFT not in pressed_this_frame
                    and pygame.K_RIGHT not in self.held_keys):
                self.current_tetromino.move_left()
                if not self.is_valid_position(self.current_tetromino):
                    self.current_tetromino.move_right()
            elif (pygame.K_RIGHT in self.held_keys
                  and pygame.K_RIGHT not in pressed_this_frame
                  and pygame.K_LEFT not in self.held_keys):
                self.current_tetromino.move_right()
                if not self.is_valid_position(self.current_tetromino):
                    self.current_tetromino.move_left()

            if pygame.K_DOWN in self.held_keys and pygame.K_DOWN not in pressed_this_frame:
                self.current_tetromino.move_down()
                if not self.is_valid_position(self.current_tetromino):
                    self.current_tetromino.y -= 1
        
        return True

    def update(self, elapsed=GRAVITY_INTERVAL):
        """Update game state"""
        if self.game_over or self.paused:
            return

        self.fall_timer += elapsed
        while self.fall_timer >= GRAVITY_INTERVAL and not self.game_over:
            self.fall_timer -= GRAVITY_INTERVAL
            self.current_tetromino.move_down()
            if not self.is_valid_position(self.current_tetromino):
                self.current_tetromino.y -= 1
                self.lock_tetromino()

                self.score += self.clear_lines()

                self.current_tetromino = self.next_tetromino
                self.next_tetromino = Tetromino(random.choice(list(Shape)), self.grid_width)

                if not self.is_valid_position(self.current_tetromino):
                    self.game_over = True

    def draw(self):
        """Draw the game"""
        self.screen.fill(BLACK)

        # Draw grid
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, GRAY, rect, 1)
                if self.grid[y][x]:
                    pygame.draw.rect(self.screen, self.grid[y][x], rect)

        # Draw current tetromino
        for x, y in self.current_tetromino.get_blocks():
            if y >= 0:
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, self.current_tetromino.color, rect)
                pygame.draw.rect(self.screen, WHITE, rect, 2)

        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        # Draw game over message
        if self.game_over:
            game_over_text = self.font.render("GAME OVER", True, RED)
            restart_text = pygame.font.Font(None, 24).render("Press R to restart or ESC to quit", True, WHITE)
            screen_width, screen_height = self.screen.get_size()
            self.screen.blit(game_over_text, (screen_width // 2 - 100, screen_height // 2 - 50))
            self.screen.blit(restart_text, (screen_width // 2 - 140, screen_height // 2))

        if self.paused:
            pause_text = self.font.render("PAUSED - Press P to resume " \
            "Esc to quit", True, YELLOW)
            self.screen.blit(pause_text, (10, 50))

        if self.debug_visible:
            debug_font = pygame.font.Font(None, 24)
            debug_lines = [
                f"DEBUG  Board: {self.grid_width} x {self.grid_height}",
                f"Render FPS: {self.render_fps}",
                "W/S width  E/D height  [ or ] FPS",
            ]
            for index, line in enumerate(debug_lines):
                text = debug_font.render(line, True, WHITE)
                self.screen.blit(text, (10, 90 + index * 24))

        pygame.display.flip()

    def run(self):
        """Main game loop"""
        running = True
        while running:
            running = self.handle_input()

            elapsed = self.clock.tick(self.get_current_fps()) / 1000
            self.update(elapsed)
            
            self.draw()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = TetrisGame()
    game.run()
