# -*- coding: utf-8 -*-

"""The main views

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
from gevent import monkey
monkey.patch_all()

import logging # NOQA
from flask import render_template # NOQA
from pyozwweb.app import socketio, app # NOQA


logger = logging.getLogger('pyozwweb')


@app.errorhandler(404)
def not_found(_):
    return render_template('404.html'), 404


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/node')
@app.route('/node/<int:node_id>')
def node(node_id=1):
    return render_template('node.html', node_id=node_id)


@app.route('/values')
def values():
    return render_template('values.html')


@app.route('/controller')
def controller():
    return render_template('controller.html')


@app.route('/debug')
def debug():
    return render_template('debug.html')


@app.route('/map')
def map():
    return render_template('map.html')


@app.route('/scenes')
def scenes():
    return render_template('scenes.html')


@app.route('/chat')
def chat():
    return render_template('chat.html')
