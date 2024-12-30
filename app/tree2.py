import asyncio
import threading
import time
from typing import List, Tuple
from pydantic import BaseModel, Field

from gpiozero import SPIDevice

MAX_BRIGHTNESS: int = 31

DEFAULT_BRIGHTNESS: float = 0.3


class ColorBrightness(BaseModel):
    """Represents the color and brightness of a light."""

    red: int = Field(..., ge=0, le=255)
    green: int = Field(..., ge=0, le=255)
    blue: int = Field(..., ge=0, le=255)
    brightness: float = Field(..., ge=0.0, le=1.0)

    def as_tuple(self) -> Tuple[int, int, int, float]:
        """Return the color and brightness as a tuple."""
        return self.red, self.green, self.blue, self.brightness


class Light:
    """Represents a single LED in the tree."""

    def __init__(self, id: int):
        self.id = id
        self.state = ColorBrightness(
            red=0, green=0, blue=0, brightness=1.0
        )  # Default state
        self.effect_task: asyncio.Task | None = None

    def set_state(self, color: Tuple[int, int, int], brightness: float) -> None:
        """Set the color and brightness of the light."""
        self.state = ColorBrightness(
            red=color[0], green=color[1], blue=color[2], brightness=brightness
        )

    async def glow(
        self, min_brightness: float, max_brightness: float, duration: float
    ) -> None:
        """Create a glow effect by oscillating brightness asynchronously."""
        while True:
            for b in [
                x / 100
                for x in range(int(min_brightness * 100), int(max_brightness * 100))
            ]:
                self.state.brightness = b
                await asyncio.sleep(duration / 100)
            for b in [
                x / 100
                for x in range(int(max_brightness * 100), int(min_brightness * 100), -1)
            ]:
                self.state.brightness = b
                await asyncio.sleep(duration / 100)

    async def hue(self, colors: List[Tuple[int, int, int]], duration: float) -> None:
        """Create a hue effect by transitioning between colors asynchronously."""
        while True:
            for color in colors:
                self.state.red, self.state.green, self.state.blue = color
                await asyncio.sleep(duration)

    def start_effect(self, effect_coro) -> None:
        """Start an effect coroutine."""
        self.stop_effect()  # Stop any ongoing effect first
        self.effect_task = asyncio.create_task(effect_coro)

    def stop_effect(self) -> None:
        """Stop any ongoing effect."""
        if self.effect_task:
            self.effect_task.cancel()
            self.effect_task = None

    def get_state(self) -> ColorBrightness:
        """Get the current state of the light."""
        return self.state

    def off(self) -> None:
        self.state = ColorBrightness(red=0, green=0, blue=0, brightness=0.0)


class LEDValue256(BaseModel):
    red: int
    green: int
    blue: int
    brightness: int | None = None

    @staticmethod
    def from_base(value: Light) -> "LEDValue256":
        state: ColorBrightness = value.get_state()

        brightness: int = 0b11100000 | int(state.brightness * MAX_BRIGHTNESS)
        return LEDValue256(
            red=int(state.red * 255),
            green=int(state.green * 255),
            blue=int(state.blue * 255),
            brightness=brightness,
        )

    @staticmethod
    def from_color_brightness(value: ColorBrightness) -> "LEDValue256":
        brightness: int = 0b11100000 | int(value.brightness * MAX_BRIGHTNESS)
        return LEDValue256(
            red=value.red,
            green=value.green,
            blue=value.blue,
            brightness=brightness,
        )


class LEDTree(SPIDevice):
    """Represents the LED Christmas tree."""

    def __init__(self, num_lights: int = 24, device_refresh_rate: int = 60):
        super(LEDTree, self).__init__(mosi_pin=12, clock_pin=25)

        self.lights = [Light(i) for i in range(num_lights)]
        self.device_refresh_rate = device_refresh_rate
        self.device_thred = threading.Thread(
            target=self._spi_transfer_loop, daemon=True
        )
        self.device_running = False

    def start_spi(self) -> None:
        """Start the SPI transfer loop."""
        self.device_running = True
        self.device_thred.start()

    def shutdown(self) -> None:
        """Stop the SPI transfer loop."""
        self.lights_off()

        # Pause for 0.2 seconds to ensure the last frame is displayed
        time.sleep(0.2)

        self.device_running = False
        self.device_thred.join()

    def _spi_transfer_loop(self) -> None:
        """Run the SPI transfer loop."""
        while self.device_running:
            snapshot = self.get_tree_state()  # Take a snapshot of the current state
            self.spi_transfer(snapshot)
            time.sleep(1 / self.device_refresh_rate)

    def spi_transfer(self, snapshot: List[ColorBrightness]) -> None:
        """Transfer the current tree state via SPI (placeholder)."""

        start_of_frame = [0] * 4
        end_of_frame = [0] * 5
        pixels: list[LEDValue256] = [
            LEDValue256.from_color_brightness(value=v) for i, v in enumerate(snapshot)
        ]
        flattened_pixels: list[int] = [
            i for p in pixels for i in (p.brightness or 0, p.blue, p.green, p.red)
        ]

        data: list[int] = start_of_frame + flattened_pixels + end_of_frame
        if self._spi is None:
            raise ValueError("SPI must be opened before setting value")
        self._spi.transfer(data)

    def set_light(
        self, light_id: int, color: Tuple[int, int, int], brightness: float
    ) -> None:
        """Set the color and brightness of a specific light."""
        self._get_light(light_id).set_state(color, brightness)

    def set_all_lights(self, color: Tuple[int, int, int], brightness: float) -> None:
        """Set the color and brightness for all lights."""
        for light in self.lights:
            light.set_state(color, brightness)

    async def start_glow_effect(
        self,
        light_id: int,
        min_brightness: float,
        max_brightness: float,
        duration: float,
    ) -> None:
        """Start a glow effect on a specific light."""
        light = self._get_light(light_id)
        light.start_effect(light.glow(min_brightness, max_brightness, duration))

    async def start_hue_effect(
        self, light_id: int, colors: List[Tuple[int, int, int]], duration: float
    ) -> None:
        """Start a hue effect on a specific light."""
        light = self._get_light(light_id)
        light.start_effect(light.hue(colors, duration))

    def stop_light_effect(self, light_id: int) -> None:
        """Stop any effect running on a specific light."""
        self._get_light(light_id).stop_effect()

    def get_tree_state(self) -> List[ColorBrightness]:
        """Get the current state of all lights."""
        return [light.get_state() for light in self.lights]

    def _get_light(self, light_id: int) -> Light:
        """Retrieve a light by its ID."""
        if 0 <= light_id < len(self.lights):
            return self.lights[light_id]
        raise ValueError(
            f"Light ID {light_id} is out of range (0-{len(self.lights) - 1})."
        )

    def lights_off(self) -> None:
        """
        Turn off all lights.
        """
        for light in self.lights:
            light.off()


# Example Usage
async def main():
    tree = LEDTree()

    # Set specific light

    # Set all lights
    tree.set_all_lights((0, 255, 0), 0.8)  # Green at 80% brightness
    tree.set_light(3, (255, 0, 0), 0.5)  # Red at 50% brightness

    # Start effects
    await tree.start_glow_effect(
        3, min_brightness=0.2, max_brightness=1.0, duration=0.5
    )
    await tree.start_hue_effect(
        2, colors=[(255, 0, 0), (0, 255, 0), (0, 0, 255)], duration=1.0
    )

    # Start SPI transfer
    tree.start_spi()

    # Run for 10 seconds
    await asyncio.sleep(5)

    # Stop effects and SPI
    tree.stop_light_effect(1)
    tree.stop_light_effect(2)
    tree.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
