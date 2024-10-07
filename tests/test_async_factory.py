import pytest

from dij.exception import AsyncDependencyError

from .fixtures.models import Bar, Foo, FooInit, FooInitSlot


@pytest.mark.asyncio
async def test_async_factory(fixture_async_factory):
    """should resolve dependency created by an async factory"""
    [container] = fixture_async_factory

    sess = await container.aresolve(Bar)
    assert isinstance(sess, Bar)


def test_fail_if_trying_to_resolve_async_factory_syncly(fixture_async_factory):
    """should fail if trying to resolve it synchronously"""
    [container] = fixture_async_factory

    with pytest.raises(AsyncDependencyError):
        container.resolve(Bar)


@pytest.mark.asyncio
async def test_async_factory_as_dependency_of_another_service(fixture_async_factory):
    """
    should resolve service that has a dependency on another dependency created by an async factory
    """

    [container] = fixture_async_factory

    svc = await container.aresolve(Foo)

    assert isinstance(svc, Foo)
    assert isinstance(svc.bar, Bar)

    id = svc.get_bar_id()
    assert isinstance(id, str)


def test_fail_if_trying_to_resolve_async_factory_as_dependency_of_another_service_syncly(
    fixture_async_factory,
):
    """
    should fail if trying to resolve service that has a dependency on another dependency created by
    an async factory, using the synchronous resolve method
    """

    [container] = fixture_async_factory

    with pytest.raises(AsyncDependencyError):
        container.resolve(Foo)


@pytest.mark.asyncio
async def test_async_factory_imported_in_init_method(fixture_async_factory):
    """
    should resolve dependency created by an async factory when it's declar in the __init__ method
    of the dependant service
    """
    [container] = fixture_async_factory

    svc = await container.aresolve(FooInit)

    assert isinstance(svc, FooInit)
    assert isinstance(svc.bar, Bar)


@pytest.mark.asyncio
async def test_async_factory_imported_in_init_method_using_slots(fixture_async_factory):
    """
    should resolve dependency created by an async factory when it's declar in the __init__ method
    of the dependant service using __slots__
    """
    [container] = fixture_async_factory

    svc = await container.aresolve(FooInitSlot)

    assert isinstance(svc, FooInitSlot)
    assert isinstance(svc.bar, Bar)
