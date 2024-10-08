import inspect
from typing import Any, Callable, Dict, Optional

from .container import Container
from .svc import ActivationScope, Services
from .types import ContainerProtocol, ServiceLifeStyle


def inject(
    globalsns: Optional[Dict[str, Any]] = None, localns: Optional[Dict[str, Any]] = None
) -> Callable[..., Any]:
    """
    Marks a class or a function as injected. This method is only necessary if the class
    uses locals and the user uses Python >= 3.10, to bind the function's locals to the
    factory.
    """
    if localns is None or globalsns is None:
        frame = inspect.currentframe()
        try:
            if localns is None:
                localns = frame.f_back.f_locals  # type: ignore
            if globalsns is None:
                globalsns = frame.f_back.f_globals  # type: ignore
        finally:
            del frame

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        f._locals = localns
        f._globals = globalsns
        return f

    return decorator


__all__ = [
    'Container',
    'ActivationScope',
    'Services',
    'ServiceLifeStyle',
    'ContainerProtocol',
    'inject',
]
