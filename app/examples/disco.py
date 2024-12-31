from app.tree import LEDTree
from colorzero import Color
import asyncio


async def main():
    tree = LEDTree()

    # Start effects
    await tree.start_glow_effect(
        min_brightness=0.2,
        max_brightness=0.45,
        duration=1,
        offset_ms=250,
        offset_is_randomised=True,
    )

    await tree.start_hue_effect(
        colors=[Color("indigo"), Color("hotpink"), Color("red")],
        duration=1.1,
        offset_ms=275,
        offset_is_randomised=True,
    )

    await tree.start_hue_effect(
        colors=[Color("pink"), Color("fuchsia"), Color("midnightblue")], duration=4, light_id=3
    )
    await tree.start_glow_effect(
        min_brightness=0.1, max_brightness=0.6, duration=0.4, light_id=3
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
