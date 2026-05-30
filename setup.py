#!/usr/bin/env python

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import setuptools
import os
import subprocess
import platform
import io

__version__ = "0.9.2"
FASTTEXT_SRC = "src"

class get_pybind_include:
    """Helper class to determine the pybind11 include path"""

    def __init__(self, user=False):
        try:
            pass
        except ImportError:
            if subprocess.call([sys.executable, "-m", "pip", "install", "pybind11"]):
                raise RuntimeError("pybind11 install failed.")

        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)

try:
    coverage_index = sys.argv.index("--coverage")
except ValueError:
    coverage = False
else:
    del sys.argv[coverage_index]
    coverage = True

fasttext_src_files = map(str, os.listdir(FASTTEXT_SRC))
fasttext_src_cc = list(filter(lambda x: x.endswith(".cc"), fasttext_src_files))
fasttext_src_cc = list(
    map(lambda x: str(os.path.join(FASTTEXT_SRC, x)), fasttext_src_cc)
)

ext_modules = [
    Extension(
        str("fasttext_pybind"),
        [
            str("python/fasttext_module/fasttext/pybind/fasttext_pybind.cc"),
        ]
        + fasttext_src_cc,
        include_dirs=[
            get_pybind_include(),
            get_pybind_include(user=True),
            FASTTEXT_SRC,
        ],
        language="c++",
        # Оставляем пустые extra_compile_args, так как они полностью сформируются в BuildExt
        extra_compile_args=[],
    ),
]

def has_flag(compiler, flags):
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".cpp", delete=False) as f:
        f.write("int main (int argc, char **argv) { return 0; }")
        f_name = f.name
    try:
        compiler.compile([f_name], extra_postargs=flags)
    except Exception:
        return False
    finally:
        try:
            os.remove(f_name)
        except OSError:
            pass
    return True

def cpp_flag(compiler):
    standards = ["-std=c++17"]
    for standard in standards:
        if has_flag(compiler, [standard]):
            return standard
    raise RuntimeError("Unsupported compiler -- at least C++17 support is needed!")

class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    c_opts = {
        "msvc": ["/EHsc", "/O2", "/std:c++17", "/Dssize_t=intptr_t"],  # ПАТЧ ДЛЯ WINDOWS (C++17 + ssize_t)
        "unix": ["-O3", "-funroll-loops", "-pthread", "-march=native"],
    }

    def build_extensions(self):
        if sys.platform == "darwin":
            mac_osx_version = float(".".join(platform.mac_ver()[0].split(".")[:2]))
            os.environ["MACOSX_DEPLOYMENT_TARGET"] = str(mac_osx_version)
            all_flags = ["-stdlib=libc++", "-mmacosx-version-min=10.7"]
            if has_flag(self.compiler, [all_flags[0]]):
                self.c_opts["unix"] += [all_flags[0]]
            elif has_flag(self.compiler, all_flags):
                self.c_opts["unix"] += all_flags

        ct = self.compiler.compiler_type
        opts = list(self.c_opts.get(ct, []))
        extra_link_args = []

        if coverage:
            if ct == "unix":
                opts.append("--coverage")
                extra_link_args.append("--coverage")

        if ct == "unix":
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, ["-fvisibility=hidden"]):
                opts.append("-fvisibility=hidden")
        elif ct == "msvc":
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())

        for ext in self.extensions:
            ext.extra_compile_args = opts
            ext.extra_link_args = extra_link_args
        build_ext.build_extensions(self)

def _get_readme():
    try:
        with io.open("python/README.rst", encoding="utf-8") as fid:
            return fid.read()
    except IOError:
        return "fasttext Python bindings"

setup(
    name="fasttext",
    version=__version__,
    author="Onur Celebi",
    author_email="celebio@fb.com",
    description="fasttext Python bindings",
    long_description=_get_readme(),
    ext_modules=ext_modules,
    url="https://github.com/facebookresearch/fastText",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS",
    ],
    install_requires=["pybind11>=2.2", "setuptools >= 0.7.0", "numpy"],
    cmdclass={"build_ext": BuildExt},
    packages=[
        str("fasttext"),
        str("fasttext.util"),
        str("fasttext.tests"),
    ],
    package_dir={str(""): str("python/fasttext_module")},
    zip_safe=False,
)
