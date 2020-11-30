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
"""A library to use precomputed simulation results for a fixed set of actions.

"""
from typing import FrozenSet, Optional, Sequence, Union
import logging
import os
import pathlib
import urllib.request

import joblib
import numpy as np

import phyre.action_simulator

ACTION_SEED = 42  # Default seed for the action space.
PHYRE_CACHE_ENV = 'PHYRE_CACHE_DIR'
ACTION_FILE_NAME = 'actions.pickle'
CACHE_FILE_NAME = 'simulation_cache.gz'
# Map: action_tier -> tuple of task tiers.
TIERS = {'ball': ('BALL', 'VIRTUAL_TOOLS'), 'two_balls': 'TWO_BALS'}

DEFAULT_NUM_ACTIONS = 100000

SOLVED = int(phyre.action_simulator.SimulationStatus.SOLVED)
INVALID = int(phyre.action_simulator.SimulationStatus.INVALID_INPUT)
NOT_SOLVED = int(phyre.action_simulator.SimulationStatus.NOT_SOLVED)


def get_default_100k_cache(tier: str) -> 'SimulationCache':
    """Get cache with results for simulation of 100k "default" actions."""
    url = (f'https://dl.fbaipublicfiles.com/phyre/simulation_cache/v1'
           f'/{DEFAULT_NUM_ACTIONS}/{tier}/{CACHE_FILE_NAME}')

    cache_dir = (phyre.simulation_cache.get_cache_folder(DEFAULT_NUM_ACTIONS) /
                 tier)
    cache_path = cache_dir / CACHE_FILE_NAME
    if not cache_path.exists():
        logging.info('Downloading cache from %s', url)
        cache_dir.mkdir(exist_ok=True, parents=True)
        urllib.request.urlretrieve(url, str(cache_path))
    logging.info('Loading cache from %s', cache_dir)
    cache = SimulationCache(cache_dir)
    return cache


def _get_root_cache_folder() -> pathlib.Path:
    cache_root = pathlib.Path(
        os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')))
    return pathlib.Path(os.environ.get(PHYRE_CACHE_ENV, cache_root / 'phyre'))


def get_cache_folder(action_size: int) -> pathlib.Path:
    """Path to the final cache files."""
    return _get_root_cache_folder() / 'offline_simulation' / str(action_size)


def get_partial_cache_folder(action_size: int) -> pathlib.Path:
    """Path to the partial cache files."""
    return _get_root_cache_folder() / 'partial' / str(action_size)


class SimulationCache():
    """Cache of simulation statuses for a subset of actions and tasks."""

    def __init__(self, cache_dir: Union[str, pathlib.Path]):
        cache_dir_path = pathlib.Path(cache_dir)
        if not cache_dir_path.exists():
            raise ValueError(f'Cache folder doesn\'t exists: {cache_dir}')

        cache = joblib.load(cache_dir_path / CACHE_FILE_NAME)
        self._action_array = cache['actions']
        self._statuses_per_task = cache['statuses_per_task']

    def __len__(self) -> int:
        return len(self._action_array)

    @property
    def action_array(self) -> np.ndarray:
        """Return an array of action with shape (cache_size, action_dim)."""
        return self._action_array

    def load_simulation_states(self, task_id: str) -> np.ndarray:
        """Returns an array of simulation statuses as ints."""
        return self._statuses_per_task[task_id]

    @property
    def task_ids(self) -> FrozenSet[str]:
        """Returns a set of tasks in the cache."""
        return frozenset(self._statuses_per_task)

    def get_sample(self,
                   task_ids: Optional[Sequence[str]] = None,
                   num_actions: Optional[int] = None):
        """Samples cache for a set of actions on series of tasks.

        Args:
            task_ids: List of tasks ids to sample form cache. Default None
                corresponds to all tasks in cache.
            num_actions: Number of actions to sample per task. Default None
                corresponds to all actions in cache.

        Returns:
            Dictionary ::

            {
                'task_ids': array of task ids,
                'actions': array of size (num_actions, action space),
                'simulation_statuses': array of size (task_ids, num_actions) of
                    simulation results from cache
            }

        Raises:
            ValueError: num_actions is greater than number of actions in cache.
        """
        if task_ids is None:
            task_ids = self.task_ids
        if num_actions is None:
            num_actions = len(self)
        if num_actions > len(self):
            raise ValueError(f'Requested more actions ({num_actions}) than'
                             ' exists in the cache ({len(self)}).')
        actions = self._action_array[:num_actions]
        simulations_states = np.array([
            self.load_simulation_states(task_id)[:num_actions]
            for task_id in task_ids
        ])
        assert actions.shape[0] == simulations_states.shape[1], (
            actions.shape, simulations_states.shape)
        assert actions.shape[0] == num_actions, (actions.shape, num_actions)
        return dict(task_ids=task_ids,
                    actions=actions,
                    simulation_statuses=simulations_states)
