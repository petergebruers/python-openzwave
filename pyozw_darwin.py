# -*- coding: utf-8 -*-

import os
import pyozw_common
import pyozw_pkgconfig


class Extension(pyozw_common.Extension):
    def __init__(
        self,
        openzwave,
        flavor,
        static,
        backend
    ):

        extra_compile_args = [
            "-stdlib=libc++",
            "-mmacosx-version-min=10.7"
        ]
        extra_objects = []
        libraries = []
        include_dirs = []
        sources = []
        define_macros = []

        cpp_path = os.path.join(openzwave, 'cpp')

        if static:
            extra_objects += [
                "{0}/libopenzwave.a".format(openzwave)
            ]
            include_dirs += [
                os.path.join(cpp_path, 'build', 'mac')
            ]

        else:
            libraries += ["openzwave"]
            extra = pyozw_pkgconfig.cflags('libopenzwave')
            if extra:
                extra = os.path.abspath(extra)
                extra_compile_args += [
                    extra,
                    os.path.join(extra, 'value_classes'),
                    os.path.join(extra, 'platform')
                ]

        pyozw_common.Extension.__init__(
            self,
            openzwave,
            flavor,
            static,
            backend,
            extra_objects=extra_objects,
            sources=sources,
            include_dirs=include_dirs,
            define_macros=define_macros,
            libraries=libraries,
            extra_compile_args=extra_compile_args
        )

        self.extra_link_args = [
            "-framework",
            "CoreFoundation",
            "-framework",
            "IOKit"
        ]


class Library(pyozw_common.Library):

    def install(self, command_class):
        command_class.spawn(['make', 'install'], cwd=self.openzwave)
        command_class.spawn(['ldconfig', self.so_path], cwd=self.openzwave)

    def build(self, command_class):
        command_class.spawn(['make'], cwd=self.openzwave)

    def clean(self, command_class):
        pyozw_common.Library.clean(self, command_class)
        command_class.spawn(['make', 'clean'], cwd=self.openzwave)
