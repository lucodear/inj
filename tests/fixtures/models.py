import uuid
from typing import Any

# region async factory models


class Session:
    id: uuid.UUID
    connected: bool

    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def __enter__(self) -> 'Session':
        self.connect()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.disconnect()


class Foo:
    bar: Session

    def get_bar_id(self) -> str:
        return str(self.bar.id)


class FooInit:
    def __init__(self, bar: Session) -> None:
        self.bar = bar

    def get_bar_id(self) -> str:
        return str(self.bar.id)


class FooInitSlot:
    __slots__ = ('bar',)

    def __init__(self, bar: Session) -> None:
        self.bar = bar

    def get_session_id(self) -> str:
        return str(self.bar.id)


# endregion


# region generator factory models


class AsyncSession:
    id: uuid.UUID
    connected: bool

    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def __aenter__(self) -> 'AsyncSession':
        await self.connect()
        return self

    async def __aexit__(self, *_args: Any) -> None:
        await self.disconnect()


class UserSvc:
    session: Session

    def get_session_id(self) -> str:
        return str(self.session.id)


class AsyncUserSvc:
    session: AsyncSession

    def get_session_id(self) -> str:
        return str(self.session.id)


# endregion
