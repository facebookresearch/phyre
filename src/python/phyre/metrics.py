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
"""Tools to get train/test splits and compute evaluation metrics.

"""
from typing import (Any, Callable, Dict, List, Sequence, Tuple, Union)
import collections
import functools
import hashlib
import itertools
import logging
import math

import phyre.action_mappers
import phyre.action_simulator
import phyre.loader
import phyre.util

MAIN_EVAL_SETUPS: Sequence[str] = (
    'ball_cross_template',
    'ball_within_template',
    'two_balls_cross_template',
    'two_balls_within_template',
    'ball_phyre_to_tools',
)
"""List of valid evaluation setups for phyre.
"""

EVAL_SETUP_BUILDERS: Dict[str, Callable] = {}

MAX_TEST_ATTEMPTS: int = 100
"""Maximum number of attempts agents are allowed to make per specific task.
"""

TRAIN_SHARE = 0.8  # Size of the train split.
AUCCESS_METRIC = 'independent_solved_by_aucs'

SimulationStatusLike = Union[int, str, phyre.action_simulator.SimulationStatus]
SimulationLog = Sequence[Tuple[str, SimulationStatusLike]]
EvaluationLog = List[Tuple[str, phyre.action_simulator.SimulationStatus]]
EvalSetup = Sequence[Tuple[Sequence[str], Sequence[Sequence[str]]]]
Metrics = Dict[str, Any]

logger = logging.getLogger(__name__)


def eval_setup_to_action_tier(eval_setup_name: str) -> str:
    """Gets a default action tier for an eval setup."""
    for tier in phyre.action_mappers.ACTION_MAPPERS:
        if eval_setup_name.startswith(tier):
            return tier
    raise ValueError('Failed to derive action tier for eval setup %s' %
                     eval_setup_name)


def list_eval_setups() -> Tuple[str, ...]:
    """Get a list of names for all known eval setups."""
    return tuple(sorted(EVAL_SETUP_BUILDERS))


def get_fold(eval_setup: str, seed: int
            ) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    """Get seed'th fold for specified evaluation setup.

    Args:
        eval_setup: The name of the evaluation setup to use. E.g.,
            ball_cross_template.
        seed: The random seed to create the fold.

    Returns:
        Tuple (train_ids, dev_ids, test_ids)
            Contains task ids to use for each split.

    Raises:
        ValueError: Eval_setup is not valid evaluation setup.
    """
    try:
        builder = EVAL_SETUP_BUILDERS[eval_setup]
    except KeyError:
        raise ValueError(f'Unknown eval setup: {eval_setup}. Chose one of'
                         f' {",".join(EVAL_SETUP_BUILDERS)}')
    _, test_ids = _flatten_eval_setup(builder(seed))
    train_ids, dev_ids = _flatten_eval_setup(builder(seed=seed, dev_seed=seed))
    return train_ids, dev_ids, test_ids


def _flatten_eval_setup(eval_setup: EvalSetup
                       ) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    all_train_ids, all_test_ids = [], []
    for train_ids, test_groups in eval_setup:
        all_train_ids.extend(train_ids)
        for test_ids in test_groups:
            all_test_ids.extend(test_ids)
    return tuple(sorted(all_train_ids)), tuple(sorted(all_test_ids))


def _register_eval_setup_builder(func: Callable) -> Callable:
    EVAL_SETUP_BUILDERS[func.__name__] = func
    return func


def _register_multi_tier_eval_setup_builder(func: Callable) -> Callable:
    assert func.__name__.startswith('_'), func
    for tier in phyre.action_mappers.ACTION_MAPPERS:
        EVAL_SETUP_BUILDERS[f'{tier}{func.__name__}'] = functools.partial(
            func, tier)
    return func


def get_task_ids_in_tier(tier_name):
    """Returns a list of all task_ids in iter."""
    # dict of dicts: template_id -> task_id -> tier.
    template_task_tiers = collections.defaultdict(dict)
    for task_id, task in phyre.loader.load_compiled_task_dict().items():
        template_id = task_id.split(':')[0]
        template_task_tiers[template_id][task_id] = task.tier

    selected_task_ids = set()
    tier_name = tier_name.upper()
    for template_id, task_to_tier in template_task_tiers.items():
        tiers = frozenset(task_to_tier.values())
        if len(tiers) == 1 and next(iter(tiers)) == tier_name:
            selected_task_ids.update(task_to_tier)
    return sorted(selected_task_ids)


def create_dev_set(eval_setup, train_share=TRAIN_SHARE, seed=0):
    """Create a new train/test split from a train part of another eval setup."""
    dev_eval_setup = []
    for train_task_ids, _ in eval_setup:
        train_task_ids = phyre.util.stable_shuffle(train_task_ids,
                                                   f'make_dev{seed}')
        num_train = int(len(train_task_ids) * train_share)
        train, dev = train_task_ids[:num_train], train_task_ids[num_train:]
        dev_eval_setup.append((train, [dev]))
    return dev_eval_setup


def _get_task_per_tpl(task_ids):
    tasks_per_tpl = collections.defaultdict(list)
    for task_id in task_ids:
        tasks_per_tpl[task_id.split(':')[0]].append(task_id)
    return tasks_per_tpl


@_register_eval_setup_builder
def ball_single_instance(max_per_tpl=10) -> EvalSetup:
    """Eval setup where each task instance is in separate eval group.

    The number of tasks that is randomly picked from each template is limited to
    10.
    """
    task_ids = get_task_ids_in_tier('ball')
    tasks_per_tpl = _get_task_per_tpl(task_ids)
    eval_setup = []
    for _, task_ids_group in sorted(tasks_per_tpl.items()):
        eval_task_ids = phyre.util.stable_shuffle(
            task_ids_group, 'ball_online_ind_tasks')[:max_per_tpl]
        for task_id in eval_task_ids:
            eval_groups = ((task_id,),)
            train_set = ()
            train_group = (train_set, eval_groups)
            eval_setup.append(train_group)

    return eval_setup


@_register_eval_setup_builder
def ball_single_instance_tiny() -> EvalSetup:
    return ball_single_instance(1)


@_register_eval_setup_builder
def ball_phyre_to_tools(seed=1, dev_seed=None) -> EvalSetup:
    """A set of train have train and PHYRE-B and val and test in TOOLS."""
    tool_task_ids = get_task_ids_in_tier("VIRTUAL_TOOLS")
    tasks_per_tpl = collections.defaultdict(list)
    for task_id in tool_task_ids:
        tasks_per_tpl[task_id.split(':')[0]].append(task_id)

    key_order = phyre.util.stable_shuffle(tasks_per_tpl,
                                          f'virtual_tools_{seed}')
    if dev_seed is not None:
        key_order = key_order[::2]
    else:
        key_order = key_order[1::2]
    eval_ids = sum([tasks_per_tpl[k] for k in key_order], [])

    # Always use train+val as train set from cross-dataset.
    [(train_ids, _)] = _cross_template("BALL", seed=seed)
    train_group = (tuple(train_ids), [tuple(eval_ids)])
    eval_setup = []
    eval_setup.append(train_group)
    return eval_setup


@_register_multi_tier_eval_setup_builder
def _cross_template(tier, seed=1, dev_seed=None,
                    train_share=TRAIN_SHARE) -> EvalSetup:
    """A set of train groups with half templates in train and half in test."""
    task_ids = get_task_ids_in_tier(tier)
    tasks_per_tpl = collections.defaultdict(list)
    for task_id in task_ids:
        tasks_per_tpl[task_id.split(':')[0]].append(task_id)
    key_order = phyre.util.stable_shuffle(list(tasks_per_tpl),
                                          f'ball_cross_template_half_{seed}')
    train_size = int(round(len(key_order) * train_share))
    if dev_seed is not None:
        key_order = key_order[:train_size]
        key_order = phyre.util.stable_shuffle(
            key_order, f'dev_ball_cross_template_half_{dev_seed}')
        train_size = int(len(key_order) * train_share)
    tasks_per_tpl = [tasks_per_tpl[key] for key in key_order]
    train, test = tasks_per_tpl[:train_size], tasks_per_tpl[train_size:]
    eval_setup = []
    train_ids = sum(train, [])
    eval_ids = sum(test, [])
    train_group = (tuple(train_ids), [tuple(eval_ids)])
    eval_setup.append(train_group)
    return eval_setup


@_register_multi_tier_eval_setup_builder
def _single_template(tier, seed=1, dev_seed=None,
                     train_share=TRAIN_SHARE) -> EvalSetup:
    """Each template is a separate group."""
    task_ids = get_task_ids_in_tier(tier)
    tasks_per_tpl = _get_task_per_tpl(task_ids)
    eval_setup = []
    for _, task_ids_group in sorted(tasks_per_tpl.items()):
        task_ids_group = phyre.util.stable_shuffle(
            task_ids_group, f'ball_online_ind_tasks{seed}')
        train_size = int(round(len(task_ids_group) * train_share))
        if not train_size:
            continue
        train_ids, eval_ids = (task_ids_group[:train_size],
                               task_ids_group[train_size:])
        eval_groups = (tuple(eval_ids),)
        train_set = tuple(train_ids)
        train_group = (train_set, eval_groups)
        eval_setup.append(train_group)

    if dev_seed is not None:
        eval_setup = create_dev_set(eval_setup, train_share, seed=dev_seed)

    return eval_setup


@_register_multi_tier_eval_setup_builder
def _within_template(tier, seed=1, dev_seed=None,
                     train_share=TRAIN_SHARE) -> EvalSetup:
    per_template_eval_setup = _single_template(tier,
                                               seed=seed,
                                               train_share=train_share)
    all_train_ids = []
    all_eval_ids = []
    for train_ids, (eval_ids,) in per_template_eval_setup:
        all_train_ids.extend(train_ids)
        all_eval_ids.extend(eval_ids)
    eval_setup = [(all_train_ids, [all_eval_ids])]
    if dev_seed is not None:
        eval_setup = create_dev_set(eval_setup, train_share, seed=dev_seed)
    return eval_setup


def _normalize_sumulation_status(status: SimulationStatusLike
                                ) -> phyre.action_simulator.SimulationStatus:
    if isinstance(status, str):
        status = int(status)
    return phyre.action_simulator.SimulationStatus(status)


def compute_metrics(raw_simulation_log: SimulationLog) -> Metrics:
    assert isinstance(raw_simulation_log,
                      (tuple, list)), type(raw_simulation_log)
    if not raw_simulation_log:
        logger.warning('Computing metrics for empty evaluation log!')
    else:
        assert len(raw_simulation_log[0]) == 2, raw_simulation_log[0]

    simulation_log = [(task, _normalize_sumulation_status(status))
                      for task, status in raw_simulation_log]
    simulation_log = [(task, _normalize_sumulation_status(status))
                      for task, status in simulation_log
                      if not status.is_invalid()]

    attempts = collections.defaultdict(int)
    solved_at = {}
    first_solution_points = []
    for attempt_index, (task, status) in enumerate(simulation_log, start=1):
        attempts[task] += 1
        if task not in solved_at and status.is_solved():
            first_solution_points.append(attempt_index)
            solved_at[task] = attempts[task]

    if solved_at and max(solved_at.values()) > MAX_TEST_ATTEMPTS:
        logger.warning(
            'Used more than %d attempts at least of one of the'
            ' tasks. It most likely means a bug in evaluation loop.',
            MAX_TEST_ATTEMPTS)

    # independent_solved_by[i] := how many task was solved with at most i
    # attempts on the task.
    independent_solved_by = [0]
    for num_attempts, group in itertools.groupby(sorted(solved_at.values())):
        count = len(list(group))
        if num_attempts > MAX_TEST_ATTEMPTS:
            break
        while len(independent_solved_by) <= num_attempts:
            independent_solved_by.append(independent_solved_by[-1])
        independent_solved_by[num_attempts] += count
    while len(independent_solved_by) <= MAX_TEST_ATTEMPTS:
        independent_solved_by.append(independent_solved_by[-1])

    independent_solved_by_aucs = [0.]
    num, denom = 0., 0.
    for up_to in range(1, MAX_TEST_ATTEMPTS + 1):
        weight = math.log(up_to + 1) - math.log(up_to)
        num += weight * independent_solved_by[up_to]
        denom += weight
        independent_solved_by_aucs.append(num / denom)

    global_solved_by = {
        t: sum(num_attempts <= t for num_attempts in first_solution_points)
        for t in [100, 1000, 100000]
    }

    return dict(
        independent_solved_by=independent_solved_by,
        independent_solved_by_aucs=independent_solved_by_aucs,
        global_solved_by=global_solved_by,
        total_attempts=sum(attempts.values()),
        total_solved=len(first_solution_points),
    )


def normalize_metrics(metrics: Metrics, num_tasks: int) -> Metrics:

    def _normalize(value):
        if isinstance(value, dict):
            return {k: _normalize(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_normalize(v) for v in value]
        else:
            return value / num_tasks

    return _normalize(metrics)


def compute_metrics_normalized(simulation_log: SimulationLog,
                               num_tasks: int) -> Metrics:
    metrics = compute_metrics(simulation_log)
    if metrics['total_attempts'] < MAX_TEST_ATTEMPTS * num_tasks:
        logger.warning(
            'Used %f attempts per task instead of maximum allowed'
            ' %f. That probably indicate a bug in evaluation loop.',
            metrics['total_attempts'] / num_tasks, MAX_TEST_ATTEMPTS)
    return normalize_metrics(metrics, num_tasks)


class Evaluator():
    """Class for storing simulation results and calculating metrics."""

    def __init__(self, task_ids: Tuple[str]):
        self._task_ids = task_ids
        self._log: EvaluationLog = []
        self.attempts_per_task_index: List[int] = [0] * len(task_ids)

    def maybe_log_attempt(self, task_index: int,
                          status: SimulationStatusLike) -> bool:
        """Logs status of attempt on task iff status is for a valid action.

        Args:
            task_index: index into task_ids of task.
            status: simulation status of attempt on task.

        Returns:
            True if attempt was logged (valid action, less than
                MAX_TEST_ATTEMPTS made on task), else False.


        Raises:
            AssertionError: More than MAX_TEST_ATTEMPTS attempts were made on
                the task.
        """
        status = _normalize_sumulation_status(status)
        if status.is_invalid():
            return False
        assert self.attempts_per_task_index[task_index] < MAX_TEST_ATTEMPTS, (
            f'Task {self._task_ids[task_index]} of index {task_index} has '
            f'{self.attempts_per_task_index[task_index]} attempts made, '
            'greater than maximum number of test attempts '
            f'{MAX_TEST_ATTEMPTS}')
        task_id = self._task_ids[task_index]
        self._log.append((task_id, status))
        self.attempts_per_task_index[task_index] += 1
        return True

    def compute_all_metrics(self) -> Metrics:
        """Computes metrics based on recorded log of simulation results.

        Returns:
            Dictionary mapping metric name to computed value.
        """
        return compute_metrics_normalized(self._log, len(self._task_ids))

    # Deprecated spelling.
    def get_aucess(self, attempts: int = MAX_TEST_ATTEMPTS) -> float:
        return self.get_auccess(attempts)

    def get_auccess(self, attempts: int = MAX_TEST_ATTEMPTS) -> float:
        """Calculated AUCCESS metric.

        Starting in v0.0.1.1 renamed from get_aucess to get_auccess.

        Args:
            attempts: Number of attempts to use for calulation of auccess,
                default MAX_TEST_ATTEMPTS.

        Returns:
            Result of AUCCESS calculation.
        """
        metrics = self.compute_all_metrics()
        return metrics[AUCCESS_METRIC][attempts]

    def get_attempts_for_task(self, task_index):
        """
        Args:
            task_index: index into task_ids of task.

        Returns:
            Number recorded attempts on task_index.
        """
        return self.attempts_per_task_index[task_index]

    @property
    def task_ids(self) -> Tuple[str, ...]:
        """Returns ordered list of tasks ids."""
        return self._task_ids

    def __len__(self) -> int:
        """Returns number of recorded attempts."""
        return len(self._log)
