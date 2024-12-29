from gpiozero import SPIDevice, SourceMixin
from colorzero import Color
from statistics import mean
from pydantic import BaseModel

from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from app.tree import RGBXmasTree


class LEDValueBase(BaseModel):
    red: float
    green: float
    blue: float

    @staticmethod
    def new_on() -> "LEDValueBase":
        return LEDValueBase(red=1, green=1, blue=1)

    @staticmethod
    def new_off() -> "LEDValueBase":
        return LEDValueBase(red=0, green=0, blue=0)


class LEDValueBase256(BaseModel):
    red: int
    green: int
    blue: int
    brightness: int | None = None

    @staticmethod
    def from_base1(
        value: LEDValueBase, brightness: int | None = None
    ) -> "LEDValueBase256":
        return LEDValueBase256(
            red=int(value.red * 255),
            green=int(value.green * 255),
            blue=int(value.blue * 255),
            brightness=brightness,
        )


class Pixel:
    def __init__(self, parent: RGBXmasTree, index: int) -> None:
        self.parent: RGBXmasTree = parent
        self.index: int = index

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


class RGBXmasTree(SourceMixin, SPIDevice):
    def __init__(
        self,
        pixels: int = 25,
        brightness: float = 0.5,
        mosi_pin: int = 12,
        clock_pin: int = 25,
        *args,
        **kwargs,
    ) -> None:
        super(RGBXmasTree, self).__init__(
            mosi_pin=mosi_pin, clock_pin=clock_pin, *args, **kwargs
        )

        self._all: list[Pixel] = [Pixel(parent=self, index=i) for i in range(pixels)]
        self.max_brightness: int = 31
        default_led: LEDValueBase = LEDValueBase(red=0, green=0, blue=0)
        self._value: list[LEDValueBase] = [default_led] * pixels
        self._brightness: float = brightness
        self._brightness_bits: int = int(brightness * self.max_brightness)
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
        led: LEDValueBase = LEDValueBase(red=r, green=g, blue=b)
        self.value = [led] * len(self)

    @property
    def star(self) -> Pixel:
        return self[3]

    @property
    def brightness(self) -> float:
        return self._brightness

    @brightness.setter
    def brightness(self, brightness: float) -> None:
        max_brightness = self.max_brightness
        self._brightness_bits = int(brightness * max_brightness)
        self._brightness = brightness
        self.value = self.value

    @property
    def value(self) -> list[LEDValueBase]:
        return self._value

    @value.setter
    def value(self, value: list[LEDValueBase]) -> None:
        start_of_frame = [0] * 4
        end_of_frame = [0] * 5
        # SSSBBBBB (start, brightness)
        brightness = 0b11100000 | self._brightness_bits
        pixels: list[LEDValueBase256] = [
            LEDValueBase256.from_base1(value=v, brightness=brightness) for v in value
        ]
        flattened_pixels: list[int] = [
            i for p in pixels for i in p.model_dump().values()
        ]
        data = start_of_frame + flattened_pixels + end_of_frame
        if self._spi is None:
            raise ValueError("SPI must be opened before setting value")
        self._spi.transfer(data)
        self._value = value

    def on(self) -> None:
        self.value = [LEDValueBase.new_on()] * len(self)

    def off(self) -> None:
        self.value = [LEDValueBase.new_off()] * len(self)

    def close(self) -> None:
        super(RGBXmasTree, self).close()


if __name__ == "__main__":
    tree = RGBXmasTree()

    tree.on()
