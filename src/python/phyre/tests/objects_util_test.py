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
import unittest
import unittest.mock
import numpy as np

import phyre.simulation
import phyre.objects_util
from phyre import creator
from phyre import simulator
from phyre.creator import constants


@creator.define_task
def build_task_for_objects(C):

    left = C.add('static bar',
                 scale=0.3).set_center_x(50).set_center_y(30).set_angle(-10)
    right = C.add('dynamic bar', scale=0.2).set_center_x(70).set_center_y(200)

    # Always valid.
    C.update_task(body1=left,
                  body2=right,
                  relationships=[C.SpatialRelationship.TOUCHING])


@creator.define_task
def build_complicated_task_for_objects(C):

    left = C.add('static bar',
                 scale=0.3).set_center_x(50).set_center_y(30).set_angle(-10)
    right = C.add('dynamic bar', scale=0.2).set_center_x(70).set_center_y(200)
    C.add('dynamic ball', scale=0.2).set_center_x(100).set_center_y(100)
    C.add('static jar',
          scale=0.2).set_center_x(200).set_center_y(100).set_angle(20)
    C.add('dynamic standingsticks',
          scale=0.25).set_center_x(150).set_center_y(150).set_angle(90)
    # Always valid.
    C.update_task(body1=left,
                  body2=right,
                  relationships=[C.SpatialRelationship.TOUCHING])


class ObjectUtilTest(unittest.TestCase):

    def setUp(self):
        # Build tasks for test scene -> featurized objects -> scene
        [self._task_object_test] = build_task_for_objects('test_objects')
        [self._task_complicated_object_test
        ] = build_complicated_task_for_objects('test_objects_complicated')
        self._ball_user_input_small = simulator.build_user_input(
            balls=[100, 100, 5])
        self._ball_user_input_big = simulator.build_user_input(
            balls=[200, 200, 10])

        # Build vectorized objects for unit tests
        self.x_s = np.array([[0.1, 0.3, 0.2, 0.4]])
        self.y_s = np.array([[0.05, 0.15, 0.25, 0.65]])
        self.thetas = np.array([[0.0, 0.1, 0.2, 0.3]])
        self.diameters = np.array([[0.15, 0.1, 0.25, 0.23]])
        self.colors_str = np.array(['black', 'blue', 'red', 'purple'])
        colors_one_hot = np.array([[0, 0, 0, 0, 0, 1], [0, 0, 1, 0, 0, 0],
                                   [1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0,
                                                        0]]).astype(float)
        self.dynamic = np.array([False, True, False, False])
        self.user_input = np.array([False, False, True, False])
        self.shapes_str = np.array(['jar', 'standingsticks', 'ball', 'bar'])
        shapes_one_hot = np.array([[0, 0, 1, 0], [0, 0, 0, 1], [1, 0, 0, 0],
                                   [0, 1, 0, 0]]).astype(float)
        self.features = np.concatenate(
            (self.x_s.T, self.y_s.T, self.thetas.T, self.diameters.T,
             shapes_one_hot, colors_one_hot),
            axis=1)
        phyre.simulation.DIAMETER_CENTERS = {}

    def test_object_features_to_values(self):
        with unittest.mock.patch.object(phyre.creator.shapes.Jar,
                                        'center_of_mass',
                                        return_value=(0.0, 0.0)) as mock_method:
            for i in range(len(self.features)):
                object_parameters = phyre.objects_util._object_features_to_values(
                    self.features[i])
                self.assertTrue(object_parameters['x'] == self.x_s[0, i] *
                                constants.SCENE_WIDTH)
                self.assertTrue(object_parameters['y'] == self.y_s[0, i] *
                                constants.SCENE_HEIGHT)
                self.assertTrue(
                    object_parameters['angle'] == self.thetas[0, i] * 360.)
                self.assertTrue(
                    object_parameters['diameter'] == self.diameters[0, i] *
                    constants.SCENE_WIDTH)
                self.assertTrue(object_parameters['dynamic'] == self.dynamic[i])
                self.assertTrue(
                    object_parameters['user_input'] == self.user_input[i])
                self.assertTrue(
                    object_parameters['color'] == self.colors_str[i])
                self.assertTrue(
                    object_parameters['shape_type'] == self.shapes_str[i])

    def test_object_vec_to_scene(self):
        steps = 50
        _, _, images, objects = simulator.magic_ponies(
            self._task_object_test,
            self._ball_user_input_small,
            steps=steps,
            stride=1,
            need_images=True,
            need_featurized_objects=True)
        objects = phyre.simulation.Simulation(
            featurized_objects=objects).featurized_objects.features
        for i in range(len(images)):
            image = images[i]
            object_vec = objects[i]
            self.assertTrue(
                np.allclose(
                    object_vec,
                    simulator.scene_to_featurized_objects(
                        phyre.objects_util.featurized_objects_vector_to_scene(
                            object_vec)).features,
                    atol=1e-4))
            self.assertTrue((image == simulator.scene_to_raster(
                phyre.objects_util.featurized_objects_vector_to_scene(
                    object_vec))).all())

    def test_complicated_object_vec_to_scene(self):
        steps = 50
        _, _, images, objects = simulator.magic_ponies(
            self._task_complicated_object_test,
            self._ball_user_input_big,
            steps=steps,
            stride=1,
            need_images=True,
            need_featurized_objects=True)
        objects = phyre.simulation.Simulation(
            featurized_objects=objects).featurized_objects.features
        for i in range(len(images)):
            image = images[i]
            original_object_vec = objects[i]
            object_vec = original_object_vec
            for j in range(5):
                # Test no loss of information in conversion
                self.assertTrue(
                    np.allclose(original_object_vec,
                                simulator.scene_to_featurized_objects(
                                    phyre.objects_util.
                                    featurized_objects_vector_to_scene(
                                        object_vec)).features,
                                atol=1e-4))
                object_vec = simulator.scene_to_featurized_objects(
                    phyre.objects_util.featurized_objects_vector_to_scene(
                        object_vec)).features[0]
            self.assertTrue((image == simulator.scene_to_raster(
                phyre.objects_util.featurized_objects_vector_to_scene(
                    object_vec))).all())

    def test_object_vec_to_scene_simple(self):
        _, _, images, featurized_objects = simulator.magic_ponies(
            self._task_complicated_object_test,
            self._ball_user_input_big,
            steps=1,
            stride=1,
            need_images=True,
            need_featurized_objects=True)
        objects = phyre.simulation.Simulation(
            featurized_objects=featurized_objects).featurized_objects.features
        image = images[0]
        object_vec = objects[0]
        self.assertTrue(
            (image == phyre.objects_util.featurized_objects_vector_to_raster(
                object_vec)).all())
        self.assertTrue(
            np.array_equal(
                object_vec,
                simulator.scene_to_featurized_objects(
                    phyre.objects_util.featurized_objects_vector_to_scene(
                        object_vec)).features[0]))


if __name__ == '__main__':
    unittest.main()
