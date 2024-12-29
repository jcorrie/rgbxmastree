from app.tree import RGBXmasTree
from colorzero import Color
from time import sleep

tree = RGBXmasTree()

colors = [Color('red'), Color('green'), Color('blue')]  # Add more colors if desired

try:
    while True:
        for i in range(len(colors)):
            start_color = colors[i]
            end_color = colors[(i + 1) % len(colors)]  # Next color in the list (wrap around)
            
            # Gradually transition from start_color to end_color
            for step in range(100):  # Number of steps for the gradient
                # Interpolate each RGB component
                r = start_color.red + (end_color.red - start_color.red) * (step / 100)
                g = start_color.green + (end_color.green - start_color.green) * (step / 100)
                b = start_color.blue + (end_color.blue - start_color.blue) * (step / 100)
                
                # Set the interpolated color to the tree
                tree.color = Color(r, g, b)
                sleep(0.1)  # Adjust for desired smoothness (smaller = smoother)
except KeyboardInterrupt:
    tree.off()
    tree.close()
