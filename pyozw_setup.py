#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file is part of **python-openzwave** project https://github.com/OpenZWave/python-openzwave.
    :platform: Unix, Windows, MacOS X

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

Build process :
- ask user what to do (zmq way in pip)
- or parametrizes it
    --dev : use local sources and cythonize way (for python-openzwave devs, ...)
    --embed : use local sources and cpp file (for third parties packagers, ...)
    --git : download openzwave from git (for geeks)
    --shared : use pkgconfig and cython (for debian devs and common users)
    --pybind : use pybind alternative (not tested)
    --auto (default) : try static, shared and cython, fails if it can't
"""
import os
import sys
import glob
import shutil
import setuptools
from distutils import log
from distutils.spawn import find_executable
from distutils.command.build import build as _build
from distutils.command.clean import clean as _clean
from setuptools.command.install import install as _install
from setuptools.command.bdist_egg import bdist_egg as _bdist_egg
from setuptools.command.develop import develop as _develop
from pyozw_version import pyozw_version

try:
    _bdist_wheel = __import__('wheel.bdist_wheel', fromlist=['bdist_wheel'])[0]
except ImportError:
    log.warn(
        "ImportError in : from wheel.bdist_wheel "
        "import bdist_wheel as _bdist_wheel"
    )
    _bdist_wheel = None


PY3 = sys.version_info[0] > 2
LOCAL_OPENZWAVE = os.getenv('LOCAL_OPENZWAVE', 'openzwave')
SETUP_DIR = os.path.dirname(os.path.abspath(__file__))


if sys.platform.startswith('win'):
    from pyozw_windows import Library, Extension
elif sys.platform.startswith('darwin'):
    from pyozw_darwin import Library, Extension
elif sys.platform.startswith('linux'):
    from pyozw_linux import Library, Extension
elif sys.platform.startswith('freebsd'):
    from pyozw_freebsd import Library, Extension
elif sys.platform.startswith('sunos'):
    from pyozw_sunos import Library, Extension
elif sys.platform.startswith('cygwin'):
    from pyozw_cygwin import Library, Extension
else:
    raise RuntimeError('OS {0} is not supported'.format(sys.platform))


class Template(object):

    def __init__(
        self,
        openzwave=None,
        cleanozw=False,
        sysargv=None,
        flavor='embed',
        backend='cython',
        static=True
    ):
        if flavor:
            flavor = flavor.replace('--flavor=', '')
        else:
            flavor = 'embed'

        if not backend:
            backend = 'cython'

        self._extension = Extension(
            openzwave=openzwave,
            flavor=flavor,
            static=static,
            backend=backend
        )

        self.library = Library(openzwave)

        self.openzwave = openzwave
        self.cleanozw = cleanozw
        self.flavor = flavor
        self.backend = backend
        self.sysargv = sysargv

        if (
            'install' in sys.argv or
            'develop' in sys.argv or
            'bdist_egg' in sys.argv
        ):
            current_template.install_minimal_dependencies()

        if backend == 'cython':
            path = os.path.join('src-lib', 'libopenzwave', 'libopenzwave.cpp')
            if os.path.exists(os.path.abspath(path)):
                try:
                    os.remove(os.path.abspath(path))
                except OSError:
                    log.error('Unable to remove file {0}'.format(path))

    @property
    def spawn(self):
        from pyozw_common import build_clib
        return build_clib.spawn

    def clean(self):
        self.library.clean(self)

    @property
    def extension(self):
        return self._extension

    # def pybind_context(self):
    #     exts = self.get_default_exts()
    #     exts["sources"] = [
    #         "src-lib/libopenzwave/LibZWaveException.cpp",
    #         "src-lib/libopenzwave/Driver.cpp",
    #         "src-lib/libopenzwave/Group.cpp",
    #         "src-lib/libopenzwave/Log.cpp",
    #         "src-lib/libopenzwave/Options.cpp",
    #         "src-lib/libopenzwave/Manager.cpp",
    #         "src-lib/libopenzwave/Notification.cpp",
    #         "src-lib/libopenzwave/Node.cpp",
    #         "src-lib/libopenzwave/Values.cpp",
    #         "src-lib/libopenzwave/libopenzwave.cpp"
    #     ]
    #
    #     exts["include_dirs"] = ["pybind11/include"]
    #     exts['extra_compile_args'] += ["-fvisibility=hidden"]
    #     return exts

    @property
    def build_ext(self):
        if self.backend == 'cython':
            _build_ext = __import__('Cython.Distutils', fromlist=['build_ext'])
        else:
            from setuptools.command import build_ext as _build_ext

        return _build_ext

    @property
    def install_requires(self):
        if self.backend == 'cython':
            return ['Cython']
        return []

    @property
    def build_requires(self):
        if self.backend == 'cython':
            return ['Cython']
        return []

    def clean_all(self):
        log.info("Clean-all openzwave ... be patient ...")
        try:
            from pkg_resources import resource_filename
            dirn = resource_filename(
                'python_openzwave.ozw_config',
                '__init__.py'
            )

            dirn = os.path.dirname(dirn)

            if not os.path.isfile(os.path.join(dirn, 'device_classes.xml')):
                return self.clean()

            for f in os.listdir(dirn):
                if f not in ['__init__.py', '__init__.pyc']:
                    if os.path.isfile(os.path.join(dirn, f)):
                        os.remove(os.path.join(dirn, f))
                    elif os.path.isdir(os.path.join(dirn, f)):
                        shutil.rmtree(os.path.join(dirn, f))

            return self.clean()

        except ImportError:
            return self.clean()

    def check_minimal_config(self):
        if sys.platform.startswith("win"):
            from pyozw_windows import environment
            log.info(str(environment))
        else:
            log.info("Found g++ : {0}".format(find_executable("g++")))
            log.info("Found gcc : {0}".format(find_executable("gcc")))
            log.info("Found make : {0}".format(find_executable("make")))
            log.info("Found gmake : {0}".format(find_executable("gmake")))
            log.info("Found cython : {0}".format(find_executable("cython")))
            exe = find_executable("pkg-config")
            log.info("Found pkg-config : {0}".format(exe))
            if exe is not None:
                import pyozw_pkgconfig

                libraries = [
                    'yaml-0.1',
                    'libopenzwave',
                    'python',
                    'python2',
                    'python3'
                ]
                libraries += self._extension.libraries[:]

                for lib in libraries:
                    log.info(
                        "Found library {0} : {1}".format(
                            lib,
                            pyozw_pkgconfig.exists(lib)
                        )
                    )

    def install_minimal_dependencies(self):
        if len(self.build_requires) == 0:
            return

        try:
            main = __import__('pip', fromlist=['main'])[0] # py2
            get_installed_distributions = __import__(
                'pip.utils',
                fromlist=['get_installed_distributions']
            )[0]

        except ImportError:
            main = __import__('pip._internal', fromlist=['main'])[0]  # py3
            get_installed_distributions = __import__(
                'pip._internal.utils.misc',
                fromlist=['get_installed_distributions']
            )[0]

        log.info("Get installed packages")
        packages = get_installed_distributions()
        for pyreq in self.build_requires:
            if pyreq not in packages:
                try:
                    log.info(
                        "Install minimal dependencies {0}".format(pyreq)
                    )
                    main(['install', pyreq])
                except Exception:
                    log.warn(
                        "Fail to install minimal "
                        "dependencies {0}".format(pyreq)
                    )
            else:
                log.info(
                    "Minimal dependencies "
                    "already installed {0}".format(pyreq)
                )

    def get_openzwave(
        self,
        url='https://codeload.github.com/OpenZWave/open-zwave/zip/master'
    ):
        """download an archive to a specific location"""

        if os.path.exists(self.openzwave):
            if not self.cleanozw:
                # ~ log.info(
                # "Already have directory %s. Use it.
                # Use --cleanozw to clean it.", self.openzwave)
                return self.openzwave
            else:
                # ~ log.info(
                # "Already have directory %s but remove
                # and clean it as asked", self.openzwave)
                self.clean_all()

        log.info(
            "fetching {0} into "
            "{1} for version {2}".format(url, self.openzwave, pyozw_version)
        )

        import io
        import zipfile

        try:
            urllib = __import__('urllib2')  # py2
        except ImportError:
            urllib = __import__('urllib.request')  # py3

        response = urllib.urlopen(url)
        dst_file = io.BytesIO(response.read())

        dst_file.seek(0)
        zip_ref = zipfile.ZipFile(dst_file, 'r')
        dst = os.path.split(self.openzwave)[0]
        zip_ref.extractall(dst)
        zip_ref.close()
        dst_file.close()

        dst = os.path.join(dst, zip_ref.namelist()[0])

        if dst != self.openzwave:
            os.rename(dst, self.openzwave)

        return self.openzwave


class DevTemplate(Template):

    def __init__(self, backend='cython', static=True, **kwargs):
        Template.__init__(self, backend=backend, static=static, **kwargs)

    def get_openzwave(
        self,
        url='https://codeload.github.com/OpenZWave/open-zwave/zip/master'
    ):
        return True


class GitTemplate(Template):

    def __init__(self, backend='cython', static=True, **kwargs):
        Template.__init__(
            self,
            openzwave=os.path.join("openzwave-git", 'open-zwave-master'),
            backend=backend,
            static=static,
            **kwargs
        )

    def get_openzwave(
        self,
        url='https://codeload.github.com/OpenZWave/open-zwave/zip/master'
    ):
        return Template.get_openzwave(self, url)

    def clean_all(self):
        ret = self.clean()
        dst, tail = os.path.split(self.openzwave)
        if tail == "openzwave-git":
            if os.path.isdir(self.openzwave):
                log.info('Try to remove {0}'.format(self.openzwave))
                try:
                    shutil.rmtree(self.openzwave)
                except OSError:
                    pass

        elif tail == 'open-zwave-master':
            if os.path.isdir(dst):
                log.info('Try to remove {0}'.format(dst))
            try:
                shutil.rmtree(dst)
            except OSError:
                pass
        return ret


class GitSharedTemplate(GitTemplate):

    def __init__(self, static=False, **kwargs):
        GitTemplate.__init__(self, static=static, **kwargs)

    @property
    def extension(self):
        ext = self._extension
        if '-I/usr/local/include/openzwave' not in ext.extra_compile_args:
            ext.extra_compile_args += [
                '-I/usr/local/include/openzwave',
                '-I/usr/local/include/openzwave/value_classes',
                '-I/usr/local/include/openzwave/platform'
            ]
        return ext

    @property
    def copy_openzwave_config(self):
        return sys.platform.startswith("win")

    @property
    def install_openzwave_so(self):
        return True


class OzwdevTemplate(GitTemplate):

    def __init__(self, **kwargs):
        Template.__init__(
            self,
            openzwave=os.path.join("openzwave-git", 'open-zwave-Dev'),
            **kwargs
        )

    def get_openzwave(
        self,
        url='https://codeload.github.com/OpenZWave/open-zwave/zip/Dev'
    ):
        return Template.get_openzwave(self, url)


class OzwdevSharedTemplate(GitSharedTemplate):

    def get_openzwave(
        self,
        url='https://codeload.github.com/OpenZWave/open-zwave/zip/Dev'
    ):
        return Template.get_openzwave(self, url)


class EmbedTemplate(Template):

    def __init__(
        self,
        backend='cpp',
        static=True,
        **kwargs
    ):
        Template.__init__(
            self,
            openzwave=os.path.join("openzwave-embed", 'open-zwave-master'),
            backend=backend,
            static=static,
            **kwargs,

        )

    @property
    def build_ext(self):
        if 'install' in sys.argv or 'develop' in sys.argv:
            current_template.check_minimal_config()
            current_template.install_minimal_dependencies()
        from distutils.command.build_ext import build_ext as _build_ext
        return _build_ext

    def get_openzwave(
        self,
        url=(
            'https://raw.githubusercontent.com/OpenZWave/python-openzwave/'
            'master/archives/open-zwave-master-{0}.zip'.format(pyozw_version)
        )
    ):
        ret = Template.get_openzwave(self, url)
        src = os.path.join(
            self.openzwave,
            'python-openzwave',
            'openzwave.vers.cpp'
        )
        dst = os.path.join(self.openzwave, 'cpp', 'src', 'vers.cpp')
        shutil.copyfile(src, dst)
        return ret

    def clean(self):
        ret = Template.clean(self)

        src = os.path.join(
            self.openzwave,
            'python-openzwave',
            'openzwave.vers.cpp'
        )

        dst = os.path.join(self.openzwave, 'cpp', 'src', 'vers.cpp')
        log.info('Try to copy {0}'.format(src))

        try:
            shutil.copyfile(src, dst)
        except OSError:
            pass

        return ret

    def clean_all(self):
        ret = self.clean()
        dst, tail = os.path.split(self.openzwave)
        if tail == "openzwave-embed":
            log.info('Try to remove {0}'.format(self.openzwave))
            try:
                shutil.rmtree(self.openzwave)
            except OSError:
                pass

        elif tail == 'open-zwave-master':
            log.info('Try to remove {0}'.format(dst))
            try:
                shutil.rmtree(dst)
            except OSError:
                pass
        return ret


class EmbedSharedTemplate(EmbedTemplate):

    def __init__(self, **kwargs):
        EmbedTemplate.__init__(self, static=False, backend='cpp', **kwargs)

    @property
    def extension(self):
        ext = self._extension
        if '-I/usr/local/include/openzwave' not in ext.extra_compile_args:
            ext.extra_compile_args += [
                '-I/usr/local/include/openzwave',
                '-I/usr/local/include/openzwave/value_classes',
                '-I/usr/local/include/openzwave/platform'
            ]
        return ext

    def clean(self):
        self.library.clean_openzwave()
        return EmbedTemplate.clean(self)

    @property
    def copy_openzwave_config(self):
        return False

    @property
    def install_openzwave_so(self):
        return True


class SharedTemplate(Template):
    def __init__(self,  backend='cython', static=False, **kwargs):
        Template.__init__(self, backend=backend, static=static, **kwargs)

    def build(self):
        return True

    @property
    def copy_openzwave_config(self):
        return sys.platform.startswith("win")

    def get_openzwave(
        self,
        url='https://codeload.github.com/OpenZWave/open-zwave/zip/master'
    ):
        return True


def parse_template(sysargv):
    tmpl = None
    flavor = None
    if '--flavor=dev' in sysargv:
        index = sysargv.index('--flavor=dev')
        flavor = sysargv.pop(index)
        tmpl = DevTemplate(sysargv=sysargv)
    elif '--flavor=git' in sysargv:
        index = sysargv.index('--flavor=git')
        flavor = sysargv.pop(index)
        tmpl = GitTemplate(sysargv=sysargv)
    elif '--flavor=git_shared' in sysargv:
        index = sysargv.index('--flavor=git_shared')
        flavor = sysargv.pop(index)
        tmpl = GitSharedTemplate(sysargv=sysargv)
    elif '--flavor=ozwdev' in sysargv:
        index = sysargv.index('--flavor=ozwdev')
        flavor = sysargv.pop(index)
        tmpl = OzwdevTemplate(sysargv=sysargv)
    elif '--flavor=ozwdev_shared' in sysargv:
        index = sysargv.index('--flavor=ozwdev_shared')
        flavor = sysargv.pop(index)
        tmpl = OzwdevSharedTemplate(sysargv=sysargv)
    elif '--flavor=embed' in sysargv:
        index = sysargv.index('--flavor=embed')
        flavor = sysargv.pop(index)
        tmpl = EmbedTemplate(sysargv=sysargv)
    elif '--flavor=embed_shared' in sysargv:
        index = sysargv.index('--flavor=embed_shared')
        flavor = sysargv.pop(index)
        tmpl = EmbedSharedTemplate(sysargv=sysargv)
    elif '--flavor=shared' in sysargv:
        index = sysargv.index('--flavor=shared')
        flavor = sysargv.pop(index)
        tmpl = SharedTemplate(sysargv=sysargv)
    if tmpl is None:
        flavor = 'embed'
        try:
            import pyozw_pkgconfig
            if pyozw_pkgconfig.exists('libopenzwave'):
                try:
                    from Cython.Distutils import build_ext
                    flavor = 'shared'
                except ImportError:
                    log.info("Can't find cython")
        except:
            log.info("Can't find pkg-config")

        # Default template
        if flavor == 'embed':
            log.info("Use embedded package of openzwave")
            tmpl = EmbedTemplate(sysargv=sysargv)
        elif flavor == 'shared':
            log.info("Use precompiled library openzwave")
            tmpl = SharedTemplate(sysargv=sysargv)

    tmpl.flavor = flavor
    if '--cleanozw' in sysargv:
        index = sysargv.index('--cleanozw')
        sysargv.pop(index)
        tmpl.cleanozw = True

    log.info('sysargv', sysargv)
    print('sysargv', sysargv)
    log.info("Found SETUP_DIR : {0}".format(SETUP_DIR))
    print("Found SETUP_DIR : {0}".format(SETUP_DIR))
    return tmpl


current_template = parse_template(sys.argv)


def install_requires():
    pkgs = ['six']
    if sys.version_info > (3, 0):
         pkgs.append('PyDispatcher>=2.0.5')
    else:
         pkgs.append('Louie>=1.1')
    pkgs += current_template.install_requires
    return pkgs


def build_requires():
    return current_template.build_requires


def get_dirs(base):
    return [
        x for x in glob.iglob(os.path.join(base, '*'))
        if os.path.isdir(x)
    ]


def data_files_config(target, source, pattern):
    ret = list()
    tup = list()
    tup.append(target)
    tup.append(glob.glob(os.path.join(source, pattern)))
    ret.append(tup)
    dirs = get_dirs(source)
    if len(dirs):
        for d in dirs:
            rd = d.replace(source+os.sep, "", 1)
            ret.extend(
                data_files_config(
                    os.path.join(target, rd),
                    os.path.join(source, rd),
                    pattern
                )
            )
    return ret


class bdist_egg(_bdist_egg):
    def run(self):
        build_openzwave = self.distribution.get_command_obj('build_openzwave')
        build_openzwave.develop = True
        self.run_command('build_openzwave')
        _bdist_egg.run(self)


class build_openzwave(setuptools.Command):
    description = 'download and build openzwave'

    user_options = [
        ('openzwave-dir=', None,
         'the source directory where openzwave sources should be stored'),
        ('flavor=', None,
         'the flavor of python_openzwave to install'),
    ]

    def initialize_options(self):
        self.openzwave_dir = None
        self.flavor = None

    def finalize_options(self):
        if self.openzwave_dir is None:
            if (
                getattr(self, 'develop', False)
                or not getattr(self, 'install', False)
            ):
                self.openzwave_dir = current_template.openzwave
            else:
                build = self.distribution.get_command_obj('build')
                build.ensure_finalized()
                self.openzwave_dir = os.path.join(
                    build.build_lib,
                    current_template.openzwave
                )
        self.flavor = current_template.flavor

    def run(self):
        current_template.check_minimal_config()
        current_template.get_openzwave()
        current_template.clean()
        current_template.build()
        if current_template.install_openzwave_so:
            current_template.install_so()


class openzwave_config(setuptools.Command):
    description = 'Install config files from openzwave'

    user_options = [
        (
            'install-dir=', None,
            'the installation directory where '
            'openzwave configuration should be stored'
        ),
    ]

    def initialize_options(self):
        self.install_dir = None

    def finalize_options(self):
        if self.install_dir is None:
            install = self.distribution.get_command_obj('install')
            install.ensure_finalized()
            self.install_dir = install.install_lib

    def run(self):
        if self.install_dir is None:
            log.warning("Can't install ozw_config to None")
            return

        if not current_template.copy_openzwave_config:
            log.info(
                "Don't install ozw_config for template "
                "{0}".format(current_template)
            )
            return

        log.info(
            "Install ozw_config for template {0}".format(current_template)
        )
        dest = os.path.join(self.install_dir, 'python_openzwave', "ozw_config")
        if os.path.isdir(dest):
            # Try to remove old config
            try:
                import shutil
                shutil.rmtree(dest)
            except Exception:
                log.exception(
                    "Can't remove old config directory"
                )

        if not os.path.isdir(dest):
            os.makedirs(dest)
        self.copy_tree(os.path.join(current_template.openzwave,'config'), dest)


class build(_build):
    sub_commands = [('build_openzwave', None)] + _build.sub_commands


try:
    class bdist_wheel(_bdist_wheel):
        def run(self):
            build_openzwave = self.distribution.get_command_obj(
                'build_openzwave'
            )

            build_openzwave.develop = True
            self.run_command('build_openzwave')
            _bdist_wheel.run(self)
except NameError:
    log.warn(
        "NameError in : class bdist_wheel(_bdist_wheel) - "
        "Use bdist_egg instead"
    )


    class bdist_wheel(bdist_egg):
        pass


class clean(_clean):
    def run(self):
        if getattr(self, 'all', False):
            current_template.clean_all()
        else:
            current_template.clean()
        _clean.run(self)


class develop(_develop):
    description = 'Develop python_openzwave'

    user_options = _develop.user_options + [
        ('flavor=', None, 'the flavor of python_openzwave to install'),
    ]

    def initialize_options(self):
        self.flavor = None
        return _develop.initialize_options(self)

    def finalize_options(self):
        if self.flavor is None:
            self.flavor = current_template.flavor
        log.info('flavor {0}'.format(self.flavor))
        return _develop.finalize_options(self)

    def run(self):
        # In case of --uninstall,
        #          it will build openzwave to remove it ... stupid.
        # In develop mode, build is done by the makefile
        # ~ build_openzwave =
        #           self.distribution.get_command_obj('build_openzwave')
        # ~ build_openzwave.develop = True
        # ~ self.run_command('build_openzwave')
        _develop.run(self)


class install(_install):
    description = 'Install python_openzwave'

    user_options = _install.user_options + [
        ('flavor=', None, 'the flavor of python_openzwave to install'),
    ]

    def initialize_options(self):
        self.flavor = None
        return _install.initialize_options(self)

    def finalize_options(self):
        if self.flavor is None:
            self.flavor = current_template.flavor
        log.info('flavor {0}'.format(self.flavor))
        return _install.finalize_options(self)

    def run(self):
        build_openzwave = self.distribution.get_command_obj('build_openzwave')
        build_openzwave.develop = True
        self.run_command('build_openzwave')
        self.run_command('openzwave_config')
        _install.run(self)
