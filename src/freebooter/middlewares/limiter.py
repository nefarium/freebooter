"""
    freebooter downloads photos & videos from the internet and uploads it onto your social media accounts.
    Copyright (C) 2023 Parker Wahle

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import annotations

import random
import time
from datetime import timedelta, datetime
from threading import Lock

from .common import Middleware
from ..file_management import ScratchFile
from ..metadata import MediaMetadata


class Limiter(Middleware):
    """
    Limits the number of files that can be passed through the middleware.
    """

    def __init__(
        self,
        name: str,
        *,
        amount: int = 1,
        per: dict[str, float],
        variance: dict[str, float] | None = None,
        **config,
    ) -> None:
        """
        :param limit: The maximum number of files that can be passed through the middleware.
        """
        super().__init__(name, **config)

        self._max_amount_per_period = amount

        self._period = timedelta(**per)
        self._variance = timedelta(**(variance or {}))

        self._current_count = 0
        self._counter_started_at = datetime.now()
        self._current_period = self.random_period_length()

        self._lock = Lock()

    def random_period_length(self) -> timedelta:
        """
        Returns a random period length within the variance.
        """
        return self._period + timedelta(
            seconds=random.uniform(
                -self._variance.total_seconds(), self._variance.total_seconds()
            )
        )

    def process_many(
        self, media: list[tuple[ScratchFile, MediaMetadata]]
    ) -> list[tuple[ScratchFile, MediaMetadata]]:
        with self._lock:
            # If the start time + the period is before right now, reset everything.
            if (self._counter_started_at + self._current_period) < datetime.now():
                self._counter_started_at = datetime.now()
                self._current_period = self.random_period_length()
                self._current_count = 0

            # Increment the amount in this period
            if media:
                self._current_count += 1

            if self._current_count > self._max_amount_per_period:
                self.logger.debug(
                    f"Reached limit of {self._max_amount_per_period} in {self._current_period}! "
                    f"Sleeping until the next period begins."
                )
                time_until_next_period = (
                    self._counter_started_at + self._current_period
                ) - datetime.now()
                seconds_to_sleep_for = time_until_next_period.total_seconds()
                self.logger.debug(f"Sleeping for {time_until_next_period}.")
                time.sleep(seconds_to_sleep_for)

            return media


__all__ = ("Limiter",)
