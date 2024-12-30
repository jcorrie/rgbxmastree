from gpiozero import SPIDevice
from colorzero import Color
import random
from statistics import mean
from pydantic import BaseModel

from typing import Iterator

MAX_BRIGHTNESS: int = 31

DEFAULT_BRIGHTNESS: float = 0.3


def random_color():
    r = random.random()
    g = random.random()
    b = random.random()
    return (r, g, b)


class LEDValueBase(BaseModel):
    """
    Base class for LED values.
    Brightness is a float between 0 and 1.
    """

    red: float
    green: float
    blue: float
    brightness: float | None = None

    @staticmethod
    def new_on(brightness: int | None = None) -> "LEDValueBase":
        return LEDValueBase(red=1, green=1, blue=1, brightness=brightness)

    @staticmethod
    def new_off() -> "LEDValueBase":
        return LEDValueBase(red=0, green=0, blue=0)

    @staticmethod
    def new_from_hex(hex: str, brightness: float | None = None) -> "LEDValueBase":
        r: int = int(hex[1:3], 16)
        g: int = int(hex[3:5], 16)
        b: int = int(hex[5:7], 16)
        return LEDValueBase(
            red=r / 255, green=g / 255, blue=b / 255, brightness=brightness
        )


class LEDValue256(BaseModel):
    """
    Class for LED values in 256-bit format.
    """

    red: int
    green: int
    blue: int
    brightness: int | None = None

    @staticmethod
    def from_base(value: LEDValueBase) -> "LEDValue256":
        if value.brightness is None:
            brightness = 0b11100000 | int(DEFAULT_BRIGHTNESS * MAX_BRIGHTNESS)
        else:
            brightness: int = 0b11100000 | int(value.brightness * MAX_BRIGHTNESS)
        return LEDValue256(
            red=int(value.red * 255),
            green=int(value.green * 255),
            blue=int(value.blue * 255),
            brightness=brightness,
        )


class Pixel:
    def __init__(self, parent: "RGBXmasTree", index: int) -> None:
        self.parent: RGBXmasTree = parent
        self.index: int = index
        self.glowing_up: bool = True

    @property
    def value(self) -> LEDValueBase:
        return self.parent.value[self.index]

    @value.setter
    def value(self, value: LEDValueBase) -> None:
        new_parent_value: list[LEDValueBase] = self.parent.value.copy()
        new_parent_value[self.index] = value
        self.parent.value = new_parent_value

    @property
    def color(self) -> Color:
        value: LEDValueBase = self.value
        return Color(value.red, value.green, value.blue)

    @color.setter
    def color(self, c: Color) -> None:
        r, g, b = c
        self.value = LEDValueBase(red=r, green=g, blue=b)

    def on(self) -> None:
        self.value = LEDValueBase.new_on()

    def off(self) -> None:
        self.value = LEDValueBase.new_off()

    def glow_next_value(
        self,
        max_brightness: float = 0.7,
        min_brightness: float = 0.2,
        rate_of_change: float = 0.08,
    ) -> float:
        """
        Get next brightness, dimming from 0 to base_brightness.
        """

        if self.glowing_up and self.value.brightness is not None:
            new_brightness = self.value.brightness + rate_of_change
            if new_brightness >= max_brightness:
                self.glowing_up = False
        elif self.value.brightness is not None:
            new_brightness = self.value.brightness - rate_of_change
            if new_brightness <= min_brightness:
                self.glowing_up = True
        else:
            new_brightness = min_brightness
        return new_brightness


class RGBXmasTree(SPIDevice):
    def __init__(
        self,
        pixels: int = 25,
        brightness: float = DEFAULT_BRIGHTNESS,
        mosi_pin: int = 12,
        clock_pin: int = 25,
        seperate_star: bool = True,
        *args,
        **kwargs,
    ) -> None:
        super(RGBXmasTree, self).__init__(
            mosi_pin=mosi_pin, clock_pin=clock_pin, *args, **kwargs
        )

        self._all: list[Pixel] = [Pixel(parent=self, index=i) for i in range(pixels)]
        self.max_brightness: int = MAX_BRIGHTNESS
        default_led: LEDValueBase = LEDValueBase(red=0, green=0, blue=0)
        self._value: list[LEDValueBase] = [default_led] * pixels
        self._brightness: float = brightness
        self._brightness_bits: int = int(brightness * self.max_brightness)
        self._seperate_star: bool = seperate_star

        self.off()

    def __len__(self) -> int:
        return len(self._all)

    def __getitem__(self, index) -> Pixel:
        return self._all[index]

    def __iter__(self) -> Iterator[Pixel]:
        return iter(self._all)

    @property
    def color(self) -> Color:
        average_r: float = mean(pixel.color.red for pixel in self)
        average_g: float = mean(pixel.color.green for pixel in self)
        average_b: float = mean(pixel.color.blue for pixel in self)
        return Color(average_r, average_g, average_b)

    @color.setter
    def color(self, c: Color) -> None:
        r, g, b = c
        leds: list[LEDValueBase] = [
            LEDValueBase(red=r, green=g, blue=b) for _ in range(len(self))
        ]
        star_next_brightness: float = self.star.glow_next_value(max_brightness=0.8)
        star: LEDValueBase = LEDValueBase.new_from_hex(
            "#FFD700", brightness=star_next_brightness
        )
        if self._seperate_star:
            leds[3] = star
        self.value = leds

    @property
    def star(self) -> Pixel:
        return self[3]

    @property
    def value(self) -> list[LEDValueBase]:
        return self._value

    @value.setter
    def value(self, value: list[LEDValueBase]) -> None:
        self._value = value
        start_of_frame = [0] * 4
        end_of_frame = [0] * 5
        pixels: list[LEDValue256] = [
            LEDValue256.from_base(value=v) for i, v in enumerate(value)
        ]
        flattened_pixels: list[int] = [
            i for p in pixels for i in (p.brightness or 0, p.blue, p.green, p.red)
        ]

        data = start_of_frame + flattened_pixels + end_of_frame
        print(data)
        if self._spi is None:
            raise ValueError("SPI must be opened before setting value")
        self._spi.transfer(data)

    def on(self) -> None:
        self.value = [LEDValueBase.new_off()] * len(self)

    def off(self) -> None:
        self.value = [LEDValueBase.new_off()] * len(self)

    def close(self) -> None:
        super(RGBXmasTree, self).close()


if __name__ == "__main__":
    tree = RGBXmasTree()

    tree.on()
