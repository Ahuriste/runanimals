#!/usr/bin/env python
import random
from math import ceil, lcm
import asyncio
from runners import runners

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
        self.label: str = ""
        self.message: str = ""
        self.__return_type = return_type

    def __str__(self) -> str:
        if self.__return_type == "json":
            return json.dumps(
                {
                    "text": self.text,
                    "alt": self.alt,
                    "tooltip": self.tooltip_format.format(
                        **{"label": self.label, "percentage": self.percentage}
                    ),
                    "class": self.cls,
                    "percentage": self.percentage,
                    "label": self.label,
                }
            )

        return f"{self.text}"

    def __repr__(self) -> str:
        return self.__str__()


class CPU:
    def __init__(
        self,
        interval: float,
        file: str | pathlib.Path,
        states: Dict[str, int],
        animal=None,
    ) -> None:
        self.__update_interval = interval
        self.__file = pathlib.Path(file)
        self.__states = states
        self.state = None
        self.percent: int = 0
        self.num_cores: int = 0
        self.total_a: int = 0
        self.total_b: int = 0
        self.last = None
        self.animal = animal

    async def update_zozo(self):
        while True:
            if not self.last:
                percent = int(100 * random.random())
            else:
                percent = int(
                    min(100, max(10, self.last + (1 - 2 * random.random()) * 4))
                )
            self.percent = percent
            self.last = percent
            out.percentage = self.percent
            self.state = ""
            for key, value in sorted(
                self.__states.items(), key=lambda key_value: key_value[1]
            ):
                if value <= self.percent:
                    self.state = key
            out.cls = self.state
            out.message = "Hohoho"
            out.label = self.animal
            await asyncio.sleep(self.__update_interval)

    async def update_temp(self):
        while True:
            temp_path = "/sys/class/thermal/thermal_zone0/temp"
            raw = pathlib.Path(temp_path).read_text()
            used = round(int(raw) / 1000)
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

    async def update_signal(self):
        while True:
            signal = float(
                open("/home/remi/.config/waybar/modules/runcat-text/bw.log", "r").read()
            )
            self.percent = ceil(20 * min(1, signal / 10**8)) * 5

            out.percentage = self.percent
            self.state = ""
            for key, value in sorted(
                self.__states.items(), key=lambda key_value: key_value[1]
            ):
                if value <= self.percent:
                    self.state = key
            out.cls = self.state

            await asyncio.sleep(self.__update_interval)

    async def update_battery(self):
        while True:
            current_path = "/sys/class/power_supply/BAT1/charge_now"
            full_path = "/sys/class/power_supply/BAT1/charge_full"
            charging_path = "/sys/class/power_supply/ACAD/online"
            current = pathlib.Path(current_path).read_text()
            full = pathlib.Path(full_path).read_text()
            charging = pathlib.Path(charging_path).read_text().strip()
            self.percent = round(int(current) / int(full) * 100)
            out.percentage = self.percent
            if charging == "1":
                out.label = "Charging"
                self.state = "charging"
            else:
                out.label = "Discharging"
                self.state = ""
                for key, value in sorted(
                    self.__states.items(), key=lambda key_value: key_value[1]
                ):
                    if value <= self.percent:
                        self.state = key
            out.cls = self.state

            await asyncio.sleep(self.__update_interval)

    async def update_ram(self):
        while True:
            mem_path = "/proc/meminfo"
            raw = pathlib.Path(mem_path).read_text().splitlines()
            tot = int(raw[0][9:-2].strip())
            av = int(raw[2][14:-2].strip())
            used = int(100 * (1 - av / tot))
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

    async def update_cpu(self):
        while True:
            raw = pathlib.Path(self.__file).read_text()

            lines = raw.splitlines()
            total = sum(map(int, lines[0].split()[1:4]))

            if self.num_cores == 0:
                self.num_cores = (
                    int(
                        list(
                            filter(
                                lambda line: line.startswith("cpu"),
                                lines,
                            )
                        )[-1].split()[0][-1]
                    )
                    + 1
                )

            self.total_a, self.total_b = self.total_b, total
            if self.total_a != 0 and self.total_b != 0:
                self.percent = int(
                    (
                        (self.total_b - self.total_a)
                        / 1.0
                        / ui.SAMPLE_RATE
                        / self.num_cores
                        * 100
                    )
                )
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
            if cpu.percent != -1:
                cat = spinner.next
            else:
                cat = spinner.data[0]
            out.text = cat
            print(out)
            sys.stdout.flush()
            if cpu.percent != 0 and cpu.percent != -1:
                diff = self.FPS_DELTA * cpu.percent
                time = 1 / self.fps_l - diff

                await asyncio.sleep(time)
            else:
                await asyncio.sleep(1)


import argparse

parser = argparse.ArgumentParser(description="Simple runner script")
parser.add_argument("type", type=str, help="Runner type")
args = parser.parse_args()
# load config
if args.type == "zoo":
    cname = "config_zoo.json"
elif args.type == "cpu":
    cname = "config.json"
elif args.type == "ram":
    cname = "config_ram.json"
elif args.type == "temp":
    cname = "config_temp.json"
elif args.type == "eiffel":
    cname = "config_eiffel.json"
elif args.type == "pigeon":
    cname = "config_pigeon.json"
else:
    print(f"Error: Module '{args.type}' not found.")
    cname = "config.json"

config_path = pathlib.Path(__file__).parent.joinpath(cname)
config = dict(json.loads(config_path.read_text()))

user_config_path = pathlib.Path(__file__).parent.joinpath("user_conf.json")
user_config = dict(json.loads(user_config_path.read_text()))
if args.type == "zoo":
    # animal = random.choice(list(runners.keys())[:-2])
    animals = random.sample(
        list(runners.keys())[:-2], config["how_many_animals_in_a_zoo"]
    )
    length = lcm(*[runners[animal][1] - runners[animal][0] for animal in animals])
    icons = [
        "".join(
            [
                chr(runners[animal][0] + i % (runners[animal][1] - runners[animal][0]))
                for animal in animals
            ]
        )
        for i in range(length)
    ]
    animal = ", ".join(animals)
else:
    animal = user_config["animal"][args.type]

    icons = [chr(i) for i in range(runners[animal][0], runners[animal][1])]

if args.type == "eiffel":
    icons.extend(icons[1:-1][::-1])
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
    animal=animal,
)

_ui = config.get("ui")
if _ui is None:
    _ui = {}

ui = UI()
ui.fps_l = int(_ui.get("fps_l", 6))
ui.fps_h = int(_ui.get("fps_h", 90))

# if ui.fps_h < ui.fps_l:
#    raise ValueError("fps_h can't be lower than fps_l")

###

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
if args.type == "cpu":
    task_cpu = loop.create_task(cpu.update_cpu())
elif args.type == "pigeon":
    task_cpu = loop.create_task(cpu.update_signal())
elif args.type == "eiffel":
    task_cpu = loop.create_task(cpu.update_battery())
elif args.type == "ram":
    task_cpu = loop.create_task(cpu.update_ram())
elif args.type == "temp":
    task_cpu = loop.create_task(cpu.update_temp())
elif args.type == "zoo":
    task_cpu = loop.create_task(cpu.update_zozo())

else:
    print(f"Error: Module '{args.type}' not found.")
    sys.exit(1)
task_ui = loop.create_task(ui.update())
loop.run_until_complete(asyncio.gather(task_cpu, task_ui))
