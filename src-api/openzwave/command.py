# -*- coding: utf-8 -*-
"""
.. module:: openzwave.command

This file is part of **python-openzwave** project https://github.com/OpenZWave/python-openzwave.
    :platform: Unix, Windows, MacOS X
    :sinopsis: openzwave wrapper

.. moduleauthor:: bibi21000 aka Sébastien GALLET <bibi21000@gmail.com>

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
from openzwave.object import ZWaveNodeInterface
import threading

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """NullHandler logger for python 2.6"""
        def emit(self, record):
            pass
logger = logging.getLogger('openzwave')
logger.addHandler(NullHandler())


class ZWaveNodeBasic(ZWaveNodeInterface):
    """
    Represents an interface to BasicCommands
    I known it's not necessary as they can be included in the node directly.
    But it's a good starting point.

    What I want to do is provide an automatic mapping system hidding
    the mapping classes.

    First example, the battery level, it's not a basic command but don't care.
    Its command class is 0x80.

    A user should write

    .. code-block:: python

        if self.handle_command_class(class_id):
            ret=command_Class(...)

    The classic way to do it is a classic method of registering. But

    Another way : using heritage multiple

    ZWaveNode(ZWaveObject, ZWaveNodeBasic, ....)
    The interface will implement methods
    command_class_0x80(param1,param2,...)
    That's the first thing to do
    We also can define a property with a friendly name

    handle_command_class will do the rest

    Another way to do it :
    A node can manage actuators (switch, dimmer, ...)
    and sensors (temperature, consummation, temperature)

    So we need a kind of mechanism to retrieve commands in a user friendly way
    Same for sensors.

    A good use case is the AN158 Plug-in Meter Appliance Module
    We will study the following command classes :
    'COMMAND_CLASS_SWITCH_ALL', 'COMMAND_CLASS_SWITCH_BINARY',
    'COMMAND_CLASS_METER',

    The associated values are :

    .. code-block:: python

        COMMAND_CLASS_SWITCH_ALL : {
            72057594101481476L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': 'On and Off Enabled',
                'min': 0L,
                'writeonly': False,
                'label': 'Switch All',
                'readonly': False,
                'data_str': 'On and Off Enabled',
                'type': 'List'}
        }
        COMMAND_CLASS_SWITCH_BINARY : {
            72057594093060096L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': False,
                'min': 0L,
                'writeonly': False,
                'label': 'Switch',
                'readonly': False,
                'data_str': False,
                'type': 'Bool'}
        }
        COMMAND_CLASS_METER : {
            72057594093273600L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': False,
                'min': 0L,
                'writeonly': False,
                'label': 'Exporting',
                'readonly': True,
                'data_str': False,
                'type': 'Bool'},
            72057594101662232L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': 'False',
                'min': 0L,
                'writeonly': True,
                'label': 'Reset',
                'readonly': False,
                'data_str': 'False',
                'type': 'Button'},
            72057594093273090L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': 'kWh',
                'data': 0.0,
                'min': 0L,
                'writeonly': False,
                'label': 'Energy',
                'readonly': True,
                'data_str': 0.0,
                'type': 'Decimal'},
            72057594093273218L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': 'W',
                'data': 0.0,
                'min': 0L,
                'writeonly': False,
                'label': 'Power',
                'readonly': True,
                'data_str': 0.0,
                'type': 'Decimal'}
        }

    Another example from an homePro dimmer (not configured in openzwave):

    .. code-block:: python

        COMMAND_CLASS_SWITCH_MULTILEVEL : {
            72057594109853736L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': 'False',
                'min': 0L,
                'writeonly': True,
                'label': 'Dim',
                'readonly': False,
                'data_str': 'False',
                'type': 'Button'},
            72057594109853697L: {
                'help': '',
                'max': 255L,
                'is_polled': False,
                'units': '',
                'data': 69,
                'min': 0L,
                'writeonly': False,
                'label': 'Level',
                'readonly': False,
                'data_str': 69,
                'type': 'Byte'},
            72057594118242369L: {
                'help': '',
                'max': 255L,
                'is_polled': False,
                'units': '',
                'data': 0,
                'min': 0L,
                'writeonly': False,
                'label': 'Start Level',
                'readonly': False,
                'data_str': 0,
                'type': 'Byte'},
            72057594109853720L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': 'False',
                'min': 0L,
                'writeonly': True,
                'label': 'Bright',
                'readonly': False,
                'data_str': 'False',
                'type': 'Button'},
            72057594118242352L: {
                'help': '',
                'max': 0L,
                'is_polled': False,
                'units': '',
                'data': False,
                'min': 0L,
                'writeonly': False,
                'label': 'Ignore Start Level',
                'readonly': False,
                'data_str': False,
                'type': 'Bool'}
        }

    What about the conclusion :

        The COMMAND_CLASS_SWITCH_ALL is defined with the same label and
        use a list as parameter. This should be a configuration parameter.
        Don't know what to do for this command class

        The COMMAND_CLASS_SWITCH_BINARY use a bool as parameter while
        COMMAND_CLASS_SWITCH_MULTILEVEL use 2 buttons : Dim and Bright.
        Dim and Bright must be done in 2 steps : set the level and activate
        the button.

        So we must add one or more lines in the actuators :

        Switch : {setter:self.set_command_class_0xYZ(valueId, new), getter:}
        We must find a way to access the value directly

        Bright
        Dim

        So for the COMMAND_CLASS_SWITCH_BINARY we must define a function called
        Switch (=the label of the value). What happen if we have 2 switches
        on the node : 2 values I suppose.

        COMMAND_CLASS_SWITCH_MULTILEVEL uses 2 commands : 4 when 2 dimmers on the
        done ? Don't know but it can.

        COMMAND_CLASS_METER export many values : 2 of them sends a decimal
        and are readonly. They also have a Unit defined ans values are readonly

        COMMAND_CLASS_METER are used for sensors only. So we would map
        every values entries as defined before

        Programming :
        get_switches : retrieve the list of switches on the node
        is_switch (label) : says if the value with label=label is a switch
        get_switch (label) : retrieve the value where label=label
    """

    @property
    def battery_level(self):
        """
        The battery level of this node.
        The command 0x80 (COMMAND_CLASS_BATTERY) of this node.

        :param value_id: The value to retrieve state. If None, retrieve the first value
        :type value_id: int
        :return: The level of this battery
        :rtype: int
        """

        if 0x80 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x80].level.data

    @property
    def battery_levels(self):
        """
        The command 0x80 (COMMAND_CLASS_BATTERY) of this node.
        Retrieve the list of values to consider as batteries.
        Filter rules are :

            command_class = 0x80
            genre = "User"
            type = "Byte"
            readonly = True
            writeonly = False

        :return: The list of switches on this node
        :rtype: dict()
        """
        if 0x80 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x80].level.data

    @property
    def power_level(self):
        """
        The power level of this node.
        The command 0x73 (COMMAND_CLASS_POWERLEVEL) of this node.

        :param value_id: The value to retrieve state. If None, retrieve the first value
        :type value_id: int
        :return: The level of this battery
        :rtype: int
        """

        if 0x73 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x73].level.data

    @property
    def power_levels(self):
        """
        The command 0x73 (COMMAND_CLASS_POWERLEVEL) of this node.
        Retrieve the list of values to consider as power_levels.
        Filter rules are :

            command_class = 0x73
            genre = "User"
            type = "Byte"
            readonly = True
            writeonly = False

        :return: The list of switches on this node
        :rtype: dict()
        """

        if 0x73 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x73].level.data

    @property
    def can_wake_up(self):
        """
        Check if node contain the command class 0x84 (COMMAND_CLASS_WAKE_UP).

        Filter rules are :

            command_class = 0x84

        :return: True if the node can wake up
        :rtype: bool
        """
        return 0x84 in self.command_classes

    def get_configs(self, readonly='All', writeonly='All'):
        """
        The command 0x70 (COMMAND_CLASS_CONFIGURATION) of this node.
        Retrieve the list of configuration parameters.

        Filter rules are :
            command_class = 0x70
            genre = "Config"
            readonly = "All" (default) or as passed in arg

        :param readonly: whether to retrieve readonly configs
        :param writeonly: whether to retrieve writeonly configs
        :return: The list of configuration parameters
        :rtype: dict()
        """
        if 0x70 not in self._value_index_mapping:
            return

        indices = self._value_index_mapping[0x70]

        values = {}
        for i in range(indices.indexes.param_start, indices.indexes.param_end + 1):
            if self._value_index_mapping[0x70][i] is not None:
                value = self._value_index_mapping[0x70][i]

                if (
                    readonly in ('All', value.readonly) and
                    writeonly in ('All', value.writeonly)
                ):
                    values[value.value_id] = value

        return values

    def set_config(self, index, value):
        """
        The command 0x70 (COMMAND_CLASS_CONFIGURATION) of this node.
        Set config to value (using value value_id)

        :param index: The index of the value
        :type index: int
        :param value: Appropriate value for given config
        :type value: any
        """

        if 0x70 not in self._value_index_mapping:
            return False

        if self._value_index_mapping[0x70][index] is None:
            return False

        self._value_index_mapping[0x70][index].data = value
        return True

    def get_config(self, index):
        """
        The command 0x70 (COMMAND_CLASS_CONFIGURATION) of this node.
        Set config to value (using value value_id)

        :param index: The index of the value to retrieve.
        :type index: int
        :return: The data stored in the value
        :rtype: any
        """

        if 0x70 not in self._value_index_mapping:
            return

        if self._value_index_mapping[0x70][index] is None:
            return

        return self._value_index_mapping[0x70][index].data

    @property
    def can_set_indicator(self):
        """
        Check if node contain the command class 0x87 (COMMAND_CLASS_INDICATOR).

        Filter rules are :

            command_class = 0x87

        :return: True if the node can set the indicator
        :rtype: bool
        """

        return 0x87 in self.command_classes


class ZWaveNodeSwitch(ZWaveNodeInterface):
    """
    Represents an interface to switches and dimmers Commands

    """

    @property
    def switches_all(self):
        """
        The command 0x27 (COMMAND_CLASS_SWITCH_ALL) of this node.
        Retrieve the list of values to consider as switches_all.
        Filter rules are :

            command_class = 0x27
            genre = "System"
            type = "List"
            readonly = False
            writeonly = False

        :return: The list of switches on this node
        :rtype: dict()

        """

        if 0x27 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x27].switch_all.data_items

    @property
    def switch_all_state(self):
        """
        The command 0x27 (COMMAND_CLASS_SWITCH_ALL) of this node.
        Return the state (using value value_id) of a switch or a dimmer.

        :return: The state of the value
        :rtype: bool

        """

        if 0x27 not in self._value_index_mapping:
            return

        for command_class in range(0x25, 0x27):
            if command_class in self._value_index_mapping:
                break
        else:
            return

        indices = self._value_index_mapping[command_class]
        instance = self._value_index_mapping[0x27].switch_all.instance

        if indices.level.instance == instance:
            return indices.level.data

        for switch in self.get_switches():
            if self.values[switch].instance == instance:
                return self.values[switch].data
        for dimmer in self.get_dimmers():
            if self.values[dimmer].instance == instance:
                if self.values[dimmer].data == 0:
                    return False
                else:
                    return True
        return None

    @switch_all_state.setter
    def switch_all_state(self, value):
        """
        The command 0x27 (COMMAND_CLASS_SWITCH_ALL) of this node.
        Set switches_all to value (using value value_id).

        :param value: A predefined string
        :type value: str

        """

        if 0x27 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x27].switch_all.data = value

    @property
    def switch_all_item(self):
        """
        The command 0x27 (COMMAND_CLASS_SWITCH_ALL) of this node.
        Return the current value (using value value_id) of a switch_all.

        :return: The value of the value
        :rtype: str

        """

        if 0x27 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x27].switch_all.data

    @property
    def switch_all_items(self):
        """
        The command 0x27 (COMMAND_CLASS_SWITCH_ALL) of this node.
        Return the all the possible values (using value value_id) of a switch_all.

        :return: The value of the value
        :rtype: set()

        """

        if 0x27 not in self._value_index_mapping:
            return []

        return self._value_index_mapping[0x27].switch_all.data_items

    @property
    def switches(self):
        """
        The command 0x25 (COMMAND_CLASS_SWITCH_BINARY) of this node.
        Retrieve the list of values to consider as switches.
        Filter rules are :

            command_class = 0x25
            genre = "User"
            type = "Bool"
            readonly = False
            writeonly = False

        :return: The list of switches on this node
        :rtype: dict()

        """
        values = {}

        for value in self.value.values():
            if value.command_class == 0x25:
                values[value.value_id] = value

        return values

    @property
    def switch_state(self):
        """
        The command 0x25 (COMMAND_CLASS_SWITCH_BINARY) of this node.
        Return the state (using value value_id) of a switch.

        :return: The state of the value
        :rtype: bool

        """

        if 0x25 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x25].level.data

    @switch_state.setter
    def switch_state(self, value):
        """
        The command 0x25 (COMMAND_CLASS_SWITCH_BINARY) of this node.
        Set switch to value (using value value_id).

        :param value: True or False
        :type value: bool

        """

        if 0x25 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x25].level.data = value

    @property
    def dimmers(self):
        """
        The command 0x26 (COMMAND_CLASS_SWITCH_MULTILEVEL) of this node.
        Retrieve the list of values to consider as dimmers.
        Filter rules are :

            command_class = 0x26
            genre = "User"
            type = "Bool"
            readonly = False
            writeonly = False

        :return: The list of dimmers on this node
        :rtype: dict()

        """
        values = {}

        for value in self.value.values():
            if value.command_class == 0x26:
                values[value.value_id] = value

        return values

    @property
    def dimmer_level(self):
        """
        The command 0x26 (COMMAND_CLASS_SWITCH_MULTILEVEL) of this node.
        Get the dimmer level (using value value_id).

        :return: The level : a value between 0-99
        :rtype: int

        """

        if 0x26 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x26].level.data

    @dimmer_level.setter
    def dimmer_level(self, value):
        """
        The command 0x26 (COMMAND_CLASS_SWITCH_MULTILEVEL) of this node.
        Set switch to value (using value value_id).

        :param value: The level : a value between 0-99 or 255. 255 set the level to the last value. \
        0 turn the dimmer off
        :type value: int

        """

        logger.debug(u"set_dimmer Level:%s", value)

        if 0x26 not in self._value_index_mapping:
            return

        if 99 < value < 255:
            value = 99
        elif value < 0:
            value = 0

        event = threading.Event()

        if self._value_index_mapping[0x26].target_value is not None:
            while self._value_index_mapping[0x26].target_value != value:
                self._value_index_mapping[0x26].level.data = value
                event.wait(0.1)

        else:
            self._value_index_mapping[0x26].level.data = value
            # Dimmers doesn't return the good level.
            # Add a Timer to refresh the value
            if value == 0:
                timer1 = threading.Timer(1, self._value_index_mapping[0x26].level.refresh)
                timer1.start()
                timer2 = threading.Timer(2, self._value_index_mapping[0x26].level.refresh)
                timer2.start()

    @property
    def rgb_bulbs(self):
        """
        The command 0x33 (COMMAND_CLASS_COLOR) of this node.
        Retrieve the list of values to consider as RGBW bulbs.
        Filter rules are :

            command_class = 0x33
            genre = "User"
            type = "String"
            readonly = False
            writeonly = False

        :return: The list of dimmers on this node
        :rtype: dict()

        """

        values = {}

        for value in self.value.values():
            if value.command_class == 0x33:
                values[value.value_id] = value

        return values

    @property
    def rgbw(self):
        """
        The command 0x33 (COMMAND_CLASS_COLOR) of this node.
        Get the RGW value (using value value_id).

        :return: The level : a value between 0-99
        :rtype: int

        """
        if 0x33 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x33].color.data

    @rgbw.setter
    def rgbw(self, value):
        """
        The command 0x33 (COMMAND_CLASS_COLOR) of this node.
        Set RGBW to value (using value value_id).

        :param value: The level : a RGBW value
        :type value: int

        """

        if 0x33 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x33].color.data = value


class ZWaveNodeSensor(ZWaveNodeInterface):
    """
    Represents an interface to Sensor Commands

    """

    @property
    def sensors(self):
        """
        The command 0x30 (COMMAND_CLASS_SENSOR_BINARY) of this node.
        The command 0x31 (COMMAND_CLASS_SENSOR_MULTILEVEL) of this node.
        The command 0x32 (COMMAND_CLASS_METER) of this node.
        Retrieve the list of values to consider as sensors.
        Filter rules are :

            command_class = 0x30-32
            genre = "User"
            readonly = True
            writeonly = False

        :param type: the type of value
        :type type: 'All' or PyValueTypes
        :return: The list of switches on this node
        :rtype: dict()

        """
        values = {}

        for command_class in range(0x30, 0x33):
            if command_class in self._value_index_mapping:
                break
        else:
            return

        indices = self._value_index_mapping[command_class]

        for i in range(indices.indexes.start, indices.indexes.end + 1):
            if self._value_index_mapping[command_class][i] is not None:
                value = self._value_index_mapping[command_class][i]
                values[value.value_id] = value

    @property
    def sensor_value(self):
        """
        The command 0x30 (COMMAND_CLASS_SENSOR_BINARY) of this node.
        The command 0x31 (COMMAND_CLASS_SENSOR_MULTILEVEL) of this node.
        The command 0x32 (COMMAND_CLASS_METER) of this node.

        :return: The state of the sensors
        :rtype: variable

        """

        for command_class in range(0x30, 0x33):
            if command_class in self._value_index_mapping:
                break
        else:
            return

        indices = self._value_index_mapping[command_class]

        for i in range(indices.indexes.start, indices.indexes.end + 1):
            if self._value_index_mapping[command_class][i] is not None:
                return self._value_index_mapping[command_class][i].data


class ZWaveNodeThermostat(ZWaveNodeInterface):
    """
    Represents an interface to Thermostat Commands

    """

    @property
    def thermostats(self):
        """
        The command 0x40 (COMMAND_CLASS_THERMOSTAT_MODE) of this node.
        The command 0x42 (COMMAND_CLASS_THERMOSTAT_OPERATING_STATE) of this node.
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        The command 0x44 (COMMAND_CLASS_THERMOSTAT_FAN_MODE) of this node.
        The command 0x45 (COMMAND_CLASS_THERMOSTAT_FAN_STATE) of this node.
        Retrieve the list of values to consider as thermostats.
        Filter rules are :

            command_class = 0x40-45
            genre = "User"
            readonly = True/False
            writeonly = False

        :return: The list of switches on this node
        :rtype: dict()

        """
        values = {}

        for value in self.values.values():
            if value.command_class in (0x40, 0x42, 0x43, 0x44, 0x45):
                values[value.value_id] = value

        return values

    @property
    def thermostat_state(self):
        """
        The command 0x40 (COMMAND_CLASS_THERMOSTAT_MODE) of this node.
        The command 0x42 (COMMAND_CLASS_THERMOSTAT_OPERATING_STATE) of this node.
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        The command 0x44 (COMMAND_CLASS_THERMOSTAT_FAN_MODE) of this node.
        The command 0x45 (COMMAND_CLASS_THERMOSTAT_FAN_STATE) of this node.

        :return: The state of the thermostats
        :rtype: variable

        """
        res = {}

        if 0x43 in self._value_index_mapping:
            value = self._value_index_mapping[0x43]
            set_points = []

            for i in range(value.max_entry + 1):
                if value[i] is not None:
                    set_points += [
                        [
                            value[i].label,
                            value[i].data,
                            value[i].unit
                        ]
                    ]

            res['setpoints'] = set_points[:]

        if 0x42 in self._value_index_mapping:
            res['operating_state'] = (
                self._value_index_mapping[0x42].operating_state.data
            )

        if 0x40 in self._value_index_mapping:
            res['operating_mode'] = self._value_index_mapping[0x40].mode.data

        if 0x45 in self._value_index_mapping:
            res['fan_state'] = self._value_index_mapping[0x45].fan_state.data

        if 0x44 in self._value_index_mapping:
            res['fan_mode'] = self._value_index_mapping[0x44].fan_mode.data

        return res

    @property
    def thermostat_operating_mode(self):
        """
        The command 0x40 (COMMAND_CLASS_THERMOSTAT_MODE) of this node.

        :rtype value: String

        """
        if 0x40 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x40].mode.data

    @thermostat_operating_mode.setter
    def thermostat_operating_mode(self, value):
        """
        The command 0x40 (COMMAND_CLASS_THERMOSTAT_MODE) of this node.
        Set MODE to value (using value).

        :param value: The mode : 'Off', 'Heat', 'Cool'
        :type value: String

        """
        logger.debug(u"set_thermostat_mode value:%s", value)

        if 0x40 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x40].mode.data = value

    @property
    def thermostat_operating_state(self):
        """
        The command 0x42 (COMMAND_CLASS_THERMOSTAT_OPERATING_STATE) of this node.
        Get thermostat state.

        :rtype value: String

        """
        if 0x42 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x42].operating_state.data

    @property
    def thermostat_fan_mode(self):
        """
        The command 0x44 (COMMAND_CLASS_THERMOSTAT_FAN_MODE) of this node.

        :rtype value: String

        """
        if 0x44 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x44].fan_mode.data

    @thermostat_fan_mode.setter
    def thermostat_fan_mode(self, value):
        """
        The command 0x44 (COMMAND_CLASS_THERMOSTAT_FAN_MODE) of this node.
        Set FAN_MODE to value (using value).

        :param value: The mode : 'On Low', 'Auto Low'
        :type value: String

        """
        logger.debug(u"set_thermostat_fan_mode value:%s", value)

        if 0x44 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x44].fan_mode.data = value

    @property
    def thermostat_fan_state(self):
        """
        The command 0x45 (COMMAND_CLASS_THERMOSTAT_FAN_STATE) of this node.
        Get thermostat state.

        :rtype value: String

        """
        if 0x45 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x45].fan_state.data

    @property
    def thermostat_heating(self):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Get Target Heat temperature.
        """
        if 0x43 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x43].heating.data

    @thermostat_heating.setter
    def thermostat_heating(self, value):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Set Target Heat temperature.

        :param value: The Temperature.
        :type value: float

        """
        if 0x43 not in self._value_index_mapping:
            return

        logger.debug(u"set_thermostat_heating value:%s", value)
        self._value_index_mapping[0x43].heating.data = value

    @property
    def thermostat_economy_heating(self):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Get Target Heat temperature.
        """
        if 0x43 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x43].economy_heating.data

    @thermostat_economy_heating.setter
    def thermostat_economy_heating(self, value):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Set Target Heat temperature.

        :param value: The Temperature.
        :type value: float

        """
        if 0x43 not in self._value_index_mapping:
            return

        logger.debug(u"set_thermostat_economy_heating value:%s", value)
        self._value_index_mapping[0x43].economy_heating.data = value

    @property
    def thermostat_away_heating(self):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Get Target Heat temperature.
        """
        if 0x43 not in self._value_index_mapping:
            return
        return self._value_index_mapping[0x43].away_heating.data

    @thermostat_away_heating.setter
    def thermostat_away_heating(self, value):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Set Target Heat temperature.

        :param value: The Temperature.
        :type value: float

        """
        if 0x43 not in self._value_index_mapping:
            return

        logger.debug(u"set_thermostat_away_heating value:%s", value)
        self._value_index_mapping[0x43].away_heating.data = value


    @property
    def thermostat_cooling(self):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Get Target Cool temperature.
        """
        if 0x43 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x43].cooling.data

    @thermostat_cooling.setter
    def thermostat_cooling(self, value):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Set Target Cool temperature.

        :param value: The Temperature.
        :type value: float

        """
        if 0x43 not in self._value_index_mapping:
            return

        logger.debug(u"set_thermostat_cooling value:%s", value)
        self._value_index_mapping[0x43].cooling.data = value

    @property
    def thermostat_economy_cooling(self):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Get Target Cool temperature.
        """
        if 0x43 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x43].economy_cooling.data

    @thermostat_economy_cooling.setter
    def thermostat_economy_cooling(self, value):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Set Target Cool temperature.

        :param value: The Temperature.
        :type value: float

        """
        if 0x43 not in self._value_index_mapping:
            return

        logger.debug(u"set_thermostat_economy_cooling value:%s", value)
        self._value_index_mapping[0x43].economy_cooling.data = value

    @property
    def thermostat_away_cooling(self):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Get Target Cool temperature.
        """
        if 0x43 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x43].away_cooling.data

    @thermostat_away_cooling.setter
    def thermostat_away_cooling(self, value):
        """
        The command 0x43 (COMMAND_CLASS_THERMOSTAT_SETPOINT) of this node.
        Set Target Cool temperature.

        :param value: The Temperature.
        :type value: float

        """
        if 0x43 not in self._value_index_mapping:
            return

        logger.debug(u"set_thermostat_away_cooling value:%s", value)
        self._value_index_mapping[0x43].away_cooling.data = value


class ZWaveNodeSecurity(ZWaveNodeInterface):
    """
    Represents an interface to Security Commands

    """

    @property
    def protection(self):
        """
        The command 0x75 (COMMAND_CLASS_PROTECTION) of this node.
        Get/Set Protection

        :return: The value of the value
        :rtype: str
        """

        if 0x75 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x75].protection.data

    @protection.setter
    def protection(self, value):
        if 0x75 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x75].protection.data = value

    @property
    def protections(self):
        """
        The command 0x75 (COMMAND_CLASS_PROTECTION) of this node.
        Retrieve the list of values to consider as protection.
        Filter rules are :

            command_class = 0x75
            genre = "User"
            readonly = True
            writeonly = False

        :return: The list of switches on this node
        :rtype: dict()

        """

        if 0x75 not in self._value_index_mapping:
            return {}

        res = {}
        for value in self._value_index_mapping[0x75]:
            if value is None:
                continue

            res[value.value_id] = value

        return res

    @property
    def protection_items(self):
        """
        The command 0x75 (COMMAND_CLASS_PROTECTION) of this node.
        Return the all the possible values (using value value_id) of a protection.

        :return: The value of the value
        :rtype: set()

        """

        if 0x75 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x75].protection.data_items


class ZWaveSoundSwitch(ZWaveNodeInterface):
    """
    Represents an interface to Security Commands

    """

    @property
    def volume(self):
        """
        The command 0x75 (COMMAND_CLASS_SOUND_SWITCH) of this node.
        Get/Set Volume

        :return: new_volume
        :rtype: str
        """

        if 0x79 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x79].volume.data

    @volume.setter
    def volume(self, value):
        if 0x79 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x79].volume.data = value

    @property
    def tone(self):
        """
        The command 0x75 (COMMAND_CLASS_SOUND_SWITCH) of this node.
        Get/Set Tone

        :return: tone
        :rtype: str
        """

        if 0x79 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x79].tone.data

    @tone.setter
    def tone(self, value):
        if 0x79 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x79].tone.data = value

    @property
    def tone_items(self):
        """
        The command 0x75 (COMMAND_CLASS_PROTECTION) of this node.
        Return the all the possible values (using value value_id) of a protection.

        :return: The value of the value
        :rtype: set()

        """

        if 0x79 not in self._value_index_mapping:
            return []

        return self._value_index_mapping[0x75].tone.data_items


class ZWaveNotification(ZWaveNodeInterface):
    """
    Represents an interface to Security Commands

    """

    @property
    def alarm_state(self):
        """
        The command 0x71 COMMAND_CLASS_NOTIFICATION (COMMAND_CLASS_ALARM) of this node.
        Get Alarm State

        :return: state
        :rtype: str
        """

        if 0x71 not in self._value_index_mapping:
            return

        indices = self._value_index_mapping[0x71]

        for i in range(indices.indexes.start, indices.indexes.end + 1):
            if self._value_index_mapping[0x71][i] is not None:
                return self._value_index_mapping[0x71][i].data

    @property
    def alarm_level(self):
        """
        The command 0x71 COMMAND_CLASS_NOTIFICATION (COMMAND_CLASS_ALARM) of this node.
        Get Alarm Level

        :return: level
        :rtype: str
        """

        if 0x71 not in self._value_index_mapping:
            return

        return self._value_index_mapping[0x71].level_v1.data

    @property
    def alarm_type(self):
        """
        The command 0x71 COMMAND_CLASS_NOTIFICATION (COMMAND_CLASS_ALARM) of this node.
        Get Alarm Type

        :return: alarm type
        :rtype: str

        """

        if 0x71 not in self._value_index_mapping:
            return []

        return self._value_index_mapping[0x71].type_v1.data

    @property
    def alarm_parameters(self):
        """
        The command 0x71 COMMAND_CLASS_NOTIFICATION (COMMAND_CLASS_ALARM) of this node.
        Get Alarm Parameters

        :return: parameters
        :rtype: list

        """

        if 0x71 not in self._value_index_mapping:
            return []

        indices = self._value_index_mapping[0x71]

        res = []

        for i in range(indices.indexes.param_start, indices.indexes.param_end + 1):
            if self._value_index_mapping[0x71][i] is not None:
                res += [self._value_index_mapping[0x71][i]]

        return res


class ZWaveSimpleAVControl(ZWaveNodeInterface):
    """
    Represents an interface to Security Commands

    """

    def av_command_send(self, command):
        """
        The command 0x94 (COMMAND_CLASS_SIMPLE_AV_CONTROL) of this node.

        :param command: one of the values returned from av_commands
        :type command: str
        """

        if 0x94 not in self._value_index_mapping:
            return False

        self._value_index_mapping[0x94].command.data = command
        return True

    @property
    def av_commands(self):
        """
        The command 0x94 (COMMAND_CLASS_SIMPLE_AV_CONTROL) of this node.
        Return available commands

        :return: list of available commands
        :rtype: list

        """

        if 0x94 not in self._value_index_mapping:
            return []

        return list(
            itm for itm in self._value_index_mapping[0x94].command.data_items
        )


class ZWaveNodeDoorLock(ZWaveNodeInterface):
    """
    Represents an interface to door lock and user codes associated with door locks
    """

    @property
    def door_locks(self):
        """
        The command 0x62 (COMMAND_CLASS_DOOR_LOCK) of this node.
        Retrieves the list of values to consider as doorlocks.
        Filter rules are :

            command_class = 0x62
            genre = "User"
            type = "Bool"
            readonly = False
            writeonly = False

        :return: The list of door locks on this node
        :rtype: dict()

        """

        if 0x62 not in self._value_index_mapping:
            return {}

        res = {}
        for value in self._value_index_mapping[0x62]:
            if value is None:
                continue

            res[value.value_id] = value

        return res

    @property
    def door_lock(self):
        """
        The command 0x62 (COMMAND_CLASS_DOOR_LOCK) of this node.
        Gets/Sets doorlock

        :return: True/False, None
        Setter: True/False
        """

        if 0x62 not in self._value_index_mapping:
            return None

        return self._value_index_mapping[0x62].lock.data

    @door_lock.setter
    def door_lock(self, value):
        if 0x62 not in self._value_index_mapping:
            return

        self._value_index_mapping[0x62].lock.data = value

    @property
    def user_codes(self):
        """
        The command 0x63 (COMMAND_CLASS_USER_CODE) of this node.
        :return: None or UserCodes instance
        """

        if 0x63 not in self._value_index_mapping:
            return

        return UserCodes(self._value_index_mapping[0x63])

    @property
    def doorlock_logs(self):
        """
        The command 0x4c (COMMAND_CLASS_DOOR_LOCK_LOGGING) of this node.
        Retrieves the value consisting of log records.
        Filter rules are :

            command_class = 0x4c
            genre = "User"
            type = "String"
            readonly = True

        :return: The dict of log records with value_id as key
        :rtype: dict()

        """
        res = []

        if 0x4c not in self._value_index_mapping:
            return res

        event = threading.Event()
        indices = self._value_index_mapping[0x4c]

        for i in range(indices.system_config_max_records.data):
            indices.get_record_no.data = i
            if indices.log_record.data in res:
                event.wait(0.2)

            if indices.log_record.data not in res:
                res += [indices.log_record.data]
        return res


class UserCodes(object):

    def __init__(self, indices):
        '''
        start = 1
        end = 254
        refresh = 255
        remove_code = 256
        count = 257
        raw_value = 258
        raw_value_index = 259
        max_entry = raw_value_index
        '''
        self._indices = indices

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if self._indices.indexes.start <= key <= self._indices.end:
                if value not in self:
                    self._indices[key].data = value
            else:
                raise IndexError(str(key))

        else:
            for i in range(self._indices.indexes.start, self._indices.end + 1):
                if (
                    self._indices[i] is not None and
                    self._indices[i].label == key
                ):
                    self._indices[i].data = value
                    break
            else:
                i = self._indices.indexes.start + len(self)

                if i > self._indices.end:
                    raise KeyError('Maximum Codes reached.')
                self._indices[i].label = key
                self._indices[i].data = value

    def append(self, code):
        if code in self:
            return False
        try:
            self[self._indices.indexes.start + len(self)] = code
            return True
        except IndexError:
            return False

    def remove(self, code):
        if code in self:
            self._indices.remove_code.data = code
            return True
        return False

    def __radd__(self, other):
        for code in other:
            if not self.append(code):
                break

    def __contains__(self, item):
        for i in range(self._indices.indexes.start, self._indices.indexes.end + 1):
            if (
                self._indices[i] is not None and
                item in (self._indices[i].data, self._indices[i].label)
            ):
                return True

        return False

    def extend(self, codes):
        for code in codes:
            if not self.append(code):
                return False
        return True

    def __len__(self):
        return self._indices.count.data
