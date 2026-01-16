from dataclasses import dataclass


@dataclass(frozen=True)
class Event[T]:
    name: str
    payload: T
