# The MIT License (MIT)

# Copyright (c) 2021 Norizon

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

__all__ = ["data", "DataContainerMixin"]

import inspect
from typing import (
    TypeVar, 
    Any, 
    Type, 
    cast, 
    Generic, 
    Mapping, 
    overload, 
    Callable, 
    Optional, 
    Union
)

from typing_extensions import Self

from topgg.errors import TopGGException

T = TypeVar("T")
DataContainerT = TypeVar("DataContainerT", bound="DataContainerMixin")


def data(type_: Type[T]) -> T:
    """
    Represents the injected data. This should be set as the parameter's default value.

    Args:
        `type_` (:obj:`type` [ :obj:`T` ])
            The type of the injected data.

    Returns:
        :obj:`T`: The injected data of type T.

    :Example:
        .. code-block:: python

            import topgg

            # In this example, we fetch the stats from a Discord client instance.
            client = Client(...)
            dblclient = topgg.DBLClient(TOKEN).set_data(client)
            autopost: topgg.AutoPoster = dblclient.autopost()

            @autopost.stats()
            def get_stats(client: Client = topgg.data(Client)):
                return topgg.StatsWrapper(guild_count=len(client.guilds), shard_count=len(client.shards))
    """
    return cast(T, Data(type_))


class Data(Generic[T]):
    __slots__ = ("type",)

    def __init__(self, type_: Type[T]) -> None:
        self.type: Type[T] = type_


class DataContainerMixin:
    """
    A class that holds data.

    This is useful for injecting some data so that they're available
    as arguments in your functions.
    """

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data: dict[Type, Any] = {type(self): Self}

    def set_data(
        self: DataContainerT, data_: Any, *, override: bool = False
    ) -> DataContainerT:
        """
        Sets data to be available in your functions.

        Args:
            `data_` (:obj:`typing.Any`)
                The data to be injected.
            override (:obj:`bool`)
                Whether or not to override another instance that already exists.

        Raises:
            :obj:`~.errors.TopGGException`
                If override is False and another instance of the same type exists.
        """
        type_ = type(data_)
        if not override and type_ in self._data:
            raise TopGGException(
                f"{type_} already exists. If you wish to override it, pass True into the override parameter."
            )

        self._data[type_] = data_
        return self

    @overload
    def get_data(self, type_: Type[T]) -> Optional[T]:
        ...

    @overload
    def get_data(self, type_: Type[T], default: Any = None) -> Any:
        ...

    def get_data(self, type_: Any, default: Any = None) -> Any:
        """Gets the injected data."""
        return self._data.get(type_, default)

    async def _invoke_callback(
        self, callback: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        parameters: Mapping[str, inspect.Parameter]
        try:
            parameters = inspect.signature(callback).parameters
        except (ValueError, TypeError):
            parameters = {}

        signatures: dict[str, Data] = {
            k: v.default
            for k, v in parameters.items()
            if v.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and isinstance(v.default, Data)
        }

        for k, v in signatures.items():
            signatures[k] = self._resolve_data(v.type)

        res = callback(*args, Union[signatures, kwargs])
        if inspect.isawaitable(res):
            return await res

        return res

    def _resolve_data(self, type_: Type[T]) -> T:
        return self._data[type_]
