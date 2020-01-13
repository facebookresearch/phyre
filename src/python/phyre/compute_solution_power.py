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
"""A library that computes the power of solutions from evaluation stats for
a task template.
"""
import functools
import itertools
import json
import logging
import multiprocessing
import os

import joblib
import numpy as np

import phyre.action_mappers
import phyre.action_simulator
import phyre.eval_task_complexity
import phyre.loader
import phyre.settings

VERSION = '1'
SOLUTIONS = 'solutions'


def get_solution_power_path(task_path):
    task_id = os.path.basename(task_path).split('.')[0][4:]
    phyre.settings.TASK_SOLUTION_POWER_DIR.mkdir(exist_ok=True, parents=True)
    return str(phyre.settings.TASK_SOLUTION_POWER_DIR / task_id) + '.lzma'


def get_solution_power(tier, template_id, eval_data):
    _, task_path, task_script = phyre.loader.load_task_script(template_id)
    task_ids = list(eval_data.keys())

    all_sols = set()
    for task_instance in task_ids:
        all_sols.update(
            [tuple(each) for each in eval_data[task_instance][tier][SOLUTIONS]])

    # Generate the tasks and simulator.
    all_sols = list(all_sols)
    tasks = [
        task_script.build_task.get_specific_task(task_instance)
        for task_instance in task_ids
    ]
    simulator = phyre.action_simulator.ActionSimulator(tasks, tier)

    # Run simulation all solution/task pairs and record.
    task_solutions = np.zeros((len(all_sols), len(task_ids)))
    for (sol_i, task_i) in itertools.product(range(len(all_sols)),
                                             range(len(task_ids))):
        status = simulator.simulate_action(task_i, all_sols[sol_i]).status
        task_solutions[sol_i][task_i] = 1 if status.is_solved() else 0
    return task_solutions, task_ids, tier


def does_solution_power_need_update(task_path):
    eval_fpath = phyre.eval_task_complexity.get_evaluation_meta_path(task_path)
    sp_fpath = get_solution_power_path(task_path)
    logging.debug(f'Eval stats path: {eval_fpath}')
    logging.debug(f'Solution power path: {sp_fpath}')
    if not os.path.exists(eval_fpath):
        logging.debug('No eval stats data found. Cannot update solution power')
        return False
    if os.path.exists(sp_fpath):
        logging.debug('Found existing solution power file')
        # TODO(laurafustafson): the file is read twice (here and in
        # does_eval_stats_need_update). They should do a single read.
        with open(eval_fpath) as stream:
            eval_data = json.load(stream)
        solution_power_data = joblib.load(sp_fpath)
        if solution_power_data.get('solution_power_version', '1') != VERSION:
            logging.debug('Computed with old version of solution_power')
            return True
        if solution_power_data.get('evaluator_version', '1') != eval_data.get(
                'evaluator_version', '1'):
            logging.debug('Computed with old version of eval_task_complexity')
            return True
        if solution_power_data.get('task_script_version', '1') != eval_data.get(
                'task_script_version', '1'):
            logging.debug('Computed for old task (%s)',
                          solution_power_data.get('task_script_version', '1'))
            return True
        logging.debug('The solution power results up to date')
        return False
    else:
        return True


def save_solution_power(template_id,
                        eval_meta,
                        eval_data,
                        task_path,
                        num_workers=-1):
    solution_powers = {}
    solution_powers['evaluator_version'] = eval_meta.get(
        'evaluator_version', '1')
    solution_powers['task_script_version'] = eval_meta.get(
        'task_script_version', '1')
    solution_powers['soltuion_power_version'] = VERSION
    partial_worker = functools.partial(
        get_solution_power,
        template_id=template_id,
        eval_data=eval_data['eval_stats'],
    )
    num_workers = min(num_workers, len(
        phyre.action_mappers.ACTION_MAPPERS)) if num_workers > 0 else None
    pool = multiprocessing.Pool(num_workers)
    results = pool.map(partial_worker, phyre.action_mappers.ACTION_MAPPERS)
    pool.close()
    for tier_solution_power, task_ids, tier in results:
        solution_powers[f'{tier}_actions_on_tasks'] = tier_solution_power
        solution_powers['task_ids'] = task_ids
    sp_fpath = get_solution_power_path(task_path)
    logging.info('Saving %s', sp_fpath)
    joblib.dump(solution_powers, sp_fpath, compress=('lzma', 6))
