from app.tree import LEDTree
from colorzero import Color
import asyncio


async def main():
    tree = LEDTree()

    # Start effects
    await tree.start_glow_effect(min_brightness=0.15, max_brightness=0.4, duration=4.6)

    await tree.start_hue_effect(
        colors=[Color("green"), Color("blue"), Color("red")], duration=2.5
    )


    await tree.start_glow_effect(
        min_brightness=0.2, max_brightness=0.5, duration=4.5, light_id=3
    )
    await tree.start_hue_effect(
        colors=[Color("green"), Color("red")], duration=2, light_id=3
    )


    try:
        # Run indefinitely until keyboard interrupt
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        tree.shutdown()



if __name__ == "__main__":
    asyncio.run(main())

