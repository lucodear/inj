import inspect
from typing import Any, Awaitable, Callable, Type

from dij.svc import ActivationScope


class AsyncFactoryTypeProvider:
    __slots__ = ('_type', 'factory', '__dij_async__')

    def __init__(self, _type: Type, factory: Callable[[ActivationScope, Type], Awaitable[Any]]):
        self._type = _type
        self.factory = factory
        self.__dij_async__ = True

    async def __call__(self, context: ActivationScope, parent_type: Type) -> Any:
        if not isinstance(context, ActivationScope):
            raise TypeError(f'Expected ActivationScope, got {type(context)}')

        instance = await self.factory(context, parent_type)
        return await maybe_solve_async_generator(instance)


class AsyncScopedFactoryTypeProvider:
    __slots__ = ('_type', 'factory', '__dij_async__')

    def __init__(self, _type: Type, factory: Callable[[ActivationScope, Type], Awaitable[Any]]):
        self._type = _type
        self.factory = factory
        self.__dij_async__ = True

    async def __call__(self, context: ActivationScope, parent_type: Type) -> Any:
        if context.scoped_services is None:
            raise ValueError('Scoped services are not available')

        if self._type in context.scoped_services:
            return context.scoped_services[self._type]

        instance = await self.factory(context, parent_type)
        context.scoped_services[self._type] = instance
        return await maybe_solve_async_generator(instance)


class AsyncSingletonFactoryTypeProvider:
    __slots__ = ('_type', 'factory', 'instance', '__dij_async__')

    def __init__(self, _type: Type, factory: Callable[[ActivationScope, Type], Awaitable[Any]]):
        self._type = _type
        self.factory = factory
        self.instance = None
        self.__dij_async__ = True

    async def __call__(self, context: ActivationScope, parent_type: Type) -> Any:
        if self.instance is None:
            self.instance = await self.factory(context, parent_type)
        return await maybe_solve_async_generator(self.instance)


async def maybe_solve_async_generator(instance: Any) -> Any:
    """
    Check if the instance is a generator and if so, resolve it to the first value and return it.
    If it's not a generator, return the instance as is.
    """

    if inspect.isasyncgen(instance):
        return await instance.__anext__()
    return instance
