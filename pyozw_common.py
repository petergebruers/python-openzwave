# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import shutil
import threading
import subprocess
import distutils.core
import distutils.command.build_clib
import distutils.errors
import pyozw_version


DLL_MAIN = '''

void PyInit_OpenZwave() {}

'''

DEBUG_BUILD = os.path.splitext(sys.executable)[0].endswith('_d')


PYTHON_LIB = (
    'python%s%s' % (sys.hexversion >> 24, (sys.hexversion >> 16) & 0xff)
)


print_lock = threading.Lock()


def build_dll_main(openzwave):
    dll_main_path = openzwave + '\\cpp\\dllmain.cpp'
    with open(dll_main_path, 'w') as f:
        f.write(DLL_MAIN)


def get_sources(src_path, ignore):
    found = []
    for src_f in os.listdir(src_path):
        src = os.path.join(src_path, src_f)
        if os.path.isdir(src):
            if src_f.lower() in ignore:
                continue

            found += get_sources(src, ignore)
        elif src_f.endswith('.c') or src_f.endswith('.cpp'):
            found += [src]
    return found


def get_openzwave(opzw_dir):
    url = 'https://codeload.github.com/OpenZWave/open-zwave/zip/master'


class Extension(distutils.core.Extension):

    def __init__(
        self,
        openzwave,
        flavor,
        static,
        backend,
        extra_objects,
        sources,
        include_dirs,
        define_macros,
        libraries,
        extra_compile_args
    ):
        name = 'libopenzwave'
        language = 'c++'

        define_macros += [
            ('PY_LIB_VERSION', pyozw_version.pyozw_version),
            ('PY_LIB_FLAVOR', flavor),
            ('PY_LIB_BACKEND', backend),
            ('CYTHON_FAST_PYCCALL', 1),
            ('_MT', 1),
            ('_DLL', 1)
        ]

        if backend == 'cython':
            define_macros += [('PY_SSIZE_T_CLEAN', 1)]
            sources += ["src-lib/libopenzwave/libopenzwave.pyx"]

        elif backend == 'cpp':

            define_macros += [('PY_SSIZE_T_CLEAN', 1)]
            sources += [
                "openzwave-embed/open-zwave-master/"
                "python-openzwave/src-lib/libopenzwave/libopenzwave.cpp"
            ]
            include_dirs += ["src-lib/libopenzwave"]

        cpp_path = os.path.join(openzwave, 'cpp')
        src_path = os.path.join(cpp_path, 'src')

        if static:
            include_dirs += [
                src_path,
                os.path.join(src_path, 'value_classes'),
                os.path.join(src_path, 'platform')
            ]

        distutils.core.Extension.__init__(
            self,
            name=name,
            language=language,
            extra_objects=extra_objects,
            sources=sources,
            include_dirs=include_dirs,
            define_macros=define_macros,
            libraries=libraries,
            extra_compile_args=extra_compile_args
        )


class Library(object):

    def __init__(
        self,
        openzwave,
        sources=[],
        define_macros=[],
        libraries=[],
        library_dirs=[],
        include_dirs=[],
        extra_compile_args=[],
        extra_link_args=[]
    ):
        self.openzwave = openzwave
        self.name = 'OpenZwave'
        self.sources = sources
        self.define_macros = define_macros
        self.libraries = libraries
        self.library_dirs = library_dirs
        self.include_dirs = include_dirs
        self.extra_compile_args = extra_compile_args
        self.extra_link_args = extra_link_args

    def clean_openzwave(self):
        distutils.command.build_clib.log.info(
            'Removing {0}'.format(self.openzwave)
        )
        try:
            shutil.rmtree(self.openzwave)
            distutils.command.build_clib.log.info(
                'Successfully removed {0}'.format(self.openzwave)
            )
        except OSError:
            distutils.command.build_clib.log.error(
                'Failed to remove {0}'.format(self.openzwave)
            )
        return True

    def clean_cython(self):
        try:
            os.remove('src-lib/libopenzwave/libopenzwave.cpp')
        except Exception:
            pass

    @property
    def so_path(self):
        import pyozw_pkgconfig
        ldpath = pyozw_pkgconfig.libs_only_l('libopenzwave')[2:]

        distutils.command.build_clib.log.info(
            "Running ldconfig on {0}... be patient ...".format(ldpath)
        )

        return ldpath

    def clean(self, command_class):
        distutils.command.build_clib.log.info(
            "Clean OpenZwave in {0} ... be patient ...".format(
                self.openzwave
            )
        )



class build_clib(distutils.command.build_clib.build_clib):

    def build_libraries(self, libraries):
        self.compiler.spawn = self.spawn

        for lib in self.original_libraries:
            if 'clean' in sys.argv:

                lib.clean(self)

            if self.build_type == 'install':
                distutils.command.build_clib.log.info(
                    "Install OpenZwave... be patient ..."
                )
                lib.install(self)
                distutils.command.build_clib.log.info(
                    "OpenZwave installed and loaded."
                )

            else:
                distutils.command.build_clib.log.info(
                    "building '{0}' library".format(lib.name)
                )
                lib.build(self)

    def finalize_options(self):
        libraries = self.distribution.libraries
        self.original_libraries = libraries
        self.build_type = sys.argv[0].lower()
        converted_libraries = []

        for lib in libraries:
            build_info = dict(
                sources=lib.sources,
                macros=lib.define_macros,
                include_dirs=lib.include_dirs,
            )

            converted_libraries += [(lib.name, build_info)]

        self.distribution.libraries = converted_libraries

        distutils.command.build_clib.build_clib.finalize_options(self)

    @staticmethod
    def spawn(cmd, search_path=1, level=1, cwd=None):
        if sys.version_info[0] > 2:
            dummy_return = b''
            line_endings = [b'.cpp', b'.c']
        else:
            dummy_return = ''
            line_endings = ['.cpp', '.c']

        if cwd is None:

            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd
            )

        while p.poll() is None:
            with print_lock:
                for line in iter(p.stdout.readline, dummy_return):
                    line = line.strip()
                    if line:
                        if sys.platform.startswith('win'):
                            for ending in line_endings:
                                if line.endswith(ending):
                                    if sys.version_info[0] > 2:
                                        line = b'compiling ' + line + b'...'
                                    else:
                                        line = 'compiling ' + line + '...'
                                    break
                        if sys.version_info[0] > 2:
                            sys.stdout.write(line.decode('utf-8') + '\n')
                        else:
                            sys.stdout.write(line + '\n')

                for line in iter(p.stderr.readline, dummy_return):
                    line = line.strip()
                    if line:
                        if sys.version_info[0] > 2:
                            sys.stderr.write(line.decode('utf-8') + '\n')
                        else:
                            sys.stderr.write(line + '\n')

        if not p.stdout.closed:
            p.stdout.close()

        if not p.stderr.closed:
            p.stderr.close()


