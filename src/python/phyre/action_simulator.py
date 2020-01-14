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
"""Action simulator combines simulator interface with action mappers.

Simulator takes a list of tasks at initialization, builds agent-readable
representation for them, and provides interface to run simulation in a
specified action tier.
"""
from typing import Mapping, Optional, Sequence, Tuple, Union
import enum
import copy

import numpy as np

import phyre.action_mappers
import phyre.loader
import phyre.simulator
import phyre.interface.scene.ttypes as scene_if
import phyre.interface.task.ttypes as task_if
import phyre.simulation

MAX_RELATION = max(task_if.SpatialRelationship._VALUES_TO_NAMES) + 1
# First 4 objects are walls. Everything else are visible objects and encoded
# with colors.
MAX_OBJECT_TYPE = 5
MAX_GOAL = max(MAX_RELATION, MAX_OBJECT_TYPE)

ActionLike = Union[Sequence[float], np.ndarray]
MaybeImages = Optional[np.ndarray]
MaybeObjects = Optional[np.ndarray]


class SimulationStatus(enum.IntEnum):
    """Status that ActionSimulator returns given a task and an action."""

    NOT_SOLVED = -1
    INVALID_INPUT = 0
    SOLVED = 1
    UNSTABLY_SOLVED = 2
    STABLY_SOLVED = 3

    def is_solved(self) -> bool:
        """Whether the action solved the task."""
        return (self is SimulationStatus.SOLVED or
                self is SimulationStatus.STABLY_SOLVED or
                self is SimulationStatus.UNSTABLY_SOLVED)

    def is_stably_solved(self) -> bool:
        """Whether the action is stable solution for the task.

        This only applies if the simulation was called with `stable` flag.
        """
        return self is SimulationStatus.STABLY_SOLVED

    def is_not_solved(self) -> bool:
        """Whether the action is valid, but doesn't solve the task."""
        return self is SimulationStatus.NOT_SOLVED

    def is_invalid(self) -> bool:
        """whether the action is invalid for the task."""
        return self is SimulationStatus.INVALID_INPUT


class ActionSimulator():
    """Interface to query the simulator with actions within the tier."""

    def __init__(
            self,
            tasks: Union[Sequence[task_if.Task], Mapping[str, task_if.Task]],
            action_mapper,
            no_goals: bool = True):
        if isinstance(tasks, Mapping):
            self._tasks = tuple(tasks.values())
        else:
            self._tasks = tuple(tasks)
        if isinstance(action_mapper, str):
            self.tier = action_mapper
            action_mapper = phyre.action_mappers.get_action_mapper(
                action_mapper)
        else:
            self.tier = 'unknown'
        self._action_mapper = action_mapper
        self._initial_scenes, self._initial_featurized_objects, self._goals = _get_observations(
            self._tasks, self._action_mapper)
        if no_goals:
            self._goals = None
        self._serialized = tuple(
            phyre.simulator.serialize(task) for task in self._tasks)
        self._keep_spaces = self._action_mapper.KEEP_SPACE_AROUND_BODIES
        self._task_ids = tuple(task.taskId for task in self._tasks)

    def sample(self, valid_only=True, rng=None) -> ActionLike:
        """Sample a random (valid) action from the action space."""
        return self._action_mapper.sample(valid_only=valid_only, rng=rng)

    @property
    def action_space_dim(self) -> int:
        """Return dimension of the actions space."""
        return len(self._action_mapper.DIMENSION_TYPES)

    def build_discrete_action_space(self, max_actions,
                                    seed=1) -> Sequence[ActionLike]:
        """Build a mapping from the given number of action to the action space.

        Args:
            max_actions: int, maximum number of discrete actions.
            seed: int, random seed to generate the subspace.

        Returns:
            discrete_actions: tuple of actions of length max_actions.
        """
        rng = np.random.RandomState(seed=seed)
        return [self.sample(rng=rng) for _ in range(max_actions)]

    @property
    def initial_scenes(self) -> np.ndarray:
        """Represents intial scene for each task before agent input.

        uint8 array with shape (task, height, width).
        """
        return self._initial_scenes

    @property
    def initial_featurized_objects(self) -> np.ndarray:
        """Inital scene objects featurized for each task before agent input.
        
        List (length tasks) of FeaturizedObjects containing float arrays of size
        (number scene objects, OBJECT_FEATURE_SIZE).
        """
        return self._initial_featurized_objects

    @property
    def goals(self) -> Optional[np.ndarray]:
        """Represents goals for each task.

        uint8 array with shape (task, 3). Each goal is encoded with
        three numbers: (obj_type1, obj_type2, rel). All three are less than
        MAX_GOAL. To be more precise, obj_types are less than MAX_OBJECT_TYPE
        and rel is less than MAX_RELATION.
        """
        return self._goals

    @property
    def task_ids(self) -> Tuple[str, ...]:
        """Tuple of task ids in simulator.
        """
        return self._task_ids

    def _get_user_input(self, action):
        user_input, is_valid = self._action_mapper.action_to_user_input(action)
        return user_input, is_valid

    def _simulate_user_input(
            self, task_index, user_input, need_images, need_featurized_objects,
            stride) -> Tuple[SimulationStatus, MaybeImages, MaybeObjects]:
        serialzed_task = self._serialized[task_index]
        # FIXME: merge this into single call to simulator.
        if not self._action_mapper.OCCLUSIONS_ALLOWED:
            if phyre.simulator.check_for_occlusions(
                    serialzed_task,
                    user_input,
                    keep_space_around_bodies=self._keep_spaces):
                return SimulationStatus.INVALID_INPUT, None, None

        if not need_images and not need_featurized_objects:
            stride = 100000
        is_solved, had_occlusions, images, objects = phyre.simulator.magic_ponies(
            serialzed_task,
            user_input,
            stride=stride,
            keep_space_around_bodies=self._keep_spaces,
            need_images=need_images,
            need_featurized_objects=need_featurized_objects)
        if not need_images:
            images = None
        if not need_featurized_objects:
            objects = None

        # We checked for occulsions before simulation, so being here means we
        # have a bug.
        assert not had_occlusions or self._action_mapper.OCCLUSIONS_ALLOWED

        if is_solved:
            status = SimulationStatus.SOLVED
        else:
            status = SimulationStatus.NOT_SOLVED

        return status, images, objects

    def simulate_single(self,
                        task_index: int,
                        action: ActionLike,
                        need_images: bool = True,
                        stride: int = phyre.simulator.DEFAULT_STRIDE,
                        stable: bool = False
                       ) -> Tuple[SimulationStatus, MaybeImages]:
        """Deprecated in version 0.2.0 in favor of simulate_action.
        Runs simluation for the action.

        Args:
            task_index: index of the task.
            action: numpy array or list of self.action_space_dim floats in
                [0, 1].
            need_images: whether simulation images are needed.
            stride: int, defines the striding for the simulation images
                array. Higher striding will result in less images and less
                compute. Note, that this parameter doesn't affect simulation
                FPS. Ignored if need_images is False.
            stable: if True, will simulate a few actions in the neigborhood
                of the actions and return STABLY_SOLVED status iff all
                neigbour actions are either SOLVED or INVALID. Otherwise
                UNSTABLY_SOLVED is returned. SOLVED is never returned if
                stable is set.

        Returns:
             * If need_images is True, returns a pair (status, images).
                * If status is INVALID_INPUT images is None.
                * Otherwise images is an array contains intermediate observations.
             * If need_images is False: returns (status, None).
        """
        simulation = self.simulate_action(task_index,
                                          action,
                                          need_images=need_images,
                                          need_featurized_objects=False,
                                          stride=stride,
                                          stable=stable)
        return simulation.status, simulation.images

    def simulate_action(self,
                        task_index: int,
                        action: ActionLike,
                        *,
                        need_images: bool = True,
                        need_featurized_objects: bool = False,
                        stride: int = phyre.simulator.DEFAULT_STRIDE,
                        stable: bool = False) -> phyre.simulation.Simulation:
        """Runs simluation for the action.

        Args:
            task_index: index of the task.
            action: numpy array or list of self.action_space_dim floats in
                [0, 1].
            need_images: whether simulation images are needed.
            need_featurized_objects: whether simulation featurized_objects are needed.
            stride: int, defines the striding for the simulation images
                array. Higher striding will result in less images and less
                compute. Note, that this parameter doesn't affect simulation
                FPS. Ignored if need_images is False.
            stable: if True, will simulate a few actions in the neigborhood
                of the actions and return STABLY_SOLVED status iff all
                neigbour actions are either SOLVED or INVALID. Otherwise
                UNSTABLY_SOLVED is returned. SOLVED is never returned if
                stable is set.

        Returns:
             * phyre.simulation.Simulation object containing the result of
                the simulation. 
             * SimulationStatus, images, and featurized_objects are easily
                 accesible with simulation.simulation_status, simulation.images,
                 and simulation.featurized_objects.
        """
        user_input, is_valid = self._get_user_input(action)
        if not is_valid:
            return phyre.simulation.Simulation(
                status=SimulationStatus.INVALID_INPUT)

        main_status, images, objects = self._simulate_user_input(
            task_index, user_input, need_images, need_featurized_objects,
            stride)
        if not stable or not main_status.is_solved():
            return phyre.simulation.Simulation(status=main_status,
                                               images=images,
                                               featurized_objects=objects)

        for modified_user_input in _yield_user_input_neighborhood(user_input):
            status, _, _ = self._simulate_user_input(
                task_index,
                modified_user_input,
                need_images=False,
                need_featurized_objects=False,
                stride=stride)
            if status.is_not_solved():
                return phyre.simulation.Simulation(
                    status=SimulationStatus.UNSTABLY_SOLVED,
                    images=images,
                    featurized_objects=objects)
        return phyre.simulation.Simulation(
            status=SimulationStatus.STABLY_SOLVED,
            images=images,
            featurized_objects=objects)


def _yield_user_input_neighborhood(base_user_input):
    for dx in (-0.5, 0, 0.5):
        for dy in (-0.5, 0, 0.5):
            if dx == 0 and dy == 0:
                continue
            user_input = copy.deepcopy(base_user_input)
            for polygon in user_input.polygons:
                for v in polygon.vertices:
                    v.x += dx
                    v.y += dy
            for circle in user_input.balls:
                circle.position.x += dx
                circle.position.y += dy
            yield user_input


def _encode_goal(task):
    obj1_code = min(task.bodyId1, MAX_OBJECT_TYPE - 1)
    obj2_code = min(task.bodyId2, MAX_OBJECT_TYPE - 1)
    assert len(task.relationships) == 1, task
    rel = task.relationships[0]
    # FIXME(akhti): move this check to creator.
    assert 0 <= rel < MAX_RELATION, rel
    assert 0 <= obj1_code < MAX_OBJECT_TYPE, rel
    assert 0 <= obj2_code < MAX_OBJECT_TYPE, rel
    return obj1_code, rel, obj2_code


def _get_observations(
        tasks: Sequence[task_if.Task],
        action_mapper=None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Encode the initial scene and the goal as arrays.

    Args:
        task: list of thift tasks.

    Returns:
        A tuple (scenes, objects, goals).
        scenes: uint8 array with shape (task, height, width).
        featurized_objects: list (length tasks) of FeaturizedObjects 
            contianing float arrays of size
            (number scene objects, OBJECT_FEATURE_SIZE).
        goals: uint8 array with shape (task, 3).
            Each goal is encoded with three numbers: (obj_type1,
                obj_type2, rel). All three are less than MAX_GOAL. To be more
                presize, obj_types are less than MAX_OBJECT_TYPE and rel is
                less than MAX_RELATION.
    """
    scenes = np.stack(
        [phyre.simulator.scene_to_raster(task.scene) for task in tasks])
    featurized_objects = [
        phyre.simulator.scene_to_featurized_objects(task.scene)
        for task in tasks
    ]
    goals = np.array([_encode_goal(task) for task in tasks], dtype=np.uint8)
    return (scenes, featurized_objects, goals)


def initialize_simulator(task_ids: Sequence[str],
                         action_tier: str) -> ActionSimulator:
    """Initialize ActionSimulator for given tasks and tier."""
    tasks = phyre.loader.load_compiled_task_list(task_ids)
    return ActionSimulator(tasks, action_tier)
