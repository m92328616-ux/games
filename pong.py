import random
import tkinter as tk

# Game Settings
WIDTH, HEIGHT = 50, 15
PADDLE_SIZE = 3
CELL_SIZE = 16
WINDOW_PADDING = 20
CANVAS_WIDTH = WIDTH * CELL_SIZE
CANVAS_HEIGHT = HEIGHT * CELL_SIZE
FRAME_DELAY = 80

# Game State
p1_y = HEIGHT // 2 - 1
p2_y = HEIGHT // 2 - 1
p2_target_y = HEIGHT // 2 - 1
bx, by = WIDTH // 2, HEIGHT // 2
bdx, bdy = 1, 1
score1, score2 = 0, 0
game_over = False
winner_name = None
key_state = {"up": False, "down": False}

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


def predict_ball_landing_approx(x, y, dx, dy):
    exact = predict_ball_landing(x, y, dx, dy)
    error = random.randint(-4, 5)
    approx = exact + error
    approx = max(0, min(HEIGHT - PADDLE_SIZE, approx))
    return approx

p2_target_y = predict_ball_landing_approx(bx, by, bdx, bdy)

# Tkinter Setup
root = tk.Tk()
root.title("Pong")
root.resizable(False, False)
canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT + 40, bg="black")
canvas.pack(padx=WINDOW_PADDING, pady=WINDOW_PADDING)

status_text = canvas.create_text(
    CANVAS_WIDTH // 2,
    CANVAS_HEIGHT + 20,
    fill="white",
    font=("Consolas", 12),
    text=""
)


def draw_frame():
    canvas.delete("game")
    # draw walls
    canvas.create_rectangle(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, outline="white", tag="game")
    # player paddle
    canvas.create_rectangle(
        0,
        p1_y * CELL_SIZE,
        CELL_SIZE,
        (p1_y + PADDLE_SIZE) * CELL_SIZE,
        fill="white",
        tag="game",
    )
    # ai paddle
    canvas.create_rectangle(
        (WIDTH - 1) * CELL_SIZE,
        p2_y * CELL_SIZE,
        WIDTH * CELL_SIZE,
        (p2_y + PADDLE_SIZE) * CELL_SIZE,
        fill="white",
        tag="game",
    )
    # ball
    canvas.create_oval(
        bx * CELL_SIZE + 2,
        by * CELL_SIZE + 2,
        bx * CELL_SIZE + CELL_SIZE - 2,
        by * CELL_SIZE + CELL_SIZE - 2,
        fill="white",
        tag="game",
    )
    if game_over and winner_name:
        display_text = f"{winner_name} wins! Closing in 3 seconds..."
    else:
        display_text = f"P1 (You): {score1}    P2 (AI): {score2}    [↑/↓] Move    [Q] Quit"

    canvas.itemconfigure(
        status_text,
        text=display_text,
    )


def reset_ball(direction=1):
    global bx, by, bdx, bdy, p2_target_y
    bx, by = WIDTH // 2, HEIGHT // 2
    bdx = direction
    bdy = 1
    p2_target_y = predict_ball_landing(bx, by, bdx, bdy)


def end_game(winner):
    global game_over, winner_name
    if game_over:
        return
    game_over = True
    winner_name = winner
    draw_frame()
    root.after(3000, root.destroy)


def on_key_press(event):
    if event.keysym == "Up":
        key_state["up"] = True
    elif event.keysym == "Down":
        key_state["down"] = True
    elif event.keysym.lower() == "q":
        root.destroy()


def on_key_release(event):
    if event.keysym == "Up":
        key_state["up"] = False
    elif event.keysym == "Down":
        key_state["down"] = False


def game_step():
    global p1_y, p2_y, bx, by, bdx, bdy, score1, score2, p2_target_y

    if game_over:
        return

    if key_state["up"] and p1_y > 0:
        p1_y -= 1
    if key_state["down"] and p1_y < HEIGHT - PADDLE_SIZE:
        p1_y += 1

    if p2_y < p2_target_y:
        p2_y += 1
    elif p2_y > p2_target_y:
        p2_y -= 1

    bx += bdx
    by += bdy

    if by <= 0 or by >= HEIGHT - 1:
        bdy *= -1
        p2_target_y = predict_ball_landing_approx(bx, by, bdx, bdy)

    if bx == 1 and p1_y <= by < p1_y + PADDLE_SIZE:
        bdx *= -1
        bx = 2
        p2_target_y = predict_ball_landing_approx(bx, by, bdx, bdy)

    if bx == WIDTH - 2 and p2_y <= by < p2_y + PADDLE_SIZE:
        bdx *= -1
        bx = WIDTH - 3

    if bx <= 0:
        score2 += 1
        if score2 >= 10:
            end_game("AI")
        else:
            reset_ball(direction=1)
    elif bx >= WIDTH - 1:
        score1 += 1
        if score1 >= 10:
            end_game("You")
        else:
            reset_ball(direction=-1)
    else:
        # periodically introduce new AI error while tracking
        if random.random() < 0.16:
            p2_target_y = predict_ball_landing_approx(bx, by, bdx, bdy)

    draw_frame()
    root.after(FRAME_DELAY, game_step)


root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)
root.protocol("WM_DELETE_WINDOW", root.destroy)

draw_frame()
root.after(FRAME_DELAY, game_step)
root.mainloop()
