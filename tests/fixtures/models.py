import uuid


class Bar:
    id: uuid.UUID

    def __init__(self) -> None:
        self.id = uuid.uuid4()


class Foo:
    bar: Bar

    def get_bar_id(self) -> str:
        return str(self.bar.id)


class FooInit:
    def __init__(self, bar: Bar) -> None:
        self.bar = bar

    def get_bar_id(self) -> str:
        return str(self.bar.id)


class FooInitSlot:
    __slots__ = ('bar',)

    def __init__(self, bar: Bar) -> None:
        self.bar = bar

    def get_session_id(self) -> str:
        return str(self.bar.id)
