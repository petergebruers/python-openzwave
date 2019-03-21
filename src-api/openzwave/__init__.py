# -*- coding: utf-8 -*-
__license__ = """

This file is part of **python-openzwave** project https://github.com/OpenZWave/python-openzwave.

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
__copyright__ = "Copyright © 2012-2015 Sébastien GALLET aka bibi21000"
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'

try:
    __import__('pkg_resources').declare_namespace("openzwave")
except:
    # bootstrapping
    pass

import logging

LOGGING_FORMAT = (
    '[%(levelname)s]'
    '[%(thread)d] '
    '%(name)s.%(module)s.%(funcName)s - '
    '%(message)s'
)


try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """NullHandler logger for python 2.6"""
        def emit(self, record):
            pass
logger = logging.getLogger(__name__)

# Set default logging handler to avoid "No handler found" warnings.
logger.addHandler(NullHandler())
logging.basicConfig(format=LOGGING_FORMAT, level=None)
