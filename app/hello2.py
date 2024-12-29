from app.tree import RGBXmasTree
import random
from colorzero import Color

tree = RGBXmasTree()

def random_color():
    r = random.random()
    g = random.random()
    b = random.random()
    return (r, g, b)

try:
    while True:
        tree.star.color = Color("yellow")
        pixel = random.choice(tree)
        if pixel != tree.star:  # Skip the star
            pixel.color = random_color()
except KeyboardInterrupt:
    tree.off()
    tree.close()