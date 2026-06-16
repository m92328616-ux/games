import os
import sys
import time
import select

# Game Settings
WIDTH, HEIGHT = 50, 15
PADDLE_SIZE = 3

# Game State
p1_y = HEIGHT // 2 - 1
p2_y = HEIGHT // 2 - 1
p2_target_y = HEIGHT // 2 - 1
bx, by = WIDTH // 2, HEIGHT // 2
bdx, bdy = 1, 1
score1, score2 = 0, 0

# --- PORTABLE RAW ARROW KEY INTERCEPTOR ---
if os.name == 'nt':
    import msvcrt
    def get_arrow_action():
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            # Windows sends a prefix byte (0 or 224) for arrow keys
            if ch in (b'\x00', b'\xe0'):
                ch2 = msvcrt.getch()
                if ch2 == b'H': return "up"
                if ch2 == b'P': return "down"
            elif ch.lower() == b'q':
                return "quit"
        return None
else:
    import tty
    import termios
    def get_arrow_action():
        dr, dw, de = select.select([sys.stdin], [], [], 0)
        if dr:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                # UNIX terminals send a 3-byte sequence for arrow keys: \x1b, [, and then A/B/C/D
                if ch == '\x1b':
                    # Non-blocking check for the remaining escape sequence bytes
                    r2, w2, e2 = select.select([sys.stdin], [], [], 0.01)
                    if r2:
                        seq = sys.stdin.read(2)
                        if seq == '[A': return "up"
                        if seq == '[B': return "down"
                elif ch.lower() == 'q':
                    return "quit"
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None

# AI Math Engine
def predict_ball_landing(x, y, dx, dy):
    if dx <= 0:
        return HEIGHT // 2 - 1
    steps_to_paddle = (WIDTH - 2 - x) // dx
    pred_y = y + (dy * steps_to_paddle)
    while pred_y < 0 or pred_y >= HEIGHT:
        if pred_y < 0:
            pred_y = -pred_y
        if pred_y >= HEIGHT:
            pred_y = 2 * (HEIGHT - 1) - pred_y
    return max(0, min(HEIGHT - PADDLE_SIZE, pred_y))

p2_target_y = predict_ball_landing(bx, by, bdx, bdy)

# Main Game Loop
try:
    while True:
        # 1. READ KEYBOARD ARROW STRUCK
        action = get_arrow_action()
        if action == "quit":
            break
        elif action == "up" and p1_y > 0:
            p1_y -= 1
        elif action == "down" and p1_y < HEIGHT - PADDLE_SIZE:
            p1_y += 1

        # 2. RUN AI PREDICTIVE MOVEMENT
        if p2_y < p2_target_y:
            p2_y += 1
        elif p2_y > p2_target_y:
            p2_y -= 1

        # 3. STEP PHYSICS FORWARD
        bx += bdx
        by += bdy

        # Wall Bounce (Top / Bottom)
        if by <= 0 or by >= HEIGHT - 1:
            bdy *= -1
            p2_target_y = predict_ball_landing(bx, by, bdx, bdy)

        # Player 1 Paddle Collision
        if bx == 1 and p1_y <= by < p1_y + PADDLE_SIZE:
            bdx *= -1
            bx = 2
            p2_target_y = predict_ball_landing(bx, by, bdx, bdy)

        # Player 2 Paddle Collision
        if bx == WIDTH - 2 and p2_y <= by < p2_y + PADDLE_SIZE:
            bdx *= -1
            bx = WIDTH - 3

        # Scoring mechanics
        if bx <= 0:
            score2 += 1
            bx, by = WIDTH // 2, HEIGHT // 2
            bdx, bdy = 1, 1
            p2_target_y = predict_ball_landing(bx, by, bdx, bdy)
        elif bx >= WIDTH - 1:
            score1 += 1
            bx, by = WIDTH // 2, HEIGHT // 2
            bdx, bdy = -1, 1
            p2_target_y = predict_ball_landing(bx, by, bdx, bdy)

        # 4. DRAW THE CURRENT FRAME
        output = []
        output.append(" " * 10 + "P1 (You): {}  |  P2 (AI): {}".format(score1, score2))
        output.append("-" * (WIDTH + 2))
        
        for y in range(HEIGHT):
            row_chars = []
            for x in range(WIDTH):
                if x == 0 and p1_y <= y < p1_y + PADDLE_SIZE:
                    row_chars.append("█")
                elif x == WIDTH - 1 and p2_y <= y < p2_y + PADDLE_SIZE:
                    row_chars.append("█")
                elif x == bx and y == by:
                    row_chars.append("O")
                else:
                    row_chars.append(" ")
            output.append("|" + "".join(row_chars) + "|")
            
        output.append("-" * (WIDTH + 2))
        output.append(" Controls: [↑ Arrow] Up  [↓ Arrow] Down  [Q] Quit")
        
        # Clear screen and draw
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write("\n".join(output) + "\n")
        sys.stdout.flush()

        time.sleep(0.06)

except KeyboardInterrupt:
    pass
print("\nGame Over!")
