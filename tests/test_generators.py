import pytest

from .fixtures.models import AsyncSession, AsyncUserSvc, Session, UserSvc


def test_generator_factory(fixture_generator_factory):
    """should resolve dependency created by a generator function as a factory"""
    [container] = fixture_generator_factory

    svc = container.resolve(UserSvc)
    assert isinstance(svc, UserSvc)
    assert isinstance(svc.session, Session)


@pytest.mark.asyncio
async def test_async_factory_imported_in_init_method_using_slots(fixture_async_generator_factory):
    """
    should resolve dependency created by an async factory when it's declar in the __init__ method
    of the dependant service using __slots__
    """
    [container] = fixture_async_generator_factory

    svc = await container.aresolve(AsyncUserSvc)

    assert isinstance(svc, AsyncUserSvc)
    assert isinstance(svc.session, AsyncSession)
