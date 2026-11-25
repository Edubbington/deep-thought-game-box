"""Put screenshots side by side on one sheet:  python tools/sheet.py OUT.png a.png b.png ..."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
pygame.display.init()
out, files = sys.argv[1], sys.argv[2:]
cols = 2
rows = -(-len(files) // cols)
sheet = pygame.Surface((cols * 810 - 10, rows * 490 - 10))
sheet.fill((90, 90, 90))
for i, f in enumerate(files):
    sheet.blit(pygame.image.load(f), ((i % cols) * 810, (i // cols) * 490))
pygame.image.save(sheet, out)
