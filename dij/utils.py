import inspect
import re
from typing import Any, Awaitable, Callable, Type, Union

try:
    from typing import TypeGuard
except ImportError:  # pragma: no cover
    from typing_extensions import TypeGuard


def class_name(input_type: Union[Type, str]) -> str:
    if isinstance(input_type, str):
        return input_type

    if input_type in {list, set} and str(type(input_type) == "<class 'types.GenericAlias'>"):  # noqa: E721
        # for Python 3.9 list[T], set[T]
        return str(input_type)
    try:
        return input_type.__name__
    except AttributeError:
        # for example, this is the case for List[str], Tuple[str, ...], etc.
        return str(input_type)


_FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
_ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')


def to_standard_param_name(name: str) -> str:
    value = _ALL_CAP_RE.sub(r'\1_\2', _FIRST_CAP_RE.sub(r'\1_\2', name)).lower()
    if value.startswith('i_'):
        return 'i' + value[2:]
    return value


def is_coroutine_fn(fn: Any) -> TypeGuard[Callable[..., Awaitable]]:
    """Check if the given callable is a coroutine function.

    This checks if 'fn' is a coroutine function itself or if it has a
    __call__ method that is a coroutine function.
    """
    # Check if fn is a coroutine function
    if inspect.iscoroutinefunction(fn):
        return True

    # Check if fn has a __call__ method and if that method is a coroutine function
    if hasattr(fn, '__call__'):
        return inspect.iscoroutinefunction(fn.__call__)

    return False


def is_async_dij(obj: Any) -> bool:
    """Check if the given object is an async dij object.

    This checks if 'obj' has a __dij_async__ attribute that is True.
    or if the object is a method, checks if the obj.__func__ has the attribute.
    """
    if inspect.ismethod(obj):
        return hasattr(obj.__func__, '__dij_async__')

    if hasattr(obj, '__dij_async__'):
        return getattr(obj, '__dij_async__')

    return False


def set_async_dij(obj: Any) -> None:
    """Set the __dij_async__ attribute to True on the given object.

    This sets the __dij_async__ attribute to True on the given object.
    """
    if inspect.ismethod(obj):
        setattr(obj.__func__, '__dij_async__', True)
    else:
        setattr(obj, '__dij_async__', True)


def needs_promesify(instance: Any) -> bool:
    """Check if the given object has awaitables that need to be awaited.

    This checks if 'obj' has any awaitables that need to be awaited.
    """
    if hasattr(instance, '__slots__'):
        for attr in instance.__slots__:
            value = getattr(instance, attr)
            if inspect.isawaitable(value):
                return True
    else:
        for _, value in getattr(instance, '__dict__', {}).items():
            if inspect.isawaitable(value):
                return True
    return False


def maybe_promesify_instance(instance: Any) -> Any:
    # check if the instance has any awaitables
    if needs_promesify(instance):

        async def async_factory() -> Any:
            if hasattr(instance, '__slots__'):
                for attr in instance.__slots__:
                    value = getattr(instance, attr)
                    if inspect.isawaitable(value):
                        setattr(instance, attr, await value)
            else:
                for attr, value in instance.__dict__.items():
                    if inspect.isawaitable(value):
                        setattr(instance, attr, await value)
            return instance

        return async_factory

    return instance
