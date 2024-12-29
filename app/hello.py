from app.tree import RGBXmasTree
import random
from colorzero import Color
import time
import threading

tree = RGBXmasTree()

def setup_star():
    """Set up the star on the tree with a constant yellow color."""
    tree.star.color = Color("yellow")

def random_primary_color():
    """Generate a random primary color (red, green, or blue)."""
    colors = [Color("red"), Color("green"), Color("blue")]
    return random.choice(colors)

def pixel_thread(pixel):
    """Each pixel runs this thread to set its color randomly once."""
    # Set the pixel color to a random primary color once
    pixel.color = random_primary_color()

def tree_thread():
    """Simulate tree brightness increase/decrease."""
    while True:
        if tree.brightness >= tree.max_brightness:
            tree.brightness = 0
        else:
            tree.brightness += 1
        time.sleep(0.1)  # Slow down the brightness change for smooth effect

def start_pixel_threads():
    """Start a thread for each pixel."""
    threads = []
    # Start the tree thread to handle brightness
    thread = threading.Thread(target=tree_thread)
    threads.append(thread)
    thread.start()

    # Start a thread for each pixel to set its color randomly once
    for pixel in tree:
        if pixel != tree.star:  # Skip the star
            thread = threading.Thread(target=pixel_thread, args=(pixel,))
            threads.append(thread)
            thread.start()

    # Optionally join threads if you need to wait for them to finish (but in this case, they run indefinitely)
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    try:
        setup_star()  # Set up the star color
        start_pixel_threads()  # Start the threads for all pixels
    except KeyboardInterrupt:
        tree.off()  # Turn off all lights on Ctrl+C
        tree.close()  # Clean up the tree
