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
    def __init__(self, shape):
        self.shape = shape
        self.rotation = 0
        self.x = random.randint(0, GRID_WIDTH - 4)
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
        pygame.key.set_repeat(50, 50)  # Enable key repeat with 50ms delay
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.reset_game()

    def reset_game(self):
        """Initialize or reset the game"""
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_tetromino = Tetromino(random.choice(list(Shape)))
        self.next_tetromino = Tetromino(random.choice(list(Shape)))
        self.score = 0
        self.game_over = False

    def is_valid_position(self, tetromino):
        """Check if tetromino position is valid"""
        for x, y in tetromino.get_blocks():
            if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock_tetromino(self):
        """Lock the tetromino in place"""
        for x, y in self.current_tetromino.get_blocks():
            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.grid[y][x] = self.current_tetromino.color

    def clear_lines(self):
        """Clear completed lines and return score"""
        lines_cleared = 0
        y = GRID_HEIGHT - 1
        while y >= 0:
            if all(self.grid[y][x] is not None for x in range(GRID_WIDTH)):
                del self.grid[y]
                self.grid.insert(0, [None for _ in range(GRID_WIDTH)])
                lines_cleared += 1
            else:
                y -= 1
        return lines_cleared * 100

    def get_current_fps(self):
        """Calculate FPS based on score (increases every 50 points)"""
        return 5 + (self.score // 50) * 0.5

    def handle_input(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_LEFT:
                    self.current_tetromino.move_left()
                    if not self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.move_right()
                elif event.key == pygame.K_RIGHT:
                    self.current_tetromino.move_right()
                    if not self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.move_left()
                elif event.key == pygame.K_UP:
                    self.current_tetromino.rotate()
                    if not self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.rotation -= 1
                elif event.key == pygame.K_DOWN:
                    self.current_tetromino.move_down()
                    if not self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.move_down()
                elif event.key == pygame.K_SPACE:
                    # Hard drop - move down until we can't move anymore
                    while self.is_valid_position(self.current_tetromino):
                        self.current_tetromino.move_down()
                    # Move back up to the last valid position (undo last move)
                    self.current_tetromino.y -= 1
                elif event.key == pygame.K_r:
                    if self.game_over:
                        self.reset_game()
        
        return True

    def update(self):
        """Update game state"""
        if self.game_over:
            return

        # Move tetromino down
        self.current_tetromino.move_down()
        if not self.is_valid_position(self.current_tetromino):
            # Undo the move
            self.current_tetromino.y -= 1
            self.lock_tetromino()

            # Check for game over
            if not self.is_valid_position(self.next_tetromino):
                self.game_over = True
                return

            # Clear lines and update score
            self.score += self.clear_lines()

            # Spawn next tetromino
            self.current_tetromino = self.next_tetromino
            self.next_tetromino = Tetromino(random.choice(list(Shape)))

    def draw(self):
        """Draw the game"""
        self.screen.fill(BLACK)

        # Draw grid
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
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
            self.screen.blit(game_over_text, (WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 - 50))
            self.screen.blit(restart_text, (WINDOW_WIDTH // 2 - 140, WINDOW_HEIGHT // 2))

        pygame.display.flip()

    def run(self):
        """Main game loop"""
        running = True
        while running:
            running = self.handle_input()

            if not self.game_over:
                self.update()
            
            self.draw()
            self.clock.tick(self.get_current_fps())

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = TetrisGame()
    game.run()
