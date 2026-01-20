import pygame
import math
import sys

# ---------- SETTINGS ----------
WIDTH, HEIGHT = 1925, 1025
HALF_HEIGHT = HEIGHT // 2
FPS = 60

FOV = math.radians(90)
NUM_RAYS = 400
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
SCALE = WIDTH / NUM_RAYS
    
TILE = 100

MOUSE_SENSITIVITY = 0.002
MAX_PITCH = math.radians(80)

ROTATE_SPEED_2D = 0.05

# Jump physics
GRAVITY = 0.6
JUMP_VELOCITY = 18
AIR_SPEED_MULTIPLIER = 1.2
EYE_HEIGHT = 0

# Mode
mode = "3D"

# ---------- MAP ----------
WORLD_MAP = [
    "111111111111",
    "100000000001",
    "101111011101",
    "100100010001",
    "101100011101",
    "100000000001",
    "111111111111"
]

MAP_W = len(WORLD_MAP[0])
MAP_H = len(WORLD_MAP)

# ---------- PLAYER ----------
px, py = 150, 150
angle = 0
pitch = 0.0
speed = 4
PLAYER_RADIUS = 20

# Dash
DASH_SPEED = 20
DASH_TIME = 6
dash_timer = 0

# Dash effects
dash_shake = 0
trail_strength = 0

# Jump state
eye_z = 0.0
z_vel = 0.0
on_ground = True

# ---------- INIT ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Raycasting FPS (DDA Fixed)")
clock = pygame.time.Clock()

pygame.event.set_grab(True)
pygame.mouse.set_visible(False)

prev_frame = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()
prev_frame.set_alpha(0)

# ---------- HELPERS ----------
def is_wall(x, y):
    i = int(x // TILE)
    j = int(y // TILE)
    if i < 0 or j < 0 or i >= MAP_W or j >= MAP_H:
        return True
    return WORLD_MAP[j][i] == '1'

def move_with_collision(dx, dy):
    global px, py
    new_x = px + dx
    if not is_wall(new_x + PLAYER_RADIUS, py) and not is_wall(new_x - PLAYER_RADIUS, py):
        px = new_x
    new_y = py + dy
    if not is_wall(px, new_y + PLAYER_RADIUS) and not is_wall(px, new_y - PLAYER_RADIUS):
        py = new_y

def move_with_collision_2d(dx, dy):
    global px, py
    nx = px + dx
    ny = py + dy

    if not is_wall(nx, py):
        px = nx
    if not is_wall(px, ny):
        py = ny

# ---------- RAYCAST ----------
def raycasting():
    start_angle = angle - FOV / 2
    pitch_clamped = max(-MAX_PITCH, min(MAX_PITCH, pitch))
    tan_pitch = math.tan(pitch_clamped)
    proj_plane = WIDTH / (2 * math.tan(FOV / 2))

    for ray in range(NUM_RAYS):
        cur_angle = start_angle + ray * DELTA_ANGLE
        sin_a = math.sin(cur_angle)
        cos_a = math.cos(cur_angle)

        map_x = int(px // TILE)
        map_y = int(py // TILE)

        delta_dist_x = abs(1 / cos_a) if cos_a != 0 else 1e30
        delta_dist_y = abs(1 / sin_a) if sin_a != 0 else 1e30

        if cos_a < 0:
            step_x = -1
            side_dist_x = (px - map_x * TILE) * delta_dist_x
        else:
            step_x = 1
            side_dist_x = ((map_x + 1) * TILE - px) * delta_dist_x

        if sin_a < 0:
            step_y = -1
            side_dist_y = (py - map_y * TILE) * delta_dist_y
        else:
            step_y = 1
            side_dist_y = ((map_y + 1) * TILE - py) * delta_dist_y

        hit = False
        side = 0

        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x * TILE
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y * TILE
                map_y += step_y
                side = 1

            if map_x < 0 or map_y < 0 or map_x >= MAP_W or map_y >= MAP_H:
                break
            if WORLD_MAP[map_y][map_x] == '1':
                hit = True

        if not hit:
            continue

        if side == 0:
            wall_distance = (map_x - px / TILE + (1 - step_x) / 2) / cos_a
        else:
            wall_distance = (map_y - py / TILE + (1 - step_y) / 2) / sin_a

        wall_distance *= TILE
        wall_distance *= math.cos(angle - cur_angle)

        wall_height = 30000 / (wall_distance + 0.0001)
        wall_y = HALF_HEIGHT - wall_height // 2
        wall_y += tan_pitch * HALF_HEIGHT

        jump_offset = eye_z * (proj_plane / (wall_distance + 0.0001)) * 0.12
        wall_y += jump_offset

        shade = 255 / (1 + wall_distance * wall_distance * 0.0001)
        shade = max(0, min(255, shade))
        color = (int(shade), int(shade), int(shade))

        pygame.draw.rect(
            screen,
            color,
            (int(ray * SCALE), int(wall_y), int(SCALE + 1), int(wall_height))
        )


# ---------- 2D DRAW ----------
def draw_2d():

    scale_x = WIDTH / (MAP_W * TILE)
    scale_y = HEIGHT / (MAP_H * TILE)
    scale = min(scale_x, scale_y)  # uniform scale to fit screen

    offset_x = (WIDTH - MAP_W * TILE * scale) // 2
    offset_y = (HEIGHT - MAP_H * TILE * scale) // 2

    # Draw map tiles
    for y, row in enumerate(WORLD_MAP):
        for x, cell in enumerate(row):
            color = (90, 90, 90) if cell == '1' else (30, 30, 30)
            pygame.draw.rect(
                screen,
                color,
                (
                    offset_x + x * TILE * scale,
                    offset_y + y * TILE * scale,
                    TILE * scale,
                    TILE * scale
                )
            )

    # Draw player
    pxs = offset_x + px * scale
    pys = offset_y + py * scale
    pygame.draw.circle(screen, (0, 200, 255), (int(pxs), int(pys)), 6)

    # Draw player direction arrow
    pygame.draw.line(
        screen,
        (0, 200, 255),
        (pxs, pys),
        (pxs + math.cos(angle) * 20, pys + math.sin(angle) * 20),
        2
    )

    # Draw FOV cone
    NUM_2D_RAYS = 60
    FOV_LENGTH = 200  # length of cone in pixels
    cone_points = [(pxs, pys)]

    for r in range(NUM_2D_RAYS + 1):
        ray_angle = angle - FOV/2 + r * (FOV / NUM_2D_RAYS)
        end_x = pxs + math.cos(ray_angle) * FOV_LENGTH
        end_y = pys + math.sin(ray_angle) * FOV_LENGTH
        cone_points.append((end_x, end_y))

    # Semi-transparent polygon for cone
    cone_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(cone_surface, (0, 255, 255, 50), cone_points)
    screen.blit(cone_surface, (0, 0))

    # Draw rays to walls (like mini raycasting)
    for r in range(NUM_2D_RAYS):
        ray_angle = angle - FOV/2 + r * (FOV / NUM_2D_RAYS)
        step = 2  # pixel step for ray march
        ray_x, ray_y = px, py

        for _ in range(MAX_DEPTH // step):
            ray_x += math.cos(ray_angle) * step
            ray_y += math.sin(ray_angle) * step

            # convert to map coordinates
            if is_wall(ray_x, ray_y):
                end_x = offset_x + ray_x * scale
                end_y = offset_y + ray_y * scale
                pygame.draw.line(screen, (255, 100, 0), (pxs, pys), (end_x, end_y), 1)
                break

# ---------- GAME LOOP ----------
running = True
while running:
    screen.fill((30, 30, 30))

    pitch_clamped = max(-MAX_PITCH, min(MAX_PITCH, pitch))
    tan_pitch = math.tan(pitch_clamped)
    horizon = HALF_HEIGHT + tan_pitch * HALF_HEIGHT
    floor_shift = -eye_z * 0.008

    pygame.draw.rect(screen, (50,50,50), (0,0,WIDTH,int(horizon)))
    pygame.draw.rect(screen, (100,100,100), (0,int(horizon+floor_shift),WIDTH,HEIGHT))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_TAB:
                mode = "2D" if mode == "3D" else "3D"
            if event.key == pygame.K_SPACE and on_ground:
                z_vel = JUMP_VELOCITY
                on_ground = False
            if event.key == pygame.K_q and dash_timer == 0:
                dash_timer = DASH_TIME

    # Mouse look ONLY in 3D
    if mode == "3D":
        mx, my = pygame.mouse.get_rel()
        angle += mx * MOUSE_SENSITIVITY
        pitch -= my * MOUSE_SENSITIVITY
        pitch = max(-MAX_PITCH, min(MAX_PITCH, pitch))
    else:
        pygame.mouse.get_rel()

    dx = dy = 0
    keys = pygame.key.get_pressed()
    move_speed = speed

    if dash_timer > 0:
        move_speed = DASH_SPEED
        dash_timer -= 1
        dash_shake = 4
        trail_strength = 160
    else:
        trail_strength = max(0, trail_strength - 10)

    if not on_ground:
        move_speed *= AIR_SPEED_MULTIPLIER

    if mode == "3D":
        if keys[pygame.K_w]:
            dx += move_speed * math.cos(angle)
            dy += move_speed * math.sin(angle)
        if keys[pygame.K_s]:
            dx -= move_speed * math.cos(angle)
            dy -= move_speed * math.sin(angle)
        if keys[pygame.K_a]:
            dx += move_speed * math.cos(angle - math.pi/2)
            dy += move_speed * math.sin(angle - math.pi/2)
        if keys[pygame.K_d]:
            dx += move_speed * math.cos(angle + math.pi/2)
            dy += move_speed * math.sin(angle + math.pi/2)
    else:
        if keys[pygame.K_w]:
            dx += move_speed * math.cos(angle)
            dy += move_speed * math.sin(angle)
        if keys[pygame.K_s]:
            dx -= move_speed * math.cos(angle)
            dy -= move_speed * math.sin(angle)
        if keys[pygame.K_a]:
            angle -= ROTATE_SPEED_2D
        if keys[pygame.K_d]:
            angle += ROTATE_SPEED_2D

    if mode == "3D":
        move_with_collision(dx, dy)
    else:
        move_with_collision_2d(dx, dy)


    if not on_ground:
        z_vel -= GRAVITY
        eye_z += z_vel
        if eye_z <= EYE_HEIGHT:
            eye_z = EYE_HEIGHT
            z_vel = 0
            on_ground = True

    if trail_strength > 0:
        prev_frame.set_alpha(trail_strength)
        screen.blit(prev_frame, (int(math.cos(angle)*4), int(math.sin(angle)*4)))

    if mode == "3D":
        raycasting()
    else:
        draw_2d()

    prev_frame.blit(screen,(0,0))
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
