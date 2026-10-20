import pygame, asyncio, random

pygame.init()

# Window
WIDTH, HEIGHT = 800, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cat Collector")
clock = pygame.time.Clock()

# Assets
PLAYER_GIF = "assets/cat.gif"
COLLECT_GIF = "assets/mcdonald_cat.gif"
NPC_GIF = "assets/evil_cat.gif"

PLAYER_SIZE = (50, 50)
COLLECT_SIZE = (30, 30)
NPC_SIZE = (60, 50)

# Colors
SKY = (107, 140, 255)
BRICK = (200, 76, 12)
MORTAR = (90, 30, 0)
GRASS = (60, 170, 60)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Physics
GRAVITY = 0.5
JUMP_SPEED = -10
PLAYER_SPEED = 5

# Evil cat
STROLL_SPEED = 1.2
CHASE_ACCEL = 0.35
MAX_CHASE = 6.5
BRAKE = 0.9

GAME_TIME = 60
COLLECT_COUNT = 3

platforms = [
    pygame.Rect(0, 450, WIDTH, 50),
    pygame.Rect(80, 370, 160, 20),
    pygame.Rect(560, 370, 160, 20),
    pygame.Rect(320, 290, 160, 20),
    pygame.Rect(60, 210, 160, 20),
    pygame.Rect(580, 210, 160, 20),
    pygame.Rect(320, 130, 160, 20)
]
ground = platforms[0]

font = pygame.font.Font(None, 40)
big_font = pygame.font.Font(None, 70)


# GIF loading
def load_gif(path, size, color):
    try:
        frames = pygame.image.load_animation(path)
    except Exception:
        try:
            frames = [(pygame.image.load(path), 100)]
        except Exception:
            box = pygame.Surface(size)
            box.fill(color)
            frames = [(box, 100)]
    images = [pygame.transform.scale(img.convert_alpha(), size) for img, delay in frames]
    delays = [max(delay, 20) for img, delay in frames]
    return images, delays


# GIF frame
def gif_frame(gif, ticks):
    images, delays = gif
    t = ticks % sum(delays)
    for img, delay in zip(images, delays):
        if t < delay:
            return img
        t -= delay
    return images[-1]


player_gif = load_gif(PLAYER_GIF, PLAYER_SIZE, (255, 160, 0))
collect_gif = load_gif(COLLECT_GIF, COLLECT_SIZE, (255, 220, 0))
npc_gif = load_gif(NPC_GIF, NPC_SIZE, (120, 0, 120))


# Spawning
def spawn_collectable(cupcakes):
    for _ in range(100):
        plat = random.choice(platforms)
        x = random.randint(plat.left, plat.right - COLLECT_SIZE[0])
        y = plat.top - COLLECT_SIZE[1] - random.randint(5, 40)
        rect = pygame.Rect(x, y, COLLECT_SIZE[0], COLLECT_SIZE[1])
        if rect.top < 40 or rect.left < 0 or rect.right > WIDTH:
            continue
        if rect.collidelist(platforms) != -1 or rect.collidelist(cupcakes) != -1:
            continue
        return rect
    plat = platforms[3]
    return pygame.Rect(plat.centerx - COLLECT_SIZE[0] // 2, plat.top - 40, COLLECT_SIZE[0], COLLECT_SIZE[1])


# Blocks
def draw_platform(plat):
    pygame.draw.rect(screen, BRICK, plat)
    for x in range(plat.left, plat.right, 40):
        pygame.draw.rect(screen, MORTAR, (x, plat.top, 40, plat.height), 2)
    if plat == ground:
        pygame.draw.rect(screen, GRASS, (plat.left, plat.top, plat.width, 8))


# Outlined text
def draw_text(text, f, pos, center=False):
    shadow = f.render(text, True, BLACK)
    label = f.render(text, True, WHITE)
    rect = label.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    screen.blit(shadow, rect.move(2, 2))
    screen.blit(label, rect)


async def main():
    running = True
    while running:
        # Reset
        player_x = 50
        player_y = ground.top - PLAYER_SIZE[1]
        player_dy = 0
        on_ground = True
        on_floor = True
        facing_left = False
        hurt_timer = 0

        npc_x = WIDTH / 2
        npc_y = ground.top - NPC_SIZE[1]
        npc_vx = STROLL_SPEED
        npc_dir = 1
        chasing = False

        cupcakes = []
        for _ in range(COLLECT_COUNT):
            cupcakes.append(spawn_collectable(cupcakes))

        score = 0
        time_left = GAME_TIME
        game_over = False
        restart = False

        while running and not restart:
            dt = min(clock.tick(60) / 1000, 0.1)
            ticks = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r and game_over:
                    restart = True

            if not game_over:
                # Input
                keys = pygame.key.get_pressed()
                player_dx = 0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    player_dx = -PLAYER_SPEED
                    facing_left = True
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    player_dx = PLAYER_SPEED
                    facing_left = False
                if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
                    player_dy = JUMP_SPEED
                    on_ground = False

                # Horizontal
                player_x += player_dx
                player_x = max(0, min(player_x, WIDTH - PLAYER_SIZE[0]))
                player_rect = pygame.Rect(player_x, player_y, PLAYER_SIZE[0], PLAYER_SIZE[1])
                for plat in platforms:
                    if player_rect.colliderect(plat):
                        if player_dx > 0:
                            player_rect.right = plat.left
                        elif player_dx < 0:
                            player_rect.left = plat.right
                        player_x = player_rect.x

                # Gravity
                player_dy += GRAVITY
                player_y += player_dy
                player_rect = pygame.Rect(player_x, player_y, PLAYER_SIZE[0], PLAYER_SIZE[1])
                for plat in platforms:
                    if player_rect.colliderect(plat):
                        if player_dy > 0:
                            player_rect.bottom = plat.top
                        elif player_dy < 0:
                            player_rect.top = plat.bottom
                        player_dy = 0
                        player_y = player_rect.y

                # Ceiling
                if player_y < 0:
                    player_y = 0
                    player_dy = 0
                player_rect = pygame.Rect(player_x, player_y, PLAYER_SIZE[0], PLAYER_SIZE[1])

                # Feet check
                feet = player_rect.move(0, 1)
                on_ground = False
                on_floor = False
                for plat in platforms:
                    if player_dy >= 0 and feet.colliderect(plat) and player_rect.bottom <= plat.top:
                        on_ground = True
                        if plat == ground:
                            on_floor = True

                # Collecting
                for cupcake in cupcakes[:]:
                    if player_rect.colliderect(cupcake):
                        cupcakes.remove(cupcake)
                        score += 1
                        cupcakes.append(spawn_collectable(cupcakes))

                # Chase
                npc_center = npc_x + NPC_SIZE[0] / 2
                if on_floor:
                    chasing = True
                    direction = 1 if player_rect.centerx > npc_center else -1
                    npc_vx += CHASE_ACCEL * direction
                    npc_vx = max(-MAX_CHASE, min(npc_vx, MAX_CHASE))
                else:
                    # Braking
                    if chasing:
                        chasing = False
                        npc_dir = 1 if npc_vx >= 0 else -1
                    target = npc_dir * STROLL_SPEED
                    if npc_vx < target:
                        npc_vx = min(npc_vx + BRAKE, target)
                    else:
                        npc_vx = max(npc_vx - BRAKE, target)

                # Walls
                npc_x += npc_vx
                if npc_x < 0:
                    npc_x = 0
                    npc_vx = 0
                    npc_dir = 1
                if npc_x > WIDTH - NPC_SIZE[0]:
                    npc_x = WIDTH - NPC_SIZE[0]
                    npc_vx = 0
                    npc_dir = -1
                npc_rect = pygame.Rect(npc_x, npc_y, NPC_SIZE[0], NPC_SIZE[1])

                # Damage
                if hurt_timer > 0:
                    hurt_timer -= dt
                elif player_rect.colliderect(npc_rect):
                    score = max(0, score - 1)
                    player_dy = JUMP_SPEED
                    on_ground = False
                    hurt_timer = 1

                # Timer
                time_left -= dt
                if time_left <= 0:
                    time_left = 0
                    game_over = True

            # Drawing
            screen.fill(SKY)
            for plat in platforms:
                draw_platform(plat)

            for cupcake in cupcakes:
                screen.blit(gif_frame(collect_gif, ticks), cupcake.topleft)

            npc_image = gif_frame(npc_gif, ticks)
            if npc_vx < 0:
                npc_image = pygame.transform.flip(npc_image, True, False)
            screen.blit(npc_image, (npc_x, npc_y))

            if hurt_timer <= 0 or (ticks // 100) % 2 == 0:
                player_image = gif_frame(player_gif, ticks)
                if facing_left:
                    player_image = pygame.transform.flip(player_image, True, False)
                screen.blit(player_image, (player_x, player_y))

            # HUD
            seconds = int(time_left + 0.999)
            draw_text("score: " + str(score), font, (10, 8))
            draw_text(str(seconds // 60) + ":" + str(seconds % 60).zfill(2), font, (WIDTH - 85, 8))

            if game_over:
                shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                shade.fill((0, 0, 0, 150))
                screen.blit(shade, (0, 0))
                draw_text("Time's up!", big_font, (WIDTH // 2, HEIGHT // 2 - 50), True)
                draw_text("score: " + str(score), font, (WIDTH // 2, HEIGHT // 2 + 5), True)
                draw_text("press R to play again", font, (WIDTH // 2, HEIGHT // 2 + 45), True)

            pygame.display.flip()
            await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
