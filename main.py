import asyncio
import pygame
import math
import random

# ==========================================
# UNIT 2 MATH & AI EXPLANATION
# ==========================================
# VECTORS:
# The player, zombies and bullets all use pygame.Vector2 for position and velocity.
#
# DISTANCE:
# Used for bullets hitting zombies, zombies hitting the player, and the zombie
# detection range. Zombies give up when you are 1.5x their detection range away.
#
# NORMALIZATION:
# Bullets use direction.normalize() * BULLET_SPEED. Zombies normalize the vector
# to the player so they move at their own speed no matter how far away you are.
#
# ANGLES / SINE / COSINE:
# The player turns toward the mouse with atan2 and forward = (cos, -sin).
# Chasing zombies wobble left and right using math.sin.
#
# VELOCITY AND ACCELERATION:
# The player uses WASD -> acceleration -> velocity, with DRAG and a max speed
# (higher when sprinting). Zombies speed up a little every frame until they
# reach their top speed.
# Lunge: the zombie adds the lunge acceleration for the first half and
# subtracts it for the second half, so it shoots forward then stops.
#
# DOT PRODUCT:
# Zombie field of view. forward.dot(to_player) > FOV_THRESHOLD means the
# player is in front of the zombie.
#
# AI DECISION-MAKING:
# Zombies have the states WANDER, CHASE, LUNGE and REST.
# Perception: distance to player + dot product.
# Decision: close enough AND in front -> CHASE (or a 10% chance to LUNGE first),
# LUNGE -> REST -> CHASE, too far away -> WANDER.
# Action: walk around randomly, lunge, or run at the player and attack.

# Screen
WIDTH = 1000
HEIGHT = 700
CLOCK = pygame.time.Clock()
pygame.font.init()
BIG_FONT = pygame.font.SysFont('arial', 60, bold=True)
FONT = pygame.font.SysFont('arial', 24)
SMALL_FONT = pygame.font.SysFont('arial', 18)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FLOOR_GRAY = (110, 110, 110)
WALL_GRAY = (190, 190, 190)
YELLOW = (240, 210, 40)
GREEN = (80, 170, 70)
DARK_GREEN = (40, 100, 40)
RED = (220, 50, 50)
BLUE = (60, 140, 230)
BAR_BACK = (50, 50, 50)
GUN_COLOR = (40, 40, 40)

# Player
PLAYER_RADIUS = 18
THRUST = 0.8
SPRINT_THRUST = 1.3
DRAG = 0.8
MAX_SPEED = 3.2
SPRINT_SPEED = 5
MAX_HEALTH = 100
MAX_STAMINA = 100
BULLET_SPEED = 12

# Zombies
ZOMBIE_COUNT = 10
ZOMBIE_RADIUS = 18
ZOMBIE_HEALTH = 3
WANDER_SPEED = 0.8
ZOMBIE_ACCEL = 0.1
DETECTION_RANGE = 250
FOV_THRESHOLD = 0.4
ZOMBIE_DAMAGE = 10

# Lunge
LUNGE_CHANCE = 0.1
LUNGE_MIN = 100
LUNGE_MAX = 200
LUNGE_FRAMES = 12      # frames speeding up, then the same amount slowing down
REST_TIME = 60
LUNGE_DAMAGE = 25


class Game:
    REFRESH_RATE = 60

    def __init__(self, title, width, height):
        self.title = title
        self.width = width
        self.height = height
        self.game_screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)

    def make_walls(self):
        walls = []
        walls.append(Wall(200, 100, 40, 220))
        walls.append(Wall(450, 250, 200, 40))
        walls.append(Wall(750, 80, 40, 200))
        walls.append(Wall(300, 500, 250, 40))
        walls.append(Wall(750, 450, 40, 180))
        return walls

    def make_zombies(self, walls):
        zombies = []
        while len(zombies) < ZOMBIE_COUNT:
            x = random.randint(50, self.width - 50)
            y = random.randint(50, self.height - 50)
            zombie = Zombie(x, y)
            # dont spawn in a wall or right next to the player
            if zombie.hits_wall(walls) or x < 350:
                continue
            zombies.append(zombie)
        return zombies

    def draw_text(self, text, font, color, y):
        rendered = font.render(text, True, color)
        self.game_screen.blit(rendered, (self.width / 2 - rendered.get_width() / 2, y))

    # Screens
    async def start_screen(self):
        rules = [
            "RULES",
            "Shoot all the zombies to win.",
            "Zombies walk around until they see you.",
            "They see you if you are close AND in front of them.",
            "If you get far enough away they lose you.",
            "Some zombies are faster than others.",
            "Some zombies lunge at you. Dodge, then run while they rest!",
            "You have 100 health. Sprinting uses stamina.",
            "",
            "CONTROLS",
            "WASD - Move",
            "Mouse - Aim",
            "Left Click - Shoot",
            "Shift - Sprint",
        ]
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    return True
            self.game_screen.fill(BLACK)
            self.draw_text("ZOMBIE APOCALYPSE", BIG_FONT, GREEN, 40)
            y = 140
            for line in rules:
                color = YELLOW if line in ("RULES", "CONTROLS") else WHITE
                self.draw_text(line, FONT, color, y)
                y += 32
            self.draw_text("Press ENTER to start", FONT, YELLOW, 620)
            pygame.display.update()
            CLOCK.tick(Game.REFRESH_RATE)
            await asyncio.sleep(0)    # lets the browser update

    async def print_end_game_message(self, player_win, seconds):
        self.game_screen.fill(BLACK)
        if player_win:
            self.draw_text("CONGRATULATIONS!", BIG_FONT, YELLOW, 200)
            self.draw_text("You killed all the zombies in " + str(seconds) + " seconds!", FONT, WHITE, 300)
        else:
            self.draw_text("YOU DIED", BIG_FONT, RED, 200)
            self.draw_text("The zombies got you.", FONT, WHITE, 300)
        self.draw_text("Press R to play again", FONT, WHITE, 400)
        pygame.display.update()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    return True
            CLOCK.tick(Game.REFRESH_RATE)
            await asyncio.sleep(0)

    # HUD
    def draw_hud(self, player, zombies):
        text = SMALL_FONT.render("Zombies left: " + str(len(zombies)), True, WHITE)
        self.game_screen.blit(text, (10, 10))

        # health and stamina bars in the bottom right
        x = self.width - 230
        pygame.draw.rect(self.game_screen, BAR_BACK, (x, self.height - 50, 210, 18))
        pygame.draw.rect(self.game_screen, GREEN, (x, self.height - 50, 210 * player.health / MAX_HEALTH, 18))
        pygame.draw.rect(self.game_screen, BAR_BACK, (x, self.height - 26, 210, 12))
        pygame.draw.rect(self.game_screen, BLUE, (x, self.height - 26, 210 * player.stamina / MAX_STAMINA, 12))
        self.game_screen.blit(SMALL_FONT.render("HP", True, WHITE), (x - 30, self.height - 52))
        self.game_screen.blit(SMALL_FONT.render("ST", True, WHITE), (x - 30, self.height - 30))

    async def run_game_loop(self):
        walls = self.make_walls()
        player = Player(100, 350)
        zombies = self.make_zombies(walls)
        bullets = []
        start_time = pygame.time.get_ticks()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    bullets.append(player.shoot())

            keys = pygame.key.get_pressed()
            player.move(keys, walls, self.width, self.height)
            player.aim(pygame.mouse.get_pos())

            for zombie in zombies:
                zombie.update(player, walls, self.width, self.height)

            # Bullets
            for bullet in bullets[:]:
                bullet.move()
                if bullet.is_off_screen(self.width, self.height) or bullet.hits_wall(walls):
                    bullets.remove(bullet)
                    continue
                for zombie in zombies:
                    if bullet.detect_collision(zombie):
                        zombie.health -= 1
                        bullets.remove(bullet)
                        break

            zombies = [z for z in zombies if z.health > 0]

            # Draw everything
            self.game_screen.fill(FLOOR_GRAY)
            for wall in walls:
                wall.draw(self.game_screen)
            for bullet in bullets:
                bullet.draw(self.game_screen)
            for zombie in zombies:
                zombie.draw(self.game_screen)
            player.draw(self.game_screen)
            self.draw_hud(player, zombies)
            pygame.display.update()
            CLOCK.tick(Game.REFRESH_RATE)
            await asyncio.sleep(0)

            # Win / lose
            if player.health <= 0:
                return await self.print_end_game_message(False, 0)
            if len(zombies) == 0:
                seconds = (pygame.time.get_ticks() - start_time) // 1000
                return await self.print_end_game_message(True, seconds)


class Wall:

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, background):
        pygame.draw.rect(background, WALL_GRAY, self.rect)


# GameObject is the parent class for the player, zombies and bullets
class GameObject:

    def __init__(self, x, y, radius, color):
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.radius = radius
        self.color = color
        self.angle = 0

    def draw(self, background):
        pygame.draw.circle(background, self.color, self.position, self.radius)

    def detect_collision(self, other_body):
        distance = self.position.distance_to(other_body.position)
        return distance < self.radius + other_body.radius

    def get_forward_vector(self):
        radians = math.radians(self.angle)
        return pygame.Vector2(math.cos(radians), -math.sin(radians))

    def get_rect(self):
        return pygame.Rect(self.position.x - self.radius, self.position.y - self.radius,
                           self.radius * 2, self.radius * 2)

    def hits_wall(self, walls):
        for wall in walls:
            if self.get_rect().colliderect(wall.rect):
                return True
        return False

    def move_with_walls(self, walls, width, height):
        # move x and y separately, undo the move if it goes into a wall
        blocked = False
        self.position.x += self.velocity.x
        if self.hits_wall(walls) or self.position.x < self.radius or self.position.x > width - self.radius:
            self.position.x -= self.velocity.x
            self.velocity.x = 0
            blocked = True
        self.position.y += self.velocity.y
        if self.hits_wall(walls) or self.position.y < self.radius or self.position.y > height - self.radius:
            self.position.y -= self.velocity.y
            self.velocity.y = 0
            blocked = True
        return blocked

    def draw_with_hands(self, background, angle):
        # body + two small circles for hands
        radians = math.radians(angle)
        forward = pygame.Vector2(math.cos(radians), -math.sin(radians))
        side = pygame.Vector2(-forward.y, forward.x)
        left_hand = self.position + forward * self.radius - side * self.radius * 0.6
        right_hand = self.position + forward * self.radius + side * self.radius * 0.6
        pygame.draw.circle(background, self.color, self.position, self.radius)
        pygame.draw.circle(background, BLACK, self.position, self.radius, 2)
        pygame.draw.circle(background, self.color, left_hand, 7)
        pygame.draw.circle(background, BLACK, left_hand, 7, 2)
        pygame.draw.circle(background, self.color, right_hand, 7)
        pygame.draw.circle(background, BLACK, right_hand, 7, 2)


class Player(GameObject):

    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS, YELLOW)
        self.health = MAX_HEALTH
        self.stamina = MAX_STAMINA

    def move(self, keys, walls, width, height):
        acceleration = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            acceleration.y -= 1
        if keys[pygame.K_s]:
            acceleration.y += 1
        if keys[pygame.K_a]:
            acceleration.x -= 1
        if keys[pygame.K_d]:
            acceleration.x += 1

        # Sprint
        thrust = THRUST
        top_speed = MAX_SPEED
        if keys[pygame.K_LSHIFT] and self.stamina > 0 and acceleration.length() > 0:
            thrust = SPRINT_THRUST
            top_speed = SPRINT_SPEED
            self.stamina -= 1
        elif self.stamina < MAX_STAMINA:
            self.stamina += 0.3

        if acceleration.length() > 0:
            acceleration = acceleration.normalize() * thrust
        self.velocity += acceleration
        self.velocity *= DRAG
        if self.velocity.length() > top_speed:
            self.velocity.scale_to_length(top_speed)
        self.move_with_walls(walls, width, height)

    def aim(self, mouse_pos):
        diff = pygame.Vector2(mouse_pos) - self.position
        self.angle = math.degrees(math.atan2(-diff.y, diff.x))

    def shoot(self):
        forward = self.get_forward_vector()
        side = pygame.Vector2(-forward.y, forward.x)
        right_hand = self.position + forward * self.radius + side * self.radius * 0.6
        return Bullet(right_hand + forward * 22, forward)

    def draw(self, background):
        # gun is a rectangle held in the right hand
        forward = self.get_forward_vector()
        side = pygame.Vector2(-forward.y, forward.x)
        right_hand = self.position + forward * self.radius + side * self.radius * 0.6
        back = right_hand - forward * 2
        tip = right_hand + forward * 22
        gun = [back + side * 3.5, tip + side * 3.5, tip - side * 3.5, back - side * 3.5]
        pygame.draw.polygon(background, GUN_COLOR, gun)
        self.draw_with_hands(background, self.angle)


class Zombie(GameObject):

    def __init__(self, x, y):
        super().__init__(x, y, ZOMBIE_RADIUS, GREEN)
        self.health = ZOMBIE_HEALTH
        self.angle = random.randint(0, 359)
        self.state = "WANDER"
        self.max_speed = random.uniform(1.5, 3.0)    # some zombies are faster
        self.wander_timer = 0
        self.attack_timer = 0
        self.wobble = 0
        self.lunge_direction = pygame.Vector2(0, 0)
        self.lunge_accel = 0
        self.lunge_timer = 0
        self.lunge_hit = False
        self.rest_timer = 0

    def update(self, player, walls, width, height):
        to_player = player.position - self.position
        distance = to_player.length()

        # PERCEPTION
        forward = self.get_forward_vector()
        if distance > 0:
            dot = forward.dot(to_player.normalize())
        else:
            dot = 1

        # DECISION
        if self.state == "WANDER" and distance < DETECTION_RANGE and dot > FOV_THRESHOLD:
            if random.random() < LUNGE_CHANCE:
                self.start_lunge(to_player)
            else:
                self.state = "CHASE"
        elif self.state == "CHASE" and distance > DETECTION_RANGE * 1.5:
            self.state = "WANDER"

        # ACTION
        if self.state == "CHASE":
            self.chase(to_player, distance, player)
        elif self.state == "LUNGE":
            self.lunge(distance, player)
        elif self.state == "REST":
            self.rest()
        else:
            self.wander()

        old_position = pygame.Vector2(self.position)
        blocked = self.move_with_walls(walls, width, height)
        # if it walked into a wall while wandering, turn around
        if self.state == "WANDER" and self.position == old_position:
            self.angle += 180
        # lunging into a wall hurts
        if self.state == "LUNGE" and blocked:
            self.health -= 1
            self.start_rest()

        if self.attack_timer > 0:
            self.attack_timer -= 1

    def wander(self):
        self.wander_timer -= 1
        if self.wander_timer <= 0:
            self.angle = random.randint(0, 359)
            self.wander_timer = random.randint(60, 180)
        self.velocity = self.get_forward_vector() * WANDER_SPEED

    def chase(self, to_player, distance, player):
        if distance == 0:
            return
        direction = to_player.normalize()
        self.angle = math.degrees(math.atan2(-direction.y, direction.x))

        # speed up until top speed
        self.velocity += direction * ZOMBIE_ACCEL
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        self.wobble += 0.2

        # Attack
        if distance < self.radius + player.radius + 5 and self.attack_timer == 0:
            player.health -= ZOMBIE_DAMAGE
            self.attack_timer = 60

    # Lunge
    def start_lunge(self, to_player):
        self.state = "LUNGE"
        self.lunge_direction = to_player.normalize()    # locked in, can't turn mid lunge
        self.angle = math.degrees(math.atan2(-self.lunge_direction.y, self.lunge_direction.x))
        lunge_distance = random.randint(LUNGE_MIN, LUNGE_MAX)
        # speeding up for N frames then slowing down for N frames goes accel * N * N pixels
        self.lunge_accel = lunge_distance / (LUNGE_FRAMES * LUNGE_FRAMES)
        self.lunge_timer = 0
        self.lunge_hit = False
        self.velocity = pygame.Vector2(0, 0)

    def lunge(self, distance, player):
        if self.lunge_timer < LUNGE_FRAMES:
            self.velocity += self.lunge_direction * self.lunge_accel
        else:
            self.velocity -= self.lunge_direction * self.lunge_accel
        self.lunge_timer += 1

        if not self.lunge_hit and distance < self.radius + player.radius:
            player.health -= LUNGE_DAMAGE
            self.lunge_hit = True

        if self.lunge_timer >= LUNGE_FRAMES * 2:
            self.start_rest()

    def start_rest(self):
        self.state = "REST"
        self.rest_timer = REST_TIME
        self.velocity = pygame.Vector2(0, 0)

    def rest(self):
        self.velocity = pygame.Vector2(0, 0)
        self.rest_timer -= 1
        if self.rest_timer <= 0:
            self.state = "CHASE"

    def draw(self, background):
        angle = self.angle
        if self.state == "CHASE":
            angle += math.sin(self.wobble) * 20
        self.draw_with_hands(background, angle)

        # small health bar
        if self.health < ZOMBIE_HEALTH:
            pygame.draw.rect(background, RED, (self.position.x - 18, self.position.y - 30, 36, 5))
            pygame.draw.rect(background, DARK_GREEN, (self.position.x - 18, self.position.y - 30, 36 * self.health / ZOMBIE_HEALTH, 5))


class Bullet(GameObject):

    def __init__(self, position, direction):
        super().__init__(position.x, position.y, 4, BLACK)
        self.velocity = direction.normalize() * BULLET_SPEED

    def move(self):
        self.position += self.velocity

    def is_off_screen(self, width, height):
        return self.position.x < 0 or self.position.x > width or self.position.y < 0 or self.position.y > height


# Start Game
async def main():
    pygame.init()
    game = Game('Zombie Apocalypse', WIDTH, HEIGHT)
    if await game.start_screen():
        while await game.run_game_loop():
            pass
    pygame.quit()


asyncio.run(main())
