# -*- coding: utf-8 -*-
"""
This file is part of **python-openzwave**
project https://github.com/OpenZWave/python-openzwave.
    :platform: Unix, Windows, MacOS X
    :synopsis: openzwave API

.. moduleauthor: bibi21000 aka Sébastien GALLET <bibi21000@gmail.com> &
 kdschlosser aka Kevin Schlosser

License : GPL(v3)

**python-openzwave** is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

**python-openzwave** is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with python-openzwave. If not, see http://www.gnu.org/licenses.

"""

from .command_class_base import CommandClassBase

# Clock Command Class - Active
# Application
COMMAND_CLASS_CLOCK = 0x81


# noinspection PyAbstractClass
class Clock(CommandClassBase):
    """
    Clock Command Class

    symbol: `COMMAND_CLASS_CLOCK`
    """

    DAYS = [
        None,
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
    ]

    def __init__(self):
        CommandClassBase.__init__(self)
        self._cls_ids += [COMMAND_CLASS_CLOCK]

    @property
    def clock_hour(self):
        try:
            return self[('Hour', COMMAND_CLASS_CLOCK)].data
        except KeyError:
            return None

    @clock_hour.setter
    def clock_hour(self, value):
        try:
            self[('Hour', COMMAND_CLASS_CLOCK)].data = value
        except KeyError:
            pass

    @property
    def clock_day(self):
        try:
            return self[('Day', COMMAND_CLASS_CLOCK)].data
        except KeyError:
            return None

    @clock_day.setter
    def clock_day(self, value):
        if isinstance(value, int):
            try:
                value = self.DAYS[value]
            except IndexError:
                return

        if value in self.DAYS:
            try:
                self[('Day', COMMAND_CLASS_CLOCK)].data = value
            except KeyError:
                pass

    @property
    def clock_minute(self):
        try:
            return self[('Minute', COMMAND_CLASS_CLOCK)].data
        except KeyError:
            return None

    @clock_minute.setter
    def clock_minute(self, value):
        try:
            self[('Minute', COMMAND_CLASS_CLOCK)].data = value
        except KeyError:
            pass