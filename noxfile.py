from nox_poetry import Session, session


@session(
    python=[
        '3.13',
        '3.12',
        '3.11',
        '3.10',
        '3.9',
    ]
)
def tests(session: Session) -> None:
    session.install(
        '.',
        'pytest',
        'pytest-asyncio',
    )

    params = ['tests/']

    session.run('pytest', *params)
