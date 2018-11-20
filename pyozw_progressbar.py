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

_stdout = sys.stdout
std_lock = threading.RLock()


class CursorBase(object):

    def _get_position(self):
        raise NotImplementedError

    def _set_position(self, new_x=None, new_y=None):
        raise NotImplementedError

    def _get_size(self):
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

    def write(self, data, x=None, y=None):
        with std_lock:
            self._set_position(x, y)
            _stdout.write(data)
            _stdout.flush()


if sys.platform.startswith("win"):
    import ctypes
    from ctypes.wintypes import (
        BOOL,
        HANDLE,
        DWORD,
        _COORD,
        WORD,
        SMALL_RECT
    )

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    STD_OUTPUT_HANDLE = -11

    COORD = _COORD

    kernel32 = ctypes.windll.Kernel32

    GetStdHandle = kernel32.GetStdHandle
    GetStdHandle.restype = HANDLE

    hConsoleOutput = GetStdHandle(DWORD(STD_OUTPUT_HANDLE))

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


    class Cursor(CursorBase):

        def _get_position(self):
            with std_lock:
                lpConsoleScreenBufferInfo = CONSOLE_SCREEN_BUFFER_INFO()
                GetConsoleScreenBufferInfo(
                    hConsoleOutput,
                    ctypes.byref(lpConsoleScreenBufferInfo)
                )
                return (
                    lpConsoleScreenBufferInfo.dwCursorPosition.X,
                    lpConsoleScreenBufferInfo.dwCursorPosition.Y
                )

        def _set_position(self, new_x=None, new_y=None):
            with std_lock:
                old_x, old_y = self._get_position()

                if new_x is None:
                    new_x = old_x

                if new_y is None:
                    new_y = old_y

                coord = COORD()
                coord.X = new_x
                coord.Y = new_y
                SetConsoleCursorPosition(hConsoleOutput, coord)

        def _get_size(self):
            with std_lock:
                lpConsoleScreenBufferInfo = CONSOLE_SCREEN_BUFFER_INFO()
                GetConsoleScreenBufferInfo(
                    hConsoleOutput,
                    ctypes.byref(lpConsoleScreenBufferInfo)
                )
                return (
                    lpConsoleScreenBufferInfo.dwMaximumWindowSize.X,
                    lpConsoleScreenBufferInfo.dwMaximumWindowSize.Y
                )

else:
    import fcntl
    import termios
    import struct
    import tty

    _UP = '\u001b[{0}A'
    _DOWN = '\u001b[{0}B'
    _LEFT = '\u001b[{0}C'
    _RIGHT = '\u001b[{0}D'


    class Cursor(CursorBase):

        def _get_position(self):
            with std_lock:
                fd = sys.stdin.fileno()
                prev = termios.tcgetattr(fd)

                _stdout.write("\033[6n")
                _stdout.flush()
                resp = ""
                ch = ''

                try:
                    tty.setraw(fd)
                    while ch != 'R':
                        ch = sys.stdin.read(1)
                        resp += ch
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, prev)

                try:
                    return (int(c) for c in resp[2:-1].split(';'))
                except:
                    return -1, -1

        def _set_position(self, new_x=None, new_y=None):
            with std_lock:
                old_x, old_y = self._get_position()

                if new_x is not None:
                    if new_x > old_x:
                        _stdout.write(_RIGHT.format(new_x - old_x))
                        _stdout.flush()

                    elif new_x < old_x:
                        _stdout.write(_LEFT.format(old_x - new_x))
                        _stdout.flush()

                if new_y is not None:
                    if new_y > old_y:
                        _stdout.write(_DOWN.format(new_y - old_y))
                        _stdout.flush()

                    elif new_y < old_y:
                        _stdout.write(_UP.format(old_y - new_y))
                        _stdout.flush()

        def _get_size(self):
            with std_lock:
                t_data = fcntl.ioctl(
                    0,
                    termios.TIOCGWINSZ,
                    struct.pack('HHHH', 0, 0, 0, 0)
                )

                th, tw = struct.unpack('HHHH', t_data)[:2]
                return tw, th


cursor = Cursor()


def remap(value, old_min=0, old_max=0, new_min=0, new_max=0):
    old_range = old_max - old_min
    new_range = new_max - new_min

    return (
        int((((value - old_min) * new_range) / old_range)) + new_min
    )


print_lock = threading.Lock()


class ProgressBar(object):
    TEMPLATE = (
        '{label}\n'
        '    {percent}% '
        '{count} {file_name}\n'
        '    Elapsed: {elapsed} '
        'Remaining: {remaining} '
        'Estimated: {estimated} \n'
    )

    def __init__(self, label):
        self.count = 0
        self.count_start = None
        self.count_times = []
        self.start_time = None
        self.label = label
        self.last_line_len = None
        self.num_lines = len(self.TEMPLATE.split('\n'))
        self.row_num = None
        self.is_finished = False

    def finish(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.is_finished = True

    def start(self):
        with print_lock:
            self.row_num = cursor.y
            cursor.write('\n' * self.num_lines, x=0, y=self.row_num)
            self.start_time = time.time()
            self.update(0, 0, file_name='')
            cursor.x = 0
            cursor.y = self.row_num + self.num_lines

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
            remaining = (50 - count) * avg
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
            count='#' * count + ' ' * (50 - count),
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

        cursor.write('\n'.join(lines), x=0, y=self.row_num)


class DownloadProgressBar(ProgressBar):
    TEMPLATE = (
        '\r'
        '\u001b[35m{label} '
        '\u001b[32m{percent}% '
        '\u001b[33m{count} '
        '\u001b[31m{speed:.2f} KB/s '
        '\u001b[31m{downloaded:.2f} MB '        
        '\u001b[96mElapsed: \u001b[31m{elapsed} '
        '\u001b[96mRemaining: \u001b[31m{remaining} '
        '\u001b[96mTotal: \u001b[31m{estimated} '
        '\u001b[1m{file_name}'
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

        print_lock.acquire()

        if count * block_size >= total_size:
            count = 50
            percent = 100

        else:
            count = remap(
                count,
                old_max=self.count,
                new_max=50
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

        print_lock.release()

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
            print_lock.acquire()
            cursor.write('\n\n\n', x=0, y=self.row_num + self.num_lines)
            print_lock.release()

    def get(self, url):
        try:
            from urllib2 import urlretrieve
        except ImportError:
            from urllib.request import urlretrieve

        self.temp_file = urlretrieve(url, reporthook=self.reporthook)[0]


class CompileProgressBar(object):

    def __init__(self, label, marker, files=[]):
        self.counts = list(len(fls) for fls in files)
        self.label = label
        self.marker = marker
        self.stdout = sys.stdout
        sys.stdout = self
        self.files = files
        self.start = None
        cursor.write('\n')
        self.row_num = cursor.y
        self.num_bars = len(self.files)

        self.bars = list(
            ProgressBar('Build Thread - ' + str(i) + ':')
            for i in range(1, self.num_bars + 1)
        )
        self.file_lock = threading.Lock()

    def flush(self):
        pass

    def isatty(self):
        return True

    def close(self):
        if self.start is not None:

            for bar in self.bars:
                if not bar.is_finished:
                    bar.finish(50, 100, file_name='Finished')

            cursor.write('\n\n', x=0, y=self.row_num)

        sys.stdout = self.stdout

    def write(self, line):

        if PY3:
            line = line.decode('ascii')

        if str(self.marker) in line:
            with print_lock:
                cursor.write(self.label)
                cursor.write('\n')
                cursor.write('-' * (len(self.label) * 3))
                cursor.write('\n')

            self.start = time.time()

            for bar in self.bars:
                bar.start()

            self.row_num = cursor.y

        elif self.start is not None:
            f = line.strip()
            with self.file_lock:
                for i, files in enumerate(self.files[:]):
                    if f in files:
                        files.remove(f)
                        self.files[i] = files[:]
                        bar = self.bars[i]
                        file_count = self.counts[i]

                        count = remap(
                            file_count - len(files),
                            old_max=file_count,
                            new_max=50
                        )
                        percent = remap(
                            file_count - len(files),
                            old_max=file_count,
                            new_max=100
                        )

                        if len(files) == 0:
                            sys.stderr.write('finished!\n')
                            bar.finish(50, 100, file_name='Finished')
                        else:
                            bar.update(count, percent, f)

                        break


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
