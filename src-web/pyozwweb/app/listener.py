# -*- coding: utf-8 -*-

"""The listener."""

__license__ = """

This file is part of **python-openzwave** 
project https://github.com/OpenZWave/python-openzwave.

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
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'

from gevent import monkey
monkey.patch_all()

import sys # NOQA
from openzwave.network import ZWaveNetwork # NOQA
from openzwave.controller import ZWaveController # NOQA
import threading # NOQA
from threading import Thread # NOQA
import logging # NOQA

logger = logging.getLogger('pyozwweb')

listener = None

if sys.hexversion >= 0x3000000:
    from pydispatch import dispatcher
else:
    from louie import dispatcher


class ListenerThread(Thread):
    """ The listener Tread
    """

    def __init__(self, _socketio, _app):
        """The constructor"""
        Thread.__init__(self)
        self._stopevent = threading.Event()
        self.socketio = _socketio
        self.app = _app
        self.connected = False

    def connect(self):
        """Connect to the zwave notifications
        """
        if self.connected is False:
            self.join_room_network()
            self.join_room_controller()
            self.join_room_node()
            self.join_room_values()
            self.connected = True
            logging.info("Listener connected")

    def run(self):
        """The running method
        """
        logging.info("Start listener")
        self._stopevent.wait(5.0)
        self.connect()
        while not self._stopevent.isSet():
            self._stopevent.wait(0.1)

    def join_room_network(self):
        """Join room network
        """
        dispatcher.connect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_STARTED
        )
        dispatcher.connect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_RESETTED
        )
        dispatcher.connect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_AWAKED
        )
        dispatcher.connect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_READY
        )
        dispatcher.connect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_STOPPED
        )
        return True

    def leave_room_network(self):
        """Leave room network
        """
        dispatcher.disconnect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_STARTED
        )
        dispatcher.disconnect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_RESETTED
        )
        dispatcher.disconnect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_AWAKED
        )
        dispatcher.disconnect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_READY
        )
        dispatcher.disconnect(
            self._louie_network,
            ZWaveNetwork.SIGNAL_NETWORK_STOPPED
        )
        return True

    def _louie_network(self, network):
        """Louie dispatch for netowrk
        """
        with self.app.test_request_context():
            if network is None:
                self.socketio.emit(
                    'my network response',
                    {
                        'data': {
                            'state': "unknown",
                            'state_str': "unknown",
                            'home_id': "unknown",
                            'nodes_count': "unknown"
                        }
                    },
                    namespace='/ozwave'
                )
            else:
                self.socketio.emit(
                    'my network response',
                    {'data': network.to_dict()},
                    namespace='/ozwave'
                )
                logging.debug(
                    'OpenZWave network notification : '
                    'homeid %0.8x (state:%s) - %d nodes were found.' % (
                        network.home_id,
                        network.state,
                        network.nodes_count
                    )
                )

    def join_room_node(self):
        """Join room nodes
        """
        dispatcher.connect(self._louie_node, ZWaveNetwork.SIGNAL_NODE)
        return True

    def leave_room_node(self):
        """Leave room nodes
        """
        dispatcher.disconnect(self._louie_node, ZWaveNetwork.SIGNAL_NODE)
        return True

    def _louie_node(self, _, node):
        """Louie dispatch for node
        """
        data = node.to_dict()
        self.socketio.emit(
            'my node response',
            {'data': data},
            namespace='/ozwave'
        )
        logging.debug('OpenZWave node notification : node %s.', data)

    def join_room_values(self):
        """Join room values
        """
        dispatcher.connect(self._louie_values, ZWaveNetwork.SIGNAL_VALUE)
        return True

    def leave_room_values(self):
        """Leave room values
        """
        dispatcher.disconnect(self._louie_values, ZWaveNetwork.SIGNAL_VALUE)
        return True

    def _louie_values(self, network, node, value):
        """Louie dispatch for values
        """
        with self.app.test_request_context():
            if network is None:
                self.socketio.emit(
                    'my values response',
                    {
                        'data': {
                            'node_id': None,
                            'homeid': None,
                            'value_id': None
                        }
                    },
                    namespace='/ozwave'
                )
                logging.debug(
                    'OpenZWave values notification : Network is None.'
                )
            elif node is None:
                logging.debug('OpenZWave values notification : Node is None.')
                self.socketio.emit(
                    'my values response',
                    {
                        'data': {
                            'node_id': None,
                            'homeid': network.home_id_str,
                            'value_id': None
                        }
                    },
                    namespace='/ozwave'
                )
            elif value is None:
                self.socketio.emit(
                    'my values response',
                    {
                        'data': {
                            'node_id': node.node_id,
                            'homeid': network.home_id_str,
                            'value_id': None
                        }
                    },
                    namespace='/ozwave'
                )
                logging.debug('OpenZWave values notification : Value is None.')
            else:
                node = network.nodes[node.node_id]
                self.socketio.emit(
                    'my values response',
                    {'data': node.values[value.value_id].to_dict()},
                    namespace='/ozwave'
                )
                logging.debug(
                    'OpenZWave values notification : '
                    'homeid %0.8x - node %d - value %d.',
                    network.home_id,
                    node.node_id,
                    value.value_id
                )

    def join_room_controller(self):
        """Join room controller
        """
        dispatcher.connect(
            self._louie_controller,
            ZWaveController.SIGNAL_CTRL_WAITING
        )
        dispatcher.connect(
            self._louie_controller,
            ZWaveController.SIGNAL_CONTROLLER
        )
        return True

    def leave_room_controller(self):
        """Leave room controller
        """
        dispatcher.disconnect(
            self._louie_controller,
            ZWaveController.SIGNAL_CTRL_WAITING
        )
        dispatcher.disconnect(
            self._louie_controller,
            ZWaveController.SIGNAL_CONTROLLER
        )
        return True

    def _louie_controller(self, state, message, network, controller):
        """Louie dispatch for controller
        """
        with self.app.test_request_context():
            if network is None or controller is None:
                self.socketio.emit(
                    'my message response',
                    {'data': {'state': None, 'message': None}},
                    namespace='/ozwave'
                )
                logging.debug(
                    'OpenZWave controller message : '
                    'Nework or Controller is None.'
                )
            else:
                self.socketio.emit(
                    'my message response',
                    {'data': {'state': state, 'message': message}},
                    namespace='/ozwave'
                )
                logging.debug(
                    'OpenZWave controller message : state %s - message %s.',
                    state,
                    message
                )

    def stop(self):
        """Stop the tread
        """
        self.leave_room_node()
        self.leave_room_values()
        self.leave_room_controller()
        self.leave_room_network()
        self._stopevent.set()
        logging.info("Stop listener")


def start_listener(app_, socketio_):
    """Start the listener
    """
    global listener
    if listener is None:
        listener = ListenerThread(socketio_, app_)
        listener.start()
    return listener


def stop_listener():
    """Stop the listener
    """
    global listener
    listener.stop()
    listener = None
