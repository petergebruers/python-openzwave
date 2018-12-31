# -*- coding: utf-8 -*-
"""
This file is part of **python-openzwave** project https://github.com/OpenZWave/python-openzwave.
    :platform: Unix, Windows, MacOS X
    :sinopsis: openzwave API

.. moduleauthor: bibi21000 aka Sébastien GALLET <bibi21000@gmail.com>

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
from __future__ import print_function
import sys
import time
import datetime
import threading


PY3 = sys.version_info[0] >= 3

# Terminal size methods.
# there are several different ways to obtain the terminal size.
# each of these ways works depending on OS and python flavor. when the Cursor
# instance is constructed it will test and discover the way that works. once
# this discovery is done the method that works is stored and that method is
# what gets called from then on out.


def _ipykernel():
    # Default to 79 characters for IPython notebooks
    ipython = globals().get('get_ipython')()
    zmqshell = __import__('ipykernel', fromlist=['zmqshell'])
    if isinstance(ipython, zmqshell.ZMQInteractiveShell):
        return 79, 24

    raise Exception


def _shutil():
    # This works for Python 3, but not Pypy3. Probably the best method if
    # it's supported so let's always try
    import shutil

    w, h = shutil.get_terminal_size()
    if w and h:
        # The off by one is needed due to progressbars in some cases, for
        # safety we'll always substract it.
        return w - 1, h

    raise Exception


def _blessings():
    blessings = __import__('blessings')

    terminal = blessings.Terminal()
    w = terminal.width
    h = terminal.height
    return w, h


def _cygwin():
    # needed for window's python in cygwin's xterm!
    # get terminal width src: http://stackoverflow.com/questions/263890/
    import subprocess

    proc = subprocess.Popen(
        ['tput', 'cols'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output = proc.communicate(input=None)
    w = int(output[0])

    proc = subprocess.Popen(
        ['tput', 'lines'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output = proc.communicate(input=None)
    h = int(output[0])

    return w, h


def _os():
    w = int(os.environ.get('COLUMNS'))
    h = int(os.environ.get('LINES'))
    return w, h


def _default():
    return 79, 24


FOREGROUND_DARK_BLACK = 0x0000
FOREGROUND_DARK_RED = 0x0004  # text color contains red.
FOREGROUND_DARK_GREEN = 0x0002  # text color contains green.
FOREGROUND_DARK_BLUE = 0x0001  # text color contains blue.
FOREGROUND_DARK_YELLOW = FOREGROUND_DARK_RED | FOREGROUND_DARK_GREEN
FOREGROUND_DARK_MAGENTA = FOREGROUND_DARK_RED | FOREGROUND_DARK_BLUE
FOREGROUND_DARK_CYAN = FOREGROUND_DARK_GREEN | FOREGROUND_DARK_BLUE
FOREGROUND_DARK_WHITE = (
    FOREGROUND_DARK_RED |
    FOREGROUND_DARK_GREEN |
    FOREGROUND_DARK_BLUE
)

# 0x0008 text color is intensified.

FOREGROUND_BRIGHT_BLACK = FOREGROUND_DARK_BLACK | 0x0008
FOREGROUND_BRIGHT_RED = FOREGROUND_DARK_RED | 0x0008
FOREGROUND_BRIGHT_GREEN = FOREGROUND_DARK_GREEN | 0x0008
FOREGROUND_BRIGHT_BLUE = FOREGROUND_DARK_BLUE | 0x0008
FOREGROUND_BRIGHT_YELLOW = FOREGROUND_DARK_YELLOW | 0x0008
FOREGROUND_BRIGHT_MAGENTA = FOREGROUND_DARK_MAGENTA | 0x0008
FOREGROUND_BRIGHT_CYAN = FOREGROUND_DARK_CYAN | 0x0008
FOREGROUND_BRIGHT_WHITE = FOREGROUND_DARK_WHITE | 0x0008

BACKGROUND_DARK_BLACK = 0x0000
BACKGROUND_DARK_RED = 0x0040  # background color contains red.
BACKGROUND_DARK_GREEN = 0x0020  # background color contains green.
BACKGROUND_DARK_BLUE = 0x0010  # background color contains blue.
BACKGROUND_DARK_YELLOW = BACKGROUND_DARK_RED | BACKGROUND_DARK_GREEN
BACKGROUND_DARK_MAGENTA = BACKGROUND_DARK_RED | BACKGROUND_DARK_BLUE
BACKGROUND_DARK_CYAN = BACKGROUND_DARK_GREEN | BACKGROUND_DARK_BLUE
BACKGROUND_DARK_WHITE = (
    BACKGROUND_DARK_RED |
    BACKGROUND_DARK_GREEN |
    BACKGROUND_DARK_BLUE
)

# 0x0080 background color is intensified.

BACKGROUND_BRIGHT_BLACK = BACKGROUND_DARK_BLACK | 0x0080
BACKGROUND_BRIGHT_RED = BACKGROUND_DARK_RED | 0x0080
BACKGROUND_BRIGHT_GREEN = BACKGROUND_DARK_GREEN | 0x0080
BACKGROUND_BRIGHT_BLUE = BACKGROUND_DARK_BLUE | 0x0080
BACKGROUND_BRIGHT_YELLOW = BACKGROUND_DARK_YELLOW | 0x0080
BACKGROUND_BRIGHT_MAGENTA = BACKGROUND_DARK_MAGENTA | 0x0080
BACKGROUND_BRIGHT_CYAN = BACKGROUND_DARK_CYAN | 0x0080
BACKGROUND_BRIGHT_WHITE = BACKGROUND_DARK_WHITE | 0x0080

UNDERSCORE = 0x8000
BOLD = 0x2000


class CursorBase(object):
    _std_lock = threading.RLock()

    def __init__(self, std, handle):
        self._std = std
        self._handle = handle
        # we now call _get_size to set the method for getting the terminal size
        self._get_size()

    def _get_position(self):
        raise NotImplementedError

    def _set_position(self, new_x=None, new_y=None):
        raise NotImplementedError

    @property
    def w(self):
        return self._get_size()[0]

    @property
    def h(self):
        return self._get_size()[1]

    @property
    def x(self):
        return self._get_position()[0]

    @x.setter
    def x(self, value):
        self._set_position(new_x=value)

    @property
    def y(self):
        return self._get_position()[1]

    @y.setter
    def y(self, value):
        self._set_position(new_y=value)

    def _process_color(self, color):
        raise NotImplementedError

    def __enter__(self):
        self._std_lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._std_lock.release()

    def _get_size(self):
        """
        Get the current size of your terminal

        Multiple returns are not always a good idea, but in this case it greatly
        simplifies the code so I believe it's justified. It's not the prettiest
        function but that's never really possible with cross-platform code.

        Returns:
            width, height: Two integers containing width and height
        """

        with self._std_lock:
            methods = [
                _ipykernel,
                _shutil,
                _blessings,
                _cygwin,
                self._get_terminal_size,
                _os,
                _default,
            ]

            # this is where we test each of the methods to see which one works
            # the _get_terminal_size method is located in a subclass of this
            # class. this is done because it is platform dependant
            for method in methods:
                # we use the try: except: here instead of in each method
                # because they are expensive to use. and there really is no
                # need to use them in the method once we discover that method
                # works.
                try:
                    w, h = method()
                except Exception:
                    continue

                if not w and not h:
                    continue

                # we create a wrapper for the method. we do this so that the
                # threading.Lock instance does not get called a bunch of times
                # calls to a threading.Lock object are expensive.
                def wrapper():
                    with self._std_lock:
                        return method()

                # we then set self._get_size to the method that works so
                # testing each of these ways each and every time we want to
                # get the terminal size does not get happen.

                self._get_size = wrapper
                return w, h

            raise SystemError('This should never happen')

    def _get_terminal_size(self):
        raise NotImplementedError

    def write(self, data, color=None, x=None, y=None):
        with self._std_lock:
            if hasattr(self._std, 'isatty') and self._std.isatty():
                self._set_position(x, y)

                if color is not None:
                    self._process_color(color)

            self._std.write(data)
            self._std.flush()


if sys.platform.startswith("win"):
    # This is where we make attachment to the Windows API in order to control
    # the console output. Windows does not use ansi codes to move the cursor
    # about the screen. We have to tell the console to move the cursor through
    # the use of a Windows API function.

    import ctypes
    from ctypes.wintypes import (
        BOOL,
        HANDLE,
        DWORD,
        _COORD,
        WORD,
        SMALL_RECT,
    )

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    COORD = _COORD
    POINTER = ctypes.POINTER

    kernel32 = ctypes.windll.Kernel32

    GetStdHandle = kernel32.GetStdHandle
    GetStdHandle.restype = HANDLE

    stdout_handle = GetStdHandle(DWORD(STD_OUTPUT_HANDLE))
    stderr_handle = GetStdHandle(DWORD(STD_ERROR_HANDLE))

    # BOOL WINAPI SetConsoleCursorPosition(
    #   _In_ HANDLE hConsoleOutput,
    #   _In_ COORD  dwCursorPosition
    # );
    SetConsoleCursorPosition = kernel32.SetConsoleCursorPosition
    SetConsoleCursorPosition.restype = BOOL

    # BOOL WINAPI GetConsoleScreenBufferInfo(
    #   _In_  HANDLE                      hConsoleOutput,
    #   _Out_ PCONSOLE_SCREEN_BUFFER_INFO lpConsoleScreenBufferInfo
    # );
    GetConsoleScreenBufferInfo = kernel32.GetConsoleScreenBufferInfo
    GetConsoleScreenBufferInfo.restype = BOOL


    class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ('dwSize', COORD),
            ('dwCursorPosition', COORD),
            ('wAttributes', WORD),
            ('srWindow', SMALL_RECT),
            ('dwMaximumWindowSize', COORD)
        ]


    CONSOLE_SCREEN_BUFFER_INFO = _CONSOLE_SCREEN_BUFFER_INFO


    class _CONSOLE_CURSOR_INFO(ctypes.Structure):
        _fields_ = [
            ('dwSize', DWORD),
            ('bVisible', BOOL)
        ]


    CONSOLE_CURSOR_INFO = _CONSOLE_CURSOR_INFO
    PCONSOLE_CURSOR_INFO = POINTER(_CONSOLE_CURSOR_INFO)

    # BOOL WINAPI GetConsoleCursorInfo(
    #   _In_  HANDLE               hConsoleOutput,
    #   _Out_ PCONSOLE_CURSOR_INFO lpConsoleCursorInfo
    # );
    GetConsoleCursorInfo = kernel32.GetConsoleCursorInfo
    GetConsoleCursorInfo.restype = BOOL

    # BOOL WINAPI SetConsoleCursorInfo(
    #   _In_       HANDLE              hConsoleOutput,
    #   _In_ const CONSOLE_CURSOR_INFO *lpConsoleCursorInfo
    # );
    SetConsoleCursorInfo = kernel32.SetConsoleCursorInfo
    SetConsoleCursorInfo.restype = BOOL

    # BOOL WINAPI SetConsoleTextAttribute(
    #   _In_ HANDLE hConsoleOutput,
    #   _In_ WORD   wAttributes
    # );
    SetConsoleTextAttribute = kernel32.SetConsoleTextAttribute
    SetConsoleTextAttribute.restype = BOOL


    class Cursor(CursorBase):

        def _get_position(self):
            with self._std_lock:
                lpConsoleScreenBufferInfo = CONSOLE_SCREEN_BUFFER_INFO()
                GetConsoleScreenBufferInfo(
                    self._handle,
                    ctypes.byref(lpConsoleScreenBufferInfo)
                )
                return (
                    lpConsoleScreenBufferInfo.dwCursorPosition.X,
                    lpConsoleScreenBufferInfo.dwCursorPosition.Y
                )

        def _set_position(self, new_x=None, new_y=None):
            with self._std_lock:
                old_x, old_y = self._get_position()

                if new_x is None:
                    new_x = old_x

                if new_y is None:
                    new_y = old_y

                coord = COORD()
                coord.X = new_x
                coord.Y = new_y
                SetConsoleCursorPosition(self._handle, coord)

        def _get_terminal_size(self):
            lpConsoleScreenBufferInfo = CONSOLE_SCREEN_BUFFER_INFO()
            GetConsoleScreenBufferInfo(
                self._handle,
                ctypes.byref(lpConsoleScreenBufferInfo)
            )
            return (
                lpConsoleScreenBufferInfo.dwSize.X,
                lpConsoleScreenBufferInfo.dwSize.Y
            )

        def _process_color(self, color):

            if color & BOLD:
                color ^= BOLD

            SetConsoleTextAttribute(self._handle, WORD(color))

else:
    import fcntl
    import termios
    import struct
    import tty
    import os

    _UP = u'\u001b[{0}A'
    _DOWN = u'\u001b[{0}B'
    _RIGHT = u'\u001b[{0}C'
    _LEFT = u'\u001b[{0}D'

    BACKGROUND_DARK_BLACK = 0x0200

    _COLOR_XREF = {
        FOREGROUND_DARK_BLACK:     u'\u001b[30m',
        FOREGROUND_DARK_RED:       u'\u001b[31m',
        FOREGROUND_DARK_GREEN:     u'\u001b[32m',
        FOREGROUND_DARK_BLUE:      u'\u001b[34m',
        FOREGROUND_DARK_YELLOW:    u'\u001b[33m',
        FOREGROUND_DARK_MAGENTA:   u'\u001b[35m',
        FOREGROUND_DARK_CYAN:      u'\u001b[36m',
        FOREGROUND_DARK_WHITE:     u'\u001b[37m',
        FOREGROUND_BRIGHT_BLACK:   u'\u001b[30m;1m',
        FOREGROUND_BRIGHT_RED:     u'\u001b[31m;1m',
        FOREGROUND_BRIGHT_GREEN:   u'\u001b[32m;1m',
        FOREGROUND_BRIGHT_BLUE:    u'\u001b[34m;1m',
        FOREGROUND_BRIGHT_YELLOW:  u'\u001b[33m;1m',
        FOREGROUND_BRIGHT_MAGENTA: u'\u001b[35m;1m',
        FOREGROUND_BRIGHT_CYAN:    u'\u001b[36m;1m',
        FOREGROUND_BRIGHT_WHITE:   u'\u001b[37m;1m',
        BACKGROUND_DARK_BLACK:     u'\u001b[40m',
        BACKGROUND_DARK_RED:       u'\u001b[41m',
        BACKGROUND_DARK_GREEN:     u'\u001b[42m',
        BACKGROUND_DARK_BLUE:      u'\u001b[44m',
        BACKGROUND_DARK_YELLOW:    u'\u001b[43m',
        BACKGROUND_DARK_MAGENTA:   u'\u001b[45m',
        BACKGROUND_DARK_CYAN:      u'\u001b[46m',
        BACKGROUND_DARK_WHITE:     u'\u001b[47m',
        BACKGROUND_BRIGHT_BLACK:   u'\u001b[40m;1m',
        BACKGROUND_BRIGHT_RED:     u'\u001b[41m;1m',
        BACKGROUND_BRIGHT_GREEN:   u'\u001b[42m;1m',
        BACKGROUND_BRIGHT_BLUE:    u'\u001b[44m;1m',
        BACKGROUND_BRIGHT_YELLOW:  u'\u001b[43m;1m',
        BACKGROUND_BRIGHT_MAGENTA: u'\u001b[45m;1m',
        BACKGROUND_BRIGHT_CYAN:    u'\u001b[46m;1m',
        BACKGROUND_BRIGHT_WHITE:   u'\u001b[47m;1m',
        BOLD:                      u'\u001b[1m',
        UNDERSCORE:                u'\u001b[4m',
    }


    def _ioctl_GWINSZ(fd):
        size = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        return size


    class Cursor(CursorBase):

        def _get_position(self):
            with self._std_lock:
                fd = sys.stdin.fileno()
                prev = termios.tcgetattr(fd)

                self._std.write("\033[6n")
                self._std.flush()
                resp = ""
                ch = ''

                try:
                    tty.setraw(fd)
                    while ch != 'R':
                        ch = sys.stdin.read(1)
                        resp += ch
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, prev)

                return (int(c) for c in resp[2:-1].split(';'))

        def _set_position(self, new_x=None, new_y=None):
            with self._std_lock:
                old_x, old_y = self._get_position()

                if new_x is not None:
                    if new_x > old_x:
                        self._std.write(_RIGHT.format(new_x - old_x))
                        self._std.flush()

                    elif new_x < old_x:
                        self._std.write(_LEFT.format(old_x - new_x))
                        self._std.flush()

                if new_y is not None:
                    if new_y > old_y:
                        self._std.write(_DOWN.format(new_y - old_y))
                        self._std.flush()

                    elif new_y < old_y:
                        self._std.write(_UP.format(old_y - new_y))
                        self._std.flush()

        def _get_terminal_size(self):
            size = _ioctl_GWINSZ(0) or _ioctl_GWINSZ(1) or _ioctl_GWINSZ(2)

            if not size:
                fd = os.open(os.ctermid(), os.O_RDONLY)
                size = _ioctl_GWINSZ(fd)
                os.close(fd)

            return int(size[1]), int(size[0])

        def _process_color(self, color):
            color_data = u''

            if color & BOLD:
                color ^= BOLD
                color_data += _COLOR_XREF[BOLD]

            if color & UNDERSCORE:
                color ^= UNDERSCORE
                color_data += _COLOR_XREF[UNDERSCORE]

            color_data += _COLOR_XREF[color]

            self._std.write(color_data)
            self._std.flush()


    stdout_handle = sys.stdout.fileno()
    stderr_handle = sys.stderr.fileno()

std_out_cursor = Cursor(sys.stdout, stdout_handle)
std_err_cursor = Cursor(sys.stderr, stderr_handle)


def remap(value, old_min=0, old_max=0, new_min=0, new_max=0):
    old_range = old_max - old_min
    new_range = new_max - new_min

    return (
        int((((value - old_min) * new_range) / old_range)) + new_min
    )


class ProgressBar(object):
    TEMPLATE = (
        '{label} {file_name}\n'
        ' {percent}% {count}\n'
        ' Elapsed: {elapsed} Remaining: {remaining} Estimated: {estimated} \n'
        '\n'
    )

    def __init__(self, label):
        self.count = 0
        self.count_start = None
        self.count_times = []
        self.start_time = None
        self.label = label
        self.last_line_len = None
        self.num_lines = len(self.TEMPLATE.split('\n'))
        self.is_finished = False
        self.row_num = std_out_cursor.y

    def finish(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.is_finished = True

    def start(self):
        with std_out_cursor as std:
            std.write('\n' * self.num_lines, x=0, y=self.row_num)
            self.start_time = time.time()
            self.update(0, 0, file_name='')

    def update(
        self,
        count,
        percent,
        file_name,
        **kwargs
    ):
        elapsed = time.time() - self.start_time

        if count:
            avg = elapsed / count
            remaining = (52 - count) * avg
            estimated = elapsed + remaining

            remaining = '0' + str(
                datetime.timedelta(seconds=int(remaining))
            )
            estimated = '0' + str(
                datetime.timedelta(seconds=int(estimated))
            )
        else:
            remaining = '99:99:99'
            estimated = '99:99:99'

        percent = str(percent)
        percent = ' ' * (3 - len(percent)) + percent

        elapsed = '0' + str(
            datetime.timedelta(seconds=int(elapsed))
        )

        line = self.TEMPLATE.format(
            label=self.label,
            percent=percent,
            count='#' * count + ' ' * (52 - count),
            elapsed=elapsed,
            remaining=remaining,
            estimated=estimated,
            file_name=file_name,
            **kwargs
        )

        lines = line.split('\n')

        if self.last_line_len is not None:
            for i, line in enumerate(lines):
                old_len = self.last_line_len[i]
                self.last_line_len[i] = len(line)
                if old_len > len(line):
                    lines[i] += ' ' * (old_len - len(line))
        else:
            self.last_line_len = list(len(line) for line in lines)

        with std_out_cursor as std:
            std.write('\n'.join(lines), x=0, y=self.row_num)


class DownloadProgressBar(ProgressBar):
    TEMPLATE = (
        '{label} - {file_name} \n'
        '  {percent}% {count} {speed:.2f} KB/s {downloaded:.2f} MB\n'        
        '  Elapsed: {elapsed} Remaining: {remaining} Total: {estimated} \n'
    )

    def __init__(self, label):
        self.total_size = 0
        self.speed_samples = []
        self.temp_file = None
        ProgressBar.__init__(self, label)

    def reporthook(self, count, block_size, total_size):
        if count == 0:
            self.start()
            self.total_size = total_size
            self.count = total_size / block_size
            downloaded = 0
            speed_avg = 0

        else:
            duration = time.time() - self.start_time
            progress_size = count * block_size

            if duration:
                speed = progress_size / (1024 * duration)
            else:
                speed = progress_size

            downloaded = progress_size / (1024 * 1024)

            self.speed_samples += [speed]
            speed_avg = sum(self.speed_samples) / len(self.speed_samples)

        if count * block_size >= total_size:
            count = 52
            percent = 100

        else:
            count = remap(
                count,
                old_max=self.count,
                new_max=52
            )

            percent = remap(
                count * block_size,
                old_max=total_size,
                new_max=100
            )

        self.update(
            count,
            percent,
            '',
            downloaded=downloaded,
            speed=speed_avg
        )

    def __call__(self, url):
        self.get(url)
        return self

    def __enter__(self):
        self.temp_file = open(self.temp_file, 'rb')
        return self.temp_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.temp_file.close()
        self.close()

    def close(self):
        if self.start is not None:
            with std_out_cursor as std:
                std.write('\n\n\n', x=0, y=self.row_num + self.num_lines)

    def get(self, url):
        try:
            from urllib2 import urlretrieve
        except ImportError:
            from urllib.request import urlretrieve

        self.temp_file = urlretrieve(url, reporthook=self.reporthook)[0]


class CompileProgressBar(object):

    def __init__(self, label):
        self.counts = {}
        self.label = label
        self.stdout = sys.stdout
        self.files = {}
        self.start = None
        std_out_cursor.write('\n' + label + '\n')
        self.row_num = std_out_cursor.y
        self.num_bars = 0
        self.bars = []
        self.file_lock = threading.Lock()

    def close(self):
        if self.start is None:
            for bar in self.bars:
                if not bar.is_finished:
                    bar.finish(52, 100, file_name='Finished')
            with std_out_cursor as std:
                std.write('\n\n', x=0, y=self.row_num)

        sys.stdout = self.stdout

    def add_bar(self, files):
        if self.num_bars:
            row_num = self.num_bars * len(ProgressBar.TEMPLATE.split('\n'))
            row_num += self.row_num
        else:
            row_num = self.row_num

        with std_out_cursor as std:
            std.write(
                '\n' * len(ProgressBar.TEMPLATE.split('\n')),
                x=0,
                y=row_num
            )
            std.x = 0
            std.y = row_num

        self.num_bars += 1
        bar = ProgressBar('')
        self.counts[bar] = len(files)
        self.files[bar] = files
        self.bars += [bar]

    def write(self, line):
        if PY3:
            line = line.decode('ascii')

        if self.start is None:
            self.start = time.time()

        for bar, files in self.files.items():
            if line in files:
                break
        else:
            return

        file_count = self.counts[bar]
        files = self.files[bar]

        if bar.start_time is None:
            bar.label = (
                'Build Thread - ' + str(threading.current_thread().ident) + ':'
            )
            bar.start()

        f = line.strip()

        if f in files:
            self.file_lock.acquire()
            files.remove(f)
            self.files[bar] = files[:]

            count = remap(
                file_count - len(files),
                old_max=file_count,
                new_max=52
            )
            percent = remap(
                file_count - len(files),
                old_max=file_count,
                new_max=100
            )

            if len(files) == 0:
                bar.finish(52, 100, file_name='Finished')
            else:
                bar.update(count, percent, f)

            self.file_lock.release()


if __name__ == '__main__':
    import random

    test_files = []

    used = []

    for _ in range(1, 11):
        test_file = []
        for _ in range(1, 31):
            num = random.randrange(50, 50000)
            while num in used:
                num = random.randrange(50, 50000)

            used += [num]

            test_file += [str(num) + '.h']
        test_files += [test_file]

    cpb = CompileProgressBar('Compile Test', 'Test Started', test_files)

    event = threading.Event()

    sys.stdout.write('Test Started\n')
    sys.stdout.flush()
    event.wait(0.1)

    threads = []

    def do(tst_files):
        for tst_file in tst_files:
            wait = random.randrange(0, 200) / 100.00
            event.wait(wait)
            sys.stdout.write(tst_file + '\n')
            sys.stdout.flush()
            event.wait(0.1)
        threads.remove(threading.current_thread())

    for test_file_list in test_files:
        t = threading.Thread(target=do, args=(test_file_list,))
        t.daemon = True
        threads += [t]
        t.start()

    while threads:
        event.wait(0.1)

    cpb.close()
