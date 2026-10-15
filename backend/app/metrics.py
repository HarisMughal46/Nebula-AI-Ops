"""System metrics collection via psutil."""

from __future__ import annotations

import time

import psutil


class MetricsCollector:
    """Collects snapshots and computes network rates between calls."""

    def __init__(self) -> None:
        self._last_net = psutil.net_io_counters()
        self._last_t = time.monotonic()
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
    def _top_processes(n: int = 5) -> list[dict]:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                cpu = p.cpu_percent(None)
                mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
                if p.info["pid"] == 0:
                    continue
                procs.append(
                    {
                        "pid": p.info["pid"],
                        "name": p.info["name"] or "?",
                        "cpu": round(cpu / psutil.cpu_count(), 1),
                        "mem_mb": round(mem / 1048576, 1),
                    }
                )
            except (psutil.Error, OSError):
                continue
        procs.sort(key=lambda x: (x["cpu"], x["mem_mb"]), reverse=True)
        return procs[:n]

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
            "processes": self._top_processes(),
        }
