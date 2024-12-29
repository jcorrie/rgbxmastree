from gpiozero import SPIDevice, SourceMixin
from colorzero import Color
from statistics import mean
from pydantic import BaseModel


class LEDValue(BaseModel):
    r: float
    g: float
    b: float

    @staticmethod
    def new_on() -> "LEDValue":
        return LEDValue(r=1, g=1, b=1)

    @staticmethod
    def new_off() -> "LEDValue":
        return LEDValue(r=0, g=0, b=0)


class Pixel:
    def __init__(self, parent, index: int) -> None:
        self.parent = parent
        self.index = index

    @property
    def value(self):
        return self.parent.value[self.index]

    @value.setter
    def value(self, value):
        new_parent_value = list(self.parent.value)
        new_parent_value[self.index] = value
        self.parent.value = tuple(new_parent_value)

    @property
    def color(self):
        return Color(*self.value)

    @color.setter
    def color(self, c: Color):
        r, g, b = c
        self.value = (r, g, b)

    def on(self):
        self.value = (1, 1, 1)

    def off(self):
        self.value = (0, 0, 0)


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
        default_led: LEDValue = LEDValue(r=0, g=0, b=0)
        self._value: list[LEDValue] = [default_led] * pixels
        self._brightness: float = brightness
        self._brightness_bits: int = int(brightness * self.max_brightness)
        self.off()

    def __len__(self):
        return len(self._all)

    def __getitem__(self, index):
        return self._all[index]

    def __iter__(self):
        return iter(self._all)

    @property
    def color(self):
        average_r = mean(pixel.color[0] for pixel in self)
        average_g = mean(pixel.color[1] for pixel in self)
        average_b = mean(pixel.color[2] for pixel in self)
        return Color(average_r, average_g, average_b)

    @color.setter
    def color(self, c: Color) -> None:
        r, g, b = c
        led: LEDValue = LEDValue(r=r, g=g, b=b)
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
    def value(self):
        return self._value

    @value.setter
    def value(self, value: list[LEDValue]) -> None:
        start_of_frame = [0] * 4
        end_of_frame = [0] * 5
        # SSSBBBBB (start, brightness)
        brightness = 0b11100000 | self._brightness_bits
        pixels = [[(255 * int(v)) for v in p] for p in value]
        pixels = [[brightness, b, g, r] for r, g, b in pixels]
        pixels = [i for p in pixels for i in p]
        data = start_of_frame + pixels + end_of_frame
        if self._spi is None:
            raise ValueError("SPI must be opened before setting value")
        self._spi.transfer(data)
        self._value = value

    def on(self) -> None:
        self.value = [LEDValue.new_on()] * len(self)

    def off(self) -> None:
        self.value = [LEDValue.new_off()] * len(self)

    def close(self) -> None:
        super(RGBXmasTree, self).close()


if __name__ == "__main__":
    tree = RGBXmasTree()

    tree.on()
