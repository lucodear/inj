from typing import AsyncGenerator, Generator, List

import pytest

from dij import Container
from dij.types import ServiceLifeStyle

from .models import AsyncSession, AsyncUserSvc, Foo, FooInit, FooInitSlot, Session, UserSvc


@pytest.fixture()
def fixture_async_factory() -> List[Container]:
    async def get_bar_async() -> Session:
        return Session()

    container = Container(strict=False)
    container.register_factory(get_bar_async, Session, ServiceLifeStyle.SCOPED)
    container.add_scoped(Foo)
    container.add_scoped(FooInit)
    container.add_scoped(FooInitSlot)
    container.build_provider()
    return [container]


@pytest.fixture()
def fixture_generator_factory() -> List[Container]:
    def get_session() -> Generator[Session, None, None]:
        try:
            with Session() as sess:
                print('connected')
                yield sess
        finally:
            print('disconnected')

    container = Container(strict=False)
    container.register_factory(get_session, Session, ServiceLifeStyle.SCOPED)
    container.add_scoped(UserSvc)
    container.build_provider()
    return [container]


@pytest.fixture()
def fixture_async_generator_factory() -> List[Container]:
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        try:
            async with AsyncSession() as sess:
                print('connected')
                yield sess
        finally:
            print('disconnected')

    container = Container(strict=False)
    container.register_factory(get_session, AsyncSession, ServiceLifeStyle.SCOPED)
    container.add_scoped(AsyncUserSvc)
    container.build_provider()
    return [container]
