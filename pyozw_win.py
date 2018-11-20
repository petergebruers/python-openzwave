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
import os
from pyozw_version import pyozw_version
import pyozw_progressbar
from distutils.command import build_clib
from subprocess import Popen, PIPE


class BuildCLib(build_clib.build_clib):

    def build_libraries(self, libraries):
        p_bar = None

        def spawn(cmd):
            if sys.version_info[0] > 2:
                dummy_return = b''
            else:
                dummy_return = ''

            p = Popen(
                cmd,
                stdout=PIPE,
                stderr=PIPE
            )
            while p.poll() is None:
                for line in iter(p.stdout.readline, dummy_return):
                    if line.strip():
                        if p_bar is None:
                            print(line.strip().decode('utf-8'))
                        else:
                            try:
                                sys.stdout.write(line)
                            except TypeError:
                                break

                for line in iter(p.stderr.readline, dummy_return):
                    if line.strip():
                        sys.stderr.write(line)

            if not p.stdout.closed:
                p.stdout.close()

            if not p.stderr.closed:
                p.stderr.close()

        self.compiler.spawn = spawn

        for (lib_name, build_info) in libraries:
            sources = build_info.get('sources')
            if sources is None or not isinstance(sources, (list, tuple)):
                raise build_clib.DistutilsSetupError(
                       "in 'libraries' option (library '%s'), "
                       "'sources' must be present and must be "
                       "a list of source filenames" % lib_name)
            sources = list(sources)

            # First, compile the source code to object files in the library
            # directory.  (This should probably change to putting object
            # files in a temporary build directory.)
            macros = build_info.get('macros')
            include_dirs = build_info.get('include_dirs')
            link_args = build_info.get('link_args')
            compile_args = build_info.get('compile_args')
            libs = build_info.get('libs')
            if libs is not None:
                self.compiler.set_libraries(libs)

            files = list(os.path.split(s)[1] for s in sources)
            file_break = int(len(files) / 8)

            pbar_files = []
            thread_files = []
            add_thread_files = []
            add_pbar_files = []

            while files:
                add_pbar_files += [files.pop(0)]
                add_thread_files += [sources.pop(0)]
                if len(add_pbar_files) == file_break:
                    pbar_files += [add_pbar_files[:]]
                    thread_files += [add_thread_files[:]]
                    del add_pbar_files[:]
                    del add_thread_files[:]

            if add_pbar_files:
                pbar_files += [add_pbar_files[:]]
                thread_files += [add_thread_files[:]]

            p_bar = pyozw_progressbar.CompileProgressBar(
                label='',
                marker="building 'OpenZwave' library",
                files=pbar_files
            )

            build_clib.log.info("building '%s' library", lib_name)

            objects = []

            import threading
            threads = []

            def do(srcs):

                objs = self.compiler.compile(
                    srcs,
                    output_dir=self.build_temp,
                    macros=macros,
                    include_dirs=include_dirs,
                    debug=self.debug,
                    extra_preargs=compile_args
                )
                objects.extend(objs)
                threads.remove(threading.current_thread())

            event = threading.Event()

            for sources in thread_files:
                t = threading.Thread(target=do, args=(sources,))
                t.daemon = True
                threads += [t]
                t.start()

            while threads:
                event.wait(0.1)

            p_bar.close()
            p_bar = None

            from distutils import msvccompiler

            if not self.compiler.initialized:
                self.compiler.initialize()
            (objects, output_dir) = self.compiler._fix_object_args(
                objects,
                self.build_clib
            )

            output_filename = self.compiler.library_filename(
                lib_name,
                output_dir=output_dir
            )

            if self.compiler._need_link(objects, output_filename):
                lib_args = link_args + objects + ['/OUT:' + output_filename]
                if self.debug:
                    lib_args = ['/VERBOSE'] + lib_args

                self.compiler.spawn([self.compiler.lib] + lib_args)

            else:
                msvccompiler.log.debug(
                    "skipping %s (up-to-date)",
                    output_filename
                )


VERSION_COMMAND = 'GIT-VS-VERSION-GEN.bat --quiet . winversion.cpp'

DLL_MAIN = '''

void PyInit_OpenZwave() {}

'''


def get_system_context(
    ctx,
    openzwave="openzwave",
    static=False,
    debug=False,
    build_path="openzwave\\build"
):
    import msvc

    environment = msvc.Environment(minimum_visual_c_version=14.0) # minimum_visual_c_version=14.0)
    for key, value in environment.build_environment.items():
        os.environ[key] = value
        print(key, value)
    os.environ['PATH'] += (
        ';' + os.path.join(os.environ['WindowsSdkVerBinPath'], environment.architecture)
    )

    if debug:
        print("get_system_context for windows")

    print(environment)

    # one feature i added is building a debugging version, this is only going
    # to happen if sys.executable ends with _d which identifies that the python
    # interpreter is a debugging build.

    if os.path.splitext(sys.executable)[0].endswith('_d'):
        ctx['define_macros'] += [('_DEBUG', 1)]
        ctx['libraries'] += ["setupapi", "msvcrtd", "ws2_32", "dnsapi"]
    else:
        ctx['libraries'] += ["setupapi", "msvcrt", "ws2_32", "dnsapi"]

    ctx['libraries'] += [environment.py_dependency.split('.')[0]]

    cpp_path = os.path.join(openzwave, 'cpp')
    src_path = os.path.join(cpp_path, 'src')

    if static:

        def iter_sources(src_path):
            bad_src = ['unix', 'winrt', 'mac', 'linux', 'examples', 'libusb']
            found = []
            for src_f in os.listdir(src_path):
                src = os.path.join(src_path, src_f)
                if os.path.isdir(src):
                    if src_f.lower() in bad_src:
                        continue

                    found += iter_sources(src)
                elif src_f.endswith('.c') or src_f.endswith('.cpp'):
                    found += [src]
            return found

        version_file = openzwave + "\\cpp\\build\\windows\\winversion.cpp"
        if os.path.exists(version_file):
            os.remove(version_file)

        os.chdir(os.path.abspath(openzwave + '\\cpp\\build\\windows'))
        p = Popen(VERSION_COMMAND)
        p.communicate()
        os.chdir(os.path.dirname(__file__))

        dll_main_path = openzwave + '\\cpp\\dllmain.cpp'
        with open(dll_main_path, 'w') as f:
            f.write(DLL_MAIN)

        define_macros = [
            ('WIN32', 1),
            ('DEBUG', 1),
            ('_LIB', 1),
            ('USE_HID', 1),
            ('_MT', 1),
            ('_DLL', 1),
            ('OPENZWAVE_MAKEDLL', 1),
            ('_MBCS', 1),
            ('NDEBUG', 1)
        ]

        if environment.architecture == 'x64':
            define_macros += [('WIN64', 1)]

        sources = iter_sources(os.path.abspath(os.path.join(openzwave, 'cpp')))

        for item in sources:
            print('    ' + repr(item) + ',')

        lib = [(
            'OpenZwave',
            dict(
                sources=sources,
                libs=['setupapi'],
                macros=define_macros,
                compile_args=[
                    '/Gy', # Enables function-level linking.
                    '/O2', # Creates fast code.
                    '/Gd', # Uses the __cdecl calling convention (x86 only).
                    '/Oy', # Omits frame pointer (x86 only).
                    '/Oi', # 	Generates intrinsic functions.
                    '/FS', # Forces writes to the program database (PDB) file to be serialized through MSPDBSRV.EXE.
                    '/Fd"{0}\\lib_build\\OpenZWave.pdb"'.format(build_path), # Renames program database file.
                    '/fp:precise',  # Specify floating-point behavior.
                    '/Zc:inline',  # Specifies standard behavior
                    '/Zc:wchar_t',  # Specifies standard behavior
                    '/Zc:forScope',  # Specifies standard behavior
                    '/wd4251',
                    '/wd4244',
                    '/wd4101',
                    '/wd4267',
                    '/wd4996'
                ],
                link_args=[
                    '/IGNORE:4098',
                    '/MACHINE:' + environment.architecture.upper(),
                    '/NOLOGO',
                    '/SUBSYSTEM:WINDOWS'
                ],
                include_dirs=[
                    openzwave + '\\cpp\\src',
                    openzwave + '\\cpp\\tinyxml',
                    openzwave + '\\cpp\\hidapi\\hidapi',
                ]
            )
        )]
        ctx['extra_objects'] = [
            os.path.join(build_path + '\\lib_build', 'OpenZWave.lib')
        ]

        ctx['include_dirs'] += [
            src_path,
            build_path,
            os.path.join(src_path, 'value_classes'),
            os.path.join(src_path, 'platform'),
            os.path.join(cpp_path, 'build', 'windows'),
        ]
    else:
        lib = []
        ctx['libraries'] += ["OpenZWave"]
        ctx['extra_compile_args'] += [
            src_path,
            os.path.join(src_path, 'value_classes'),
            os.path.join(src_path, 'platform'),
        ]

    ctx['define_macros'] += [
        ('CYTHON_FAST_PYCCALL', 1),
        ('_MT', 1),
        ('_DLL', 1)
    ]

    return lib


def get_openzwave(opzw_dir):
    url = 'https://codeload.github.com/OpenZWave/open-zwave/zip/master'

    from io import BytesIO
    import zipfile
    from pyozw_progressbar import DownloadProgressBar

    base_path = os.path.dirname(__file__)

    pbar = DownloadProgressBar('Downloading OpenZwave')

    with(pbar(url)) as f:
        dest_file = BytesIO(f.read())

    dest_file.seek(0)

    zip_ref = zipfile.ZipFile(dest_file, 'r')
    zip_ref.extractall(base_path)
    zip_ref.close()
    dest_file.close()

    os.rename(
        os.path.join(base_path, zip_ref.namelist()[0]),
        opzw_dir
    )


if __name__ == '__main__':
    print("Start pyozw_win")

    ctx = dict(
        name='libopenzwave',
        sources=['src-lib\\libopenzwave\\libopenzwave.pyx'],
        include_dirs=['src-lib\\libopenzwave'],
        define_macros=[
            ('PY_LIB_VERSION', pyozw_version),
            ('PY_SSIZE_T_CLEAN', 1),
            ('PY_LIB_FLAVOR', 'dev'),
            ('PY_LIB_BACKEND', 'cython')
        ],
        libraries=[],
        extra_objects=[],
        extra_compile_args=[
            '/Gy',  # Enables function-level linking.
            '/O2',  # Creates fast code.
            '/Gd',  # Uses the __cdecl calling convention (x86 only).
            '/Oy',  # Omits frame pointer (x86 only).
            '/Oi',  # Generates intrinsic functions.
            '/FS',  # Forces writes to the program database (PDB) file to be serialized through MSPDBSRV.EXE.
            '/fp:precise',  # Specify floating-point behavior.
            '/Zc:inline',  # Specifies standard behavior
            '/Zc:wchar_t',  # Specifies standard behavior
            '/Zc:forScope',  # Specifies standard behavior
            '/wd4996',
            '/wd4244',
            '/wd4005'
        ],
        extra_link_args=[],
        language='c++'
    )

    ozw_path = os.path.abspath('openzwave')

    if not os.path.exists(ozw_path):
        get_openzwave('openzwave')

    options = dict()

    library = get_system_context(
        ctx,
        static=True,
        debug=True
    )

    from distutils.core import setup
    from distutils.extension import Extension
    from Cython.Distutils import build_ext

    setup(
        script_args=['build'],
        version=pyozw_version,
        name='libopenzwave',
        description='libopenzwave',
        verbose=1,
        ext_modules=[Extension(**ctx)],
        libraries=library,
        cmdclass={'build_clib': BuildCLib, 'build_ext': build_ext},
        options=dict(
            build_clib=dict(
                build_clib="openzwave\\build\\lib_build",
                build_temp="openzwave\\build\\lib_build\\temp",
                compiler='msvc'
            ),
            build_ext=dict(
                build_lib="openzwave\\build",
                build_temp="openzwave\\build\\temp"
            )
        )
    )
