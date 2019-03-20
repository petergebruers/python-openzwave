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

# Multi Channel Command Class - Active
# Transport-Encapsulation
COMMAND_CLASS_MULTI_CHANNEL = 0x60


# noinspection PyAbstractClass
class MultiChannel(CommandClassBase):
    """
    Multi Channel Command Class

    symbol: `COMMAND_CLASS_MULTI_CHANNEL`
    """

    def __init__(self):
        CommandClassBase.__init__(self)
        self._cls_ids += [COMMAND_CLASS_MULTI_CHANNEL]

    @property
    def channels(self):
        """
        Retrieve the list of values to consider as protection.
        Filter rules are :
            command_class = 0x60
            genre = "User"
            readonly = False
            writeonly = False

        :return: Multi Channel values
        :rtype: dict

        """
        res = []
        for value in self[(None, COMMAND_CLASS_MULTI_CHANNEL)]:
            if value.genre != 'User':
                continue

            res += [value]

        return res
