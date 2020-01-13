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

import copy
import math
import unittest
import unittest.mock

import numpy as np

import phyre.action_simulator
import phyre.simulation
from phyre.interface.scene import ttypes as scene_if
from phyre.interface.shared import ttypes as shared_if


class SimulationTest(unittest.TestCase):

    def setUp(self):
        phyre.simulation.DIAMETER_CENTERS = {}
        self.x_s = np.array([0.1, 0.3, 0.2, 0.4])
        self.y_s = np.array([0.05, 0.15, 0.25, 0.65])
        self.thetas = np.array([0.0, 0.1, 0.2, 0.3])
        self.diameters = np.array([0.15, 0.1, 0.25, 0.23])
        colors = np.array([
            shared_if.Color.BLACK, shared_if.Color.BLUE, shared_if.Color.RED,
            shared_if.Color.PURPLE
        ])
        self.colors_str = np.array(['BLACK', 'BLUE', 'RED', 'PURPLE'])
        self.colors_one_hot = np.array([[0, 0, 0, 0, 0, 1], [0, 0, 1, 0, 0, 0],
                                        [1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0,
                                                             0]]).astype(float)
        body_shapes = np.array([
            scene_if.ShapeType.JAR, scene_if.ShapeType.STANDINGSTICKS,
            scene_if.ShapeType.BALL, scene_if.ShapeType.BAR
        ])
        self.shapes_str = np.array(['JAR', 'STANDINGSTICKS', 'BALL', 'BAR'])
        self.shapes_one_hot = np.array([[0, 0, 1, 0], [0, 0, 0,
                                                       1], [1, 0, 0, 0],
                                        [0, 1, 0, 0]]).astype(float)
        vectors = []
        for timestep in range(10):
            x_offset = timestep * 0.01
            y_offset = timestep * 0.05
            x_pos = self.x_s + x_offset
            y_pos = self.y_s + y_offset
            objects = []

            for i in range(len(x_pos)):
                o = [x_pos[i], y_pos[i], self.thetas[i], self.diameters[i]]
                o.extend(self.shapes_one_hot[i].tolist())
                o.extend(self.colors_one_hot[i].tolist())
                objects.append(o)

            vectors.append(np.array(objects))
        self.vectors = np.array(vectors)

    def test_featurized_objects_states(self):
        featurized_objects = phyre.simulation.Simulation(
            featurized_objects=self.vectors).featurized_objects
        self.assertTrue(
            np.array_equal(featurized_objects.diameters, self.diameters))
        self.assertTrue(
            np.array_equal(featurized_objects.colors, self.colors_str))
        self.assertTrue(
            np.array_equal(featurized_objects.shapes, self.shapes_str))
        self.assertTrue(
            np.array_equal(featurized_objects.features, self.vectors))
        self.assertTrue(
            np.array_equal(featurized_objects.states, self.vectors[:, :, :3]))
        self.assertTrue(
            np.array_equal(featurized_objects.xs, self.vectors[:, :, 0]))
        self.assertTrue(
            np.array_equal(featurized_objects.ys, self.vectors[:, :, 1]))
        self.assertTrue(
            np.array_equal(featurized_objects.angles, self.vectors[:, :, 2]))
        self.assertTrue(featurized_objects.num_objects, 4)
        self.assertTrue(featurized_objects.num_scene_objects, 3)
        self.assertTrue(featurized_objects.num_user_inputs, 1)

    def test_invalid_featurized_objects(self):
        two_dimension_input = np.arange(28).reshape(2, 14)
        self.assertRaises(AssertionError, phyre.simulation.FeaturizedObjects,
                          two_dimension_input)

        wrong_number_features = np.arange(60).reshape(2, 2, 15)
        self.assertRaises(AssertionError, phyre.simulation.FeaturizedObjects,
                          wrong_number_features)

    def test_simulation(self):
        simualtion = phyre.simulation.Simulation(
            featurized_objects=self.vectors)
        for i in range(10):
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.features[i, :, 0],
                               self.x_s + i * 0.01))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.xs[i],
                               self.x_s + i * 0.01))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.features[i, :, 1],
                               self.y_s + i * 0.05))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.ys[i],
                               self.y_s + i * 0.05))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.features[i, :, 2],
                               self.thetas))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.angles[i],
                               self.thetas))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.features[i, :, 3],
                               self.diameters))
            self.assertTrue(
                np.array_equal(
                    simualtion.featurized_objects.features[i, :, 4:8],
                    self.shapes_one_hot))
            self.assertTrue(
                np.array_equal(simualtion.featurized_objects.features[i, :, 8:],
                               self.colors_one_hot))

    def test_no_objects(self):
        simulation = phyre.simulation.Simulation(
            status=phyre.action_simulator.SimulationStatus.SOLVED,
            images=self.vectors)
        self.assertTrue(simulation.featurized_objects is None)
        self.assertTrue(simulation.images is not None)
        self.assertEqual(simulation.status,
                         phyre.action_simulator.SimulationStatus.SOLVED)

    def test_jars_position_center_of_mass(self):

        def mock_center_of_mass(**kwargs):
            return (0, kwargs['diameter'])

        with unittest.mock.patch.object(
                phyre.creator.shapes.Jar,
                'center_of_mass',
                side_effect=mock_center_of_mass) as mock_method:
            jar_vectors = self.vectors[:, 0:2, :]
            # Make sure shape is jars
            jar_vectors[:, :, 6] = 1.
            jar_vectors[:, :, 7:8] = 0.
            jar_vectors[:, :, 4:6] = 0.

            # Set angle to 0
            jar_vectors[:, :, 2] = 0

            expected_vectors = copy.deepcopy(jar_vectors)
            simulation = phyre.simulation.Simulation(
                featurized_objects=phyre.simulation.finalize_featurized_objects(
                    jar_vectors))
            # Entire center of mass offset for y at angle 0
            expected_vectors[:, 0, 1] += 0.15
            expected_vectors[:, 1, 1] += 0.1
            np.testing.assert_allclose(simulation.featurized_objects.states,
                                       expected_vectors[:, :, :3])

            # Set angle to 90
            jar_vectors[:, :, 2] = 0.25
            expected_vectors = copy.deepcopy(jar_vectors)
            simulation = phyre.simulation.Simulation(
                featurized_objects=phyre.simulation.finalize_featurized_objects(
                    jar_vectors))
            # Entire center of mass offset for x at angle 90
            # jar rotated left, so negative offset
            expected_vectors[:, 0, 0] -= 0.15
            expected_vectors[:, 1, 0] -= 0.1
            np.testing.assert_allclose(simulation.featurized_objects.states,
                                       expected_vectors[:, :, :3])

            # Set angle to -120
            jar_vectors[:, :, 2] = -120. / 360.
            expected_vectors = copy.deepcopy(jar_vectors)
            simulation = phyre.simulation.Simulation(
                featurized_objects=phyre.simulation.finalize_featurized_objects(
                    jar_vectors))
            # Equal center of mass offset for x,y at angle 120, jar rotated
            # right, so postive for x, rotated > 90 so negative offset for y
            expected_vectors[:, 0, 0] += 0.15 * math.sqrt(3) / 2.  # sin 60
            expected_vectors[:, 0, 1] -= 0.15 * 1 / 2.  # cos 60

            expected_vectors[:, 1, 0] += 0.1 * math.sqrt(3) / 2.  # sin 60
            expected_vectors[:, 1, 1] -= 0.1 * 1 / 2.  # cos 60
            np.testing.assert_allclose(simulation.featurized_objects.states,
                                       expected_vectors[:, :, :3])


if __name__ == '__main__':
    unittest.main()
