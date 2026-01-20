import pygame
import math
import sys

# ---------- SETTINGS ----------
WIDTH, HEIGHT = 800, 600
HALF_HEIGHT = HEIGHT // 2
FPS = 60

FOV = math.radians(90)
NUM_RAYS = 400
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
SCALE = WIDTH // NUM_RAYS

TILE = 100

MOUSE_SENSITIVITY = 0.002
MAX_PITCH = math.radians(80)

# Jump physics
GRAVITY = 0.6
JUMP_VELOCITY = 18
AIR_SPEED_MULTIPLIER = 1.2
EYE_HEIGHT = 0

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

# buffer for motion blur
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

        # DDA setup
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
        side = 0  # 0 = vertical wall, 1 = horizontal wall

        # DDA loop
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

        # calculate exact distance to wall
        if side == 0:
            wall_distance = (map_x - px / TILE + (1 - step_x) / 2) / cos_a
        else:
            wall_distance = (map_y - py / TILE + (1 - step_y) / 2) / sin_a

        wall_distance *= TILE
        wall_distance *= math.cos(angle - cur_angle)

        wall_height = 30000 / (wall_distance + 0.0001)
        wall_y = HALF_HEIGHT - wall_height // 2
        wall_y += tan_pitch * HALF_HEIGHT

        # Correct jump offset (scaled)
        jump_offset = eye_z * (proj_plane / (wall_distance + 0.0001))
        jump_offset *= 0.12

        wall_y += jump_offset

        wall_y = int(wall_y)
        wall_height = int(max(1, wall_height))

        shade = 255 / (1 + wall_distance * wall_distance * 0.0001)
        shade = max(0, min(255, shade))
        color = (int(shade), int(shade), int(shade))

        pygame.draw.rect(screen, color, (ray * SCALE, wall_y, SCALE, wall_height))


# ---------- GAME LOOP ----------
running = True
while running:
    screen.fill((30, 30, 30))

    # Horizon moves only with pitch (not jump)
    pitch_clamped = max(-MAX_PITCH, min(MAX_PITCH, pitch))
    tan_pitch = math.tan(pitch_clamped)

    horizon = HALF_HEIGHT + tan_pitch * HALF_HEIGHT
    horizon = max(0, min(HEIGHT, horizon))

    # Floor rises slightly when jumping
    floor_shift = -eye_z * 0.008

    pygame.draw.rect(screen, (50, 50, 50), (0, 0, WIDTH, int(horizon)))
    pygame.draw.rect(screen, (100, 100, 100), (0, int(horizon + floor_shift), WIDTH, HEIGHT - int(horizon + floor_shift)))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE and on_ground:
                z_vel = JUMP_VELOCITY
                on_ground = False
            if event.key == pygame.K_q and dash_timer == 0:
                dash_timer = DASH_TIME

    # Mouse look
    mx, my = pygame.mouse.get_rel()
    angle += mx * MOUSE_SENSITIVITY
    pitch -= my * MOUSE_SENSITIVITY
    pitch = max(-MAX_PITCH, min(MAX_PITCH, pitch))

    # Movement
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

    if keys[pygame.K_w]:
        dx += move_speed * math.cos(angle)
        dy += move_speed * math.sin(angle)
    if keys[pygame.K_s]:
        dx -= move_speed * math.cos(angle)
        dy -= move_speed * math.sin(angle)
    if keys[pygame.K_a]:
        dx += move_speed * math.cos(angle - math.pi / 2)
        dy += move_speed * math.sin(angle - math.pi / 2)
    if keys[pygame.K_d]:
        dx += move_speed * math.cos(angle + math.pi / 2)
        dy += move_speed * math.sin(angle + math.pi / 2)

    length = math.hypot(dx, dy)
    if length > move_speed:
        dx = dx / length * move_speed
        dy = dy / length * move_speed

    move_with_collision(dx, dy)

    # Jump physics
    if not on_ground:
        z_vel -= GRAVITY
        eye_z += z_vel

        if eye_z <= EYE_HEIGHT:
            eye_z = EYE_HEIGHT
            z_vel = 0
            on_ground = True

    # apply shake
    if dash_shake > 0:
        shake_x = math.sin(pygame.time.get_ticks() * 0.05) * dash_shake
        shake_y = math.cos(pygame.time.get_ticks() * 0.05) * dash_shake
        dash_shake -= 1
    else:
        shake_x = 0
        shake_y = 0

    # motion blur: draw previous frame on top with alpha
    if trail_strength > 0:
        prev_frame.set_alpha(trail_strength)

        # add movement-based blur offset (works even when going straight)
        blur_dx = int(math.cos(angle) * 4)
        blur_dy = int(math.sin(angle) * 4)

        screen.blit(prev_frame, (blur_dx, blur_dy))

    # render scene
    raycasting()

    # save current frame to buffer for next frame
    prev_frame.blit(screen, (0, 0))

    # final blit with shake
    final = pygame.Surface((WIDTH, HEIGHT))
    final.blit(screen, (0, 0))
    screen.fill((0, 0, 0))
    screen.blit(final, (int(shake_x), int(shake_y)))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
