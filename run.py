import multiprocessing
import os

from granian import Granian
from granian.constants import Interfaces


def main():
    workers = int(os.getenv("WORKERS", min(multiprocessing.cpu_count(), 4)))
    server = Granian(
        target="app:app",
        address="0.0.0.0",
        port=9999,
        interface=Interfaces.ASGI,
        workers=workers,
        workers_kill_timeout=5,
        reload=False,
    )
    server.serve()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        ...
