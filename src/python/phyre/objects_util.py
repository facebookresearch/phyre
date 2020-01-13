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
"""Tools to visualize the featurized representation of scenes."""
import numpy as np

import phyre.interface.scene.ttypes as scene_if
import phyre.interface.shared.ttypes as shared_if
import phyre.interface.shared.constants as shared_constants
import phyre.simulator
from phyre import creator
from phyre.creator import constants
from phyre.creator import shapes as shapes_lib
from phyre.creator.creator import Body


def featurized_objects_vector_to_scene(featurized_objects: np.ndarray
                                      ) -> scene_if.Scene:
    """Convert an array of featurized objects into a Scene.

        Args:
            featurized_objects: np.ndarray of size (num_objects, OBJECT_FEATURE_SIZE)
        
        Returns:
            A scene_if.Scene contianing each of the featurized objects.
    """
    task = creator.creator.TaskCreator()
    user_input = scene_if.UserInput(flattened_point_list=[],
                                    balls=[],
                                    polygons=[])
    for features in featurized_objects:
        object_properties = _object_features_to_values(features)
        if object_properties['user_input']:
            assert object_properties['shape_type'] == 'ball', (
                'User input objects must be balls')
            user_input.balls.append(
                scene_if.CircleWithPosition(
                    position=scene_if.Vector(x=object_properties['x'],
                                             y=object_properties['y']),
                    radius=object_properties['diameter'] / 2.0))
        else:
            builder = shapes_lib.get_builders()[object_properties['shape_type']]
            shapes, phantom_vertices = builder.build(
                diameter=object_properties['diameter'])

            body = Body(shapes, object_properties['dynamic'],
                        object_properties['shape_type'],
                        object_properties['diameter'], phantom_vertices)
            body.push(object_properties['x'], object_properties['y'])
            body.set_angle(object_properties['angle'])
            body.set_color(object_properties['color'])

            task.scene.bodies.append(body._thrift_body)
            task.body_list.append(body)
    scene = phyre.simulator.add_user_input_to_scene(task.scene,
                                                    user_input,
                                                    allow_occlusions=True)
    return scene


def featurized_objects_vector_to_raster(featurized_objects: np.ndarray
                                       ) -> np.ndarray:
    """Convert featurized objects array to int array height x width of color codes.

        Args:
            featurized_objects: np.ndarray of size (num_objects, OBJECT_FEATURE_SIZE)
        
        Returns:
            A np.ndarray of size (SCENE_HEIGHT x SCENE_HEIGHT) of color codes,
                consistent with Simulation.images returned by the simulator
    """
    return phyre.simulator.scene_to_raster(
        featurized_objects_vector_to_scene(featurized_objects))


def _object_features_to_values(features):
    featurized_objects = phyre.simulation.FeaturizedObjects(
        phyre.simulation.finalize_featurized_objects(
            features[None, None, ...],
            phyre.simulation.PositionShift.FROM_CENTER_OF_MASS))
    x = featurized_objects.xs.item()
    y = featurized_objects.ys.item()
    angle = featurized_objects.angles.item()
    diameter = featurized_objects.diameters.item()
    x *= constants.SCENE_WIDTH
    y *= constants.SCENE_HEIGHT
    angle *= 360.
    diameter *= constants.SCENE_WIDTH

    shape_type = featurized_objects.shapes[0].lower()
    color = featurized_objects.colors[0].lower()
    dynamic = constants.color_to_id(color) in constants.DYNAMIC_COLOR_IDS
    user_input = featurized_objects.num_user_inputs == 1
    return dict(x=x,
                y=y,
                angle=angle,
                diameter=diameter,
                dynamic=dynamic,
                user_input=user_input,
                color=color,
                shape_type=shape_type)
