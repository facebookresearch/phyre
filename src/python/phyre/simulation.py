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
"""A thin wrapper around the simulation result."""
from typing import List, Optional
import enum
import math

import numpy as np

import phyre.creator.shapes
import phyre.interface.scene.ttypes as scene_if
import phyre.interface.shared.constants as shared_constants
import phyre.interface.shared.ttypes as shared_if
from phyre.creator import constants

DIAMETER_CENTERS = {}


class PositionShift(enum.Enum):
    TO_CENTER_OF_MASS = 1
    FROM_CENTER_OF_MASS = 2


def _get_jar_offset(featurized_object):
    diameter = featurized_object[
        FeaturizedObjects._DIAMETER_INDEX] * constants.SCENE_WIDTH
    if diameter not in DIAMETER_CENTERS:
        center_x, center_y = phyre.creator.shapes.Jar.center_of_mass(**dict(
            diameter=diameter))
        DIAMETER_CENTERS[diameter] = center_y
    return DIAMETER_CENTERS[diameter]


def finalize_featurized_objects(featurized_objects: np.ndarray,
                                shift_direction=PositionShift.TO_CENTER_OF_MASS
                               ) -> np.ndarray:
    assert isinstance(shift_direction, PositionShift), shift_direction
    """Processes featurized objects returned by simulator.
    
    Args:
        shift_direction: Either PositionShift.TO_CENTER_OF_MASS or
            PositionShift.FROM_CENTER_OF_MASS representing which direction
            to shift position of jar objects. Default is
            PositionShift.TO_CENTER_OF_MASS representing the processing done
            on the array returned by the simulator.

    The features are by index:
        - 0: x in pixels of center of mass divided by SCENE_WIDTH
        - 1: y in pixels of center of mass divided by SCENE_HEIGHT
        - 2: angle of the object between 0 and 2pi divided by 2pi
        - 3: diameter in pixels of object divided by SCENE_WIDTH
        - 4-8: One hot encoding of the object shape, according to order:
            ball, bar, jar, standing sticks
        - 8-14: One hot encoding of object color, according to order:
            red, green, blue, purple, gray, black
    """
    featurized_objects = np.copy(featurized_objects)
    direction = 1.0 if shift_direction == PositionShift.TO_CENTER_OF_MASS else -1.0
    is_jar = featurized_objects[:, :, FeaturizedObjects._SHAPE_START_INDEX +
                                scene_if.ShapeType.JAR - 1] == 1
    if featurized_objects[is_jar].shape[0] > 0:
        offsets = np.apply_along_axis(_get_jar_offset, 1,
                                      featurized_objects[0, :, :][is_jar[0, :]])
        offsets_expanded = np.concatenate([offsets] *
                                          featurized_objects.shape[0],
                                          axis=0)
        angles = featurized_objects[is_jar][:, FeaturizedObjects.
                                            _ANGLE_INDEX] * 2 * math.pi
        directional_offsets = np.stack(
            [
                -1 * offsets_expanded * np.sin(angles),
                offsets_expanded * np.cos(angles)
            ],
            axis=-1) / constants.SCENE_WIDTH * direction
        featurized_objects[is_jar, :FeaturizedObjects.
                           _ANGLE_INDEX] += directional_offsets
    return featurized_objects


class Simulation(object):
    """Interface for the result of an ActionSimulator simulation.

    Featurized objects and images are returned in the same order, such that
    simulation.images[i] is the pixel representation of 
    simulation.featurized_objects[i].
    
    If self.status is INVALID_INPUT self.images,
    and self.featurized_objects are both None.

    :ivar images: Initial pixel representation of intermeidate obervations.
    :ivar featurized_objects: Object representation of intermediate observations.
        FeaturizedObjects containing information about object features and state.
    :ivar status: SimulationStatus of simulation.
    """

    def __init__(self,
                 *,
                 status=None,
                 images: Optional[np.ndarray] = None,
                 featurized_objects: Optional[np.ndarray] = None):
        self.status = status
        self.images = images
        if featurized_objects is not None:
            self.featurized_objects = FeaturizedObjects(featurized_objects)
        else:
            self.featurized_objects = None


class FeaturizedObjects():
    """Featurization of objects in a series of scene, such as from a simulation.
    Returned by either ActionSimulator.intial_featurized_objects, or 
    ActionSimulator.simulate_action if `need_featurized_objects=True`.
    *Note*, for object order, user input objects (if any) are always
    last.
    :ivar features: Featurs of objects of observations for a set (or one) timesteps.
        TxNx14 np.array where T is the number of timestes, N is the number
        of objects in the scene and 14 is the feature vector size.
        The features are by index:
            - 0: x in pixels of center of mass divided by SCENE_WIDTH
            - 1: y in pixels of center of mass divided by SCENE_HEIGHT
            - 2: angle of the object between 0 and 2pi divided by 2pi
            - 3: diameter in pixels of object divided by SCENE_WIDTH
            - 4-8: One hot encoding of the object shape, according to order:
                ball, bar, jar, standing sticks
            - 8-14: One hot encoding of object color, according to order:
                red, green, blue, purple, gray, black
    :ivar shapes: List(str) of length number of objects of the
        shape types of the objects in order. Values are members of scene_if.ShapeType
    :ivar shapes_one_hot: np.array of size (T, N, 4) corresponding to one hot
        encoding of shapes. Features 4-8
        shape types of the objects in order. Values are members of scene_if.ShapeType
    :ivar colors: List(str) of length number of objects of the colors of the
        objects in order. Values are members of shared_if.Colors
    :ivar shapes_one_hot: np.array of size (T, N, 6) corresponding to one hot
        encoding of colors. Features 8-14
    :ivar diameters: np.ndarray of dtype=float of shape(num objects, ) containing
        the object diameter in pixels divided by SCENE_WIDTH in order
    :ivar states: np.array of size (T, N, 3) where T is the number of timesteps,
        N is the number of objects and the remaining 3 features are:
            - 0: x in pixels of center of mass divided by SCENE_WIDTH
            - 1: y in pixels of center of mass divided by SCENE_HEIGHT
            - 2: angle of the object in [0, 2pi]  divided by 2pi
    :ivar num_user_inputs: (int) Number of user input objects in the simulation
    :ivar num_objects: (int) Number of objects in the simulation_states
    :ivar num_scene_obejcts: (int) Number of scene objects in the simulation.
    """
    _NUM_FEATURES = 14

    _X_INDEX = 0
    _Y_INDEX = 1
    _ANGLE_INDEX = 2
    _DIAMETER_INDEX = 3
    _SHAPE_START_INDEX = 4
    _SHAPE_END_INDEX = 8
    _COLOR_START_INDEX = _SHAPE_END_INDEX
    _COLOR_END_INDEX = _NUM_FEATURES

    _STATE_START_INDEX = 0
    _STATE_END_INDEX = _DIAMETER_INDEX

    def __init__(self, featurized_objects: np.ndarray):
        assert len(featurized_objects.shape) == 3, (
            f'Input must be 3 dimensional (TxNx{self._NUM_FEATURES}) np.array,'
            f'dimensions found {len(featurized_objects.shape)}')
        assert featurized_objects.shape[-1] == self._NUM_FEATURES, (
            f'Input must be of shape TxNx{self._NUM_FEATURES}'
            f', got {featurized_objects.shape}')
        self.features = featurized_objects

        self.xs = featurized_objects[:, :, self._X_INDEX]
        self.ys = featurized_objects[:, :, self._Y_INDEX]
        self.angles = featurized_objects[:, :, self._ANGLE_INDEX]
        self.diameters = featurized_objects[0, :, self._DIAMETER_INDEX]
        self.shapes_one_hot = featurized_objects[0, :, self._SHAPE_START_INDEX:
                                                 self._SHAPE_END_INDEX]
        self.colors_one_hot = featurized_objects[0, :, self._COLOR_START_INDEX:
                                                 self._COLOR_END_INDEX]

        self.states = featurized_objects[:, :, self._STATE_START_INDEX:self.
                                         _STATE_END_INDEX]

        self._shapes = None
        self._colors = None
        self._num_user_inputs = None

    @property
    def colors(self) -> List[str]:
        if self._colors is None:
            color_indicies = np.argmax(self.colors_one_hot, axis=1) + 1
            self._colors = [
                shared_if.Color._VALUES_TO_NAMES[each]
                for each in color_indicies
            ]
        return self._colors

    @property
    def shapes(self) -> List[str]:
        if self._shapes is None:
            shape_indicies = np.argmax(self.shapes_one_hot, axis=1) + 1
            self._shapes = [
                scene_if.ShapeType._VALUES_TO_NAMES[each]
                for each in shape_indicies
            ]
        return self._shapes

    @property
    def num_objects(self) -> int:
        """Number of objects in the scene."""
        return self.features.shape[1]

    @property
    def num_user_inputs(self) -> List[str]:
        if self._num_user_inputs is None:
            self._num_user_inputs = sum(
                1 for each in self.colors
                if each == shared_if.Color._VALUES_TO_NAMES[
                    shared_constants.USER_BODY_COLOR])
        return self._num_user_inputs

    @property
    def num_scene_objects(self) -> int:
        """Number of scene objects in the scene."""
        return self.num_objects - self.num_user_inputs
