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

import numpy as np
import unittest

import phyre


def _get_ball_properties(ball):
    x_min, x_max = ball[:, 0].min(), ball[:, 0].max()
    y_min, y_max = ball[:, 1].min(), ball[:, 1].max()
    return (x_max + x_min) // 2, (y_max + y_min) // 2, (y_max - y_min) // 2


class ClevrEnvTest(unittest.TestCase):
    pass
    # def setUp(self):
    #     self._task_id = '00000:000'
    #     manager = phyre.TaskManager(task_id_list=[self._task_id])
    #     assert manager.get_ids() == [self._task_id], manager.get_ids()
    #     self._manager = manager

    # def _run_env(self, env, action=(0, 0, 0)):
    #     scene, goal = env.reset().values()
    #     self.assertEqual(scene.shape, (phyre.SCENE_WIDTH, phyre.SCENE_HEIGHT))
    #     self.assertEqual(goal.shape, (3, ))
    #     end_observation, reward, done, info = env.step(action)
    #     end_scene, end_goal = end_observation.values()
    #     self.assertEqual(end_scene.shape,
    #                      (phyre.SCENE_WIDTH, phyre.SCENE_HEIGHT))
    #     np.testing.assert_array_equal(end_goal, goal)
    #     self.assertIn(reward, (-1., 1.))
    #     self.assertTrue(done)
    #     all_scenes = info['all_scenes']
    #     self.assertEqual(len(all_scenes.shape), 3)
    #     self.assertEqual(all_scenes.shape[1:],
    #                      (phyre.SCENE_WIDTH, phyre.SCENE_HEIGHT))

    # def test_continious_ball(self):
    #     env = phyre.env.ContiniousBallClevrEnv(
    #         self._manager, [self._task_id], min_radius=2, max_radius=5)
    #     center = phyre.SCENE_WIDTH // 2
    #     self.assertEqual((center, center, 2),
    #                      _get_ball_properties(
    #                          env.action_to_user_input((0.5, 0.5, 0.0))))
    #     self._run_env(env)

    # def test_discrete_ball(self):
    #     env = phyre.env.DiscreteBallClevrEnv(
    #         self._manager, [self._task_id],
    #         min_radius=2,
    #         max_radius=6,
    #         position_grid_step=32,
    #         radius_grid_step=3)
    #     self.assertEqual((16, 16, 2),
    #                      _get_ball_properties(
    #                          env.action_to_user_input((0, 0, 0))))
    #     self.assertEqual((16, 16, 5),
    #                      _get_ball_properties(
    #                          env.action_to_user_input((0, 0, 1))))
    #     self.assertEqual((48, 48, 2),
    #                      _get_ball_properties(
    #                          env.action_to_user_input((1, 1, 0))))
    #     self._run_env(env)

    # def test_continious_double_ball(self):
    #     env = phyre.env.ContiniousDoubleBallClevrEnd(
    #         self._manager, [self._task_id], min_radius=2, max_radius=5)
    #     self._run_env(env, action=(0, 0, 0, 1, 1, 1))

    # def test_discrete_ball_packed_observations(self):
    #     env = phyre.env.DiscreteBallClevrEnv(
    #         self._manager, [self._task_id],
    #         pack_observations=phyre.env.PackingType.BOX_HWC,
    #         min_radius=2,
    #         max_radius=6,
    #         position_grid_step=32,
    #         radius_grid_step=3)
    #     array = env.reset()
    #     self.assertEqual(array.shape,
    #                      (256, 256, phyre.MAX_COLOR + 3 * phyre.MAX_GOAL))


if __name__ == '__main__':
    unittest.main()
