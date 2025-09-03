from gint import *
import random
import math

# === Constants ===
SCREEN_WIDTH = DWIDTH
SCREEN_HEIGHT = DHEIGHT

PADDLE_HEIGHT = 30
BALL_RADIUS = 9
BRICK_SPACING = 6
BRICKS_GRID_X = 5  # How many bricks in a row
BRICK_WIDTH = DWIDTH//BRICKS_GRID_X - BRICK_SPACING
BRICK_HEIGHT = 26
PADDLE_Y = SCREEN_HEIGHT - 30
BRICK_DROP_INTERVAL = 80  # frames

BRICK_COLORS = {
    1: 0x000FFF,
    2: 0x0FFF00,
    3: 0xFF000F,
}

UPGRADE_COSTS = {
    "paddle_size": 30,
    "ball_speed": 50,
    "ball_power": 50,
    "extra_ball": 70,  # Add this line
}


# === Game State ===
score = 0
STARTING_MONEY = 200
money = STARTING_MONEY
tick_count = BRICK_DROP_INTERVAL
STARTING_DIFFICULTY = 10
difficulty = STARTING_DIFFICULTY
game_over = False
shop_open = False

# Upgrades
paddle_upgrade = 0
ball_speed_upgrade = 0
BALL_BASE_POWER = 1
ball_power_upgrade = 0

# Paddle
PADDLE_WIDTH_BASE = 60
paddle_x = (SCREEN_WIDTH - PADDLE_WIDTH_BASE) // 2
paddle_speed = 8

# Ball
BALL_SPEED_BASE = 5
balls = []

# bricks_queue: list of [x1, y1, x2, y2, health]
bricks_queue = []

# Input state
left_down = False
right_down = False


# === Game Functions ===
def reset_game():
    global score, money, paddle_x, ball_x, ball_y, ball_dx, ball_dy
    global paddle_upgrade, ball_speed_upgrade, ball_power_upgrade
    global bricks_queue, game_over, tick_count, difficulty
    global balls
    paddle_x = (SCREEN_WIDTH - PADDLE_WIDTH_BASE) // 2
    balls = [{
        "x": SCREEN_WIDTH // 2,
        "y": SCREEN_HEIGHT // 2,
        "dx": 1,
        "dy": -1,
    }]
    bricks_queue = []
    score = 0
    money = STARTING_MONEY
    tick_count = BRICK_DROP_INTERVAL-1
    difficulty = STARTING_DIFFICULTY
    game_over = False
    paddle_upgrade = 0
    ball_speed_upgrade = 0
    ball_power_upgrade = 0

    for _ in range(1):
        update_bricks(force_drop=True, force_100_chance=True)


def current_paddle_width():
    return PADDLE_WIDTH_BASE + paddle_upgrade * 10


def current_ball_speed():
    return BALL_SPEED_BASE + ball_speed_upgrade


def current_ball_power():
    return BALL_BASE_POWER + ball_power_upgrade


def handle_input():
    global left_down, right_down, shop_open, game_over

    while True:
        ev = pollevent()
        if ev.type == KEYEV_NONE:
            break
        if ev.type == KEYEV_DOWN:
            if ev.key == KEY_LEFT:
                left_down = True
            elif ev.key == KEY_RIGHT:
                right_down = True
            elif ev.key == KEY_EXIT:
                game_over = True
            elif ev.key == KEY_EXE:
                shop_open = not shop_open
                dclear(0)
            elif shop_open:
                if ev.key == KEY_1 and money >= UPGRADE_COSTS["paddle_size"]:
                    upgrade("paddle_size")
                elif ev.key == KEY_2 and money >= UPGRADE_COSTS["ball_speed"]:
                    upgrade("ball_speed")
                elif ev.key == KEY_3 and money >= UPGRADE_COSTS["ball_power"]:
                    upgrade("ball_power")
                elif ev.key == KEY_4 and money >= UPGRADE_COSTS["extra_ball"]:
                    upgrade("extra_ball")
        elif ev.type == KEYEV_UP:
            if ev.key == KEY_LEFT:
                left_down = False
            elif ev.key == KEY_RIGHT:
                right_down = False


def upgrade(name):
    global money, paddle_upgrade, ball_speed_upgrade, ball_power_upgrade

    money -= UPGRADE_COSTS[name]
    if name == "paddle_size":
        paddle_upgrade += 1
    elif name == "ball_speed":
        ball_speed_upgrade += 1
    elif name == "ball_power":
        ball_power_upgrade += 1
    elif name == "extra_ball":
        balls.append({
            "x": random.randint(BALL_RADIUS, SCREEN_WIDTH - BALL_RADIUS),
            "y": PADDLE_Y-PADDLE_HEIGHT - BALL_RADIUS*2,
            "dx": random.choice([-0.5, 0.5]),
            "dy": -0.7,
        })


def move_paddle() -> bool:
    global paddle_x, paddle_speed
    moved = False
    new_paddle_x = paddle_x
    if left_down:
        new_paddle_x = max(paddle_x - paddle_speed, 0)
        moved = True
    if right_down:
        new_paddle_x = min(paddle_x + paddle_speed,
                           SCREEN_WIDTH - current_paddle_width())
        moved = True
    if moved:
        efficient_clear_paddle()
        paddle_x = new_paddle_x
    return moved


def normalize(dx, dy):
    length = math.sqrt(dx ** 2 + dy ** 2)
    if length == 0:
        return 0, -1  # Default upward
    return dx / length, dy / length


def update_balls():
    global game_over, money, score
    global bricks_queue

    speed = current_ball_speed()
    for ball in balls[:]:  # Copy to allow removal
        ball["dx"], ball["dy"] = normalize(ball["dx"], ball["dy"])
        dx = ball["dx"] * speed
        dy = ball["dy"] * speed
        steps = 1  # max(1, int(speed * 2))
        dx /= steps
        dy /= steps

        for _ in range(steps):
            next_x = ball["x"] + dx
            next_y = ball["y"] + dy

            # Wall collisions
            if next_x - BALL_RADIUS <= 0 or next_x + BALL_RADIUS >= SCREEN_WIDTH:
                ball["dx"] *= -1
                dx *= -1
                next_x = max(BALL_RADIUS, min(
                    SCREEN_WIDTH - BALL_RADIUS, next_x))

            if next_y - BALL_RADIUS <= 0:
                ball["dy"] *= -1
                dy *= -1
                next_y = BALL_RADIUS
            elif next_y - BALL_RADIUS >= SCREEN_HEIGHT:
                balls.remove(ball)
                if not balls:
                    game_over = True
                break

            # Paddle collision
            if PADDLE_Y <= next_y + BALL_RADIUS <= PADDLE_Y + PADDLE_HEIGHT:
                if paddle_x <= next_x <= paddle_x + current_paddle_width():
                    hit_pos = (next_x - paddle_x) / \
                        current_paddle_width() - 0.5
                    angle = hit_pos * math.pi / 2
                    ball["dx"] = math.sin(angle)
                    ball["dy"] = -math.cos(angle)
                    dx = ball["dx"] * (speed / steps)
                    dy = ball["dy"] * (speed / steps)

            # Brick collision
            for brick in bricks_queue:
                x1, y1, x2, y2, health = brick
                if health <= 0:
                    continue
                if x1 - BALL_RADIUS <= next_x <= x2 + BALL_RADIUS and y1 - BALL_RADIUS <= next_y <= y2 + BALL_RADIUS:
                    overlap_left = abs(next_x - (x1 - BALL_RADIUS))
                    overlap_right = abs(next_x - (x2 + BALL_RADIUS))
                    overlap_top = abs(next_y - (y1 - BALL_RADIUS))
                    overlap_bottom = abs(next_y - (y2 + BALL_RADIUS))

                    min_overlap = min(overlap_left, overlap_right,
                                      overlap_top, overlap_bottom)

                    if min_overlap in [overlap_left, overlap_right]:
                        ball["dx"] *= -1
                        dx *= -1
                    else:
                        ball["dy"] *= -1
                        dy *= -1

                    brick[4] -= current_ball_power()
                    if brick[4] <= 0:
                        score += 10
                        money += 10
                        # Clear the dead brick
                        drect(x1, y1, x2, y2, C_BLACK)
                    break

            # Clear old ball position
            dcircle(int(ball["x"]), int(ball["y"]), BALL_RADIUS, C_BLACK, 0)
            ball["x"] = next_x
            ball["y"] = next_y


def update_bricks(force_drop=False, force_100_chance=False):
    global tick_count, difficulty
    global bricks_queue

    tick_count += 1

    # Drop all bricks_queue
    if force_drop or tick_count % BRICK_DROP_INTERVAL == 0:
        efficient_clear_blocks()
        for brick in bricks_queue:
            brick[1] += BRICK_HEIGHT + BRICK_SPACING
            brick[3] += BRICK_HEIGHT + BRICK_SPACING

        # Update difficulty
        difficulty += 1

        # Spawn new bricks_queue
        # 1st find all indices of bricks that are dead
        dead_indices = [i for i, brick in enumerate(
            bricks_queue) if brick[4] <= 0]
        spawn_chance = max(0.4, difficulty / 100)
        # for col in range(SCREEN_WIDTH // (BRICK_WIDTH + BRICK_SPACING)):
        for col in range(BRICKS_GRID_X):
            if force_100_chance or random.random() < spawn_chance:
                health = max(1, min(3, difficulty // 6))
                # Take a dead brick from the list if available
                if len(dead_indices) != 0:
                    index = dead_indices.pop(0)
                    brick = bricks_queue[index]
                    brick[0] = col * \
                        (BRICK_WIDTH + BRICK_SPACING) + BRICK_SPACING // 2
                    brick[1] = 0
                    brick[2] = brick[0] + BRICK_WIDTH
                    brick[3] = brick[1] + BRICK_HEIGHT
                    brick[4] = health
                else:
                    # Create a new brick
                    x1 = col * (BRICK_WIDTH + BRICK_SPACING) + \
                        BRICK_SPACING // 2
                    y1 = 0
                    x2 = x1 + BRICK_WIDTH
                    y2 = y1 + BRICK_HEIGHT
                    bricks_queue.append([x1, y1, x2, y2, health])


def efficient_clear_blocks():
    # Only clear bricks_queue that were on screen
    global bricks_queue
    # bricks_queue
    for x1, y1, x2, y2, health in bricks_queue:
        if health > 0:
            drect(x1, y1, x2, y2, C_BLACK)


def efficient_clear_paddle():
    # Only clear paddle area
    drect(paddle_x, PADDLE_Y, paddle_x + current_paddle_width(),
          PADDLE_Y + PADDLE_HEIGHT, C_BLACK)


def draw_game():
    # dclear(0)

    # Paddle
    drect(paddle_x, PADDLE_Y, paddle_x + current_paddle_width(),
          PADDLE_Y + PADDLE_HEIGHT, 0xFFFFFF)

    # Ball
    for ball in balls:
        dcircle(int(ball["x"]), int(ball["y"]), BALL_RADIUS, 0xFFFFFF, 0)

    # bricks_queue
    for x1, y1, x2, y2, health in bricks_queue:
        if health > 0:
            color = BRICK_COLORS.get(health, 0xFF00FF)
            drect(x1, y1, x2, y2, color)

    # HUD
    # Clear the previous text
    drect(0, SCREEN_HEIGHT - 15, SCREEN_WIDTH, SCREEN_HEIGHT, C_BLACK)
    dtext(4, SCREEN_HEIGHT - 12, 0x00FFFF,
          f"${money}  Score: {score}  Diff: {difficulty}")

    # Shop
    if shop_open:
        dclear(0)
        dtext(10, 20, 0xFFFFFF, f"== Money ${money}")
        dtext(10, 40, 0xFFFFFF,
              f"[1] PaddleSize (${UPGRADE_COSTS['paddle_size']}) ({paddle_upgrade})")
        dtext(10, 56, 0xFFFFFF,
              f"[2] Ball_Speed (${UPGRADE_COSTS['ball_speed']}) ({ball_speed_upgrade})")
        dtext(10, 72, 0xFFFFFF,
              f"[3] Ball_Power (${UPGRADE_COSTS['ball_power']}) ({ball_power_upgrade})")
        dtext(10, 88, 0xFFFFFF,
              f"[4] Extra_Ball (${UPGRADE_COSTS['extra_ball']}) ({len(balls)})")

    if game_over:
        dtext((SCREEN_WIDTH - 10 * 8)//2, SCREEN_HEIGHT // 2,
              0xFF0000, "GAME OVER")

    dupdate()


# === Main Loop ===

reset_game()
dclear(0)
while not game_over:
    handle_input()
    if not shop_open:

        update_balls()
        move_paddle()
        update_bricks()

    draw_game()
