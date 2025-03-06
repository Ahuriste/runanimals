#!/usr/bin/env python
from runners import runners
import asyncio

try:
    import pyjson5 as json
except ImportError:
    import json

import pathlib
import sys
from typing import Dict, Generic, Literal, Sequence, TypeVar

T = TypeVar("T")


class Spinner(Generic[T]):
    def __init__(self, data: Sequence[T]) -> None:
        if len(data) == 0:
            raise ValueError("data has to contain at least one element")

        self.data = data
        self.__current = 0

    @property
    def next(self) -> T:
        item = self.data[self.__current]
        self.__current = (self.__current + 1) % len(self.data)

        return item


class Output:
    def __init__(self, return_type: Literal["json"] | None = None) -> None:
        self.text: str = ""
        self.alt: str = ""
        self.tooltip_format: str = ""
        self.cls: str = ""
        self.percentage: int = 0
        self.__return_type = return_type

    def __str__(self) -> str:
        if self.__return_type == "json":
            return json.dumps(
                {
                    "text": self.text,
                    "alt": self.alt,
                    "tooltip": self.tooltip_format.format(
                        **{"percentage": self.percentage}
                    ),
                    "class": self.cls,
                    "percentage": self.percentage,
                }
            )

        return f"{self.text}"

    def __repr__(self) -> str:
        return self.__str__()


class CPU:
    def __init__(
        self, interval: float, file: str | pathlib.Path, states: Dict[str, int]
    ) -> None:
        self.__update_interval = interval
        self.__file = pathlib.Path(file)
        self.__states = states
        self.state = None
        self.percent: int = 0
        self.num_cores: int = 0
        self.total_a: int = 0
        self.total_b: int = 0

    async def update(self):
        while True:

            temp_path = "/sys/class/thermal/thermal_zone0/temp"
            raw = pathlib.Path(temp_path).read_text()
            used = round(int(raw)/1000)
            self.percent = used
            out.percentage = self.percent
            self.state = ""
            for key, value in sorted(
                self.__states.items(), key=lambda key_value: key_value[1]
            ):
                if value <= self.percent:
                    self.state = key
            out.cls = self.state

            await asyncio.sleep(self.__update_interval)


class UI:
    def __init__(self) -> None:
        self.SAMPLE_RATE = 100
        self.fps_l = 6
        self.fps_h = 90

    @property
    def FPS_DELTA(self) -> float:
        return (1 / self.fps_l - 1 / self.fps_h) / self.SAMPLE_RATE

    async def update(self):
        while True:
            cat = spinner.next
            out.text = cat
            print(out)
            sys.stdout.flush()
            diff = self.FPS_DELTA * cpu.percent
            time = 1 / self.fps_l - diff
            await asyncio.sleep(time)



# load config
config_path = pathlib.Path(__file__).parent.joinpath("config_temp.json")
config = dict(json.loads(config_path.read_text()))

user_config_path = pathlib.Path(__file__).parent.joinpath("user_conf.json")
user_config = dict(json.loads(user_config_path.read_text()))
animal = user_config["animal"]["temp"]
icons = config.get("icons", "")

if isinstance(icons, str):
    icons = list(icons)
icons = list(map(str, icons))
icons = [chr(i) for i in range(runners[animal][0]+2, runners[animal][1]+1)]
spinner = Spinner(icons)

return_type = config.get("return-type")
out = Output(return_type)
out.tooltip_format = config.get("tooltip-format", "")

_cpu = config.get("cpu")
if _cpu is None:
    _cpu = {}
cpu = CPU(
    float(_cpu.get("interval", 1)),
    pathlib.Path(_cpu.get("stat-file", "/proc/stat")),
    _cpu.get("states", {}),
)

_ui = config.get("ui")
if _ui is None:
    _ui = {}

ui = UI()
ui.fps_l = int(_ui.get("fps_l", 6))
ui.fps_h = int(_ui.get("fps_h", 90))

if ui.fps_h < ui.fps_l:
    raise ValueError("fps_h can't be lower than fps_l")

###

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
task_cpu = loop.create_task(cpu.update())
task_ui = loop.create_task(ui.update())
loop.run_until_complete(asyncio.gather(task_cpu, task_ui))
