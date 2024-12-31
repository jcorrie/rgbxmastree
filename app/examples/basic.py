from app.tree import LEDTree
from colorzero import Color
import asyncio


async def main():
    tree = LEDTree()


    await tree.start_glow_effect(
        min_brightness=0.1, max_brightness=0.5, duration=3, light_id=3
    )
    await tree.start_hue_effect(
        colors=[Color("gold"), Color("orange")], duration=4, light_id=3
    )


    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        tree.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
