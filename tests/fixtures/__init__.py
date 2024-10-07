from typing import List

import pytest

from dij import Container
from dij.types import ServiceLifeStyle

from .models import Bar, Foo, FooInit, FooInitSlot


@pytest.fixture()
def fixture_async_factory() -> List[Container]:
    async def get_bar_async() -> Bar:
        return Bar()

    container = Container(strict=False)
    container.register_factory(get_bar_async, Bar, ServiceLifeStyle.SCOPED)
    container.add_scoped(Foo)
    container.add_scoped(FooInit)
    container.add_scoped(FooInitSlot)
    container.build_provider()
    return [container]
