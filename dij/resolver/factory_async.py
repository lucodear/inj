import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Type

from dij.svc import ActivationScope


# parameterless decorator
def async_lru_cache_decorator(async_function: Callable) -> Callable:
    @functools.lru_cache
    def cached_async_function(*args: Any, **kwargs: Any) -> Any:
        coroutine = async_function(*args, **kwargs)
        return asyncio.ensure_future(coroutine)

    return cached_async_function


# decorator with options
def async_lru_cache(*lru_cache_args: Any, **lru_cache_kwargs: Any) -> Callable:
    def async_lru_cache_decorator(async_function: Callable) -> Callable:
        @functools.lru_cache(*lru_cache_args, **lru_cache_kwargs)
        def cached_async_function(*args: Any, **kwargs: Any) -> Any:
            coroutine = async_function(*args, **kwargs)
            res = asyncio.ensure_future(coroutine)
            return res

        return cached_async_function

    return async_lru_cache_decorator


class AsyncFactoryTypeProvider:
    __slots__ = ('_type', 'factory', '__dij_async__')

    def __init__(self, _type: Type, factory: Callable[[ActivationScope, Type], Awaitable[Any]]):
        self._type = _type
        self.factory = factory
        self.__dij_async__ = True

    @async_lru_cache()
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

    @async_lru_cache()
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

    @async_lru_cache()
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
