import time
from contextlib import contextmanager
from typing import Generator

GREEN = '\033[92m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
DIM = '\033[2m'
R = '\033[0m'


def log(message: str, description: str = '') -> None:
    print(f'{MAGENTA}{description}{R} {DIM}»{R} {GREEN}{message}{R}')


@contextmanager
def time_it(desc: str = '') -> Generator[None, None, None]:
    start_time = time.perf_counter()  # High-precision start time
    try:
        yield
    finally:
        end_time = time.perf_counter()  # High-precision end time
        elapsed_time = end_time - start_time
        if elapsed_time >= 1:
            log(f'Execution time: {elapsed_time:.6f}s', desc)
        else:
            log(f'Execution time: {elapsed_time * 1e3:.3f}ms', desc)
