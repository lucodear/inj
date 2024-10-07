from typing import Any

from ..utils import class_name
from .context import ResolutionContext


class InstanceProvider:
    __slots__ = ('instance',)

    def __init__(self, instance: Any):
        self.instance = instance

    def __call__(self, context: ResolutionContext, *_args: Any) -> Any:
        return self.instance


class InstanceResolver:
    __slots__ = ('instance',)

    def __init__(self, instance: Any):
        self.instance = instance

    def __repr__(self) -> str:
        return f'<Singleton {class_name(self.instance.__class__)}>'

    def __call__(self, context: ResolutionContext, *_args: Any) -> Any:
        return InstanceProvider(self.instance)
