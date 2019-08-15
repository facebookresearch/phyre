#!/usr/bin/env python
# Copyright (c) Facebook, Inc. and its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys
import subprocess

import setuptools
import setuptools.command.build_ext

BUILD_COMMANDS = [['make', 'react_deps'], ['make', 'develop']]


class build_ext(setuptools.command.build_ext.build_ext):

    def run(self):
        for command in BUILD_COMMANDS:
            subprocess.check_call(command, cwd='../..')
        setuptools.command.build_ext.build_ext.run(self)
        self.run_command('egg_info')


setuptools.setup(name='phyre',
      version='0.0.1',
      author='Facebook AI Research',
      package_data={
          'phyre': [
              os.path.join('interface', '*', '*.py'),
              os.path.join('simulator_bindings*.so'),
              os.path.join('data', '*'),
              os.path.join('data', '*', '*'),
              os.path.join('data', '*', '*', '*'),
              os.path.join('viz_static_file', '*'),
              os.path.join('viz_static_file', '*', '*'),
          ]
      },
      packages=['phyre', 'phyre.creator', 'phyre.viz_server'],
      install_requires=[
          'nose', 'numpy', 'tornado', 'thrift', 'imageio', 'scipy',
          'joblib'
      ],
      cmdclass={'build_ext': build_ext})
