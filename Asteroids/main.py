import random
from math import pi, sin, cos, sqrt

import engine_main
import engine
import engine_io
import engine_draw
import engine_save

from engine_draw import Color
from engine_animation import Delay
from engine_resources import TextureResource
from engine_math import Vector2
from engine_nodes import Sprite2DNode, Rectangle2DNode, Circle2DNode, CameraNode, Text2DNode

ACCELERATION = 17 # Lower number is faster acceleration
TOP_SPEED = 1.5 # Top speed in pixels/frame
ROT_SPEED = 25 # Rotation speed; Lower is faster
BULLET_SPEED = 2.5 # Bullet speed in pixels/frame

engine_save.set_location("highscore.data")

menu = False
score = 0
highscore = engine_save.load("highscore", 0)

camera = CameraNode()
engine.fps_limit(25)

class Bullet:
    def __init__(self, pos, angle):
        self.angle = angle
        self.active = True
        self.sprite = Rectangle2DNode(position=pos, 
                                      rotation=self.angle,
                                      height=2, width=2,
                                      layer=1)

    def move(self):
        self.sprite.position.x += BULLET_SPEED * cos(2*pi-self.angle)
        self.sprite.position.y += BULLET_SPEED * sin(2*pi-self.angle)

    def is_offscreen(self):
        if not self.active:
            self.sprite.mark_destroy()
            return True
        if abs(self.sprite.position.x) > 63:
            self.sprite.mark_destroy()
            return True
        elif abs(self.sprite.position.y) > 63:
            self.sprite.mark_destroy()
            return True
        else:
            return False

class Player:
    def __init__(self):
        self.sprite = Sprite2DNode(Vector2(0, 0),
                                   TextureResource("/Games/Asteroids/spaceship.bmp"),
                                   layer=1)
        #self.sprite = Rectangle2DNode(Vector2(0, 0), 7, 7, layer=1)
        self.shield_sprite = Circle2DNode(Vector2(0, 0), 7,
                                          layer=0, outline=True, color=Color(0, 0, 1))

        self.shield = False
        self.x_momentum = 0
        self.y_momentum = 0
        self.angle = 0
        self.bullets = []

    def rotate(self, direction):
        self.angle += direction * (pi / ROT_SPEED)
        self.angle = self.angle % (2 * pi)
        self.sprite.rotation = self.angle

    def thrust(self):
        self.x_momentum = max(min(self.x_momentum + cos(self.angle)/ACCELERATION, TOP_SPEED), -TOP_SPEED)
        self.y_momentum = max(min(self.y_momentum + sin(self.angle)/ACCELERATION, TOP_SPEED), -TOP_SPEED)

    def move(self):
        self.sprite.position.x += self.x_momentum
        self.sprite.position.y -= self.y_momentum
        # Screenwrap
        if self.sprite.position.x >= 64:
            self.sprite.position.x = -63
        elif self.sprite.position.x <= -64:
            self.sprite.position.x = 63
        if self.sprite.position.y >= 64:
            self.sprite.position.y = -63
        elif self.sprite.position.y <= -64:
            self.sprite.position.y = 63
        
        self.shield_sprite.position = self.sprite.position
        if self.shield:
            self.shield_sprite.color = Color(0, 0, 1)
        else:
            self.shield_sprite.color = Color(0, 0, 0)

    def move_bullets(self):
        self.bullets = [b for b in self.bullets
                        if not b.is_offscreen()]
            
        for bullet in self.bullets:
            bullet.move()

    def shoot(self):
        x = self.sprite.position.x
        y = self.sprite.position.y
        self.bullets.append(Bullet(Vector2(x, y), self.angle))

    def toggle_shield(self, onoff):
        self.shield = onoff

    def clear_bullets(self):
        for b in self.bullets:
            b.sprite.mark_destroy()


class Meteroid():
    def __init__(self, size):
        self.sprite = Circle2DNode()
        self.sprite.layer = 2
        self.sprite.radius = size
        self.sprite.outline = False
        self.sprite.color = Color(random.uniform(0.65, 1), 
                                  random.uniform(0.65, 1),
                                  random.uniform(0.65, 1))

        pos = [0, 0]
        rand_axis = random.randint(0, 1)
        pos[rand_axis] = random.uniform(-63, 63)
        pos[not rand_axis] = random.choice([-63, 63])
        self.sprite.position = Vector2(pos[0], pos[1])

        self.slopes = [random.randint(1, 4), random.randint(1, 4)]
        self.slopes[0] *= int(pos[0] < 0) * 2 - 1
        self.slopes[1] *= int(pos[1] < 0) * 2 - 1

    def move(self):
        self.sprite.position.x += self.slopes[0] / (8 - min(score//100, 3))
        self.sprite.position.y += self.slopes[1] / (8 - min(score//100, 3))

    def get_points_value(self):
        return (10 - self.sprite.radius) * 10

    def explode(self):
        self.sprite.radius -= 2
        self.slopes = [random.randint(1, 4), random.randint(1, 4)]
        self.slopes[0] *= int(self.sprite.position.x < 0) * 2 - 1
        self.slopes[1] *= int(self.sprite.position.y < 0) * 2 - 1

        if self.sprite.radius > 0:
            clone = Meteroid(self.sprite.radius)
            clone.sprite.position = self.sprite.position
            return clone
        return False

    def is_offscreen(self):
        if self.sprite.radius <= 0:
            self.sprite.mark_destroy()
            return True
        elif abs(self.sprite.position.x) > 63:
            self.sprite.mark_destroy()
            return True
        elif abs(self.sprite.position.y) > 63:
            self.sprite.mark_destroy()
            return True
        else:
            return False

class Space:
    def __init__(self):
        self.meteroids = []

    def manage_meteroids(self):
        # Add new meteroids
        if len(self.meteroids) <= min(score // 200 + 7, 20):
            size = random.choice([2, 4, 4, 6, 6, 6, 8])
            self.meteroids.append(Meteroid(size))

        # Delete old meteroids
        self.meteroids = [m for m in self.meteroids
                          if not m.is_offscreen()]

        # Move current meteroids
        for m in self.meteroids:
            m.move()

    def split_meteroid(self, meteroid):
        new_meteroid = meteroid.explode()
        if new_meteroid != False:
            self.meteroids.append(new_meteroid)

    def clear_meteroids(self):
        for m in self.meteroids:
            m.sprite.mark_destroy()


def check_collisions(game, player):
    global score
    # Check for collision between player and meteroid
    player_xy = [player.sprite.position.x,
                 player.sprite.position.y]
    for meteroid in game.meteroids:
        meter_xy = [meteroid.sprite.position.x,
                    meteroid.sprite.position.y]
        ab = [meter_xy[0] - player_xy[0],
             meter_xy[1] - player_xy[1]]
        distance = sqrt( ab[0]**2 + ab[1]**2 )
        if distance < meteroid.sprite.radius:
            if not player.shield:
                return {"happened":True, "what":-1}
    # Check for collision between bullet and meteroid
    for meteroid in game.meteroids:
        for bullet in player.bullets:
            bullet_xy = [bullet.sprite.position.x,
                         bullet.sprite.position.y]
            meter_xy = [meteroid.sprite.position.x,
                        meteroid.sprite.position.y]
            ab = [meter_xy[0] - bullet_xy[0],
                 meter_xy[1] - bullet_xy[1]]
            distance = sqrt( ab[0]**2 + ab[1]**2 )
            if distance < meteroid.sprite.radius:
                game.split_meteroid(meteroid)
                bullet.active = False
                return {"happened":True,
                        "what":meteroid.get_points_value()}
    return {"happened":False, "what":0}


game = Space()
player = Player()
scoreboard = Text2DNode(position=Vector2(50, -56), layer=4,
                        text=f"{score}",
                        letter_spacing=1.1, line_spacing=1.3)

game_running = True
paused = False
while game_running:
    if engine.tick():
        if menu:
            if engine_io.A.is_just_pressed:
                score = 0
                if not paused:
                    game = Space()
                    player = Player()
                
                scoreboard.position = Vector2(50, -56)
                scoreboard.text = f"{score}"

                menu = False
                paused = False

            if engine_io.MENU.is_just_pressed:
                game_running = False
        else:
            game.manage_meteroids()
            player.move()
            player.move_bullets()
            if player.shield and score <= 0:
                player.toggle_shield(False)
          
            if player.shield:
                score = max(score-1.5, 0)
                scoreboard.text = f"{score}"
            
            collisions = check_collisions(game, player)
            if collisions["happened"]:
                if collisions["what"] == -1:
                    # Clear the game
                    if score > highscore:
                        highscore = score
                      
                    game.clear_meteroids()
                    player.clear_bullets()
                    player.sprite.mark_destroy()
                    player.shield_sprite.mark_destroy()
                  
                    scoreboard.position = Vector2(0, 0)
                    scoreboard.text = f"Your score was: {score}\nHighscore: {highscore}\nPress A to restart."
                  
                    menu = True
                else:
                    score += collisions["what"]
                    scoreboard.text = f"{score}"
                continue

            if engine_io.LEFT.is_pressed or engine_io.LB.is_pressed:
                player.rotate(1)
            if engine_io.RIGHT.is_pressed or engine_io.RB.is_pressed:
                player.rotate(-1)

            if engine_io.UP.is_pressed:
                player.thrust()

            if engine_io.A.is_just_pressed:
                player.shoot()
            if engine_io.B.is_just_pressed:
                if score > 0:
                    player.toggle_shield(True)
            elif engine_io.B.is_just_released:
                player.toggle_shield(False)

            if engine_io.MENU.is_just_pressed:
                menu = True
                paused = True
                scoreboard.position=Vector2(0, 0)
                scoreboard.text = "Paused\nPress A to resume"
                continue

engine_save.save("highscore", highscore)
