"""System metrics collection via psutil."""

from __future__ import annotations

import platform
import socket
import time

import psutil


class MetricsCollector:
    """Collects snapshots, network rates and a cached top-process list."""

    def __init__(self, proc_ttl: float = 3.0) -> None:
        self._last_net = psutil.net_io_counters()
        self._last_t = time.monotonic()
        self.proc_ttl = proc_ttl
        self._procs: list[dict] = []
        self._procs_t = 0.0
        psutil.cpu_percent(percpu=True)
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except (psutil.Error, OSError):
                pass

    def _net_rates(self) -> tuple[float, float]:
        now = time.monotonic()
        net = psutil.net_io_counters()
        dt = max(now - self._last_t, 1e-3)
        up = (net.bytes_sent - self._last_net.bytes_sent) / dt
        down = (net.bytes_recv - self._last_net.bytes_recv) / dt
        self._last_net, self._last_t = net, now
        return max(up, 0.0), max(down, 0.0)

    @staticmethod
    def _scan_processes(n: int = 8) -> list[dict]:
        procs = []
        ncpu = psutil.cpu_count() or 1
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                if p.info["pid"] == 0:
                    continue
                cpu = p.cpu_percent(None)
                mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
                procs.append(
                    {
                        "pid": p.info["pid"],
                        "name": p.info["name"] or "?",
                        "cpu": round(cpu / ncpu, 1),
                        "mem_mb": round(mem / 1048576, 1),
                    }
                )
            except (psutil.Error, OSError):
                continue
        procs.sort(key=lambda x: (x["cpu"], x["mem_mb"]), reverse=True)
        return procs[:n]

    def top_processes(self, force: bool = False) -> list[dict]:
        """Top 8 processes, rescanned at most every ``proc_ttl`` seconds."""
        now = time.monotonic()
        if force or not self._procs or now - self._procs_t >= self.proc_ttl:
            self._procs, self._procs_t = self._scan_processes(), now
        return self._procs

    @staticmethod
    def system_info() -> dict:
        vm = psutil.virtual_memory()
        boot = psutil.boot_time()
        cpu_model = platform.processor() or platform.machine()
        return {
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "os_version": platform.version(),
            "cpu_model": cpu_model,
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(),
            "ram_total_gb": round(vm.total / 1e9, 2),
            "boot_time": boot,
            "uptime_s": round(time.time() - boot),
        }

    def snapshot(self) -> dict:
        cores = psutil.cpu_percent(percpu=True)
        vm = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage("C:\\" if psutil.WINDOWS else "/")
        except OSError:
            disk = psutil.disk_usage("/")
        up, down = self._net_rates()
        return {
            "ts": time.time(),
            "cpu": round(sum(cores) / max(len(cores), 1), 1),
            "cores": [round(c, 1) for c in cores],
            "ram": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / 1e9, 2),
            "ram_total_gb": round(vm.total / 1e9, 2),
            "disk": round(disk.percent, 1),
            "net_up": round(up, 1),
            "net_down": round(down, 1),
            "processes": self.top_processes(),
        }
