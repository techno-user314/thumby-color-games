import random
from math import pi

import engine_main
import engine
import engine_io
import engine_draw
import engine_save

from engine_draw import Color
from engine_animation import Delay
from engine_math import Vector2
from engine_resources import TextureResource
from engine_nodes import Rectangle2DNode, CameraNode, Text2DNode, Sprite2DNode

engine_save.set_location("save.data")

world = engine_save.load("world", 1) # Used for the random generator seed
highworld = engine_save.load("highworld", 1) # The world where the highscore was reached
highscore = engine_save.load("highscore", 0) # Global high score

score = 0 # Number of lanes survived
lanes = []
danger_streak = 0 # Number of dangerous lanes in a row

menu = False
rumble = False
rumble_clock = 0

camera = CameraNode()
engine.fps_limit(25)


class Player:
    def __init__(self):
        sprite_resource = TextureResource("/Games/FroggyRoad/frog.bmp")
        self.sprite = Sprite2DNode(Vector2(0, 24),
                                   sprite_resource,
                                   rotation=pi/2, layer=3)
        #self.sprite = Rectangle2DNode(position=Vector2(0, 24), rotation=pi/2,
        #                              height=10, width=10, layer=3)

    def move(self, direction):
        xpos = self.sprite.position.x
        self.sprite.position.x = max(min(xpos + direction * 8, 56), -56)

        if direction == -1: self.sprite.rotation = pi
        elif direction == 1: self.sprite.rotation = 0


class MovingObject:
    def __init__(self, speed, sprite_file):
        self.speed = speed
        self.moved = False

        self.sprite = Sprite2DNode(Vector2(0, 0),
                                   TextureResource(sprite_file),
                                   layer=3)
        #self.sprite = Rectangle2DNode(height=6, width=10, layer=2)
        #self.sprite.position = Vector2(0, 0)

    def move(self, direction):
        if self.moved == False:
            self.moved = True
            self.sprite.position.x = -64 * direction
        self.sprite.position.x += self.speed * direction

    def offscreen(self):
        return (abs(self.sprite.position.x) > 64)
    
    def adjust_y(self, new_y):
        self.sprite.position.y = new_y

class Car(MovingObject):
    def __init__(self, speed):
        super().__init__(speed, "/Games/FroggyRoad/car.bmp")

class Log(MovingObject):
    def __init__(self, speed):
        super().__init__(speed, "/Games/FroggyRoad/log.bmp")
        self.sprite.width = 25

class Lily(MovingObject):
    def __init__(self, speed):
        super().__init__(speed, "/Games/FroggyRoad/lily.bmp")


class Lane:
    def __init__(self, speed, spawn_rate, lane_type):
        self.ltype = lane_type
        self.speed = speed
        self.direction = random.choice([-1, 1])
        self.spawn_rate = spawn_rate
      
        self.box = Rectangle2DNode(width=128, height=16, layer=1)
        self.box.position = Vector2(0, 0)

        self.objects = []
        self.spawn_timer = 100

    def update_position(self, pos_id):
        self.box.position = Vector2(0, 16*pos_id - 56)
        for obj in self.objects:
            obj.adjust_y(16*pos_id - 56)

    def manage_objects(self):
        # Delete old objects
        for obj in self.objects:
            if obj.offscreen():
                obj.sprite.mark_destroy()
        self.objects = [obj for obj in self.objects
                        if not obj.offscreen()]

        # Spawn new objects
        self.spawn_timer += 1
        if self.spawn_timer > self.spawn_rate + random.randint(-5, 10):
            self.spawn_timer = 0

            if random.randint(1, 16) != 1:
                if self.ltype == 0:
                    pass
                elif self.ltype == 1:
                    self.objects.append(Car(self.speed))
                elif self.ltype == 2:
                    self.objects.append(Log(self.speed))
                elif self.ltype == 3:
                    self.objects.append(Lily(self.speed))
                  
                if self.ltype != 0:
                    self.objects[-1].adjust_y(self.box.position.y)

        # Move current objects
        for obj in self.objects:
            obj.move(self.direction)

    def destroy_objects(self):
        for obj in self.objects:
            obj.sprite.mark_destroy()

class Grass(Lane):
    def __init__(self):
        super().__init__(0, 0, 0)
        self.box.color = Color(0.75, 0, 0.75)
      
class Street(Lane):
    def __init__(self, speed, spawn_rate):
        super().__init__(speed, spawn_rate, 1)
        self.box.color = Color(0.15, 0.15, 0.15)

class RiverLog(Lane):
    def __init__(self, speed, spawn_rate):
        super().__init__(speed, spawn_rate, 2)
        self.box.color = Color(0.075, 0, 0.5)
      
class RiverLily(Lane):
    def __init__(self, speed, spawn_rate):
        super().__init__(speed, spawn_rate, 3)
        self.box.color = Color(0.075, 0, 0.5)


def get_next_lane(score):
    """
    Generate the next Lane based only on score.
    Assumes random.seed() is set externally if reproducibility is needed.
    """
    global danger_streak
  
    # Calculate difficulty based on score
    difficulty = min(score // 25, 5)  # Cap difficulty at 5

    # Define lane type weights based on difficulty
    lane_weights = {
        'Grass': max(5 - difficulty, 1),
        'Street': 2 + difficulty,
        'RiverLily': 1 + difficulty // 2,
        'RiverLog': 1 + difficulty // 2
    }

    # If there have been a lot of dangerous sections in a row...
    if danger_streak >= 3:
        lane_weights['Grass'] += 4  # ...Gently favor Grass
    elif danger_streak >= 4:
        lane_weights['Grass'] += 6  # ...Stronger boost if streak is even longer

    # Build weighted choices
    choices = []
    for lane_type, weight in lane_weights.items():
        choices.extend([lane_type] * weight)

    # Randomly pick a lane type
    lane_type = random.choice(choices)

    if lane_type == 'Grass':
        danger_streak = 0
        return Grass()

    elif lane_type == 'Street':
        danger_streak += 1
        speed = random.uniform(0.8 + difficulty * 0.5, 1.2 + difficulty * 0.5)
        spawn_rate = 65 - 9 * difficulty
        return Street(speed=speed, spawn_rate=spawn_rate)

    elif lane_type == 'RiverLily':
        danger_streak += 1
        speed = random.uniform(0.8 + difficulty * 0.25, 1.2 + difficulty * 0.25)
        spawn_rate = 65 - 9 * difficulty
        return RiverLily(speed=speed, spawn_rate=spawn_rate)

    elif lane_type == 'RiverLog':
        danger_streak += 1
        speed = random.uniform(0.8 + difficulty * 0.25, 1.2 + difficulty * 0.25)
        spawn_rate = 65 - 9 * difficulty
        return RiverLog(speed=speed, spawn_rate=spawn_rate)

def check_collision(lane, player):
    if lane.ltype == 0: # Grass
        return False
      
    dead = True
    player_x = player.sprite.position.x
    player_left = player_x - 5
    player_right = player_x + 5

    if player_x > 64 or player_x < -64:
        return True
      
    if lane.ltype == 1: # Street
        dead = False
        for car in lane.objects:
            car_left = car.sprite.position.x - car.sprite.width/2
            car_right = car.sprite.position.x + car.sprite.width/2
            if player_right >= car_left and player_right < car_right:
                dead = True
                break
            if player_left <= car_right and player_right > car_left:
                dead = True
                break
              
    elif lane.ltype == 2: # Log river
        for log in lane.objects:
            log_left = log.sprite.position.x - log.sprite.width/2
            log_right = log.sprite.position.x + log.sprite.width/2
            if player_x >= log_left and player_x <= log_right:
                player.sprite.position.x += lane.speed * lane.direction
                dead = False
                break
              
    elif lane.ltype == 3: # Lily river
        for lily in lane.objects:
            lily_left = lily.sprite.position.x - lily.sprite.width/2
            lily_right = lily.sprite.position.x + lily.sprite.width/2
            if player_x >= lily_left and player_x <= lily_right:
                player.sprite.position.x += lane.speed * lane.direction
                dead = False
                break
    return dead


scoreboard = Text2DNode(position=Vector2(0, -56), layer=4,
                        text=f"Score: {score}",
                        letter_spacing=1.1, line_spacing=1.1)
player = Player()
lanes = [Grass(), Grass(), Grass(), Grass(), Grass(),
         RiverLog(1, 75), Grass(), Street(1, 75)]
for i, lane in enumerate(lanes):
    lane.update_position(len(lanes) - 1 - i)

random.seed(world)
game_running = True
while game_running:
    if engine.tick():
        if rumble:
            rumble_clock += 1
            if rumble_clock > 20:
                rumble_clock = 0
                rumble = False
                engine_io.rumble(0)
        if menu:
            scoreboard.position = Vector2(0, -32)
            scoreboard.text = f"World Number: {world}\nPress A to start\n\nHighscore: {highscore}\nachieved in world\n{highworld}"
            if engine_io.A.is_just_pressed:
                # Delete old game
                menu = False
                score = 0
                scoreboard.position = Vector2(0, -56)
                scoreboard.text = f"Score: {score}"
                for lane in lanes:
                    if lane is not None:
                        lane.destroy_objects()
                        lane.box.mark_destroy()
                # Create new game
                random.seed(world)
                lanes = [Grass(), Grass(), Grass(), Grass(), Grass(),
                         RiverLog(1, 75), Grass(), Street(1, 75)]
                for i, lane in enumerate(lanes):
                    lane.update_position(len(lanes) - 1 - i)

            if engine_io.LEFT.is_just_pressed:
                world = 1
            if engine_io.RIGHT.is_just_pressed:
                world = random.randint(1, 99)
            if engine_io.UP.is_just_pressed:
                world += 1
            if engine_io.DOWN.is_just_pressed:
                world = max(1, world - 1)

            if engine_io.MENU.is_just_pressed:
                game_running = False
        else:
            for lane in lanes:
                lane.manage_objects()
  
            player_died = check_collision(lanes[2], player)
            if player_died:
                if score > highscore:
                    highscore = score
                    highworld = world
                for i in range(len(lanes)):
                    if 1 <= i <= 3: continue # Skip the lanes near the player so they see how they died
                    lanes[i].destroy_objects()
                    lanes[i].box.mark_destroy()
                    lanes[i] = None
                rumble = True
                engine_io.rumble(0.25)
                menu = True
            
            if engine_io.UP.is_just_pressed:
                score += 1
                scoreboard.text = f"Score: {score}"
              
                lanes.append(get_next_lane(score))
                for i, lane in enumerate(lanes):
                    if lane is not None:
                        lane.update_position(len(lanes) - 1 - i)
                
                if lanes[0] is not None:
                    lanes[0].destroy_objects()
                    lanes[0].box.mark_destroy()
                    lanes.pop(0)

            if engine_io.LEFT.is_just_pressed:
                player.move(-1)
            if engine_io.RIGHT.is_just_pressed:
                player.move(1)
              
            if engine_io.MENU.is_just_pressed:
                if score > highscore:
                    highscore = score
                    highworld = world
                for i in range(len(lanes)):
                    if 1 <= i <= 3: continue # Skip the lanes near the player so they see how they died
                    lanes[i].destroy_objects()
                    lanes[i].box.mark_destroy()
                    lanes[i] = None
                menu = True

engine_save.save("world", world)
engine_save.save("highscore", highscore)
engine_save.save("highworld", highworld)
