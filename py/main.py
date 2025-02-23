import math
import sys
import pygame
import classic_component
import classic_entity
import network
import time
import threading

# Initialize Pygame
pygame.init()

# Set up the display
screen_size = pygame.display.get_desktop_sizes()[0]
screen_width = screen_size[0]
screen_height = screen_size[1]
screen = pygame.display.set_mode((screen_width, screen_height), pygame.SRCALPHA | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
pygame.display.set_caption("Pygame Initialization Example")

# Clock
clock = pygame.time.Clock()

# Font
font = pygame.font.SysFont("Arial", 20)

# Load resources
background = pygame.image.load("14e9a331115edf4e61686b563dda859f.jpg")
block_textures = [
    pygame.transform.scale(pygame.image.load("skyblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("grassblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("stoneblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("woodblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("woodblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("waterblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("woodblock.png").convert_alpha(), (10, 10)),
    pygame.transform.scale(pygame.image.load("woodblock.png").convert_alpha(), (10, 10))
]

block_textures = [pygame.transform.scale(tex, (10, 10)) for tex in block_textures]

# Player animation setup
sprite_sheet = pygame.image.load("player_spritesheet.png").convert_alpha()
sprite_width, sprite_height = 20, 20
num_frames = 4  # Number of frames in the sprite sheet

# Extract individual frames from the sprite sheet
idle_frames = [sprite_sheet.subsurface((i * sprite_width, 0, sprite_width, sprite_height)) for i in range(num_frames)]
walk_frames = [sprite_sheet.subsurface((i * sprite_width, sprite_height, sprite_width, sprite_height)) for i in range(num_frames)]

player_rect = pygame.Rect(screen_width / 2 - 5, screen_height / 2 - 10, 10, 20)

# Sounds
place_sound = pygame.mixer.Sound("click.mp3")
remove_sound = pygame.mixer.Sound("click.mp3")

# Animation control
frame_index = 0
frame_timer = 0
animation_speed = 0.1  # Time per frame (seconds)

def draw_player(is_moving, dt):
    """
    Draw the player sprite with animation based on movement state.
    """
    global frame_index, frame_timer

    # Select animation frames based on movement
    frames = walk_frames if is_moving else idle_frames

    # Update the animation frame based on elapsed time
    frame_timer += dt
    if frame_timer >= animation_speed:
        frame_index = (frame_index + 1) % num_frames  # Loop through frames
        frame_timer = 0

    # Draw the current frame
    screen.blit(frames[frame_index], (player_rect.x, player_rect.y))

# Colors
WHITE = (255, 255, 255)

# Entities
currentPlayer = classic_entity.Player()
currentPlayer.keys = [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_e, pygame.K_q]
position2D = currentPlayer.getComponent("transform2D").getVariable("position")
speed = 1000

otherPlayers = []

# World
World = {}
WorldPosition = classic_component.Position2D()
WorldDelta = classic_component.Velocity2D()

# Block Types
BlockType = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255),
             (255, 255, 255)]

# Set connection
cliNet = network.ServerConnection("127.0.0.1")
cliNet.send(network.Hello("test"))

# Synchronize network initialization
INIT_DATA = cliNet.recv()['data']
print(INIT_DATA)

# Initialize Data
currentPlayer.player_id = INIT_DATA['player_id']
position2D.x = INIT_DATA['spawn_x'] * 10
position2D.y = INIT_DATA['spawn_y'] * 10
WorldPosition.x = -INIT_DATA['spawn_x'] * 10
WorldPosition.y = -INIT_DATA['spawn_y'] * 10

# Network thread with proper handling of shared resources
network_lock = threading.Lock()

running = True

def NetworkThread():
    global World, position2D, running

    while True:
        time.sleep(0.016)  # Sleep for 16ms (for approx. 60FPS)
        receiving = cliNet.recv()

        # Synchronize access to the shared resource
        with network_lock:
            print(receiving)
            if receiving['t'] == network.KICK:
                print("kicked because", receiving['data']['msg'])
                running = False
                return
            elif receiving['t'] == network.HEARTBEAT_SERVER:
                print("heartbeat received")
                cliNet.send(network.Heartbeat())
            elif receiving['t'] == network.CHUNK_UPDATE:
                updated_chunk = receiving['data']['chunk']
                chunk_coord = (updated_chunk['chunk_x'], updated_chunk['chunk_y'])
                World[chunk_coord] = {}
                for i in range(0, len(updated_chunk['blocks'])):
                    World[chunk_coord][(i % 16 * 10, i // 16 * 10)] = updated_chunk['blocks'][len(updated_chunk['blocks']) - 1 - i]
            else:
                print(receiving)

def draw_world(chunkCoord):
    dChunkX = math.ceil(screen_width / 320)
    dChunkY = math.ceil(screen_height / 320)

    for loadChunkX in range(chunkCoord[0] - dChunkX, chunkCoord[0] + dChunkX + 1):
        for loadChunkY in range(chunkCoord[1] - dChunkY, chunkCoord[1] + dChunkY + 1):
            loadChunk = (loadChunkX, loadChunkY)
            if loadChunk in World:
                for blockPos, blockType in World[loadChunk].items():
                    blockScreenPos = (
                        loadChunk[0] * 160 - blockPos[0] + WorldPosition.x + 145 + screen_width / 2,
                        -loadChunk[1] * 160 + blockPos[1] - WorldPosition.y - 150 + screen_height / 2
                    )
                    if 0 <= blockType < len(block_textures):
                        screen.blit(block_textures[blockType], blockScreenPos)
                    else:
                        print(f"Invalid blockType: {blockType} at position {blockPos}")
            else:
                if (loadChunkX < 0) or (loadChunkY < 0):
                    continue
                World[loadChunk] = {}
                cliNet.send(network.ClientRequestChunk(loadChunk[0], loadChunk[1]))

# Game loop
def main():
    global running, screen_size, screen_width, screen_height
    show_debug = False
    while running:
        dt = clock.tick(50) / 1000  # Calculate time per frame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cliNet.send(network.Goodbye())
                pygame.quit()
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen_size = screen.get_size()
                screen_width = screen_size[0]
                screen_height = screen_size[1]

        # Toggle debug information
        keys = pygame.key.get_pressed()
        if keys[pygame.K_TAB]:
            show_debug = not show_debug

        # Update movement / controls
        movement_update = False
        WorldDelta.setVariable(vx=0, vy=0)

        chunkCoord = (int(position2D.x // 160), int(position2D.y // 160))
        chunkPos = (int(position2D.x % 160 // 10 * 10), int(position2D.y % 160 // 10 * 10))

        if keys[currentPlayer.keys[0]]:
            position2D.y += speed * dt
            WorldDelta.vy += speed * dt
            movement_update = True
        if keys[currentPlayer.keys[1]]:
            position2D.x -= speed * dt
            WorldDelta.vx -= speed * dt
            movement_update = True
        if keys[currentPlayer.keys[2]]:
            position2D.y -= speed * dt
            WorldDelta.vy -= speed * dt
            movement_update = True
        if keys[currentPlayer.keys[3]]:
            position2D.x += speed * dt
            WorldDelta.vx += speed * dt
            movement_update = True
        if keys[currentPlayer.keys[4]]:
            if chunkCoord not in World:
                World[chunkCoord] = {}
            World[chunkCoord][chunkPos] = 2
            place_sound.play()
        if keys[currentPlayer.keys[5]]:
            if World.get(chunkCoord).get(chunkPos) is not None:
                del World[chunkCoord][chunkPos]
                if len(World[chunkCoord]) == 0:
                    del World[chunkCoord]
                remove_sound.play()

        # Reset screen
        screen.blit(pygame.transform.scale(background, (screen_width, screen_height)), (0, 0))

        # Move world
        if movement_update:
            WorldPosition.x -= WorldDelta.vx
            WorldPosition.y -= WorldDelta.vy

        # Draw world (visible chunks)
        draw_world(chunkCoord)

        # Draw player with animation
        draw_player(movement_update, dt)

        # Debug FPS and Position
        if show_debug:
            screen.blit(font.render(f"{clock.get_fps():.2f} FPS", 1, (0, 0, 0)), (10, 10))
            screen.blit(font.render(f"Position: {position2D}", 1, (0, 0, 0)), (10, 30))
            screen.blit(font.render(f"Chunk: {chunkCoord}", 1, (0, 0, 0)), (10, 50))

        # Update the display
        pygame.display.flip()

if __name__ == '__main__':
    netThread = threading.Thread(target=NetworkThread, daemon=True)
    netThread.start()
    main()

pygame.quit()
sys.exit()
