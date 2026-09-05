import curses
import os
import random
import sys
import time


FPS = 20
MAX_LEVEL = 10
ALIEN_ROWS = 5
ALIEN_COLUMNS = 8
ALIEN_GAP_X = 8
ALIEN_GAP_Y = 2
ALIEN_SPEED = 7
ALIEN_DROP = 1
PLAYER_FRAME = "018"
BULLET_FRAME = "019"
PLAYER_HIT_FRAMES = ("020", "021")
ENEMY_HIT_FRAME = "022"
SAUCER_FRAME = "023"


def load_frames(file_path):
    frames = {}
    with open(file_path, "r", encoding="utf-8") as data_file:
        for raw_line in data_file:
            line = raw_line.rstrip("\r\n")
            if len(line) >= 3 and line[:3].isdigit():
                frames.setdefault(line[:3], []).append(line[3:].rstrip())

    required = [f"{number:03d}" for number in range(1, 11)]
    required += [PLAYER_FRAME, BULLET_FRAME, *PLAYER_HIT_FRAMES, ENEMY_HIT_FRAME, SAUCER_FRAME]
    missing = [frame_id for frame_id in required if frame_id not in frames]
    if missing:
        raise ValueError(f"Missing frames in ASCINV.DAT: {', '.join(missing)}")
    return frames


def build_aliens(width):
    formation_width = (ALIEN_COLUMNS - 1) * ALIEN_GAP_X + 5
    start_x = max(1, (width - formation_width) // 2)
    aliens = []
    for row in range(ALIEN_ROWS):
        frame_ids = (f"{row * 2 + 1:03d}", f"{row * 2 + 2:03d}")
        for column in range(ALIEN_COLUMNS):
            aliens.append({
                "row": row,
                "column": column,
                "frame_ids": frame_ids,
                "x": start_x + column * ALIEN_GAP_X,
                "y": 2 + (ALIEN_ROWS - 1 - row) * ALIEN_GAP_Y,
                "alive": True,
            })
    return aliens


def reset_remaining_aliens(aliens):
    for row in range(ALIEN_ROWS):
        row_aliens = sorted(
            (alien for alien in aliens if alien["alive"] and alien["row"] == row),
            key=lambda alien: alien["column"],
        )
        for position, alien in enumerate(row_aliens):
            alien["x"] = 1 + position * ALIEN_GAP_X
            alien["y"] = 2 + (ALIEN_ROWS - 1 - row) * ALIEN_GAP_Y


def new_game(width, height):
    return {
        "aliens": build_aliens(width),
        "bullets": [],
        "enemy_bullets": [],
        "side_hit_effect": None,
        "enemy_effects": [],
        "player_explosion": None,
        "death_pause": 0,
        "player_x": width // 2,
        "player_y": height - 4,
        "player_invulnerable": 0,
        "player_effect_timer": 0,
        "score": 0,
        "lives": 5,
        "level": 1,
        "alien_direction": 1,
        "animation_frame": 0,
        "animation_timer": 0,
        "alien_shot_timer": 1.0,
        "shot_timer": 0,
        "saucer_x": 0,
        "saucer_timer": random.uniform(12, 24),
        "saucer_active": False,
        "saucer_direction": 1,
        "game_over": False,
        "won": False,
        "level_transition": 0,
    }


def start_next_level(game, width):
    game["level"] += 1
    game["lives"] = 5
    game["aliens"] = build_aliens(width)
    game["bullets"] = []
    game["enemy_bullets"] = []
    game["enemy_effects"] = []
    game["alien_direction"] = 1
    game["animation_frame"] = 0
    game["animation_timer"] = 0
    game["alien_shot_timer"] = 1.0
    game["saucer_active"] = False
    game["saucer_timer"] = random.uniform(12, 24)
    game["level_transition"] = 1.5


def enemy_speed_multiplier(game, living_count):
    level_bonus = 1.12 ** (game["level"] - 1)
    low_count_bonus = 1.08 ** max(0, 10 - living_count)
    return level_bonus * low_count_bonus


def frame_size(frames, frame_id):
    lines = frames[frame_id]
    return max((len(line) for line in lines), default=1), len(lines)


def draw_lines(screen, y, x, lines, color):
    height, width = screen.getmaxyx()
    for line_number, line in enumerate(lines):
        target_y = y + line_number
        if 0 <= target_y < height and x < width:
            try:
                screen.addstr(target_y, max(0, x), line[:max(0, width - x)], color)
            except curses.error:
                pass


def draw_frame(screen, x, y, frames, frame_id, color):
    draw_lines(screen, y, x, frames[frame_id], color)


def alien_hit(alien, bullet_x, bullet_y, frames):
    alien_width, alien_height = frame_size(frames, alien["frame_ids"][0])
    return (alien["x"] - 1 <= bullet_x <= alien["x"] + alien_width
            and alien["y"] - 1 <= bullet_y <= alien["y"] + alien_height)


def player_hit(player_x, player_y, bullet_x, bullet_y, frames):
    player_width, player_height = frame_size(frames, PLAYER_FRAME)
    return (player_x - 1 <= bullet_x <= player_x + player_width
            and player_y - 1 <= bullet_y <= player_y + player_height)


def living_aliens(game):
    return [alien for alien in game["aliens"] if alien["alive"]]


def update_game(game, frames, width, height, delta):
    if game["game_over"] or game["won"]:
        return

    if game["level_transition"] > 0:
        game["level_transition"] = max(0, game["level_transition"] - delta)
        return

    game["shot_timer"] -= delta
    game["player_invulnerable"] = max(0, game["player_invulnerable"] - delta)
    game["player_effect_timer"] = max(0, game["player_effect_timer"] - delta)
    if game["side_hit_effect"] is not None:
        game["side_hit_effect"]["age"] += delta
        if game["side_hit_effect"]["age"] >= 0.35:
            game["side_hit_effect"] = None
    for effect in game["enemy_effects"]:
        effect["age"] += delta
    game["enemy_effects"] = [effect for effect in game["enemy_effects"] if effect["age"] < 0.4]
    if game["player_explosion"] is not None:
        game["player_explosion"]["age"] += delta
        if game["player_explosion"]["age"] >= 0.7:
            if game["lives"] > 0:
                game["death_pause"] = 1.0
            else:
                game["game_over"] = True
            game["player_explosion"] = None
        return

    if game["death_pause"] > 0:
        game["death_pause"] = max(0, game["death_pause"] - delta)
        if game["death_pause"] == 0:
            player_width, _ = frame_size(frames, PLAYER_FRAME)
            game["player_x"] = max(1, width - player_width - 2)
            game["player_invulnerable"] = 1.0
        return

    living = living_aliens(game)
    if not living:
        if game["level"] >= MAX_LEVEL:
            game["won"] = True
        else:
            start_next_level(game, width)
        return

    speed_multiplier = enemy_speed_multiplier(game, len(living))
    game["animation_timer"] -= delta
    if game["animation_timer"] <= 0:
        game["animation_frame"] = 1 - game["animation_frame"]
        game["animation_timer"] = 0.35 / speed_multiplier

    for bullet in game["bullets"]:
        bullet[1] -= 18 * delta
    game["bullets"] = [bullet for bullet in game["bullets"] if bullet[1] > 1]

    for bullet in game["enemy_bullets"]:
        bullet[1] += 9 * delta
    remaining_enemy_bullets = []
    for bullet in game["enemy_bullets"]:
        if player_hit(game["player_x"], game["player_y"], bullet[0], bullet[1], frames):
            hit_frame = random.choice(PLAYER_HIT_FRAMES)
            if game["player_invulnerable"] <= 0:
                game["lives"] -= 1
                game["player_explosion"] = {"age": 0, "frame_id": hit_frame}
                game["bullets"] = []
                game["enemy_bullets"] = []
                break
            if game["player_effect_timer"] <= 0:
                game["player_effect_timer"] = 0.35
                game["side_hit_effect"] = {"age": 0, "frame_id": hit_frame}
            break
        elif bullet[1] < height - 1:
            remaining_enemy_bullets.append(bullet)
    game["enemy_bullets"] = remaining_enemy_bullets

    alien_width = max(frame_size(frames, alien["frame_ids"][0])[0] for alien in living)
    left = min(alien["x"] for alien in living)
    right = max(alien["x"] + alien_width for alien in living)
    if (right >= width - 1 and game["alien_direction"] > 0) or (left <= 1 and game["alien_direction"] < 0):
        game["alien_direction"] *= -1
        for alien in living:
            alien["y"] += ALIEN_DROP
    for alien in living:
        alien["x"] += game["alien_direction"] * ALIEN_SPEED * speed_multiplier * delta
        if alien["y"] + 2 >= game["player_y"]:
            game["game_over"] = True

    game["alien_shot_timer"] -= delta
    if game["alien_shot_timer"] <= 0:
        shooter = random.choice(living)
        game["enemy_bullets"].append([shooter["x"] + 2, shooter["y"] + 2])
        game["alien_shot_timer"] = random.uniform(0.8, 1.8)

    for bullet in game["bullets"][:]:
        for alien in living:
            if alien_hit(alien, int(bullet[0]), int(bullet[1]), frames):
                alien["alive"] = False
                game["score"] += (5 - alien["row"]) * 10
                game["enemy_effects"].append({"x": alien["x"], "y": alien["y"], "age": 0})
                game["bullets"].remove(bullet)
                break

    game["saucer_timer"] -= delta
    if not game["saucer_active"] and game["saucer_timer"] <= 0:
        game["saucer_active"] = True
        game["saucer_direction"] = random.choice((-1, 1))
        saucer_width = frame_size(frames, SAUCER_FRAME)[0]
        game["saucer_x"] = -saucer_width if game["saucer_direction"] > 0 else width

    if game["saucer_active"]:
        game["saucer_x"] += game["saucer_direction"] * 12 * delta
        saucer_width = frame_size(frames, SAUCER_FRAME)[0]
        if game["saucer_x"] > width + 1 or game["saucer_x"] + saucer_width < -1:
            game["saucer_active"] = False
            game["saucer_timer"] = random.uniform(12, 24)

        for bullet in game["bullets"][:]:
            if game["saucer_x"] <= bullet[0] < game["saucer_x"] + saucer_width and 1 <= bullet[1] <= 2:
                game["score"] += 100
                game["saucer_active"] = False
                game["saucer_timer"] = random.uniform(12, 24)
                game["bullets"].remove(bullet)
                break


def draw_game(screen, game, frames, width, height):
    screen.erase()
    if game["level_transition"] > 0:
        title = f"LEVEL {game['level']}"
        draw_lines(screen, height // 2, max(0, (width - len(title)) // 2), [title], curses.A_BOLD)
        screen.refresh()
        return

    lives_display = "☺" * max(0, game["lives"])
    status = f"SCORE {game['score']:05d}   LEVEL {game['level']}   LIVES {lives_display}"
    draw_lines(screen, 0, 0, [status[:width]], curses.A_NORMAL)

    for alien in game["aliens"]:
        if alien["alive"]:
            frame_id = alien["frame_ids"][game["animation_frame"]]
            draw_frame(screen, int(alien["x"]), alien["y"], frames, frame_id, curses.A_NORMAL)
    if game["player_explosion"] is not None:
        frame_id = game["player_explosion"]["frame_id"]
        draw_frame(screen, int(game["player_x"]), game["player_y"], frames, frame_id, curses.color_pair(1) | curses.A_BOLD)
    elif game["side_hit_effect"] is not None:
        frame_id = game["side_hit_effect"]["frame_id"]
        draw_frame(screen, int(game["player_x"]), game["player_y"], frames, frame_id, curses.color_pair(1) | curses.A_BOLD)
    if game["saucer_active"]:
        draw_frame(screen, int(game["saucer_x"]), 1, frames, SAUCER_FRAME, curses.A_NORMAL)
    for effect in game["enemy_effects"]:
        draw_frame(screen, int(effect["x"]), effect["y"], frames, ENEMY_HIT_FRAME, curses.A_NORMAL)
    if game["player_explosion"] is None and game["side_hit_effect"] is None and game["death_pause"] <= 0:
        draw_frame(screen, int(game["player_x"]), game["player_y"], frames, PLAYER_FRAME, curses.color_pair(1) | curses.A_BOLD)

    for bullet in game["bullets"]:
        draw_frame(screen, int(bullet[0]), int(bullet[1]), frames, BULLET_FRAME, curses.color_pair(2))
    for bullet in game["enemy_bullets"]:
        draw_frame(screen, int(bullet[0]), int(bullet[1]), frames, BULLET_FRAME, curses.color_pair(3))
    screen.addstr(height - 2, 0, "_" * max(1, width - 1), curses.A_NORMAL)

    if game["game_over"] or game["won"]:
        message = "YOU WIN - press R to restart, Q to quit" if game["won"] else "GAME OVER - press R to restart, Q to quit"
        draw_lines(screen, height // 2, max(0, (width - len(message)) // 2), [message], curses.A_NORMAL)
    screen.refresh()


def configure_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)


def run_game(screen, file_path):
    frames = load_frames(file_path)
    configure_colors()
    screen.nodelay(True)
    screen.keypad(True)
    curses.curs_set(0)
    height, width = screen.getmaxyx()
    if height < 22 or width < 68:
        screen.addstr(0, 0, "Resize the terminal to at least 68 columns by 22 rows.")
        screen.refresh()
        screen.nodelay(False)
        screen.getch()
        return

    game = new_game(width, height)
    last_time = time.monotonic()
    running = True
    while running:
        now = time.monotonic()
        delta = min(0.1, now - last_time)
        last_time = now
        key = screen.getch()
        while key != -1:
            if key in (ord("q"), ord("Q"), 27):
                running = False
            elif key in (curses.KEY_LEFT, ord("a"), ord("A")) and not game["game_over"] and not game["won"] and game["player_explosion"] is None and game["death_pause"] <= 0:
                game["player_x"] = max(1, game["player_x"] - 2)
            elif key in (curses.KEY_RIGHT, ord("d"), ord("D")) and not game["game_over"] and not game["won"] and game["player_explosion"] is None and game["death_pause"] <= 0:
                game["player_x"] = min(width - 6, game["player_x"] + 2)
            elif key == ord(" ") and not game["game_over"] and not game["won"] and game["player_explosion"] is None and game["death_pause"] <= 0 and game["shot_timer"] <= 0:
                game["bullets"].append([game["player_x"] + 2, game["player_y"] - 1])
                game["shot_timer"] = 0.35
            elif key in (ord("r"), ord("R")) and (game["game_over"] or game["won"]):
                game = new_game(width, height)
            key = screen.getch()

        update_game(game, frames, width, height, delta)
        draw_game(screen, game, frames, width, height)
        time.sleep(max(0, 1 / FPS - (time.monotonic() - now)))


if __name__ == "__main__":
    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ASCINV.DAT")
    try:
        curses.wrapper(run_game, data_file)
    except (OSError, ValueError, curses.error) as error:
        print(f"Unable to start Space Invaders: {error}")
        sys.exit(1)