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

import hashlib

import numpy as np

from phyre import settings
from phyre import simulator
from phyre.interface.scene import ttypes as scene_if


def compute_file_hash(fpath):
    with open(fpath, 'rb') as stream:
        return hashlib.md5(stream.read()).hexdigest()


def compute_tasks_hash(tasks):
    task_ids = sorted(tasks.keys())
    return hashlib.md5(' '.join(task_ids).encode('utf8')).hexdigest()


def compute_creator_hash():
    creator_files = sorted((settings.PHYRE_DIR / 'creator').glob('*.py'))
    hashes = map(compute_file_hash, creator_files)
    return hashlib.md5(' '.join(hashes).encode('utf8')).hexdigest()


def get_solution_path(task_id, solution_id=0):
    return str(settings.SOLUTION_DIR /
               f'task{task_id}.solution{solution_id:02d}')


def stable_shuffle(strings, salt=''):

    def _stable_rng(string):
        string = (str(string) + salt).encode('utf8')
        return hashlib.md5(string).hexdigest()

    return sorted(strings, key=_stable_rng)


def save_user_input(user_input, fpath):
    if not isinstance(user_input, scene_if.UserInput):
        user_input = simulator.build_user_input(*user_input)
    with open(fpath, 'wb') as stream:
        stream.write(simulator.serialize(user_input))


def _maybe_read_text_solution(fpath):
    points = []
    try:
        with open(fpath, 'r') as stream:
            for line in stream:
                if not line.strip():
                    continue
                fields = line.strip().split(',')
                if len(fields) != 2:
                    return None
                x, y = fields
                try:
                    points.append((int(x), int(y)))
                except ValueError:
                    return None
    except UnicodeDecodeError:
        return None
    return points


def load_user_input(fpath):
    # Try to read in text format first.
    points = _maybe_read_text_solution(fpath)
    user_input = scene_if.UserInput(flattened_point_list=[],
                                    polygons=[],
                                    balls=[])
    if points is not None:
        user_input.flattened_point_list = np.array(points).flatten().tolist()
    else:
        with open(fpath, 'rb') as stream:
            simulator.deserialize(user_input, stream.read())
    return user_input
