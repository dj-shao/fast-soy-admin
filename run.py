import multiprocessing
import os

from granian import Granian
from granian.constants import Interfaces
from granian.log import LogLevels


def main():
    workers = int(os.getenv("WORKERS", min(multiprocessing.cpu_count(), 4)))
    server = Granian(
        target="app:app",
        address="0.0.0.0",
        port=9999,
        workers=workers,
        reload=False,
        interface=Interfaces.ASGI,
        log_level=LogLevels.info,
        # ── Worker 健壮性 ──
        respawn_failed_workers=True,  # worker 崩溃后自动重启
        respawn_interval=3.5,  # 重启间隔(秒)，避免雪崩式重启
        workers_kill_timeout=30,  # worker 卡死超过 30 秒强制 kill
        # ── 内存保护 ──
        workers_lifetime=3600 * 4,  # 每 4 小时自动回收 worker（防内存泄漏）
        workers_max_rss=512,  # 单 worker RSS 超过 512MB 自动重启
        # ── 背压控制 ──
        backpressure=64,  # 单 worker 最大并发请求数，超过则拒绝新连接
        backlog=1024,  # TCP 连接队列长度
    )
    server.serve()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        ...
