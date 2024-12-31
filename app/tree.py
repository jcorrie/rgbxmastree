import asyncio
import threading
import time
from typing import List, Tuple
from colorzero import Color, RGB
import random
from pydantic import BaseModel, Field

from gpiozero import SPIDevice

MAX_BRIGHTNESS: int = 31

DEFAULT_BRIGHTNESS: float = 0.1


class ColorBrightness(BaseModel):
    """Represents the color and brightness of a light."""

    red: int = Field(..., ge=0, le=255)
    green: int = Field(..., ge=0, le=255)
    blue: int = Field(..., ge=0, le=255)
    brightness: float = Field(..., ge=0.0, le=1.0)

    @staticmethod
    def from_color(
        color: Color, brightness: float = DEFAULT_BRIGHTNESS
    ) -> "ColorBrightness":
        """Create a ColorBrightness object from a Color object."""
        color_rgb: RGB = color.rgb
        return ColorBrightness(
            red=int(color_rgb[0] * 255),
            green=int(color_rgb[1] * 255),
            blue=int(color_rgb[2] * 255),
            brightness=brightness,
        )


class Light:
    """Represents a single LED in the tree."""

    def __init__(self, id: int):
        self.id = id
        self.state = ColorBrightness(
            red=0, green=0, blue=0, brightness=1.0
        )  # Default state
        self.glow_effect_task: asyncio.Task | None = None
        self.hue_effect_task: asyncio.Task | None = None

    def set_state(self, color: Color, brightness: float) -> None:
        """Set the color and brightness of the light."""
        self.state = ColorBrightness.from_color(color, brightness)

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

    async def hue(self, colors: List[Color], duration: float) -> None:
        """Create a hue effect by transitioning between colors asynchronously."""
        rgb_colors: list[RGB] = [c.rgb for c in colors]
        rgb_colors_ints: list[Tuple[int, int, int]] = [
            (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255)) for c in rgb_colors
        ]
        while True:
            for i in range(len(rgb_colors_ints)):
                start_color = rgb_colors_ints[i]
                end_color = rgb_colors_ints[
                    (i + 1) % len(rgb_colors_ints)
                ]  # Next color in the list (wrap around)

                # Gradually transition from start_color to end_color
                for step in range(100):  # Number of steps for the gradient
                    # Interpolate each RGB component
                    r = int(
                        start_color[0] + (end_color[0] - start_color[0]) * (step / 100)
                    )
                    g = int(
                        start_color[1] + (end_color[1] - start_color[1]) * (step / 100)
                    )
                    b = int(
                        start_color[2] + (end_color[2] - start_color[2]) * (step / 100)
                    )
                    color_brightness = ColorBrightness(
                        red=r, green=g, blue=b, brightness=self.state.brightness
                    )
                    # Set the interpolated color to the tree

                    self.state = color_brightness
                    await asyncio.sleep(duration / 100)

    def start_glow_effect(self, effect_coro) -> None:
        """Start an effect coroutine."""
        self.stop_glow_effect()  # Stop any ongoing effect first
        self.glow_effect_task = asyncio.create_task(effect_coro)

    def stop_glow_effect(self) -> None:
        """Stop any ongoing effect."""
        if self.glow_effect_task:
            self.glow_effect_task.cancel()
            self.glow_effect_task = None

    def start_hue_effect(self, effect_coro) -> None:
        """Start an effect coroutine."""
        self.stop_hue_effect()
        self.glow_effect_task = asyncio.create_task(effect_coro)

    def stop_hue_effect(self) -> None:
        """Stop any ongoing effect."""
        if self.hue_effect_task:
            self.hue_effect_task.cancel()
            self.hue_effect_taskk = None

    def get_state(self) -> ColorBrightness:
        """Get the current state of the light."""
        return self.state

    def off(self) -> None:
        self.state = ColorBrightness(red=0, green=0, blue=0, brightness=0.0)

    def set_as_star(self) -> None:
        color = Color("yellow")
        self.state = ColorBrightness.from_color(color, DEFAULT_BRIGHTNESS)


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

    def __init__(self, num_lights: int = 24, device_refresh_rate: int = 120):
        super(LEDTree, self).__init__(mosi_pin=12, clock_pin=25)

        self.lights = [Light(i) for i in range(num_lights)]
        self.device_refresh_rate = device_refresh_rate
        self.device_thread = threading.Thread(
            target=self._spi_transfer_loop, daemon=True
        )
        self.device_running = False
        self.implement_star: bool = True
        self.star: Light = self.lights[3]

        self.set_default_state()

        self.start_spi()

    def set_default_state(self) -> None:
        # Set the default state of the tree
        self.set_all_lights(Color("green"), DEFAULT_BRIGHTNESS)
        if self.implement_star:
            self.star.set_as_star()

    def start_spi(self) -> None:
        """Start the SPI transfer loop."""
        self.device_running = True
        self.device_thread.start()

    def shutdown(self) -> None:
        """Stop the SPI transfer loop."""
        self.lights_off()

        # Pause for 0.2 seconds to ensure the last frame is displayed
        time.sleep(0.2)

        self.device_running = False
        self.device_thread.join()

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

    def set_light(self, light_id: int, color: Color, brightness: float) -> None:
        """Set the color and brightness of a specific light."""
        self._get_light(light_id).set_state(color, brightness)

    def set_all_lights(self, color: Color, brightness: float) -> None:
        """Set the color and brightness for all lights."""
        for light in self.lights:
            if light.id != 3 or not self.implement_star:
                light.set_state(color, brightness)

    async def start_glow_effect(
        self,
        min_brightness: float,
        max_brightness: float,
        duration: float,
        light_id: int | None = None,
        offset_ms: int | None = None,
        offset_is_randomised: bool = False,
    ) -> None:
        """Start a glow effect on a specific light."""
        if light_id is None:
            for light in self.lights:
                if light.id != 3 or not self.implement_star:
                    light.start_glow_effect(
                        light.glow(min_brightness, max_brightness, duration)
                    )
                    if offset_ms:
                        if offset_is_randomised:
                            randomised_offset = random.randint(0, offset_ms)
                            await asyncio.sleep(randomised_offset / 1000)
                        else:
                            await asyncio.sleep(offset_ms / 1000)
        else:
            light = self._get_light(light_id)
            light.start_glow_effect(
                light.glow(min_brightness, max_brightness, duration)
            )

    async def start_hue_effect(
        self,
        colors: List[Color],
        duration: float,
        light_id: int | None = None,
        offset_ms: int | None = None,
        offset_is_randomised: bool = False,
    ) -> None:
        """Start a hue effect on a specific light."""
        if light_id is None:
            for light in self.lights:
                if light.id != 3 or not self.implement_star:
                    light.start_hue_effect(light.hue(colors, duration))
                    if offset_ms:
                        if offset_is_randomised:
                            randomised_offset = random.randint(0, offset_ms)
                            await asyncio.sleep(randomised_offset / 1000)
                        else:
                            await asyncio.sleep(offset_ms / 1000)
        else:
            light = self._get_light(light_id)
            light.start_hue_effect(light.hue(colors, duration))

    def stop_light_effect(self, light_id: int) -> None:
        """Stop any effect running on a specific light."""
        self._get_light(light_id).stop_glow_effect()
        self._get_light(light_id).stop_hue_effect()

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
