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
import re
import sys
import subprocess

import setuptools
import setuptools.command.build_ext

BUILD_COMMANDS = [['make', 'react_deps'], ['make', 'develop']]
README_PATH = os.path.join(os.path.dirname(__file__), '../../README.md')

with open(README_PATH) as f:
    readme = f.read()
    readme = re.sub(
        r'\(([^\s()]*?)(LICENSE|.md|.ipynb)',
        r'(https://github.com/facebookresearch/phyre/blob/master/\1\2',
        readme,
    )
    readme = re.sub(
        r'(\(|=")([^\s()]*?)(.gif|.jpg)',
        r'\1https://raw.githubusercontent.com/facebookresearch/phyre/master/\2\3',
        readme,
    )


class build_ext(setuptools.command.build_ext.build_ext):

    def run(self):
        for command in BUILD_COMMANDS:
            subprocess.check_call(command, cwd='../..')
        setuptools.command.build_ext.build_ext.run(self)
        self.run_command('egg_info')


setuptools.setup(name='phyre',
                 version='0.2.1',
                 author='Facebook AI Research',
                 license='Apache Software License',
                 url='https://phyre.ai',
                 description='Benchmark for PHYsical REasoning',
                 long_description=readme,
                 long_description_content_type='text/markdown',
                 package_data={
                     'phyre': [
                         os.path.join('interface', '*.py'),
                         os.path.join('interface', '*', '*.py'),
                         os.path.join('simulator_bindings*.so'),
                         os.path.join('data', '*'),
                         os.path.join('data', '*', '*'),
                         os.path.join('data', '*', '*', '*'),
                         os.path.join('viz_static_file', '*'),
                         os.path.join('viz_static_file', '*', '*'),
                         os.path.join('viz_static_file', '*', '*', '*'),
                     ]
                 },
                 packages=['phyre', 'phyre.creator', 'phyre.viz_server'],
                 install_requires=[
                     'nose', 'numpy', 'tornado', 'thrift==0.11.0', 'imageio',
                     'scipy', 'joblib'
                 ],
                 cmdclass={'build_ext': build_ext},
                 classifiers=[
                     'Programming Language :: Python :: 3.6',
                     'License :: OSI Approved :: Apache Software License',
                 ])
