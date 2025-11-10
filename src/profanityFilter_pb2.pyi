from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ExtendProfanityValidationRequest(_message.Message):
    __slots__ = ("value", "userId")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    value: str
    userId: str
    def __init__(self, value: _Optional[str] = ..., userId: _Optional[str] = ...) -> None: ...

class ExtendProfanityValidationResponse(_message.Message):
    __slots__ = ("isProfane", "message")
    ISPROFANE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    isProfane: bool
    message: str
    def __init__(self, isProfane: bool = ..., message: _Optional[str] = ...) -> None: ...
