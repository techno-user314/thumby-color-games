import engine_main
import engine
import engine_io
import random
import engine_draw
from engine_draw import Color
from engine_animation import Delay
from engine_math import Vector2
from engine_nodes import Rectangle2DNode, CameraNode, Text2DNode

GRID_SIZE = 8
TILE_SIZE = 128 / GRID_SIZE

depth = 2 # Number of swaps till back to original
level = 15

camera = CameraNode()

class Crosshair:
    def __init__(self):
        self.pos = [0, 0]
        self.rects = [Rectangle2DNode(),
                      Rectangle2DNode(),
                      Rectangle2DNode(),
                      Rectangle2DNode()]
        for rect in self.rects:
            rect.width = 4
            rect.height = 4
            rect.layer = 2
            rect.color = Color(0.9, 0.9, 0.9)
        
        self.update_corners()

    def update_corners(self):
        half = int(GRID_SIZE / 2)
        pos1 = Vector2((self.pos[0]-half)*TILE_SIZE+2,
                       (self.pos[1]-half)*TILE_SIZE+2)
        pos2 = Vector2((self.pos[0]-half)*TILE_SIZE+TILE_SIZE-2,
                       (self.pos[1]-half)*TILE_SIZE+2)
        pos3 = Vector2((self.pos[0]-half)*TILE_SIZE+TILE_SIZE-2,
                       (self.pos[1]-half)*TILE_SIZE+TILE_SIZE-2)
        pos4 = Vector2((self.pos[0]-half)*TILE_SIZE+2,
                       (self.pos[1]-half)*TILE_SIZE+TILE_SIZE-2)
        self.rects[0].position = pos1
        self.rects[1].position = pos2
        self.rects[2].position = pos3
        self.rects[3].position = pos4
  
    def move_to(self, xy_list):
        self.pos = xy_list
        self.update_corners()
  
class Tile(Rectangle2DNode):
    def __init__(self, pos):
        super().__init__(self)
        self.position = pos
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.color = engine_draw.red
        self.opacity = 0.75
        self.outline = False
        self.layer = 1

        self.tile_type = 0

    def swap(self, forward):
        if forward:
            self.tile_type = (self.tile_type+1) % depth
        else:
            if self.tile_type == 0: 
                self.tile_type = depth-1
            else: 
                self.tile_type = self.tile_type-1
        colors = [engine_draw.red, engine_draw.blue,
                  engine_draw.green, engine_draw.purple,
                  engine_draw.yellow, engine_draw.darkgrey,
                  engine_draw.silver, engine_draw.brown,
                  engine_draw.orange, engine_draw.skyblue]
        self.color = colors[self.tile_type]

    def select(self, selected):
        if selected:
            self.opacity = 1.0
        else:
            self.opacity = 0.75

class Grid:
    def __init__(self):
        halfway = int(GRID_SIZE/2)
        self.tiles = [[] for _ in range(GRID_SIZE)]
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                new_pos = Vector2(TILE_SIZE*(x-halfway+0.5),
                                  TILE_SIZE*(y-halfway+0.5))
                self.tiles[x].append(Tile(new_pos))
        self.selector = Crosshair()
        self.selected = [halfway, halfway]
        self.selector.move_to(self.selected)
        self.tiles[self.selected[0]][self.selected[1]].select(True)

    def is_valid_swap(self, x, y):
        if x < 0 or x > GRID_SIZE-1:
            return False
        if y < 0 or y > GRID_SIZE-1:
            return False
        return True

    def swap(self, sx, sy, direction=1):
        if sx is None or sy is None:
            sx, sy = self.selected
        if not self.is_valid_swap(sx, sy):
            return False
        affected = [[sx-1, sy-1], [sx, sy-1], [sx+1, sy-1],
                    [sx-1, sy  ], [sx, sy  ], [sx+1, sy  ],
                    [sx-1, sy+1], [sx, sy+1], [sx+1, sy+1]]
        for x, y in affected:
            if self.is_valid_swap(x, y):
                self.tiles[x][y].swap(direction==1)
        return True

    def mix(self):
        all_positions = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)]
        for i in range(level):
            rand_index = int(random.random() * len(all_positions))
            self.swap(all_positions[rand_index][0], all_positions[rand_index][1])
            all_positions.pop(rand_index)

    def move_selection(self, delta_x, delta_y):
        if not self.is_valid_swap(self.selected[0]+delta_x,
                                  self.selected[1]+delta_y):
            return
        self.tiles[self.selected[0]][self.selected[1]].select(False)        
        self.selected[0] += delta_x
        self.selected[1] += delta_y
        self.tiles[self.selected[0]][self.selected[1]].select(True)
        self.selector.move_to(self.selected)

    def check_win(self):
        for row in self.tiles:
            for tile in row:
                if tile.tile_type != 0:
                    return False
        return True

class Menu:
    def __init__(self):
        self.active = True

        level_str = "Level: "+str(level)
        depth_str = "Depth: "+str(depth)
        self.texts = [Text2DNode(text="BitFlip", color=engine_draw.red),
                      Text2DNode(text=level_str, color=engine_draw.white),
                      Text2DNode(text=depth_str, color=engine_draw.white,)]
        for i, text_item in enumerate(self.texts):
            text_item.layer = 4
            text_item.letter_spacing = 1.5            
            text_item.position = Vector2(0, (i+3)*12-64)

        self.cover = Rectangle2DNode()
        self.cover.position = Vector2(0, 0)
        self.cover.width = 128
        self.cover.height = 128
        self.cover.color = engine_draw.black
        self.cover.layer = 3

        self.layer = 3

    def activate(self, a=True):
        self.active = a
        self.layer = 3 if a else 0
        for text_item in self.texts:
            text_item.layer = self.layer
            if self.layer == 3:
                text_item.layer += 1
        self.cover.layer = self.layer

    def set_difficulty(self, d):
        global level
        level = max(1, min(GRID_SIZE*GRID_SIZE, d))
        level_str = "Level: "+str(level)
        self.texts[1].text = level_str

    def set_depth(self, d):
        global depth
        depth = max(2, min(d, 10))
        depth_str = "Depth: "+str(depth)
        self.texts[2].text = depth_str

mainloop = True
menu = Menu()

game = Grid()
while mainloop:
    if engine.tick():
        if menu.active:
            if engine_io.LEFT.is_just_pressed:
                menu.set_depth(depth-1)
            if engine_io.RIGHT.is_just_pressed:
                menu.set_depth(depth+1)
            if engine_io.UP.is_just_pressed:
                menu.set_difficulty(level+1)
            if engine_io.DOWN.is_just_pressed:
                menu.set_difficulty(level-1)
            if engine_io.MENU.is_just_pressed:
                mainloop = False
            if engine_io.A.is_just_pressed:
                game.mix()
                menu.activate(False)
            continue
        else:
            if engine_io.LEFT.is_just_pressed:
                game.move_selection(-1, 0)
            if engine_io.RIGHT.is_just_pressed:
                game.move_selection(1, 0)
            if engine_io.UP.is_just_pressed:
                game.move_selection(0, -1)
            if engine_io.DOWN.is_just_pressed:
                game.move_selection(0, 1)
            if engine_io.A.is_just_pressed:
                game.swap(None, None)
            if engine_io.B.is_just_pressed:
                game.swap(None, None, direction=-1)
            if engine_io.MENU.is_just_pressed:
                menu.activate(True)
            if game.check_win():
                Delay().start(1000, menu.activate)
