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

from typing import List

import base64
import collections
import copy
import logging
import os
import io
import time

import PIL.Image

from phyre import action_mappers
from phyre import action_simulator
from phyre import eval_task_complexity
from phyre import loader
from phyre import settings
from phyre import simulator
from phyre import util
from phyre import vis
from phyre.interface.scene import ttypes as scene_if
from phyre.interface.task import ttypes as task_if

Flags = eval_task_complexity.Flags

# Where to store last user input/action.
LAST_INPUT_PATH = '/tmp/phyre_last_user_input.txt'

PROD_MODE = 'prod'
DEV_MODE = 'dev'
DEMO_MODE = 'demo'
PROD_TIERS = ('BALL', 'TWO_BALLS', 'VIRTUAL_TOOLS')

TIER_TO_CODE = {
    'ball': 'B',
    'two_balls': '2B',
    'ramp': 'R',
    'virtual_tools': 'B'
}
CODE_TO_FULLNAME = {'B': 'ball', '2B': 'two_balls', 'R': 'ramp'}

INVALID_INPUT = action_simulator.SimulationStatus.INVALID_INPUT
NOT_SOLVED = action_simulator.SimulationStatus.NOT_SOLVED
SOLVED = action_simulator.SimulationStatus.SOLVED


def _time_me(f):

    def new_f(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        print('%s took %.3fs' % (f.__name__, time.time() - start))
        return result

    return new_f


class ServiceHandler():

    def __init__(self, config, test_mode=False):
        self._task_cache = None
        self._last_read_timestamp = 0
        self._test_mode = test_mode
        self._eval_stats = None
        self._config = config
        if self._config['mode'] == DEMO_MODE:
            print('Going to pre-load cache')
            self.task_cache
            self.eval_stats

    def _initize_task_cache(self):
        """Read task list from a pickle."""
        if self._test_mode:
            self._last_read_timestamp = 0
            self._task_cache = {}
        logging.info('Reading all tasks for a pickle')
        self._task_cache = loader.load_compiled_task_dict()
        if self._config['mode'] != DEV_MODE:
            self._task_cache = {
                key: task
                for key, task in self._task_cache.items()
                if task.tier in PROD_TIERS
            }
        self._last_read_timestamp = max(
            os.path.getmtime(path)
            for path in settings.TASK_DIR.glob("*.bin.lzma"))

    @property
    @_time_me
    def eval_stats(self):
        if self._test_mode:
            return {}
        if self._eval_stats is None:
            logging.info('Reloading eval stats')
            self._eval_stats = eval_task_complexity.load_all_eval_stats(0)
        return self._eval_stats

    @property
    def task_cache(self):
        if self._task_cache is None:
            self._initize_task_cache()
        if self._config['mode'] != DEV_MODE:
            assert self._task_cache, (
                'Task reloading is off, but task.bin is not found')
            return self._task_cache
        needs_update = set()
        times = []
        for fname in sorted(os.listdir(str(settings.TASK_SCRIPTS_DIR))):
            if not fname.startswith('task'):
                continue
            mtime = (settings.TASK_SCRIPTS_DIR / fname).stat().st_mtime
            if mtime > self._last_read_timestamp:
                needs_update.add(fname[4:].split('.')[0])
                times.append(mtime)
            if self._test_mode:
                print('NOTE: Runnnig in test mode and so considering only'
                      ' the first task')
                break
        if needs_update:
            logging.info('Reloading task cache for %d task scripts: %s',
                         len(needs_update), needs_update)
            # Reseting eval cache to maybe invalidate some eval stats.
            self._eval_stats = None
            data = loader.load_tasks_from_folder(template_id_list=needs_update,
                                                 eval_stats=self.eval_stats)
            logging.info('Got %d task instances', len(data))
            bad_keys = [
                k for k in self._task_cache if k.split(':')[0] in needs_update
            ]
            for k in bad_keys:
                del self._task_cache[k]
            self._task_cache.update(data)
            self._last_read_timestamp = max(times)
        return self._task_cache

    @_time_me
    def list_task_tier_map(self, task_id_pattern):
        data = {}
        seen_templates = set()
        for task_id, task in sorted(self.task_cache.items()):
            if task_id_pattern:
                if not task_id.startswith(task_id_pattern):
                    continue
            else:
                template = task_id.split(':')[0]
                if template in seen_templates:
                    continue
                seen_templates.add(template)
            data[task_id] = task.tier
        return data

    @_time_me
    def load_evaluation_data(self, task_id_pattern):
        known_task_ids = frozenset(self.task_cache)

        tasks_in_templates = collections.Counter(
            [task_id.split(':')[0] for task_id in known_task_ids])

        all_data = {}
        solved_in_template = collections.defaultdict(collections.Counter)
        for template_stats in self.eval_stats.values():
            for tier, tier_data in template_stats['flags'].items():
                for task_id, flags in tier_data.items():
                    if task_id not in known_task_ids:
                        continue
                    if Flags.GOOD_STABLE in flags:
                        solved_in_template[task_id.split(':')[0]][tier] += 1
                    if task_id not in all_data:
                        all_data[task_id] = eval_stats_to_thrift(
                            template_stats, task_id)

        for template_id, counts in solved_in_template.items():
            num_tasks = sum(
                task_id.startswith(template_id) for task_id in known_task_ids)

            def to_percent(x):
                return int(x * 100 / num_tasks)

            all_data[template_id + ':'] = task_if.EvalData(
                percent_ball=to_percent(counts['ball']),
                percent_two_balls=to_percent(counts['two_balls']),
                percent_ramp=to_percent(counts['ramp']),
                num_tasks=tasks_in_templates[template_id],
            )
        if task_id_pattern:
            all_data = {
                k: v
                for k, v in all_data.items()
                if k.startswith(task_id_pattern)
            }
        else:
            all_data = {k: v for k, v in all_data.items() if k.endswith(':')}
        return all_data

    @_time_me
    def get_task_from_id(self, task_id):
        template_id, _ = task_id.split(':')
        if self._config['mode'] == DEMO_MODE:
            # In demo mode use cached tasks.
            task = self.task_cache[task_id]
        else:
            # Try to load the task instance directly.
            try:
                _, _, module = loader.load_task_script(template_id)
            except RuntimeError as e:
                logging.warning("Failed to load module: %s", e)
                task = self.task_cache[task_id]
            else:
                task = module.build_task.get_specific_task(task_id)
                solution_path = util.get_solution_path(task_id)
                if os.path.exists(solution_path):
                    task.solutions = [util.load_user_input(solution_path)]

        meta_task = task_if.TaskWithMeta(task=task)

        if hasattr(task, 'template_params'):
            meta_task.template_params = ' '.join(
                f'{k}={v}' for k, v in task.template_params.items())

        eval_stats = eval_task_complexity.maybe_load_evaluation(template_id)
        if eval_stats is not None and eval_stats_has_task(eval_stats, task_id):
            meta_task.eval_data = eval_stats_to_thrift(eval_stats, task_id)
            meta_task.eval_data.known_solutions = filter_known_solutions(
                meta_task.eval_data.known_solutions, self._config['mode'],
                task.tier)

            status_counts = {
                tier: stats[task_id]
                for tier, stats in eval_stats['status_counts'].items()
                if tier.upper() in PROD_TIERS or
                self._config['mode'] == DEV_MODE
            }
            # Create a text description of the eval stats.
            chunks = ['attempts to solution:']
            for tier, stats in sorted(status_counts.items()):
                if stats[SOLVED] == 0:
                    chunks.append(f'{tier}=inf')
                else:
                    cnt = int(
                        (stats[SOLVED] + stats[NOT_SOLVED]) / stats[SOLVED])
                    chunks.append(f'{tier}={cnt}')
            chunks.append('valid share:')
            for tier, stats in sorted(status_counts.items()):
                if sum(stats.values()):
                    share = 1.0 - (stats[INVALID_INPUT] / sum(stats.values()))
                    chunks.append(f'{tier}={share * 100:.1f}%')
                else:
                    chunks.append(f'{tier}=nan')
            chunks.append('flags:')
            for tier, stats in sorted(eval_stats['flags'].items()):
                chunks.append('%s={%s}' % (tier, ','.join(
                    flag.name.lower() for flag in stats[task_id])))
            meta_task.text_eval_info = ' '.join(chunks)
        if self._config['mode'] != DEMO_MODE:
            meta_task.rendered_img = get_task_as_base64_image(task)
        return meta_task

    def get_task_thumbs(self, task_ids):
        thumbs = []
        for task_id in task_ids:
            task = self.task_cache[task_id]
            [rel_id] = task.relationships
            rel = task_if.SpatialRelationship._VALUES_TO_NAMES[rel_id]
            thumbs.append(
                task_if.Thumb(img=get_task_as_base64_image(task, resize=100),
                              extra=rel))
        return thumbs

    def _simulate_task_meta(self, task, user_input, dilate=True):
        if self._config['mode'] == DEV_MODE:
            util.save_user_input(user_input, LAST_INPUT_PATH)
        if self._config['mode'] == DEMO_MODE:
            user_input.flattened_point_list = []
            user_input.polygons = []
            if user_input.balls:
                user_input.balls = user_input.balls[:self._config['max_balls']]
        task.scene = simulator.add_user_input_to_scene(
            task.scene, user_input, keep_space_around_bodies=dilate)
        print('Converted %d points, %d polygons, %d balls into %d bodies'
              ' with %d shapes' %
              (len(user_input.flattened_point_list or []) / 2,
               len(user_input.polygons or []), len(
                   user_input.balls or []), len(task.scene.user_input_bodies),
               sum(len(b.shapes) for b in task.scene.user_input_bodies)))
        simulation = simulator.simulate_task(task, stride=3)
        if self._config['mode'] == DEV_MODE:
            rendered = [
                get_scene_as_base64_image(scene)
                for scene in simulation.sceneList[::10]
            ]
        else:
            rendered = []
        return task_if.TaskSimulationWithMeta(simulation=simulation,
                                              rendered_imgs=rendered)

    @_time_me
    def simulate_task_by_id(self, task_id, user_input, dilate):
        return self._simulate_task_meta(copy.copy(self.task_cache[task_id]),
                                        user_input,
                                        dilate=dilate)

    def simulate_task_with_last_input(self, task):
        assert self._config['mode'] != DEMO_MODE
        return self._simulate_task_meta(task, self.get_last_input())

    def get_eval_user_input(self, task_id, tier_name):
        template_id = task_id.split(':')[0]
        if tier_name.endswith('U'):
            tier_name = CODE_TO_FULLNAME[tier_name[:-1]]
            solutions = self.eval_stats[template_id]['unstable_solutions'][
                tier_name][task_id]
        else:
            tier_name = CODE_TO_FULLNAME[tier_name]
            solutions = self.eval_stats[template_id]['solutions'][tier_name][
                task_id]
        action_tier = action_mappers.ACTION_MAPPERS[tier_name]()
        user_input, _ = action_tier.action_to_user_input(solutions[0])
        return user_input

    def get_last_input(self):
        assert self._config['mode'] == DEV_MODE
        if os.path.exists(LAST_INPUT_PATH):
            user_input = util.load_user_input(LAST_INPUT_PATH)
        else:
            user_input = scene_if.UserInput()
            logging.warning('No last user input found')
        return user_input

    def save_solution(self, task_id, user_input):
        assert self._config['mode'] != DEMO_MODE
        util.save_user_input(user_input, util.get_solution_path(task_id))

    @_time_me
    def render(self, scene):
        assert self._config['mode'] != DEMO_MODE
        pixels = simulator.scene_to_raster(scene).flatten().tolist()
        return scene_if.Image(width=scene.width,
                              height=scene.height,
                              values=pixels)


def eval_stats_has_task(template_stats, task_id):
    return task_id in template_stats['status_counts'][
        'ball'] and task_id in template_stats['flags']['ball']


def eval_stats_to_thrift(template_stats, task_id):
    flags_order = [
        (Flags.GOOD_STABLE, 'GS'),
        (Flags.GOOD, 'G'),
        (Flags.BAD_STABLE, 'B'),
        (Flags.BAD, 'B'),
        (Flags.IMPOSSIBLE, 'IMP'),
    ]

    def find_flag_code(flags):
        for flag, code in flags_order:
            if flag in flags:
                return code

    thrift_eval_data = {}
    solutions_codes = []
    for tier in template_stats['status_counts']:
        not_solved = template_stats['status_counts'][tier][task_id][NOT_SOLVED]
        solved = template_stats['status_counts'][tier][task_id][SOLVED]
        if solved > 0:
            attempts = int(((not_solved + solved) / solved))
        else:
            attempts = -1
        thrift_eval_data[f'attempts_to_solve_{tier}'] = attempts
    for tier in template_stats['flags']:
        thrift_eval_data[f'flag_{tier}'] = find_flag_code(
            template_stats['flags'][tier][task_id])
    for tier in template_stats['solutions']:
        if template_stats['solutions'][tier].get(task_id):
            solutions_codes.append(TIER_TO_CODE[tier])
    for tier in template_stats['unstable_solutions']:
        if template_stats['unstable_solutions'][tier].get(task_id):
            solutions_codes.append(TIER_TO_CODE[tier] + 'U')
    thrift_eval_data['known_solutions'] = solutions_codes
    return task_if.EvalData(**thrift_eval_data)


def get_task_as_base64_image(task, resize=None):
    return get_scene_as_base64_image(task.scene, resize=resize)


def get_scene_as_base64_image(scene, resize=None):
    arr = vis.observations_to_uint8_rgb(simulator.scene_to_raster(scene))
    return get_image_as_base64(arr, resize=resize)


def get_image_as_base64(arr, resize=None):
    img = PIL.Image.fromarray(arr)
    if resize is not None:
        img.thumbnail((resize, resize), PIL.Image.ANTIALIAS)
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    return base64.b64encode(img_buffer.getvalue()).decode('utf8')


def filter_known_solutions(known_solutions: List[str], mode: str,
                           task_tier: str) -> List[str]:
    """Filter the list of known solutions according to the mode."""
    if mode in (PROD_MODE, DEMO_MODE):
        # In prod and demo mode show inly stable ball solutions.
        good_codes = [TIER_TO_CODE[t.lower()] for t in PROD_TIERS]
        known_solutions = [
            code for code in known_solutions if code in good_codes
        ]
        if mode == DEMO_MODE:
            # In demo mode show only one solution. In theory it should be a
            # solution for the tier. But none exists, any solution will work.
            expected_code = TIER_TO_CODE[task_tier.lower()]
            if expected_code in known_solutions:
                return [expected_code]
            else:
                print(f'Warning! No {expected_code} solution found')
                return [known_solutions[0]]
        else:
            return known_solutions
    else:
        return known_solutions
