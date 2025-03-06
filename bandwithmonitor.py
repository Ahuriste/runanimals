import asyncio


class BandwithMonitor:

    def __init__(self, cmd=["vnstat", "-l"], max_bps=10**8):
        self.cmd = cmd
        self.process = None
        self.last_output = None
        self.dico_units = {
            'bit/s': 1,
            'kbit/s': 1000,
            'Mbit/s': 10**6,
            'gbit/s': 10**9
        }
        self.max_bps = max_bps

    async def run(self):
        """Run the command and capture dynamic output."""
        self.process = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Read stdout in chunks
        assert self.process.stdout is not None  # for type checker
        while True:
            line = await self.process.stdout.read(
                1024)  # Adjust buffer size if needed
            if not line:
                break
            self.last_output = line.decode().strip()
            #print(self.last_output, end="\r")  # Simulate dynamic updating

        await self.process.wait()

    def decode(self, output):
        if not output:
            return 0
        elif 'rx' in output:
            line = (output.split(" "))
            line = [c for c in line if c]
            tx, rx = self.float_(
                line[2]) * self.dico_units[line[3]], self.float_(
                    line[7]) * self.dico_units[line[8]]
            return (tx + rx)
        else:
            return 0

    def get_last_output(self):
        """Get the latest dynamic output."""
        return self.decode(self.last_output)

    def float_(self, s):
        return float(s.replace(",", "."))






async def main():
    runner = BandwithMonitor()

    # Run the command asynchronously
    asyncio.create_task(runner.run())

    # Example of accessing the latest output periodically
    while True:
        await asyncio.sleep(0.5)
        with open("/home/remi/.config/waybar/modules/runcat-text/bw.log","w") as f:
            f.write(str(runner.get_last_output()))

asyncio.run(main())
