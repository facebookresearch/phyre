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

import pathlib

PHYRE_DIR = pathlib.Path(__file__).parent
DATA_DIR = PHYRE_DIR / 'data'
TASK_DIR = DATA_DIR / 'generated_tasks'
VIRTUAL_TOOLS_DIR = DATA_DIR / 'virtual_tools'
TASK_EVAL_DIR = DATA_DIR / 'evaluations'
TASK_SCRIPTS_DIR = DATA_DIR / 'task_scripts' / 'main'
TASK_SOLUTION_POWER_DIR = DATA_DIR / 'solution_power'
SOLUTION_DIR = DATA_DIR / 'solutions'
HTML_DIR = PHYRE_DIR / 'viz_static_file'
TASK_CHECKSUM = TASK_DIR / 'checksum.json'
