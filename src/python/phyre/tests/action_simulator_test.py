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

import numpy as np

import phyre.action_mappers
import phyre.action_simulator
import phyre.creator
import phyre.loader

SimulationStatus = phyre.action_simulator.SimulationStatus


def _get_ball_properties(ball):
    x_min, x_max = ball[:, 0].min(), ball[:, 0].max()
    y_min, y_max = ball[:, 1].min(), ball[:, 1].max()
    return (x_max + x_min) // 2, (y_max + y_min) // 2, (y_max - y_min) // 2


@phyre.creator.define_task
def build_task_for_objects(C):

    left = C.add('static bar',
                 scale=0.3).set_center_x(50).set_center_y(30).set_angle(-10)
    right = C.add('dynamic bar', scale=0.2).set_center_x(70).set_center_y(200)

    # Always valid.
    C.update_task(body1=left,
                  body2=right,
                  relationships=[C.SpatialRelationship.TOUCHING])


class ActionSimulatorTest(unittest.TestCase):

    def setUp(self):
        self._task_id = 0
        self._task_id2 = 1
        self._tasks = list(
            phyre.loader.load_tasks_from_folder(
                task_id_list=['00204:000', '00208:000']).values())
        [self._task_object_test] = build_task_for_objects('test_objects')

    def test_single_ball_tier(self):
        action_simulator = phyre.action_simulator.ActionSimulator(
            self._tasks, phyre.action_mappers.SingleBallActionMapper())
        action_simulator.sample()
        self.assertEqual(
            action_simulator.simulate_action(self._task_id, [0, 0, 0]).status,
            SimulationStatus.INVALID_INPUT)
        self.assertEqual(
            action_simulator.simulate_action(self._task_id,
                                             [0.1, 0.2, 0.1]).status,
            SimulationStatus.INVALID_INPUT)
        self.assertEqual(
            action_simulator.simulate_action(self._task_id,
                                             [0.5, 0.5, 0.1]).status,
            SimulationStatus.NOT_SOLVED)

    def test_simulate_single(self):
        action_simulator = phyre.action_simulator.ActionSimulator(
            self._tasks, phyre.action_mappers.SingleBallActionMapper())
        action = [0.5, 0.5, 0.1]
        simulation = action_simulator.simulate_action(self._task_id,
                                                      action,
                                                      need_images=True)
        status, images = action_simulator.simulate_single(self._task_id,
                                                          action,
                                                          need_images=True)
        self.assertEqual(status, simulation.status)
        np.testing.assert_equal(images, simulation.images)

    def test_single_ball_tier_discrete(self):
        action_simulator = phyre.action_simulator.ActionSimulator(
            self._tasks, phyre.action_mappers.SingleBallActionMapper())
        discrete = action_simulator.build_discrete_action_space(10000)
        self.assertEqual(len(discrete), 10000)
        action_simulator.simulate_action(self._task_id, discrete[0])

    def test_two_balls_tier(self):
        action_simulator = phyre.action_simulator.ActionSimulator(
            self._tasks, phyre.action_mappers.TwoBallsActionMapper())
        action_simulator.sample()
        self.assertEqual(
            action_simulator.simulate_action(
                self._task_id, [0.1, 0.2, 0.1, 0.5, 0.5, 0.1]).status,
            phyre.SimulationStatus.INVALID_INPUT)
        self.assertEqual(
            action_simulator.simulate_action(
                self._task_id, [0.5, 0.5, 0.1, 0.5, 0.5, 0.1]).status,
            phyre.SimulationStatus.INVALID_INPUT)
        self.assertEqual(
            action_simulator.simulate_action(
                self._task_id, [0.6, 0.5, 0.1, 0.5, 0.5, 0.1]).status,
            phyre.SimulationStatus.NOT_SOLVED)

    def test_ramp_tier(self):
        action_simulator = phyre.action_simulator.ActionSimulator(
            self._tasks, phyre.action_mappers.RampActionMapper())
        action_simulator.sample()
        # x, y, width, left_height, right_height, angle
        # Outside of the scene (go on the left).
        self.assertEqual(
            action_simulator.simulate_action(
                self._task_id, [0.01, 0.01, 0.5, 0.5, 0.5, 0.]).status,
            phyre.SimulationStatus.INVALID_INPUT)
        # Occludes (rotated by 90 degrees).
        self.assertEqual(
            action_simulator.simulate_action(
                self._task_id, [0.01, 0.01, 0.5, 0.5, 0.5, 0.25]).status,
            phyre.SimulationStatus.INVALID_INPUT)
        # In the middle of the scene.
        self.assertEqual(
            action_simulator.simulate_action(
                self._task_id, [0.5, 0.5, 0.01, 0.3, 0.3, 0.0]).status,
            phyre.SimulationStatus.NOT_SOLVED)

    def test_initial_scene_objects(self):
        builders = phyre.creator.shapes.get_builders()
        action_simulator = phyre.action_simulator.ActionSimulator(
            [self._task_object_test], 'ball')
        ideal_vector = np.array([[
            50 / 256., 30 / 256., 350. / 360.,
            builders['bar'].diameter(0.3) / 256., 0, 1, 0, 0, 0, 0, 0, 1, 0, 0
        ],
                                 [
                                     70 / 256., 200 / 256., 0.0,
                                     builders['bar'].diameter(0.2) / 256., 0, 1,
                                     0, 0, 0, 0, 1, 0, 0, 0
                                 ]])
        self.assertTrue(
            np.allclose(action_simulator.initial_featurized_objects[0].features,
                        ideal_vector,
                        atol=1e-4))
        action_simulator = phyre.action_simulator.ActionSimulator(
            [self._task_object_test], 'two_balls')
        self.assertTrue(
            np.allclose(action_simulator.initial_featurized_objects[0].features,
                        ideal_vector,
                        atol=1e-4))


if __name__ == '__main__':
    unittest.main()
