import turtle
import random

#  Game config const
delay = 100 # Game loop in ms
score = 0
high_score = 0
ismoving = False # Input lock var prevent apid input errors
game_over_flag = False
food2 = None
segments = []

def place_food_item(food_item):
    """Place food away from the snake head, body, and other food."""
    while True:
        x = random.randint(-14, 14) * 20
        y = random.randint(-14, 14) * 20
        if head.distance(x, y) < 20:
            continue
        if any(seg.distance(x, y) < 20 for seg in segments):
            continue
        if food_item is not food and food.distance(x, y) < 20:
            continue
        if food2 is not None and food_item is not food2 and food2.distance(x, y) < 20:
            continue
        food_item.goto(x, y)
        break

# Init window layer using Screen() construct obj
wnd = turtle.Screen()
wnd.setup(width=600, height=600)
wnd.bgcolor("black")
wnd.tracer(0) # Turns off autoscreen upd for smooth anims

# Snake head init
head = turtle.Turtle()
head.speed(0)
head.shape("square")
head.color("green")
head.penup()
head.goto(0, 0)
head.direction = "stop"

# Snake food init
food = turtle.Turtle()
food.speed(0)
food.shape("circle")
food.color("red")
food.penup()
place_food_item(food)

# Optional second food (created when score reaches 100)
extra_food_added = False

# Scoreboard disp init
pen = turtle.Turtle()
pen.speed(0)
pen.shape("square")
pen.color("white")
pen.penup()
pen.hideturtle()
pen.goto(0, 260)
pen.write("Score: 0 High Score: " + str(high_score), align="center", font=("Courier", 24, "normal"))

# Game over display pen (red)
game_over_pen = turtle.Turtle()
game_over_pen.speed(0)
game_over_pen.color("red")
game_over_pen.penup()
game_over_pen.hideturtle()

def show_game_over():
    try:
        global game_over_flag
        game_over_pen.clear()
        game_over_pen.goto(0, 40)
        game_over_pen.write("GAME OVER", align="center", font=("Courier", 36, "bold"))

        # Freeze input and prevent further game loop scheduling
        game_over_flag = True

        # Hide snake head, body, and food items
        try:
            head.goto(1000, 1000)
            for seg in segments:
                seg.goto(1000, 1000)
            food.goto(1000, 1000)
            if food2 is not None:
                food2.goto(1000, 1000)
        except Exception:
            pass

        # Unbind movement keys to stop gameplay input
        try:
            wnd.onkey(None, "Up")
            wnd.onkey(None, "Down")
            wnd.onkey(None, "Left")
            wnd.onkey(None, "Right")
        except Exception:
            pass

        # Show final score under the GAME OVER title and instruction
        try:
            pen.clear()
            pen.goto(0, 0)
            score_txt = "Score: " + str(score) + " High Score: " + str(high_score)
            pen.write(score_txt, align="center", font=("Courier", 24, "normal"))
            # Instruction to close or retry
            pen.goto(0, -40)
            pen.write("Press Q to quit or R to retry", align="center", font=("Courier", 18, "normal"))
        except Exception:
            pass

        # Bind 'q', 'Q', 'r', and 'R' for closing and retry
        try:
            wnd.onkey(lambda: wnd.bye(), 'q')
            wnd.onkey(lambda: wnd.bye(), 'Q')
            wnd.onkey(reset_game, 'r')
            wnd.onkey(reset_game, 'R')
            wnd.listen()
        except Exception:
            pass
    except (turtle.Terminator, turtle.TurtleGraphicsError, Exception):
        pass


def reset_game():
    global score, ismoving, game_over_flag, extra_food_added, food2
    game_over_flag = False
    score = 0
    ismoving = False
    head.goto(0, 0)
    head.direction = "stop"

    # Hide body segments
    for seg in segments:
        seg.goto(1000, 1000)
    segments.clear()

    # Remove second food if present
    if extra_food_added and food2 is not None:
        try:
            food2.goto(1000, 1000)
        except Exception:
            pass
        food2 = None
        extra_food_added = False

    game_over_pen.clear()
    pen.clear()
    upd_score_disp()
    place_food_item(food)

    try:
        wnd.onkey(go_up, "Up")
        wnd.onkey(go_down, "Down")
        wnd.onkey(go_left, "Left")
        wnd.onkey(go_right, "Right")
        wnd.onkey(reset_game, 'r')
        wnd.onkey(reset_game, 'R')
        wnd.onkey(lambda: wnd.bye(), 'q')
        wnd.onkey(lambda: wnd.bye(), 'Q')
        wnd.listen()
        wnd.ontimer(game_loop, delay)
    except Exception:
        pass

# Funcs to handle movment direct
def go_up():
    global ismoving, game_over_flag
    if game_over_flag:
        return
    if head.direction != "down" and not ismoving:
        head.direction = "up"
        ismoving = True

def go_down():
    global ismoving, game_over_flag
    if game_over_flag:
        return
    if head.direction != "up" and not ismoving:
        head.direction = "down"
        ismoving = True

def go_left():
    global ismoving, game_over_flag
    if game_over_flag:
        return
    if head.direction != "right" and not ismoving:
        head.direction = "left"
        ismoving = True

def go_right():
    global ismoving, game_over_flag
    if game_over_flag:
        return
    if head.direction != "left" and not ismoving:
        head.direction = "right"
        ismoving = True

def move():
    if head.direction == "up":
        y = head.ycor()
        head.sety(y + 20)
    
    if head.direction == "down":
        y = head.ycor()
        head.sety(y - 20)

    if head.direction == "left":
        x = head.xcor()
        head.setx(x - 20)
    
    if head.direction == "right":
        x = head.xcor()
        head.setx(x + 20)

def upd_score_disp():
    """Helper func to draw scores without interpol crashes"""
    try:
        pen.clear()
        pen.goto(0, 260)
        score_txt = "Score: " + str(score) + " High Score: " + str(high_score)
        pen.write(score_txt, align="center", font=("Courier", 24, "normal"))
    except (turtle.Terminator, turtle.TurtleGraphicsError, NameError, AttributeError):
        pass

# Keyboard event listening setups directly linked to window obj container
wnd.listen()
wnd.onkey(go_up, "Up")
wnd.onkey(go_down, "Down")
wnd.onkey(go_left, "Left")
wnd.onkey(go_right, "Right")

def game_loop():
    """Native engine loop replace 'while True'"""
    global score, high_score, ismoving, extra_food_added, food2

    try:
        # Reset frame input lock
        ismoving = False

        # Check for wall collision boundary crash
        if head.xcor() > 290 or head.xcor() < -290 or head.ycor() > 290 or head.ycor() < -290:
            head.goto(0, 0)
            head.direction = "stop"

            # Show game over message
            show_game_over()

            # Hide body segs on reset
            for seg in segments:
                seg.goto(1000, 1000)
            segments.clear()

            # Remove extra food on reset
            if extra_food_added and food2 is not None:
                try:
                    food2.goto(1000, 1000)
                except Exception:
                    pass
                extra_food_added = False
                food2 = None

            return
        
        # Check for collision w/ primary food item
        ate_food = False
        if head.distance(food) < 20:
            ate_food = True
            x = random.randint(-14, 14) * 20
            y = random.randint(-14, 14) * 20
            food.goto(x,y)

            # Add new tail seg block to snake body
            new_seg = turtle.Turtle()
            new_seg.speed(0)
            new_seg.shape("square")
            new_seg.color("lightgreen") 
            new_seg.penup()
            segments.append(new_seg)

            # Upd scoring val
            score += 10
            if score > high_score:
                high_score = score
            upd_score_disp()

            # Spawn second food once at score 100
            if score >= 100 and not extra_food_added:
                food2 = turtle.Turtle()
                food2.speed(0)
                food2.shape("circle")
                food2.color("orange")
                food2.penup()
                place_food_item(food2)
                extra_food_added = True

        # Check for collision w/ second food (if present)
        if not ate_food and extra_food_added and food2 is not None and head.distance(food2) < 20:
            x = random.randint(-14, 14) * 20
            y = random.randint(-14, 14) * 20
            food2.goto(x,y)

            # Add new tail seg block to snake body
            new_seg = turtle.Turtle()
            new_seg.speed(0)
            new_seg.shape("square")
            new_seg.color("lightgreen") 
            new_seg.penup()
            segments.append(new_seg)

            # Upd scoring val
            score += 10
            if score > high_score:
                high_score = score
            upd_score_disp()

        # Shift trailing tail block in rev order
        for index in range(len(segments) - 1, 0, -1):
            x = segments[index - 1].xcor()
            y = segments[index - 1].ycor()
            segments[index].goto(x, y)

        # Move first seg to old head pos using indexing
        if len(segments) > 0:
            segments[0].goto(head.xcor(), head.ycor())

        move()

        # Check if snake head crashes into self body seg loops
        for seg in segments:
            if seg.distance(head) < 20:
                head.goto(0, 0)
                head.direction = "stop"

                # Show game over message
                show_game_over()

                # Hide body segs on reset
                for segm in segments:
                    segm.goto(1000, 1000)
                segments.clear()

                # Remove extra food on reset
                if extra_food_added and food2 is not None:
                    try:
                        food2.goto(1000, 1000)
                    except Exception:
                        pass
                    extra_food_added = False
                    food2 = None

                return

        # Upd graphic wnd screen frames
        wnd.update()

        # Schedule next tiick update inside event runtime (skip if game over)
        if not game_over_flag:
            wnd.ontimer(game_loop, delay)

    except (turtle.Terminator, turtle.TurtleGraphicsError, NameError, AttributeError):
        # Handle wnd termination without crashes
        return
    
# Start looping cycle and open window interface loop
game_loop()
wnd.mainloop()
