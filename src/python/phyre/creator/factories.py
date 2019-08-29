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
"""Decorators to convert a function with a task definition to Task objects."""
import collections
import itertools

import numpy as np

import phyre.creator.creator
import phyre.eval_task_complexity
import phyre.util

# How many tasks to generate per task script.
DEFAULT_MAX_TASKS = 100
# How many tasks to use for task complexity evaluation.
DEFAULT_MAX_SEARCH_TASKS = DEFAULT_MAX_TASKS * 2
# Maximum % of tasks the most powerful action can solve
# for subset of tasks to be deemed diverse.
DIVERSITY_FILTER = 0.3

EvalFlags = phyre.eval_task_complexity.Flags

# Defines paramater for task evaluation and selection.
#
#   max_search_tasks: for how many task instances to compute eval stats.
#   required_flags:
#   excluded_flags: a list of solvability flags that must present or must not
#      present. Each flag has the following syntax: <TIER>:<CLASS>,
#      e.g., BALL:GOOD_STABLE, TWO_BALLS:IMPOSSIBLE, BALL:TRIVIAL.
#      See ALLOWED_FLAGS for the list of all solvability classes.
SearchParams = collections.namedtuple(
    'SearchParams',
    'max_search_tasks,diversify_tier,required_flags,excluded_flags')

SOLVABILITY_CLASSES = ('IMPOSSIBLE', 'GOOD_STABLE', 'TRIVIAL')

SearchParams.__new__.__defaults__ = (DEFAULT_MAX_SEARCH_TASKS, None, [], [])


def select_max_diverse_subset(tasks, eval_stats, max_tasks, tier):
    assert tier in phyre.ACTION_TIERS, (
        f'Specified tier {tier} to diversify template for is not in '
        f'{phyre.ACTION_TIERS}')
    template_tasks = set(task.taskId for task in tasks)
    actions_on_tasks = eval_stats['solution_power'][tier]['actions_on_tasks']
    eval_task_ids = eval_stats['solution_power'][tier]['task_ids']
    indicies = np.array([
        i for i in range(len(eval_task_ids))
        if eval_task_ids[i] in template_tasks
    ])
    task_ids = [
        task_id for task_id in eval_task_ids if task_id in template_tasks
    ]
    action_tasks = actions_on_tasks.take(indicies, axis=1)
    threshold = DIVERSITY_FILTER * max_tasks
    assert len(task_ids) == action_tasks.shape[1], (
        f'Number of task ids {len(task_ids)} does not match number of columns '
        f'in task eval stats actions_on_tasks matrix {action_tasks.shape[1]}')
    while action_tasks.shape[1] > max_tasks:
        action_solves = action_tasks.sum(axis=1)
        # Find problem actions that solve > threshold % of task instances.
        problem_tasks = action_tasks[action_solves > threshold]
        problem_tasks_solve = problem_tasks.sum(axis=0)
        # Remove the task solved by largest number of problem actions.
        max_problem_task = problem_tasks_solve.argmax()
        num_solved = problem_tasks_solve.max()
        if not num_solved:
            # Current diveristy requirement has been fufilled, so
            # continue filtering with a stricter diversity requirement.
            threshold = 0.75 * threshold
            continue
        action_tasks = np.delete(action_tasks, max_problem_task, axis=1)
        task_ids.pop(max_problem_task)
        assert len(task_ids) == action_tasks.shape[1], (
            f'Number of task ids {len(task_ids)} does not match number of '
            'columns in task  eval stats actions_on_tasks matrix '
            f'{action_tasks.shape[1]}')
    task_ids = set(task_ids)
    assert len(task_ids) == max_tasks or len(task_ids) == len(tasks), (
        f'After diversity filtering number of task ids {len(task_ids)} does '
        f'not match maximum number of tasks {max_tasks}, or starting number'
        f' {len(task_ids)}')
    return [task for task in tasks if task.taskId in task_ids]


def define_task(f):
    """Use @creator.define_task to decorate a task definition."""

    return TempateTaskScript(f,
                             dict_of_template_values={},
                             version='1',
                             max_tasks=1,
                             search_params=SearchParams())


class SkipTemplateParams(Exception):
    """Rasing this exception in build_task allows to skip the parameters."""


def define_task_template(max_tasks=None,
                         search_params=None,
                         version='1',
                         **dict_of_template_values):
    """Specifies an array of tasks parameters by a cartsian product of params.

    Args:
        max_tasks: None or int. The maximum number of tasks to generate for
            agent to solve. If None, then DEFAULT_MAX_TASKS is used.
        search_params: None, dict or SearchParams. Additional parameters for
            running evaluation and applying evaluation results.
        version: str, name of the current version of the task script. Used to
            find task scripts that need eval stats to be re-computed.

    Returns:
        A callable that take a builder an initializes TempateTaskScript.
    """
    if not dict_of_template_values:
        raise RuntimeError('Must provide some template arguments')

    max_tasks = (max_tasks if max_tasks is not None else DEFAULT_MAX_TASKS)
    if search_params is None:
        search_params = SearchParams()
    elif isinstance(search_params, dict):
        search_params['required_flags'] = list(
            search_params.get('required_flags', []))
        search_params['excluded_flags'] = list(
            search_params.get('excluded_flags', []))
        if search_params.pop('reject_ball_solvable', False):
            search_params['excluded_flags'].append('BALL:GOOD_STABLE')
        if search_params.pop('require_ball_solvable', False):
            search_params['required_flags'].append('BALL:GOOD_STABLE')
        if search_params.pop('require_two_ball_solvable', False):
            search_params['required_flags'].append('TWO_BALLS:GOOD_STABLE')
        search_params = SearchParams(**search_params)
    else:
        assert isinstance(search_params, SearchParams)

    _validate_flags(search_params.required_flags)
    _validate_flags(search_params.excluded_flags)

    assert isinstance(version, str), version

    def decorator(f):
        return TempateTaskScript(f,
                                 dict_of_template_values,
                                 version=version,
                                 max_tasks=max_tasks,
                                 search_params=search_params)

    return decorator


def _validate_flags(flags):
    for flag in flags:
        tier, solvability = flag.split(':')
        assert tier.upper() in ('BALL', 'TWO_BALLS', 'RAMP')
        assert solvability.upper() in SOLVABILITY_CLASSES, flag


class TempateTaskScript(object):

    def __init__(self, builder, dict_of_template_values, max_tasks,
                 search_params, version):
        self.builder = builder
        self.params = dict_of_template_values
        self.max_tasks = max_tasks
        self.search_params = search_params
        self.version = version
        assert max_tasks <= search_params.max_search_tasks

    @property
    def defines_single_task(self):
        return not self.params

    def get_version(self):
        return self.version

    def yield_tasks(self, template_id):
        if self.params:
            keys, lists_of_values = zip(*sorted(self.params.items()))
            value_sets = list(itertools.product(*lists_of_values))
            indices = phyre.util.stable_shuffle(list(range(len(value_sets))))
        else:
            keys = tuple()
            value_sets = [tuple()]
            indices = [0]
        task_index = 0
        for params_id in indices:
            keyed_values = dict(zip(keys, value_sets[params_id]))
            C = phyre.creator.creator.TaskCreator()
            try:
                self.builder(C, **keyed_values)
            except SkipTemplateParams:
                continue
            C.check_task()
            C.task.taskId = '%s:%03d' % (template_id, task_index)
            task_index += 1
            # Not serialized. For within session use only.
            C.task.template_params = keyed_values
            yield C.task

    def get_specific_task(self, task_id):
        template_id, index = task_id.split(':')
        index = int(index)
        tasks = itertools.islice(self.yield_tasks(template_id), index + 1)
        return list(tasks)[index]

    def _check_flags(self, flag_eval_stats, task_id):

        def has_flag(flag):
            tier, solvability = flag.split(':')
            solvability = getattr(EvalFlags, solvability.upper())
            return solvability in flag_eval_stats[tier.lower()][task_id]

        if not all(map(has_flag, self.search_params.required_flags)):
            return False
        if any(map(has_flag, self.search_params.excluded_flags)):
            return False
        return True

    def _build_tasks_with_eval_stats(self, template_id, eval_stats):
        tasks = []
        for task in self.build_tasks_for_search(template_id):
            if not self._check_flags(eval_stats['flags'], task.taskId):
                continue

            tasks.append(task)
            if not self.search_params.diversify_tier and len(
                    tasks) >= self.max_tasks:
                break
        if self.search_params.diversify_tier:
            tasks = select_max_diverse_subset(tasks, eval_stats, self.max_tasks,
                                              self.search_params.diversify_tier)
        return tasks

    def build_tasks(self, template_id, max_tasks):
        return list(itertools.islice(self.yield_tasks(template_id), max_tasks))

    def build_tasks_for_search(self, template_id):
        return self.build_tasks(template_id,
                                self.search_params.max_search_tasks)

    def __call__(self, template_id, eval_stats=None):
        if eval_stats is not None:
            tasks = self._build_tasks_with_eval_stats(template_id, eval_stats)
        else:
            tasks = self.build_tasks(template_id, self.max_tasks)
        assert tasks, (template_id)
        if len(tasks) < self.max_tasks:
            if tasks[0].tier in ('BALL', 'TWO_BALLS', 'RAMP'):
                raise ValueError(
                    'Templates for tasks in BALL, TWO_BALLS, and RAMP tiers'
                    f' must contain max_tasks={self.max_tasks} tasks.'
                    f' Got: {len(tasks)}')
        return tasks
