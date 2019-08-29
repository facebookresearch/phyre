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

import concurrent.futures
import os

import joblib
import numpy as np

import numpy as np

import phyre.action_simulator
import phyre.eval_task_complexity
import phyre.loader

THRESHOLDS = [0.01, 0.1, 0.25, 0.3, 0.5, 0.75, 0.9]
GOOD_TIERS = ['ball', 'two_balls']
NUM_ACTIONS = 1000000


def compute_cache_power_of_solutions(template, template_tasks, tier):
    base_dir = phyre.simulation_cache.get_partial_cache_folder(NUM_ACTIONS)
    assert base_dir.exists(), (f'Partial simulation cache folder {base_dir} '
                               'does not exist')
    cached_task_actions = {}
    for task in template_tasks:
        fname = f'{base_dir}/{tier}/{template}/{task}.gz'
        assert os.path.exists(fname), (f'Partial simulation cache file {fname} '
                                       'does not exist')
        actions = joblib.load(fname)
        cached_task_actions[task] = actions
    action_task = np.stack(list(cached_task_actions.values()), axis=1)
    num_solved = (action_task > 0).sum(axis=1)
    return sorted(num_solved.tolist(), reverse=True)


def compute_power_of_solutions(template_eval, template_tasks, tier):
    """Compute power for each solution in eval stats.

    Solution power is how many tasks an action solves.
    """
    template_tasks = set(template_tasks)
    actions_on_tasks = template_eval['solution_power'][tier]['actions_on_tasks']
    task_ids = template_eval['solution_power'][tier]['task_ids']
    indicies = np.array(
        [i for i in range(len(task_ids)) if task_ids[i] in template_tasks])
    actions_template_tasks = actions_on_tasks.take(indicies, axis=1)
    solves = actions_template_tasks.sum(axis=1)
    solves.sort()
    return solves[::-1].tolist()


def print_stats(template_tier_pairs, all_task_ids, use_partial_cache):
    all_eval_stats = phyre.eval_task_complexity.load_all_eval_stats()
    print('Number of actions that solves specified percent of tasks in a'
          ' template')
    print()
    percent_thresholds = ['%d%%' % int(i * 100) for i in THRESHOLDS]
    print('tpl',
          '%10s' % 'tier',
          '%10s' % 'solutions',
          *percent_thresholds,
          sep='\t')

    executor = concurrent.futures.ProcessPoolExecutor()
    all_solution_powers = []
    for template_id, tier in template_tier_pairs:
        template_tasks = [
            task_id for task_id in all_task_ids
            if task_id.startswith(template_id)
        ]
        if use_partial_cache:
            future = executor.submit(compute_cache_power_of_solutions,
                                     template_id, template_tasks, tier)
        else:
            eval_stats = all_eval_stats[template_id]
            future = executor.submit(compute_power_of_solutions, eval_stats,
                                     template_tasks, tier)
        all_solution_powers.append((template_id, tier, future))

    for template_id, tier, future in all_solution_powers:
        solution_powers = future.result()
        num_solved = []
        for threshold in THRESHOLDS:
            num_solved.append(
                sum(1 for i in solution_powers
                    if i >= threshold * len(template_tasks)))
        print(template_id,
              '%10s' % tier,
              '%10s' % len(solution_powers),
              *num_solved,
              sep='\t')


def main(template_id, tier, use_partial_cache):
    task_dict = phyre.loader.load_compiled_task_dict()

    template_to_tier = {}
    for task_id, task in task_dict.items():
        if tier is not None:
            template_to_tier[task_id.split(':')[0]] = tier
        elif task.tier.lower() in GOOD_TIERS:
            template_to_tier[task_id.split(':')[0]] = task.tier.lower()

    if template_id != 'all':
        assert template_id in template_to_tier
        template_to_tier = {template_id: template_to_tier[template_id]}

    print_stats(sorted(template_to_tier.items(), key=lambda x: (x[1], x[0])),
                tuple(task_dict), use_partial_cache)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--template-id',
                        required=True,
                        help='Single template-id or "all".')
    parser.add_argument(
        '--tier',
        choices=GOOD_TIERS,
        help='Tier to test. If not set, will be derived automatically.')
    parser.add_argument(
        '--use-partial-cache',
        action='store_true',
        help='Use partial cache opposed to eval stats for diversity.')
    main(**vars(parser.parse_args()))
