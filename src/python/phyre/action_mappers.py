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
"""Defines action mappers, i.e., mappings from a unit box to UserInput.

The action mappers are subclases of ActionMapper. They define the dimension
of the action space and the mapping from the action space to objects. They
provide interface to check whether the action is valid, e.g., that
corresponding objects are not "on top" of the scene bodies, and to run a
simulation.

All action spaces are continious, but the resulting UserInput objects are
snapped to integer grid.
"""

from typing import ClassVar, Dict, FrozenSet, Optional, Sequence, Tuple, Union
import abc
import enum

import numpy as np

import phyre.creator
import phyre.interface.scene.ttypes as scene_if

GeneralizedAction = Union[np.ndarray, Sequence[float]]

SCENE_HEIGHT = phyre.creator.SCENE_HEIGHT
SCENE_WIDTH = phyre.creator.SCENE_WIDTH
EMPTY_USER_INPUT = scene_if.UserInput(flattened_point_list=[],
                                      balls=[],
                                      polygons=[])


def get_action_mapper(name: str) -> 'ActionMapper':
    """Get action mapper instance by name."""
    return ACTION_MAPPERS[name]()


class DimensionType(enum.IntEnum):
    """Type of values in a component of an action."""
    POSITION = 0
    SIZE = 1
    ANGLE = 2


class ActionMapper():
    """Base class for action tier."""

    # Whether user inputs that occlude scene bodies are considered valid.
    # Derived class must redefine this.
    OCCLUSIONS_ALLOWED: ClassVar[bool]
    # Whether to require some space between user input and scene bodies.
    KEEP_SPACE_AROUND_BODIES: ClassVar[bool] = True
    # A list of types for each component of an action.
    DIMENSION_TYPES: ClassVar[Tuple[DimensionType, ...]]

    def __init__(self):
        if self.OCCLUSIONS_ALLOWED is None:
            raise RuntimeError(
                'Derived ActionMapper must defined OCCLUSIONS_ALLOWED')
        if self.DIMENSION_TYPES is None:
            raise RuntimeError(
                'Derived ActionMapper must defined DIMENSION_TYPES')
        self._initialize()

    def _initialize(self):
        pass

    def sample(self,
               valid_only: bool = True,
               rng: Optional[np.random.RandomState] = None) -> np.ndarray:
        if rng is None:
            rng = np.random.RandomState()
        while True:
            action = rng.uniform(size=len(self.DIMENSION_TYPES))
            if not valid_only:
                return action
            _, is_valid = self.action_to_user_input(action)
            if is_valid:
                return action

    @abc.abstractmethod
    def action_to_user_input(self, action: GeneralizedAction
                            ) -> Tuple[scene_if.UserInput, bool]:
        """Converts actions to points and is_valid flags.

        Args:
            action: A list or an array representing a single action

        Returns:
            A pair (user_input, is_valid).
                * user_input: scene_if.User that corresponds to the action.
                * is_valid: a boolean flag indicating whether the action is in
                  valid range, i.e., a ball is withing the scene.

        Note that if the action is not valid, the function should return empty
        point_list
        """


def _is_inside_scene(user_input: scene_if.UserInput) -> bool:

    def are_points_inside(points: np.ndarray) -> bool:
        if points.shape[0] == 0:
            return True
        valid_mask = ((0 <= points[:, 0]) & (points[:, 0] < SCENE_WIDTH) &
                      (0 <= points[:, 1]) & (points[:, 1] < SCENE_HEIGHT))

        return valid_mask.all()

    if not are_points_inside(np.array(user_input.flattened_point_list)):
        return False

    polygon_points = []
    for polygon in user_input.polygons:
        for point in polygon.vertices:
            polygon_points.append((point.x, point.y))

    if not are_points_inside(np.array(polygon_points)):
        return False

    for ball in user_input.balls:
        if not ball.radius <= ball.position.x <= SCENE_WIDTH - ball.radius:
            return False
        if not ball.radius <= ball.position.y <= SCENE_HEIGHT - ball.radius:
            return False

    return True


def _scale(x, low, high):
    return x * (high - low) + low


class BallScaler(object):

    MIN_RADIUS = 2
    MAX_RADIUS = max(SCENE_WIDTH, SCENE_HEIGHT) // 8
    assert MIN_RADIUS < MAX_RADIUS

    @classmethod
    def scale(cls, x, y, radius):
        x = _scale(x, 0, SCENE_WIDTH - 1)
        y = _scale(y, 0, SCENE_HEIGHT - 1)
        radius = _scale(radius, cls.MIN_RADIUS, cls.MAX_RADIUS)
        return x, y, radius

    @classmethod
    def add_to_user_input(cls, action, user_input):
        x, y, radius = cls.scale(*action)
        user_input.balls.append(
            scene_if.CircleWithPosition(position=scene_if.Vector(x=x, y=y),
                                        radius=radius))


class RampScaler(object):

    MIN_SIDE = 4
    MAX_SIDE = max(SCENE_WIDTH, SCENE_HEIGHT) // 4

    @classmethod
    def scale(cls, x, y, width, left_height, right_height, angle):
        x = _scale(x, 0, SCENE_WIDTH - 1)
        y = _scale(y, 0, SCENE_HEIGHT - 1)

        width = _scale(width, cls.MIN_SIDE, cls.MAX_SIDE)
        # Left height may be 0, but not left height. However, to make it easier
        # to make a square we do clipping instead of scaling to enforce
        # right_height > cls.MIN_SIDE.
        left_height = _scale(left_height, 0, cls.MAX_SIDE)
        right_height = max(_scale(right_height, 0, cls.MAX_SIDE), cls.MIN_SIDE)
        angle = _scale(angle, 0, np.pi * 2)
        return x, y, width, left_height, right_height, angle

    @classmethod
    def get_vertices(cls, *action):
        x, y, width, left_height, right_height, angle = cls.scale(*action)
        if left_height < 1:
            points = [[0, 0], [0, right_height], [-width, 0]]
        else:
            points = [[0, 0], [0, right_height], [-width, left_height],
                      [-width, 0]]
        cos, sin = np.cos(angle), np.sin(angle)
        rotation_matrix = np.array([[cos, -sin], [sin, cos]])
        points = np.array(points) @ rotation_matrix + np.array([x, y])
        return points

    @classmethod
    def add_to_user_input(cls, action, user_input):
        vertices = cls.get_vertices(*action)
        vertices = [scene_if.Vector(x=x, y=y) for x, y in vertices.tolist()]
        user_input.polygons.append(
            scene_if.AbsoluteConvexPolygon(vertices=vertices))


class SingleBallActionMapper(ActionMapper):

    OCCLUSIONS_ALLOWED = False
    KEEP_SPACE_AROUND_BODIES = False
    DIMENSION_TYPES = (DimensionType.POSITION, DimensionType.POSITION,
                       DimensionType.SIZE)

    def action_to_user_input(self, action):
        if not all(0 <= x <= 1 for x in action):
            return EMPTY_USER_INPUT, False
        user_input = scene_if.UserInput(flattened_point_list=[],
                                        balls=[],
                                        polygons=[])
        BallScaler.add_to_user_input(action, user_input)
        if not _is_inside_scene(user_input):
            return EMPTY_USER_INPUT, False
        _quantize_user_input_in_place(user_input)
        return user_input, True


class TwoBallsActionMapper(ActionMapper):
    """Two ball action space.

    Ball paramterized by the centers and radiuses. The order is the following:
        x1, y1, r1, x2, y2, r2
    """

    OCCLUSIONS_ALLOWED = False
    KEEP_SPACE_AROUND_BODIES = False
    DIMENSION_TYPES = (DimensionType.POSITION, DimensionType.POSITION,
                       DimensionType.SIZE, DimensionType.POSITION,
                       DimensionType.POSITION, DimensionType.SIZE)

    def action_to_user_input(self, action: GeneralizedAction
                            ) -> Tuple[scene_if.UserInput, bool]:
        if not all(0 <= x <= 1 for x in action):
            return EMPTY_USER_INPUT, False

        user_input = scene_if.UserInput(flattened_point_list=[],
                                        balls=[],
                                        polygons=[])
        BallScaler.add_to_user_input(action[:3], user_input)
        BallScaler.add_to_user_input(action[3:], user_input)
        if not _is_inside_scene(user_input):
            return EMPTY_USER_INPUT, False
        ball1, ball2 = user_input.balls
        x1, x2 = ball1.position.x, ball2.position.x
        y1, y2 = ball1.position.y, ball2.position.y
        dist = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        if dist < ball1.radius + ball2.radius + 1:
            return EMPTY_USER_INPUT, False
        if not _is_inside_scene(user_input):
            return EMPTY_USER_INPUT, False
        _quantize_user_input_in_place(user_input)
        return user_input, True


def _pdist(p1, p2):
    return ((p1 - p2)**2).sum()**.5


def _compute_relations(p: np.ndarray, p1: np.ndarray,
                       p2: np.ndarray) -> Tuple[float, bool]:
    """Compute relation between vector p1->p2 and point p.

    Returns distance from p1->p2 to p and whether p between p1 and p2.
    """
    vector = p2 - p1
    vector_len = (vector * vector).sum()**.5
    proj_len = ((p - p1) * (p2 - p1)).sum() / vector_len
    between = 0 <= proj_len <= vector_len
    perp = p - p1 - vector * (proj_len / vector_len)
    return (perp * perp).sum()**.5, between


def _quantize_user_input_in_place(user_input: scene_if.UserInput) -> None:
    for polygon in user_input.polygons:
        for vertex in polygon.vertices:
            vertex.x = round(vertex.x)
            vertex.y = round(vertex.y)
    for circle in user_input.balls:
        circle.radius = round(circle.radius)
        circle.position.x = int(circle.position.x)
        circle.position.y = int(circle.position.y)


class RampActionMapper(ActionMapper):

    OCCLUSIONS_ALLOWED = False
    KEEP_SPACE_AROUND_BODIES = False
    DIMENSION_TYPES = (DimensionType.POSITION, DimensionType.POSITION,
                       DimensionType.SIZE, DimensionType.SIZE,
                       DimensionType.SIZE, DimensionType.ANGLE)

    def action_to_user_input(self, action: GeneralizedAction
                            ) -> Tuple[scene_if.UserInput, bool]:
        if not all(0 <= x <= 1 for x in action):
            return EMPTY_USER_INPUT, False
        user_input = scene_if.UserInput(flattened_point_list=[],
                                        balls=[],
                                        polygons=[])
        RampScaler.add_to_user_input(action, user_input)
        if not _is_inside_scene(user_input):
            return EMPTY_USER_INPUT, False
        _quantize_user_input_in_place(user_input)
        return user_input, True


ACTION_MAPPERS: Dict[str, ActionMapper] = dict(
    ball=SingleBallActionMapper,
    two_balls=TwoBallsActionMapper,
    ramp=RampActionMapper,
)

MAIN_ACITON_MAPPERS: FrozenSet[str] = frozenset({'ball', 'two_balls'})
