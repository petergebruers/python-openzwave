# -*- coding: utf-8 -*-
#
# This file is part of EventGhost.
# Copyright © 2005-2018 EventGhost Project <http://www.eventghost.net/>
#
# EventGhost is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# EventGhost is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with EventGhost. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import platform
import shutil
from xml.etree import ElementTree
from ctypes import (
    POINTER,
    byref,
    c_char,
    c_uint,
    cast,
    pointer,
    sizeof,
    Structure,
    windll,
    WinError
)

from ctypes.wintypes import (
    BOOL,
    DWORD,
    LPCVOID,
    LPCWSTR,
    LPVOID
)

try:
    _winreg = __import__('winreg')
except ImportError:
    _winreg = __import__('_winreg')

try:
    import setuptools

    setup_tools_version = float(
        '.'.join(setuptools.__version__.split('.')[:2]))

    if setup_tools_version < 40.2:
        raise ImportError

    del setuptools
    del setup_tools_version
except ImportError:
    raise RuntimeError('This library requires setuptools >= 40.2')


PUINT = POINTER(c_uint)
LPDWORD = POINTER(DWORD)

_GetFileVersionInfoSize = windll.version.GetFileVersionInfoSizeW
_GetFileVersionInfoSize.restype = DWORD
_GetFileVersionInfoSize.argtypes = [LPCWSTR, LPDWORD]

_GetFileVersionInfo = windll.version.GetFileVersionInfoW
_GetFileVersionInfo.restype = BOOL
_GetFileVersionInfo.argtypes = [LPCWSTR, DWORD, DWORD, LPVOID]

_VerQueryValue = windll.version.VerQueryValueW
_VerQueryValue.restype = BOOL
_VerQueryValue.argtypes = [LPCVOID, LPCWSTR, POINTER(LPVOID), PUINT]


class VS_FIXEDFILEINFO(Structure):
    _fields_ = [
        ("dwSignature", DWORD),  # will be 0xFEEF04BD
        ("dwStrucVersion", DWORD),
        ("dwFileVersionMS", DWORD),
        ("dwFileVersionLS", DWORD),
        ("dwProductVersionMS", DWORD),
        ("dwProductVersionLS", DWORD),
        ("dwFileFlagsMask", DWORD),
        ("dwFileFlags", DWORD),
        ("dwFileOS", DWORD),
        ("dwFileType", DWORD),
        ("dwFileSubtype", DWORD),
        ("dwFileDateMS", DWORD),
        ("dwFileDateLS", DWORD)
    ]


def _get_file_version(filename):
    dwLen  = _GetFileVersionInfoSize(filename, None)
    if not dwLen:
        raise WinError()
    lpData = (c_char * dwLen)()
    if not _GetFileVersionInfo(filename, 0, sizeof(lpData), lpData):
        raise WinError()
    uLen = c_uint()
    lpffi = POINTER(VS_FIXEDFILEINFO)()
    lplpBuffer = cast(pointer(lpffi), POINTER(LPVOID))
    if not _VerQueryValue(lpData, "\\", lplpBuffer, byref(uLen)):
        raise WinError()
    ffi = lpffi.contents
    return (
        ffi.dwFileVersionMS >> 16,
        ffi.dwFileVersionMS & 0xFFFF,
        ffi.dwFileVersionLS >> 16,
        ffi.dwFileVersionLS & 0xFFFF,
    )


def _get_reg_value(path, key):
    d = _read_reg_values(path)
    if key in d:
        return d[key]
    return ''


def _read_reg_keys(key):
    if isinstance(key, tuple):
        root = key[0]
        key = key[1]
    else:
        root = _winreg.HKEY_LOCAL_MACHINE
        key = 'SOFTWARE\\Wow6432Node\\Microsoft\\' + key

    try:
        handle = _winreg.OpenKeyEx(root, key)
    except _winreg.error:
        return []
    res = []

    for i in range(_winreg.QueryInfoKey(handle)[0]):
        res += [_winreg.EnumKey(handle, i)]

    return res


def _read_reg_values(key):
    if isinstance(key, tuple):
        root = key[0]
        key = key[1]
    else:
        root = _winreg.HKEY_LOCAL_MACHINE
        key = 'SOFTWARE\\Wow6432Node\\Microsoft\\' + key

    try:
        handle = _winreg.OpenKeyEx(root, key)
    except _winreg.error:
        return {}
    res = {}
    for i in range(_winreg.QueryInfoKey(handle)[1]):
        name, value, _ = _winreg.EnumValue(handle, i)
        res[_convert_mbcs(name)] = _convert_mbcs(value)

    return res


def _convert_mbcs(s):
    dec = getattr(s, "decode", None)
    if dec is not None:
        try:
            s = dec("mbcs")
        except UnicodeError:
            pass
    return s


class _EnvironmentLock(object):

    def __init__(self, environment):
        mod = sys.modules[__name__]
        for key, value in mod.__dict__.items():
            if key.startswith('__'):
                self.__dict__[key] = value

        self.__environment = environment
        self.__original_module__ = mod
        sys.modules[__name__] = self

    def __getattr__(self, item):
        if sys.modules[__name__] != self:
            return getattr(sys.modules[__name__], item)

        if item in self.__dict__:
            return self.__dict__[item]

        if item == 'Environment':
            return self.__environment

        raise RuntimeError(
            'Access Denied: The Environment has been locked.'
        )


class Environment(object):

    def __init__(
        self,
        strict_visual_c_version=None,
        minimum_visual_c_version=None,
        dll_build=False
    ):
        self.minimum_visual_c_version = minimum_visual_c_version
        self.strict_visual_c_version = strict_visual_c_version
        self.dll_build = dll_build
        self._win32 = None
        self.__lock = None
        self.__unlock = None
        self.__environment_set = False
        self.__installed_versions = None

    def lock(self):
        if self.__unlock is not None:
            self.__lock = self.__unlock
            self.__unlock = None
            sys.modules[__name__] = self.__lock

        elif self.__lock is None:
            self.__lock = _EnvironmentLock(self)

    def unlock(self):
        if self.__lock is not None:
            mod = getattr(self.__lock, '__original_module__')
            sys.modules[__name__] = mod
            self.__unlock = self.__lock
            self.__lock = None

    @property
    def msvc_dll_version(self):
        msvc_dll_path = self.msvc_dll_path
        for f in os.listdir(msvc_dll_path):
            if f.endswith('dll'):
                version = _get_file_version(os.path.join(msvc_dll_path, f))
                return '.'.join(str(v) for v in version)

    @property
    def msvc_dll_path(self):
        x64 = self.machine_architecture == 'x64'
        folder_name = 'Microsoft.VC{0}.CRT'.format(self.platform_toolset[1:])
        redist_path = os.path.join(self.visual_c_path['base'], 'redist')

        for root, dirs, files in os.walk(redist_path):
            if 'onecore' not in root:
                if folder_name in dirs:
                    if x64 and ('amd64' in root or 'x64' in root):
                        return os.path.join(root, folder_name)
                    elif not x64 and 'amd64' not in root and 'x64' not in root:
                        return os.path.join(root, folder_name)

    @property
    def machine_architecture(self):
        return 'x64' if '64' in platform.machine() else 'x86'

    @property
    def architecture(self):
        """
        :return: x86 or x64
        """
        win_64 = '64' in platform.machine()
        python_64 = platform.architecture()[0] == '64bit' and win_64
        return 'x64' if python_64 else 'x86'

    @property
    def platform(self):
        """
        This is used to tell MSBuild what configuration to build
        :return: Win32 or x64
        """
        if self._win32 is True:
            return 'Win32' if self.architecture == 'x86' else 'x64'
        if self._win32 is False:
            return self.architecture

        return 'Win32' if self.architecture == 'x86' else 'x64'

    @property
    def platform_toolset(self):
        """
        The platform toolset gets written to the solution file. this instructs
        the compiler to use the matching MSVCPxxx.dll file.
        :return: one of the following
            Visual C  Visual Studio  Returned Value
            VC 15.0 - VS 2017:       v141
            VC 14.0 - VS 2015:       v140
            VC 12.0 - VS 2013:       v120
            VC 11.0 - VS 2012:       v110
            VC 10.0 - VS 2010:       v100
            VC  9.0 - VS 2008:       v90

        """
        platform_toolsets = {
            15.0: 'v141',
            14.0: 'v140',
            12.0: 'v120',
            11.0: 'v110',
            10.0: 'v100',
            9.0:  'v90'
        }

        return platform_toolsets[self.visual_c_version]

    @property
    def py_architecture(self):
        return 'x64' if platform.architecture()[0] == '64bit' else 'x86'

    @property
    def py_version(self):
        return '.'.join(str(v) for v in sys.version_info)

    @property
    def py_dependency(self):
        return 'Python%d%d.lib' % sys.version_info[:2]

    @property
    def py_includes(self):
        python_path = os.path.dirname(sys.executable)
        python_include = os.path.join(python_path, 'include')
        python_includes = [python_include]
        for root, dirs, files in os.walk(python_include):
            for d in dirs:
                python_includes += [os.path.join(root, d)]
        return python_includes

    @property
    def py_libraries(self):
        python_path = os.path.dirname(sys.executable)
        python_lib = os.path.join(python_path, 'libs')
        python_libs = [python_lib]
        for root, dirs, files in os.walk(python_lib):
            for d in dirs:
                python_libs += [os.path.join(root, d)]
        return python_libs

    @property
    def target_framework(self):
        """
        .NET Version
        :return: returns the version associated with the architecture
        """
        if self.architecture == 'x64':
            return self.framework_version_64
        else:
            return self.framework_version_32

    @property
    def framework_dir_32(self):
        """
        .NET 32bit path
        :return: path to x86 .NET
        """

        directory = _get_reg_value(
            'VisualStudio\\SxS\\VC7\\',
            'FrameworkDir32'
        )

        if directory is None:
            return os.path.join(
                os.environ.get('WINDIR', r'C:\Windows'),
                'Microsoft.NET',
                'Framework'
            )

        return directory[:-1]

    @property
    def framework_dir_64(self):
        """
        .NET 64bit path
        :return: path to x64 .NET
        """
        guess_fw = os.path.join(
            os.environ.get('WINDIR', r'C:\Windows'),
            'Microsoft.NET',
            'Framework64'
        )

        return (
            _get_reg_value('VisualStudio\\SxS\\VC7\\', 'FrameworkDir64') or
            guess_fw
        )

    @property
    def framework_version_32(self):
        """
        .NET 32bit framework version
        :return: x86 .NET framework version
        """
        target_frameworks = {
            'v141': ('4.7*', '4.6*', '4.5*', '4.0*', '3.5*', '3.0*', '2.0*'),
            'v140': ('4.6*', '4.5*', '4.0*', '3.5*', '3.0*', '2.0*'),
            'v120': ('4.5*', '4.0*', '3.5*', '3.0*', '2.0*'),
            'v110': ('4.5*', '4.0*', '3.5*', '3.0*', '2.0*'),
            'v100': ('4.0*', '3.5*', '3.0*', '2.0*'),
            'v90':  ('3.5*', '3.0*', '2.0*')
        }

        target_framework = _get_reg_value(
            'VisualStudio\\SxS\\VC7',
            'FrameworkVer32'
        )

        if not target_framework:
            import fnmatch
            versions = list(
                key for key in _read_reg_keys('.NETFramework\\')
                if key.startswith('v')
            )

            target_frameworks = target_frameworks[self.platform_toolset]
            for version in versions:
                for target_framework in target_frameworks:
                    if fnmatch.fnmatch(version, 'v' + target_framework):
                        target_framework = version
                        break
                else:
                    continue

                break
            else:
                raise RuntimeError(
                    'No Suitable .NET Framework found %s' %
                    (target_frameworks,)
                )
        return target_framework

    @property
    def framework_version_64(self):
        """
        .NET 64bit framework version
        :return: x64 .NET framework version
        """
        target_framework = _get_reg_value(
            'VisualStudio\\SxS\\VC7',
            'FrameworkVer64'
        )
        if not target_framework:
            target_framework = self.framework_version_32

        return target_framework

    @property
    def configuration(self):
        """
        Build configuration
        :return: one of ReleaseDLL, DebugDLL
        """

        if os.path.splitext(sys.executable)[0].endswith('_d'):
            config = 'Debug'
        else:
            config = 'Release'

        if self.dll_build:
            config += 'DLL'

        return config

    @property
    def min_visual_c_version(self):
        """
        Minimum Visual C version

        This property is here for completeness. Because the building of
        openzwave does not seem to care if it matches the same compiler
        version that was used to compile python we have the ability to set
        a minimum that is the same for all python versions.
        the reason the version is not set to 9.0 is due to libopenzwave.pyd
        making use of map. map does not have the method "at" in VC 9.0.
        this is a method that is used quite a few times, and i do not think
        it is something that can easily be replaced


        :return: always 10.0
        """
        py_version = sys.version_info[:2]
        if py_version in ((2, 6), (2, 7), (3, 0), (3, 1), (3, 2)):
            return 9.0

        elif py_version in ((3, 3), (3, 4)):
            return 10.0

        elif py_version in ((3, 5), (3, 6), (3, 7)):
            return 14.0
        else:
            raise RuntimeError(
                'This library does not support '
                'python version %d.%d' % py_version
            )

    @property
    def _installed_c_paths(self):

        if self.__installed_versions is None:
            self.__installed_versions = {}

            reg_path = (
                _winreg.HKEY_CLASSES_ROOT,
                'Local Settings\\Software\\Microsoft\\Windows\\Shell\\MuiCache'
            )

            paths = []

            for key in _read_reg_values(reg_path):
                if 'cl.exe' in key:
                    value = _get_reg_value(reg_path, key)
                    if 'C++ Compiler Driver' in value:
                        paths += [key]

            for path in paths:
                print path
                if not os.path.exists(path):
                    continue

                if '\\VC\\bin' in path:
                    version = path.split('\\VC\\bin')[0]
                else:
                    version = path.split('\\bin\\Host')[0]

                version = os.path.split(version)[1]
                version = version.replace('Microsoft Visual Studio', '').strip()
                base_version = float(int(version.split('.')[0]))

                base_path = path.split('\\VC\\')[0] + '\\VC'
                if os.path.exists(os.path.join(base_path, 'include')):
                    vc_root = base_path
                else:
                    vc_root = path.split('\\bin\\')[0]

                self.__installed_versions[version] = dict(
                    base=base_path,
                    root=vc_root
                )
                self.__installed_versions[base_version] = dict(
                    base=base_path,
                    root=vc_root
                )
        return self.__installed_versions

    @property
    def visual_c_version(self):
        """
        Visual C version

        :return: found Visual C version or raises
        distutils.errors.DistutilsPlatformError
        """

        min_visual_c_version = self.min_visual_c_version

        max_version = 0.0

        if self.strict_visual_c_version is not None:
            if self.strict_visual_c_version < min_visual_c_version:
                raise RuntimeError(
                    'The set minimum compiler version is lower then the '
                    'required compiler version for Python'
                )
            if self.strict_visual_c_version not in self._installed_c_paths:
                raise RuntimeError(
                    'No Compatible Visual C version found.'
                )
            return self.strict_visual_c_version

        elif self.minimum_visual_c_version is not None:
            if self.minimum_visual_c_version < min_visual_c_version:
                raise RuntimeError(
                    'The set minimum compiler version is lower then the '
                    'required compiler version for Python'
                )

            for version in self._installed_c_paths:
                if not isinstance(version, float):
                    continue

                if version >= self.minimum_visual_c_version:
                    max_version = max(max_version, version)

        else:
            for version in self._installed_c_paths:
                if not isinstance(version, float):
                    continue
                if version >= min_visual_c_version:
                    max_version = max(max_version, version)

        if max_version == 0:
            raise RuntimeError(
                'No Compatible Visual C\\C++ version found.'
            )
        return max_version

    @property
    def msbuild_version(self):
        """
        MSBuild versions are specific to the Visual C version
        :return: MSBuild version, 3.5, 4.0, 12, 14, 15
        """
        vc_version = self.visual_c_version
        if vc_version == 9.0:
            return 3.5
        if vc_version in (10.0, 11.0):
            return 4.0
        else:
            return vc_version

    @property
    def vc_tools_redist_path(self):
        tools_install_path = self.tools_install_path
        if 'MSVC' in tools_install_path:
            return tools_install_path.replace('Tools', 'Redist')

        return os.path.join(self.visual_c_path['base'], 'redist')

    @property
    def tools_install_path(self):
        """
        Visual C compiler tools path.
        :return: Path to the compiler tools
        """
        vc_version = self.visual_c_version
        if vc_version >= 14.0:
            vc_tools_path = os.path.join(
                self.visual_c_path['root'],
                'bin',
                'Host' + self.architecture,
                self.architecture
            )

        else:
            vc_tools_path = os.path.join(
                self.visual_c_path['base'],
                'bin'
            )
            if self.architecture == 'x64':
                vc_tools_path = os.path.join(vc_tools_path, 'amd64')

        return vc_tools_path


    def __iter__(self):
        for item in self.build_environment.items():
            yield item

    def __call__(self, *args, **kwargs):
        if self.__lock:
            return self

        raise AttributeError

    @property
    def build_environment(self):
        """
        This would be the work horse. This is where all of the gathered
        information is put into a single container and returned.
        The information is then added to os.environ in order to allow the
        build process to run properly.

        List of environment variables generated:
        PATH
        LIBPATH
        LIB
        INCLUDE
        Platform
        FrameworkDir
        FrameworkVersion
        FrameworkDIR32
        FrameworkVersion32
        FrameworkDIR64
        FrameworkVersion64
        VCToolsRedistDir
        VCINSTALLDIR
        VCToolsInstallDir
        VCToolsVersion
        WindowsLibPath
        WindowsSdkDir
        WindowsSDKVersion
        WindowsSdkBinPath
        WindowsSdkVerBinPath
        WindowsSDKLibVersion
        __DOTNET_ADD_32BIT
        __DOTNET_ADD_64BIT
        __DOTNET_PREFERRED_BITNESS
        Framework{framework version}Version
        NETFXSDKDir
        UniversalCRTSdkDir
        UCRTVersion
        ExtensionSdkDir

        These last 2 are set to ensure that distuils uses these environment
        variables when compiling libopenzwave.pyd
        MSSDK
        DISTUTILS_USE_SDK

        :return: dict of environment variables
        """
        if self.__environment_set and self.__lock:
            raise RuntimeError(
                'Access Denied: Environment has been locked.'
            )

        self.__environment_set = True

        target_platform_path = self.target_platform_path
        target_platform = self.target_platform
        bin_path = os.path.join(target_platform_path, 'bin')

        env = dict()

        env['Platform'] = self.architecture
        env['WindowsSdkBinPath'] = bin_path
        env['MSSDK'] = target_platform_path
        env['WindowsSDKLibVersion'] = self.windows_sdk_version + '\\'
        if os.path.exists(os.path.join(bin_path, target_platform)):

            env['WindowsSdkVerBinPath'] = os.path.join(
                bin_path,
                target_platform
            )
        else:
            env['WindowsSdkVerBinPath'] = bin_path

        env['VCToolsRedistDir'] = self.vc_tools_redist_path + '\\'
        env['VCINSTALLDIR'] = self.visual_c_path + '\\'

        tools_install_path = self.tools_install_path
        env['VCToolsInstallDir'] = tools_install_path + '\\'
        env['VCToolsVersion'] = os.path.split(tools_install_path)[1]
        env['WindowsSdkDir'] = target_platform_path
        env['WindowsSDKVersion'] = env['WindowsSDKLibVersion']

        env['UniversalCRTSdkDir'] = target_platform_path
        env['UCRTVersion'] = env['WindowsSDKVersion'].replace('\\', '')

        env['INCLUDE'] = ';'.join(self.include_paths)

        base_lib = os.path.join(
            target_platform_path,
            'lib',
            target_platform,
        )
        if not os.path.exists(base_lib):
            base_lib = os.path.join(
                target_platform_path,
                'lib'
            )

        if os.path.exists(base_lib):
            ucrt = os.path.join(base_lib, 'ucrt', self.architecture)
            um = os.path.join(base_lib, 'um', self.architecture)

            if os.path.exists(ucrt) and ucrt not in env['LIB']:
                env['LIB'] += ';' + ucrt

            if os.path.exists(um) and um not in env['LIB']:
                env['LIB'] += ';' + um

        arc_bin_ver_sdk = os.path.join(
            env['WindowsSdkBinPath'],
            self.architecture
        )
        arc_bin_sdk = os.path.join(
            env['WindowsSdkBinPath'],
            self.architecture
        )
        if (
            os.path.exists(arc_bin_ver_sdk) and
            arc_bin_ver_sdk not in env['PATH']
        ):
            env['PATH'] += ';' + arc_bin_ver_sdk

        if (
            os.path.exists(arc_bin_sdk) and
            arc_bin_sdk not in env['PATH']
        ):
            env['PATH'] += ';' + arc_bin_sdk

        program_files = os.environ.get(
            'ProgramFiles(x86)',
            'C:\\Program Files (x86)'
        )
        type_script_path = os.path.join(
            program_files,
            'Microsoft SDKs',
            'TypeScript'
        )

        if os.path.exists(type_script_path):
            max_ver = 0.0
            for version in os.listdir(type_script_path):
                try:
                    version = float(version)
                except:
                    continue
                max_ver = max(max_ver, version)

            type_script_path = os.path.join(type_script_path, str(max_ver))

            if os.path.exists(type_script_path):
                env['PATH'] += ';' + type_script_path

        try:
            collection_tools_dir = _get_reg_value(
                'VisualStudio\\VSPerf',
                    'CollectionToolsDir'
            )
            env['PATH'] += ';' + collection_tools_dir
        except WindowsError:
            pass

        for path in env['PATH'].split(';'):
            if path.endswith('IDE'):
                team_explorer = os.path.join(
                    path,
                    'CommonExtensions',
                    'Microsoft',
                    'TeamFoundation',
                    'Team Explorer'
                )

                vc_packages = os.path.join(
                    path,
                    'VC',
                    'VCPackages'
                )
                if os.path.exists(team_explorer):
                    env['PATH'] += ';' + team_explorer
                if os.path.exists(vc_packages):
                    env['PATH'] += ';' + vc_packages

                break

        union_meta_data = os.path.join(
            target_platform_path,
            'UnionMetadata',
            target_platform
        )
        references = os.path.join(
            target_platform_path,
            'References',
            target_platform
        )
        if os.path.exists(union_meta_data):
            env['WindowsLibPath'] = union_meta_data + ';'
            env['LIBPATH'] = env['LIBPATH'].replace(
                os.path.split(union_meta_data)[0],
                union_meta_data
            )

        if os.path.exists(references):
            if 'WindowsLibPath' not in env:
                env['WindowsLibPath'] = ''

            env['WindowsLibPath'] += references + ';'
            env['LIBPATH'] = env['LIBPATH'].replace(
                os.path.split(references)[0],
                references
            )

        if self.architecture == 'x86':
            env['FrameworkVersion32'] = self.framework_version_32
            env['FrameworkDIR32'] = self.framework_dir_32
            env['__DOTNET_ADD_32BIT'] = '1'
            env['__DOTNET_PREFERRED_BITNESS'] = '32'
            env['FrameworkDir'] = env['FrameworkDIR32']
            env['FrameworkVersion'] = env['FrameworkVersion32']
        else:
            env['FrameworkVersion64'] = self.framework_version_64
            env['FrameworkDIR64'] = self.framework_dir_64
            env['__DOTNET_ADD_64BIT'] = '1'
            env['__DOTNET_PREFERRED_BITNESS'] = '64'
            env['FrameworkDir'] = env['FrameworkDIR64']
            env['FrameworkVersion'] = env['FrameworkVersion64']

        framework = env['FrameworkVersion'][1:].split('.')[:2]

        framework_version_key = (
            'Framework{framework}Version'.format(framework=''.join(framework))
        )

        net_fx_path = self.net_fx_sdk_path

        if net_fx_path is not None:
            if os.path.exists(net_fx_path):
                env['NETFXSDKDir'] = net_fx_path

            sdk_path = net_fx_path.split('\\Windows')[0]
            sdk_ver = env['WindowsSDKVersion'].split('.')[0]

            extension_path = os.path.join(
                sdk_path,
                'Windows Kits',
                sdk_ver,
                'ExtensionSdks'
            )
            if os.path.exists(extension_path):
                env['ExtensionSdkDir'] = extension_path

        env[framework_version_key] = 'v' + '.'.join(framework)

        framework_lib_path = os.path.join(
            env['FrameworkDir'],
            env['FrameworkVersion']
        )

        if framework_lib_path not in env['LIBPATH']:
            env['LIBPATH'] += ';' + framework_lib_path

        lib_framework = os.path.join(
            env['FrameworkDir'],
            env['FrameworkVersion'].lower().replace('v', '')
        )
        if lib_framework in env['LIB']:
            env['LIB'] = env['LIB'].replace(lib_framework + ';', '')
            env['LIB'] = env['LIB'].replace(lib_framework, '')

        env['DISTUTILS_USE_SDK'] = '1'

        return env


    @property
    def path(self):
        vc_path = self.visual_c_path
        vc_version = self.visual_c_version
        path = []

        vc_tools_path = self.tools_install_path
        if os.path.exists(vc_tools_path):
            path += [vc_tools_path]

        vs_path = _get_reg_value(
            'VisualStudio\\SxS\\VS7',
            '{0:.1f}'.format(vc_version)
        )

        vs_common7_path = os.path.join(vs_path, 'Common7')

        vs_ide_path = os.path.join(vs_common7_path, 'IDE')
        vs_tools_path = os.path.join(vs_common7_path, 'Tools')

        if os.path.exists(vs_ide_path):
            path += [vs_ide_path]
        if os.path.exists(vs_tools_path):
            path += [vs_tools_path]

        if vc_version >= 14.0:

            test_window_path = os.path.join(
                vs_ide_path,
                'CommonExtensions',
                'Microsoft', 'TestWindow'
            )
            if os.path.exists(test_window_path):
                path += [test_window_path]

            if self.architecture == 'x64':
                perf_tools_path = os.path.join(vc_tools_path, 'Team Tools', 'Performance Toolsx64')

            else:
                perf_tools_path = os.path.join(vc_tools_path, 'Team Tools', 'Performance Tools')

            if os.path.exists(perf_tools_path):
                path += [perf_tools_path]

            vs_tdb_path = os.path.join(vs_path, 'VSTSDB', 'Deploy')

            if os.path.exists(vs_tdb_path):
                path += vs_tdb_path

            bin_path = self.windows_sdk_bin_path
            if os.path.exists(bin_path):
                path += bin_path


        self.,
        self.SdkSetup,
        self.FxTools,
        self.MSBuild,
        self.HTMLHelpWorkshop,
        self.FSharp

    # path=self._build_paths('path',
    #         [
    #             ],
    #         exists),
    # )


    @property
    def lib_paths(self):
        lib_paths = []

        vc_path = self.visual_c_path['root']
        vc_lib_path = os.path.join(vc_path, 'lib')
        net_tools_paths = self.net_tools
        vc_store_refs = self.vc_store_refs

        if self.architecture == 'x64':
            if os.path.exists(os.path.join(vc_lib_path, 'amd64')):
                vc_lib_path = os.path.join(vc_lib_path, 'amd64')
            elif os.path.exists(os.path.join(vc_lib_path, 'x64')):
                vc_lib_path = os.path.join(vc_lib_path, 'x64')
        elif os.path.exists(os.path.join(vc_lib_path, 'x86')):
            vc_lib_path = os.path.join(vc_lib_path, 'x86')

        if os.path.exists(vc_lib_path):
            lib_paths += [vc_lib_path]

        for path in net_tools_paths:
            if os.path.exists(net_tools_paths):
                lib_paths += [path]

        if vc_store_refs is not None and os.path.exists(vc_store_refs):
            lib_paths += [vc_store_refs]

        return lib_paths



    @property
    def sdk_lib_paths(self):

        ref = os.path.join(self.target_platform_path, 'References')
        libpath = []

        vc_version = self.visual_c_version

        if vc_version <= 9.0:
            libpath += [self.windows_sdk_library_path]

        if 14.0 > vc_version >= 11.0:
            libpath += [os.path.join(ref, r'CommonConfiguration\Neutral')]

        if vc_version >= 14.0:
            base_path = os.path.join(ref, self.target_platform)

            def check_path(path):
                path = os.path.join(base_path, path)
                for f in os.listdir(path):
                    f = os.path.join(path, f)
                    if os.path.isdir(f):
                        libpath.append(f)
                        break

            libpath += [
                ref,
                os.path.join(self.target_platform_path, 'UnionMetadata')
            ]
            check_path('Windows.Foundation.UniversalApiContract')
            check_path('Windows.Foundation.FoundationContract')
            check_path('Windows.Networking.Connectivity.WwanContract')

            def iter_find(item, path, result=[]):
                files = os.listdir(path)
                if item in files:
                    result += [os.path.join(path, item)]
                else:
                    for f in files:
                        f = os.path.join(path, f)
                        if os.path.isdir(f):
                            result += iter_find(item, f)

                return result

            paths = iter_find(
                'CommonConfiguration',
                os.path.join(
                    self.target_platform_path,
                    'ExtensionSDKs',
                    'WindowsDesktop',
                    self.target_platform,
                )
            )

            for pth in paths:
                pth = os.path.join(pth, 'neutral')
                if os.path.isdir(pth):
                    libpath += [pth]


        return libpath

    @property
    def vc_store_refs(self):

        vc_path = self._installed_c_paths[self.visual_c_version]['root']

        if self.visual_c_version < 14.0:
            return None

        return os.path.join(
            vc_path,
            'lib',
            self.architecture,
            'store',
            'references'
        )



    @property
    def lib_includes(self):

        libs = []
        vc_path = self.visual_c_path['root']
        vc_lib_path = os.path.join(vc_path, 'lib')
        atlmfc_path = os.path.join(vc_lib_path, 'ATLMFC', 'lib')
        sdk_lib_path = self.windows_sdk_library_path
        net_tools_paths = self.net_tools
        net_fx_path = self.net_fx_sdk_path

        sdk_um_path = os.path.join(sdk_lib_path, 'um', self.architecture)
        sdk_ucrt_path = os.path.join(sdk_lib_path, 'ucrt', self.architecture)

        if self.architecture == 'x64':
            framework_include = os.path.join(self.framework_dir_64, self.framework_version_64)
            if os.path.exists(os.path.join(sdk_lib_path, 'x64')):
                sdk_lib_path = os.path.join(sdk_lib_path, 'x64')

            if os.path.exists(os.path.join(vc_lib_path, 'amd64')):
                vc_lib_path = os.path.join(vc_lib_path, 'amd64')
            elif os.path.exists(os.path.join(vc_lib_path, 'x64')):
                vc_lib_path = os.path.join(vc_lib_path, 'x64')

            atlmfc_path = os.path.join(
                vc_lib_path,
                'ATLMFC',
                'lib',
                os.path.split(vc_lib_path)[0]
            )

        elif os.path.exists(os.path.join(vc_lib_path, 'x86')):
            framework_include = os.path.join(self.framework_dir_32, self.framework_version_32)
            vc_lib_path = os.path.join(vc_lib_path, 'x86')
            atlmfc_path = os.path.join(
                vc_lib_path,
                'ATLMFC',
                'lib',
                os.path.split(vc_lib_path)[0]
            )

        else:
            framework_include = os.path.join(self.framework_dir_32, self.framework_version_32)

        store_path = os.path.join(vc_lib_path, 'store')

        if os.path.exists(vc_lib_path):
            libs += [vc_lib_path]
        if os.path.exists(store_path):
            libs += [store_path]
        if os.path.exists(atlmfc_path):
            libs += [atlmfc_path]

        if os.path.exists(sdk_um_path):
            libs += [sdk_um_path]
            if os.path.exists(sdk_ucrt_path):
                libs += [sdk_ucrt_path]
        elif os.path.exists(sdk_lib_path):
            libs += [sdk_lib_path]

        if os.path.exists(framework_include):
            libs += [framework_include]

        for path in net_tools_paths:
            if os.path.exists(net_tools_paths):
                libs += [path]

        if net_fx_path is not None:
            net_fx_path = os.path.join(net_fx_path, 'lib', 'um', self.architecture)
            if os.path.exists(net_fx_path):
                libs += [net_fx_path]

        return libs


    @property
    def include_paths(self):
        includes = []
        vc_version = self.visual_c_version
        vc_path = self.visual_c_path['root']
        sdk_path = self.target_platform_path
        target_platform = self.target_platform
        net_fx_path = self.net_fx_sdk_path

        vc_include = os.path.join(vc_path, 'include'),
        atlmfc_include = os.path.join(vc_path, r'ATLMFC\include')
        sdk_include = os.path.join(sdk_path, 'include')
        ucrt_include = os.path.join(sdk_include, 'ucrt')

        if target_platform.startswith('10'):
            platform_include = os.path.join(sdk_include, target_platform)
        else:
            platform_include = sdk_include

        shared_include = os.path.join(platform_include, 'shared')
        um_include = os.path.join(platform_include, 'um')
        winrt_include = os.path.join(platform_include, 'winrt')

        if os.path.exists(vc_include):
            includes += [vc_include]
        if os.path.exists(atlmfc_include):
            includes += [atlmfc_include]
        if os.path.exists(shared_include):
            includes += [shared_include]
        if os.path.exists(um_include):
            includes += [um_include]
        if os.path.exists(winrt_include):
            includes += [winrt_include]
        if os.path.exists(ucrt_include):
            includes += [ucrt_include]

        if vc_version <= 10.0:
            gl_include = os.path.join(sdk_include, 'gl')

            if os.path.exists(sdk_include):
                includes += [sdk_include]

            if os.path.exists(gl_include):
                includes += [gl_include]

        if net_fx_path is not None:
            net_fx_include = os.path.join(net_fx_path, 'include', 'um')
            if os.path.exists(net_fx_include):
                includes += [net_fx_include]

        return includes


    @property
    def net_tools(self):
        if self.visual_c_version <= 10.0:
            include32 = True
            include64 = self.architecture == 'x64'
        else:
            include32 = self.architecture == 'x86'
            include64 = self.architecture == 'x64'

        tools = []
        if include32:
            tools += [os.path.join(self.framework_dir_32, self.framework_version_32)]
        if include64:
            tools += [os.path.join(self.framework_dir_64, self.framework_version_64)]

        return tools


    @property
    def net_fx_sdk_path(self):

        max_fx_ver = (0, 0, 0)

        for fx_ver in _read_reg_keys('Microsoft SDKs\\NETFXSDK'):
            try:
                fx_ver = list(int(v) for v in fx_ver.split('.'))
                if len(fx_ver) == 2:
                    fx_ver += [0]
                if tuple(fx_ver) > max_fx_ver:
                    max_fx_ver = tuple(fx_ver)
            except:
                pass
        max_fx_ver = '.'.join(str(v) for v in max_fx_ver)

        try:
            net_fx_path = _get_reg_value(
                'Microsoft SDKs\\NETFXSDK\\' + max_fx_ver,
                'KitsInstallationFolder'
            )
            return net_fx_path

    @property
    def net_fx_tools_path(self):

        if self.architecture == 'x86':
            framework_version = self.framework_version_32
        else:
            framework_version = self.framework_version_64

        framework = framework_version[1:].split('.')[:2]

        max_fx_ver = (0, 0, 0)

        for fx_ver in _read_reg_keys('Microsoft SDKs\\NETFXSDK'):
            try:
                fx_ver = list(int(v) for v in fx_ver.split('.'))
                if len(fx_ver) == 2:
                    fx_ver += [0]
                if tuple(fx_ver) > max_fx_ver:
                    max_fx_ver = tuple(fx_ver)
            except:
                pass
        max_fx_ver = '.'.join(str(v) for v in max_fx_ver)
        net_fx_key = (
            '{version}\\'
            'WinSDK-NetFx{framework}Tools-{architecture}'
        ).format(
            version=max_fx_ver,
            framework=''.join(framework),
            architecture=self.architecture
        )

        try:
            net_fx_path = _get_reg_value(
                'Microsoft SDKs\\NETFXSDK\\' + net_fx_key,
                'InstallationFolder'
            )
            return net_fx_path

        except WindowsError:
            pass

    @property
    def windows_sdk_bin_path(self):


        bin_path = os.path.join(
            self.target_platform_path,
            'bin'
        )

        if self.visual_c_version >= 14:
            bin_path = os.path.join(
                bin_path,
                self.target_platform,
                self.architecture
            )
        elif self.architecture == 'x64':
            bin_path = os.path.join(bin_path, 'x64')

        return bin_path









    @property
    def windows_sdk_library_path(self):
        lib_path = os.path.join(
            self.target_platform_path,
            'lib',
            self.target_platform,
        )

        return lib_path

    @property
    def windows_sdks(self):
        """
        Windows SDK versions that are compatible with Visual C
        :return: compatible Windows SDK versions
        """
        ver = self.visual_c_version
        if ver <= 9.0:
            return '7.0', '6.1', '6.0a'
        elif ver == 10.0:
            return '7.1', '7.0a'
        elif ver == 11.0:
            return '8.0', '8.0a'
        elif ver == 12.0:
            return '8.1', '8.1a'
        elif ver >= 14.0:
            return '10.0', '8.1'

    @property
    def target_platform(self):
        """
        This is used in the solution file to tell the compiler what SDK to use.
        We obtain a list of compatible Windows SDK versions for the
        Visual C version. We check and see if any  of the compatible SDK's are
        installed and if so we return that version.

        :return: Installed Windows SDK version
        """
        for sdk in self.windows_sdks:
            sdk_version = _get_reg_value(
                'Microsoft SDKs\\Windows\\v' + sdk,
                'ProductVersion'
            )
            if sdk == '10.0':
                return sdk_version + '.0'
            else:
                return sdk

        raise RuntimeError(
            'Unable to locate suitable SDK %s' % (self.windows_sdks,)
        )

    @property
    def windows_sdk_version(self):
        """
        This is almost identical to target_platform. Except it returns the
        actual version of the Windows SDK not the truncated version.

        :return: actual Windows SDK version
        """
        for sdk in self.windows_sdks:
            sdk_version = _get_reg_value(
                'Microsoft SDKs\\Windows\\v' + sdk,
                'ProductVersion'
            )
            return sdk_version + '.0'

        raise RuntimeError(
            'Unable to locate suitable SDK %s' % (self.windows_sdks,)
        )

    @property
    def target_platform_path(self):
        """
        Path to the Windows SDK version that has been found.
        :return: Windows SDK path
        """
        for sdk in self.windows_sdks:
            sdk_installation_folder = _get_reg_value(
                'Microsoft SDKs\\Windows\\v' + sdk,
                'InstallationFolder'
            )
            if sdk_installation_folder:
                return sdk_installation_folder[:-1]
        raise RuntimeError(
            'Unable to locate suitable SDK %s' % (self.windows_sdks,)
        )

    @property
    def tools_version(self):
        """
        Used in the solution to identify the compiler version
        :return: MSBuild version
        """
        return self.msbuild_version

    @property
    def visual_c_path(self):
        """
        Visual C path
        :return: Visual C path
        """
        return self._installed_c_paths[self.visual_c_version]


    @property
    def msbuild_path(self):
        """
        MSBuild path
        :return: MSBuild path
        """
        from setuptools.msvc import EnvironmentInfo
        env_info = EnvironmentInfo(
            self.architecture,
            vc_min_ver=self.min_visual_c_version
        )

        x64 = self.architecture == 'x64'

        msbuild_path = env_info.MSBuild

        if msbuild_path:
            msbuild_path = msbuild_path[0]
        else:
            msbuild_path = self.tools_install_path

        for root, dirs, files in os.walk(msbuild_path):
            if (
                ((x64 and 'amd64' in root) or 'amd64' not in root) and
                'MSBuild.exe' in files
            ):
                msbuild_path = os.path.join(root, 'MSBuild.exe')
                break
        else:
            raise RuntimeError('Unable to locate MSBuild.exe')

        return msbuild_path

    def _command(self, solution):
        with open(solution, 'r') as f:
            self._win32 = 'Win32' in f.read()

        template = (
            '"{msbuild_path}" '
            '"{solution}" '
            '/property:Configuration={configuration} '
            '/property:Platform={platform} '
            '/t:'
        )
        command = template.format(
            msbuild_path=self.msbuild_path,
            solution=solution,
            configuration=self.configuration,
            platform=self.platform
        )

        return command

    def get_clean_command(self, solution):
        """
        Command to instruct MSBuild to clean the solution
        :return: subprocess command
        """
        return self._command(solution) + 'Clean'

    def get_build_command(self, solution):
        """
        Command to instruct MSBuild to compile the solution.
        :return: subprocess command
        """
        return self._command(solution) + 'Build'

    def update_solution(self, src, dst):
        """
        Updates a Visual Studio Solution

        This currently only supports Visual Studio 2012 and newer.

        This is going to update the solution to include x64 build
        configurations and put into place any additional includes/libs that are
        needed when compiling.


        :param src: the path to the directory containing the solution files
        :param dst: output path.
        :return: path to the sln file, path to the build folder
        """

        if os.path.exists(dst):
            shutil.rmtree(dst, True)

        shutil.copytree(src, dst)

        for sln_file in os.listdir(dst):
            if sln_file.endswith('.sln'):
                break
        else:
            raise RuntimeError('Unable to locate sln file')

        sln_file = os.path.join(dst, sln_file)

        update_vs_solution(sln_file)

        project_outputs = dict()

        for vcxproj_file in os.listdir(dst):
            if vcxproj_file.endswith('.vcxproj'):
                project_name, build_output = update_vs_project(
                    self,
                    os.path.join(dst, vcxproj_file)
                )
                project_outputs[project_name] = build_output

        if not project_outputs:
            raise RuntimeError('Unable to locate vcxproj file')

        return sln_file, project_outputs

    def __str__(self):
        template = (
            'Machine architecture: {machine_architecture}\n'
            'Build architecture: {architecture}\n'
            'Build configuration: {platform}|{configuration}\n'
            '\n'
            '== Windows SDK ================================================\n'
            '   version: {target_platform}-{windows_sdk_version}\n'
            '   path:    {target_platform_path}\n'
            '\n'
            '== .NET =======================================================\n'
            '   version: {target_framework}\n'
            '\n'
            '   -- x86 -----------------------------------------------------\n'
            '      version: {framework_version_32}\n'
            '      path:    {framework_dir_32}\n'
            '   -- x64 -----------------------------------------------------\n'
            '      version: {framework_version_64}\n'
            '      path:    {framework_dir_64}\n'
            '\n'
            '== Visual C ===================================================\n'
            '   version: {visual_c_version}\n'
            '   path:    {visual_c_path}\n'
            '\n'
            '   -- Tools ---------------------------------------------------\n'
            '      version:     {tools_version}\n'
            '      path:        {tools_install_path}\n'
            '      redist path: {vc_tools_redist_path}\n'
            '   -- DLL -----------------------------------------------------\n'
            '      version: {platform_toolset}-{msvc_dll_version}\n'
            '      path:    {msvc_dll_path}\n'
            '\n'
            '== MSBuild ====================================================\n'
            '   version: {msbuild_version}\n'
            '   path:    {msbuild_path}\n'
            '\n'
            '== Python =====================================================\n'
            '  version: {py_version}\n'
            '  architecture: {py_architecture}\n'
            '  library: {py_dependency}\n'
            '  libs: {py_libraries}\n'
            '  includes: {py_includes}\n'
            '\n'
        )
        return template.format(
            machine_architecture=self.machine_architecture,
            architecture=self.architecture,
            platform=self.platform,
            configuration=self.configuration,
            target_platform=self.target_platform,
            windows_sdk_version=self.windows_sdk_version,
            target_platform_path=self.target_platform_path,
            target_framework=self.target_framework,
            framework_version_32=self.framework_version_32,
            framework_dir_32=self.framework_dir_32,
            framework_version_64=self.framework_version_64,
            framework_dir_64=self.framework_dir_64,
            visual_c_version=self.visual_c_version,
            visual_c_path=self.visual_c_path,
            tools_version=self.tools_version,
            tools_install_path=self.tools_install_path,
            vc_tools_redist_path=self.vc_tools_redist_path,
            platform_toolset=self.platform_toolset,
            msvc_dll_version=self.msvc_dll_version,
            msvc_dll_path=self.msvc_dll_path,
            msbuild_version=self.msbuild_version,
            msbuild_path=self.msbuild_path,
            py_version=self.py_version,
            py_architecture=self.py_architecture,
            py_dependency=self.py_dependency,
            py_libraries=self.py_libraries,
            py_includes=self.py_includes,
        )


def update_vs_solution(path):
    import fnmatch

    with open(path, 'r') as f:
        sln = str(f.read())

    sln = sln.replace('\r', '')
    lines = sln.split('\n')
    output = []
    new_lines = []
    for i, line in enumerate(lines[:]):
        for j, pattern in enumerate(GLOBAL_SELECTION_PATTERNS):
            for config in BUILD_CONFIGURATIONS:
                build_pattern_1 = GLOBAL_SELECTION_BUILD_PATTERN.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[0],
                    arch2=X86_BUILD_ARCH[0]
                )
                pattern_1 = pattern.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[0],
                    arch2=X86_BUILD_ARCH[0]
                )

                build_pattern_2 = GLOBAL_SELECTION_BUILD_PATTERN.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[1],
                    arch2=X86_BUILD_ARCH[1]
                )
                pattern_2 = pattern.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[1],
                    arch2=X86_BUILD_ARCH[1]
                )

                build_pattern_3 = GLOBAL_SELECTION_BUILD_PATTERN.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[0],
                    arch2=X86_BUILD_ARCH[1]
                )
                pattern_3 = pattern.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[0],
                    arch2=X86_BUILD_ARCH[1]
                )

                build_pattern_4 = GLOBAL_SELECTION_BUILD_PATTERN.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[1],
                    arch2=X86_BUILD_ARCH[0]
                )
                pattern_4 = pattern.format(
                    config=config,
                    arch1=X86_BUILD_ARCH[1],
                    arch2=X86_BUILD_ARCH[0]
                )

                if (
                    line == build_pattern_1 or
                    line == build_pattern_2 or
                    line == build_pattern_3 or
                    line == build_pattern_4
                ):
                    template = GLOBAL_SELECTION_BUILD_TEMPLATE.format(
                        config=config
                    )
                    if template not in sln and template not in new_lines:
                        new_lines += [template]
                elif (
                    fnmatch.fnmatch(line, pattern_1) or
                    fnmatch.fnmatch(line, pattern_2) or
                    fnmatch.fnmatch(line, pattern_3) or
                    fnmatch.fnmatch(line, pattern_4)

                ):
                    guid = line[2:line.find('}') + 1]
                    template = GLOBAL_SELECTION_TEMPLATES[j].format(
                        guid=guid,
                        config=config
                    )
                    if template not in sln and template not in new_lines:
                        new_lines += [template]

        if 'EndGlobalSection' in line and new_lines:
            output += new_lines
            new_lines = []

        output += [line]

    sln = '\n'.join(output)
    with open(path, 'w') as f:
        f.write(sln)


def iter_node(old_node):

    def has_64(v):
        for pattern in ('x64', 'X64', 'WIN64'):
            if pattern in v:
                return True
        return False

    new_node = ElementTree.Element(old_node.tag)
    if old_node.text is not None:
        if has_64(old_node.text):
            return old_node

        new_node.text = old_node.text.replace('Win32', 'x64')
        new_node.text = new_node.text.replace('x86', 'x64')
        new_node.text = new_node.text.replace('X86', 'X64')
        new_node.text = new_node.text.replace('WIN32', 'WIN64')

    for key, value in old_node.attrib.items():
        if has_64(value):
            return old_node

        new_node.attrib[key] = value.replace('Win32', 'x64')
        new_node.attrib[key] = new_node.attrib[key].replace('x86', 'x64')
        new_node.attrib[key] = new_node.attrib[key].replace('X86', 'X64')
        new_node.attrib[key] = new_node.attrib[key].replace('WIN32', 'WIN64')

    for old_sub_node in old_node:
        new_nodes = iter_node(old_sub_node)
        new_node.append(new_nodes)

    return new_node


def get_output_path(project_name, solution_dir, env, project):

    build_config = env.configuration + '|' + env.platform
    vcxproj_xmlns = '{http://schemas.microsoft.com/developer/msbuild/2003}'
    output_file = None

    def build_nodes():
        for node in project:
            if (
                node.tag.replace(vcxproj_xmlns, '') == 'ItemGroup' and
                'Label' in node.attrib and
                node.attrib['Label'] == 'ProjectConfigurations'
            ):
                for sub_node in node:
                    if (
                        sub_node.tag.replace(vcxproj_xmlns, '') ==
                        'ProjectConfiguration' and
                        sub_node.attrib['Include'] != build_config
                    ):
                        continue
                    yield sub_node
                continue
            if (
                'Condition' in node.attrib and
                build_config not in node.attrib['Condition']
            ):
                continue

            yield node

    def locate_variable(var):
        if var == 'TargetName':
            val = '$(ProjectName)'
        elif var == 'ProjectName':
            val = project_name
        elif var == 'SolutionDir':
            val = solution_dir
        elif var == 'OutDir':
            val = '$(SolutionDir)$(Platform)\\$(Configuration)\\'
        elif var == 'IntDir':
            val = '$(Platform)\\$(Configuration)\\'
        elif var == 'TargetExt':
            val = None

            for node in build_nodes():
                if node.tag.replace(vcxproj_xmlns, '') == 'PropertyGroup':
                    if 'Label' not in node.attrib:
                        continue
                    if node.attrib['Label'] != 'Configuration':
                        continue

                    for sub_node in node:
                        if (
                            sub_node.tag.replace(vcxproj_xmlns, '') ==
                            'ConfigurationType'
                        ):
                            if sub_node.text == 'DynamicLibrary':
                                val = '.dll'
                            elif sub_node.text == 'StaticLibrary':
                                val = '.lib'
                            elif sub_node.text == 'Application':
                                val = '.exe'

                            break
                    else:
                        continue

                    break
        else:
            val = None

        def find_var(n):
            for c in n:
                if c.tag.replace(vcxproj_xmlns, '') == var:
                    return c.text
                else:
                    r = find_var(c)
                    if r is not None:
                        return r

        for node in build_nodes():
            ret = find_var(node)

            if ret is not None:
                val = ret
                break

        return val

    def iter_variable(variable):
        out_data = ''
        if variable is None:
            return None

        if '$' in variable:
            variables = variable.split('$')
            for variable in variables:
                if not variable.startswith('('):
                    out_data += variable
                    continue

                variable, extra = variable[1:].split(')', 1)
                var_data = iter_variable(locate_variable(variable))

                if var_data is None:
                    return None

                out_data += var_data + extra
        else:
            out_data = variable

        return out_data

    for node in build_nodes():
        if (
            node.tag.replace(vcxproj_xmlns, '') ==
            'ItemDefinitionGroup'
        ):
            for sub_node in node:
                if sub_node.tag.replace(vcxproj_xmlns, '') == 'Link':
                    for sub_sub_node in sub_node:
                        if (
                            sub_sub_node.tag.replace(vcxproj_xmlns, '') ==
                            'OutputFile'
                        ):
                            output_file = sub_sub_node.text
                            break
                    else:
                        continue

                    break

    return iter_variable(output_file)


def update_vs_project(env, path):

    tools_version = env.tools_version
    platform_toolset = env.platform_toolset
    target_platform = env.target_platform
    includes = env.py_includes
    libs = env.py_libraries
    dependency = [env.py_dependency]

    vcxproj_xmlns = 'http://schemas.microsoft.com/developer/msbuild/2003'
    ElementTree.register_namespace('', vcxproj_xmlns)

    with open(path, 'r') as f:
        vcxproj = f.read()

    # the original xml file contains some characters that the xml parser
    # does not like, these are non human readable characters and they do not
    # need to exist. So we remove them.
    for char in (187, 191, 239):
        vcxproj = vcxproj.replace(chr(char), '')

    root = ElementTree.fromstring(vcxproj)

    vcxproj_xmlns = '{' + vcxproj_xmlns + '}'

    if env.architecture == 'x64':
        root = iter_node(root)

    # there are only 3 things that need to get changed once the solution has
    # been fully updated. the tools version, the platform toolset
    # and the windows target platform. if a cached version of openzwave is used
    # there is no need to create a whole new solution. so what we do is we set
    # an attribute in the root of the xml to inform us if the file has been
    # upgraded already.

    root.attrib['ToolsVersion'] = tools_version
    project_name = os.path.splitext(os.path.split(path)[1])[0]

    for node in root.findall(vcxproj_xmlns + 'PropertyGroup'):
        if 'Label' in node.attrib:
            if node.attrib['Label'] == 'Globals':
                for sub_node in node:
                    if (
                        sub_node.tag.replace(vcxproj_xmlns, '') ==
                        'WindowsTargetPlatformVersion'
                    ):
                        sub_node.text = target_platform
                        break
                else:
                    sub_node = ElementTree.Element('WindowsTargetPlatformVersion')
                    sub_node.text = target_platform
                    node.append(sub_node)

                for sub_node in node:
                    if (
                        sub_node.tag.replace(vcxproj_xmlns, '') ==
                        'ProjectName'
                    ):
                        project_name = sub_node.text
                        break

            elif node.attrib['Label'] == 'Configuration':
                for sub_node in node:
                    if (
                        sub_node.tag.replace(vcxproj_xmlns, '') ==
                        'PlatformToolset'
                    ):
                        sub_node.text = platform_toolset
                        break
                else:
                    sub_node = ElementTree.Element('PlatformToolset')
                    sub_node.text = platform_toolset
                    node.append(sub_node)

    # this function is the core of upgrading the solution. It burrows down
    # into a node through each layer and makes a copy. this copy gets modified
    # to become an x64 version. the copy gets returned and then added to the
    # xml file

    # here is the testing to se if the file has been updated before.
    i = 0

    def add_items(old_items, new_items):
        import fnmatch
        for old_item in old_items[:]:
            if (
                not old_item.startswith('$') and
                os.path.dirname(old_item) and
                not os.path.exists(old_item)
            ):
                old_items.remove(old_item)
            if fnmatch.fnmatch(old_item, 'python*.lib'):
                old_items.remove(old_item)

        for idx, old_item in enumerate(old_items[:]):
            if not old_item.startswith('$') and not old_item.startswith('%'):
                old_item = old_item.lower()
            old_items[idx] = old_item

        for new_item in new_items:
            if new_item.lower() not in old_items:
                old_items.insert(0, new_item.lower())

        return ';'.join(old_items)

    for node in root[:]:
        tag = node.tag.replace(vcxproj_xmlns, '')
        if (
            tag == 'PropertyGroup' and
            not node.attrib.keys()
        ):
            j = 0
            for sub_item in node[:]:
                if (
                    sub_item.tag.replace(vcxproj_xmlns, '') !=
                    '_ProjectFileVersion'
                ):
                    new_data = iter_node(sub_item)
                    if new_data is not None:
                        node.insert(j, new_data)
                j += 1

        if tag == 'ItemDefinitionGroup':
            for sub_item in node:
                sub_tag = sub_item.tag.replace(vcxproj_xmlns, '')
                if sub_tag == 'ClCompile':
                    for sub_sub_item in sub_item:
                        if (
                            sub_sub_item.tag.replace(vcxproj_xmlns, '') ==
                            'AdditionalIncludeDirectories'
                        ):
                            sub_sub_item.text = add_items(
                                sub_sub_item.text.split(';'),
                                includes
                            )

                elif sub_tag == 'Link':
                    for sub_sub_item in sub_item:
                        sub_sub_tag = sub_sub_item.tag.replace(
                            vcxproj_xmlns,
                            ''
                        )
                        if sub_sub_tag == 'AdditionalDependencies':
                            cur_deps = sub_sub_item.text.split(';')
                            for dep in cur_deps[:]:
                                if (
                                    dep.startswith('Python') and
                                    dep.endswith('.lib')
                                ):
                                    cur_deps.remove(dep)

                            sub_sub_item.text = add_items(cur_deps, dependency)

                        elif sub_sub_tag == 'AdditionalLibraryDirectories':
                            sub_sub_item.text = add_items(
                                sub_sub_item.text.split(';'),
                                libs
                            )
        i += 1

    with open(path, 'w') as f:
        f.write(xml_tostring(root, vcxproj_xmlns))

    return (
        project_name,
        get_output_path(project_name, os.path.dirname(path) + '\\', env, root)
    )


# this is a custom xml writer. it recursively iterates through an
# ElementTree object creating a formatted string that is as close as i can
# get it to what Visual Studio creates. I did this for consistency as well
# as ease of bug testing

def xml_tostring(node, xmlns, indent=''):
    tag = node.tag.replace(xmlns, '')
    no_text = node.text is None or not node.text.strip()

    if indent:
        output = ''
    else:
        output = '<?xml version="1.0" encoding="utf-8"?>\n'
        if xmlns:
            node.attrib['xmlns'] = xmlns.replace('{', '').replace('}', '')

    if no_text and not list(node) and not node.attrib.keys():
        output += '{0}<{1} />\n'.format(indent, tag)
    else:
        output += '{0}<{1}'.format(indent, tag)

        for key in sorted(node.attrib.keys()):
            output += ' {0}="{1}"'.format(key, str(node.attrib[key]))

        if not list(node) and no_text:
            output += ' />\n'
        elif not no_text and not list(node):
            output += '>{0}</{1}>\n'.format(node.text, tag)
        elif list(node) and no_text:
            output += '>\n'
            for item in node:
                output += xml_tostring(item, xmlns, indent + '  ')
            output += '{0}</{1}>\n'.format(indent, tag)
        else:
            output += '>\n  {0}{1}\n'.format(indent, node.text)
            for item in node:
                output += xml_tostring(item, xmlns, indent + '  ')
            output += '{0}</{1}>\n'.format(indent, tag)
    return output


BUILD_CONFIGURATIONS = ('Debug', 'DebugDll', 'Release', 'ReleaseDll')
X86_BUILD_ARCH = ('Win32', 'x86')

GLOBAL_SELECTION_BUILD_PATTERN = '		{config}|{arch1} = {config}|{arch2}'
GLOBAL_SELECTION_BUILD_TEMPLATE = '		{config}|x64 = {config}|x64'

GLOBAL_SELECTION_PATTERNS = (
    '		{{*}}.{config}|{arch1}.ActiveCfg = {config}|{arch2}',
    '		{{*}}.{config}|{arch1}.Build.0 = {config}|{arch2}',
)

GLOBAL_SELECTION_TEMPLATES = (
    '		{guid}.{config}|x64.ActiveCfg = {config}|x64',
    '		{guid}.{config}|x64.Build.0 = {config}|x64',
)

if __name__ == '__main__':
    print(Environment())
