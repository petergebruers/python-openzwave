# -*- coding: utf-8 -*-

"""The network socket

Thinking about rooms.
- A room for the network : state,
- A room for nodes : list, add, remove, ...
- A room for each nodes (nodeid_1): values, parameters, ...
- A room for the controller
- A room for values

When joining a room, you will receive message from it.



"""

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
try:
    from gevent import monkey

    monkey.patch_all()
except ImportError:
    pass

from flask import session, request, current_app
from flask.ext.socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room,
    close_room,
    disconnect
)

from pyozwweb.app import socketio, app
import logging


logger = logging.getLogger('pyozwweb')


@socketio.on('my echo event', namespace='/ozwave')
def echo_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug(
        "Client %s request echo message : %s",
        request.remote_addr,
        message
    )
    emit(
        'my response',
        {'data': message['data'], 'count': session['receive_count']}
    )


@socketio.on('disconnect request', namespace='/ozwave')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug("Client %s disconnects", request.remote_addr)
    emit(
        'my response',
        {'data': 'Disconnected!', 'count': session['receive_count']}
    )
    disconnect()


@socketio.on('connect', namespace='/ozwave')
def echo_connect():
    logging.debug("Client %s connects", request.remote_addr)
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('my network event', namespace='/ozwave')
def echo_network_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug("Client %s network event : %s", request.remote_addr, message)
    done = False
    keys = ['zoomlevel', 'zoomx', 'zoomy', 'panx', 'pany']
    kvals = {}
    for key in keys:
        if key in message:
            kvals[key] = message[key]
    logging.debug("kvals : %s", kvals)
    if len(kvals) > 0:
        current_app.extensions['zwnetwork'].kvals = kvals
        done = True
        # Should we emit an event ? Or the api should send a new
        # python louie mesage ? Or nothing
    if done is False:
        emit(
            'my network response',
            {
                'data': current_app.extensions['zwnetwork'].to_dict(),
                'count': session['receive_count']
            }
        )


@socketio.on('my node event', namespace='/ozwave')
def echo_node_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug("Client %s node event : %s", request.remote_addr, message)
    try:
        node_id = int(message['node_id'])
    except ValueError:
        node_id = 0
    except KeyError:
        node_id = 0
    if (
        node_id == 0 or
        node_id not in current_app.extensions['zwnetwork'].nodes
    ):
        logging.warning('Received invalid node_id : %s', message)
        return

    done = False
    keys = ['posx', 'posy']
    kvals = {}
    for key in keys:
        if key in message:
            kvals[key] = message[key]

    logging.debug("kvals : %s", kvals)

    if len(kvals) > 0:
        current_app.extensions['zwnetwork'].nodes[node_id].kvals = kvals
        done = True
        # Should we emit an event ? Or the api should send a new
        # python louie mesage ? Or nothing
    if 'name' in message:

        current_app.extensions['zwnetwork'].nodes[node_id].name = (
            message['name']
        )
        done = True

    if 'location' in message:
        current_app.extensions['zwnetwork'].nodes[node_id].location = (
            message['location']
        )
        done = True

    if done is False:
        logging.debug("Client %s node event : emit my node response")
        node = current_app.extensions['zwnetwork'].nodes[node_id]
        emit(
            'my node response',
            {
                'data': node.to_dict(),
                'count': session['receive_count']
            }
        )


@socketio.on('my nodes event', namespace='/ozwave')
def echo_nodes_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug("Client %s nodes event : %s", request.remote_addr, message)
    print("%s" % current_app.extensions['zwnetwork'].nodes_to_dict())

    network = current_app.extensions['zwnetwork']

    emit(
        'my nodes response',
        {
            'data': network.nodes_to_dict(),
            'count': session['receive_count']
        }
    )


@socketio.on('my controller event', namespace='/ozwave')
def echo_controller_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug(
        "Client %s controller event : %s",
        request.remote_addr,
        message
    )

    network = current_app.extensions['zwnetwork']
    emit(
        'my controller response',
        {
            'data': network.controller.to_dict(),
            'count': session['receive_count']
        }
    )


@socketio.on('my command event', namespace='/ozwave')
def echo_command_event(message):
    network = current_app.extensions['zwnetwork']

    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug(
        "Client %s controller command event : %s",
        request.remote_addr,
        message
    )
    data = dict(
        result=False,
        message="Command fail to start"
    )

    command = message['command']
    init_data = {
        'result': False,
        'message': '',
        'state': '',
        'command': command
    }
    # Emit a blank message to clean the old data in javascript
    emit(
        'my command response',
        {
            'data':  init_data,
            'count': session['receive_count']
        }
    )
    if command == 'no_command':
        # This is for first time launch. Return default values for javascript

        data = dict(
            message=network.controller.ctrl_last_message,
            state=network.controller.ctrl_last_state
        )
        emit(
            'my message response',
            {
                'data':  data,
                'count': session['receive_count']
            }
        )
        emit(
            'my command response',
            {
                'data':  init_data,
                'count': session['receive_count']
            }
        )
        return
    elif command == 'send_node_information':
        try:
            node_id = int(message['node_id'])
        except ValueError:
            node_id = -1
        except KeyError:
            node_id = -1

        if node_id not in network.nodes:
            data['result'] = False
            data['message'] = "Bad node_id"
        else:
            data['result'] = (
                network.controller.begin_command_send_node_information(node_id)
            )
            # data['result'] = True
    elif command == 'remove_failed_node':
        try:
            node_id = int(message['node_id'])
        except ValueError:
            node_id = -1
        except KeyError:
            node_id = -1

        if node_id not in network.nodes:
            data['result'] = False
            data['message'] = "Bad node_id"
        else:
            data['result'] = (
                network.controller.begin_command_remove_failed_node(node_id)
            )
            # data['result'] = True
    elif command == 'has_node_failed':
        try:
            node_id = int(message['node_id'])
        except ValueError:
            node_id = -1
        except KeyError:
            node_id = -1

        if node_id not in network.nodes:
            data['result'] = False
            data['message'] = "Bad node_id"
        else:
            data['result'] = (
                network.controller.begin_command_has_node_failed(node_id)
            )
            # data['result'] = True
    elif command == 'replace_failed_node':
        try:
            node_id = int(message['node_id'])
        except ValueError:
            node_id = -1
        except KeyError:
            node_id = -1

        if node_id not in network.nodes:
            data['result'] = False
            data['message'] = "Bad node_id"
        else:
            data['result'] = (
                network.controller.begin_command_replace_failed_node(node_id)
            )
        # data['result'] = True
    elif command == 'request_node_neigbhor_update':
        try:
            node_id = int(message['node_id'])
        except ValueError:
            node_id = -1
        except KeyError:
            node_id = -1
        if node_id not in network.nodes:
            data['result'] = False
            data['message'] = "Bad node_id"
        else:
            data['result'] = (
                network.controller.begin_command_request_node_neigbhor_update(
                    node_id
                )
            )
            # data['result'] = True
    elif command == 'request_network_update':
        data['result'] = (
            network.controller.begin_command_request_network_update()
        )
    elif command == 'replication_send':
        try:
            high_power = (
                bool(message['high_power'])
                if 'high_power' in message
                else False
            )
        except ValueError:
            high_power = False
        except KeyError:
            high_power = False
        data['result'] = (
            network.controller.begin_command_replication_send(high_power)
        )
        # data['result'] = True
    elif command == 'add_device':
        try:
            high_power = (
                bool(message['high_power'])
                if 'high_power' in message
                else False
            )
        except ValueError:
            high_power = False
        except KeyError:
            high_power = False

        data['result'] = (
            network.controller.begin_command_add_device(high_power)
        )
        # data['result'] = True
    elif command == 'remove_device':
        try:
            high_power = (
                bool(message['high_power'])
                if 'high_power' in message
                else False
            )
        except ValueError:
            high_power = False
        except KeyError:
            high_power = False

        data['result'] = (
            network.controller.begin_command_remove_device(high_power)
        )
        # data['result'] = True
    elif command == 'cancel_command':
        data['result'] = network.controller.cancel_command()
    if data['result'] is True:
        data['message'] = "Command started"
    logging.debug(
        "Client %s controller command event, data returned : %s",
        request.remote_addr,
        data
    )
    emit(
        'my command response',
        {
            'data':  data,
            'count': session['receive_count']
        }
    )


@socketio.on('my value event', namespace='/ozwave')
def echo_value_event(message):
    network = current_app.extensions['zwnetwork']
    session['receive_count'] = session.get('receive_count', 0) + 1
    node_id = message['node_id']
    value_id = message['value_id']
    logging.debug(
        "Client %s value event : %s",
        request.remote_addr,
        network.nodes[node_id].values[value_id].to_dict()
    )
    emit(
        'my value response',
        {
            'data': network.nodes[node_id].values[value_id].to_dict(),
            'count': session['receive_count']
        }
    )


@socketio.on('my scenes event', namespace='/ozwave')
def echo_scenes_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    logging.debug("Client %s scenes event : %s", request.remote_addr, message)
    print("%s" % current_app.extensions['zwnetwork'].get_scenes())
    emit(
        'my scenes response',
        {
            'data': current_app.extensions['zwnetwork'].get_scenes(),
            'count': session['receive_count']
        })
