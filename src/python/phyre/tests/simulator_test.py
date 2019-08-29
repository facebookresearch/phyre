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

from phyre.interface.scene import ttypes as scene_if
from phyre import simulator
from phyre import creator


@creator.define_task
def build_task(C):

    left = C.add('static bar', scale=0.3).set_bottom(0).set_left(10)
    right = C.add('dynamic bar', scale=0.3).set_bottom(0).set_left(left.right)

    # Always valid.
    C.update_task(body1=left,
                  body2=right,
                  relationships=[C.SpatialRelationship.LEFT_OF])


class SimulatorTest(unittest.TestCase):

    def setUp(self):
        [self._task] = build_task('test')

        # Build a box at position 100, 100.
        points = []
        for dx in range(10):
            for dy in range(10):
                points.append((100 + dx, 100 + dy))
        self._box_compressed_user_input = (points, None, None)
        self._box_user_input = simulator.build_user_input(points=points)

    def test_simulate_scene(self):
        steps = 10  # Not too many steps.
        scenes = simulator.simulate_scene(self._task.scene, steps=steps)
        self.assertEqual(len(scenes), steps)

    def test_simulate_task(self):
        steps = 200  # Not too many steps, but more than steps_for_solution..
        assert steps >= simulator.STEPS_FOR_SOLUTION
        result = simulator.simulate_task(self._task, steps=steps, stride=1)
        self.assertEqual(len(result.sceneList), simulator.STEPS_FOR_SOLUTION)
        # Empty solution should be valid.
        self.assertEqual(result.isSolution, True)

    def test_add_user_input_to_scene(self):
        raise unittest.SkipTest
        scene = simulator.add_user_input_to_scene(self._task.scene,
                                                  self._box_user_input)
        self.assertEqual(len(scene.bodies), 6)
        self.assertEqual(len(scene.user_input_bodies), 1)

    def test_add_user_input_to_scene_ball(self):
        ball = [200, 200, 30]
        user_input = (None, None, [ball])
        scene = simulator.add_user_input_to_scene(self._task.scene, user_input)
        self.assertEqual(len(scene.bodies), 6)
        self.assertEqual(len(scene.user_input_bodies), 1)

    def test_add_empy_user_input_to_scene(self):
        points = []
        scene = simulator.add_user_input_to_scene(
            self._task.scene, simulator.build_user_input(points))
        self.assertEqual(len(scene.bodies), 6)
        self.assertEqual(len(scene.user_input_bodies), 0)

    def test_add_input_and_simulate(self):
        steps = 10

        # Check simulate_task_with_input is identical to add_user_input_to_scene
        # followed by simulate_task.
        combined_results = simulator.simulate_task_with_input(
            self._task, self._box_user_input, steps=steps)

        task = copy.copy(self._task)
        task.scene = simulator.add_user_input_to_scene(task.scene,
                                                       self._box_user_input)
        bl_resuls = simulator.simulate_task(task, steps=steps)

        self.assertEqual(combined_results, bl_resuls)

    def test_add_input_and_ponies(self):
        raise unittest.SkipTest
        steps = 10

        task_simulation = simulator.simulate_task_with_input(
            self._task, self._box_user_input, steps=steps, stride=1)

        is_solved, had_occlusions, images = simulator.magic_ponies(
            self._task, self._box_compressed_user_input, steps=steps, stride=1)

        self.assertEqual(is_solved, task_simulation.isSolution)
        self.assertEqual(len(images), steps)
        self.assertEqual(len(task_simulation.sceneList), steps)
        self.assertEqual(
            had_occlusions, task_simulation.sceneList[0].user_input_status ==
            scene_if.UserInputStatus.HAD_OCCLUSIONS)
        self.assertFalse((images[0] == simulator.scene_to_raster(
            task_simulation.sceneList[-1])).all())
        self.assertTrue((images[-1] == simulator.scene_to_raster(
            task_simulation.sceneList[-1])).all())

    def test_is_solution_valid(self):
        steps = 200
        assert steps >= simulator.STEPS_FOR_SOLUTION
        # Empty solution should be valid.
        self.assertTrue(
            simulator.magic_ponies(self._task,
                                   self._box_compressed_user_input,
                                   steps=steps)[0])

    def test_render(self):
        array = simulator.scene_to_raster(self._task.scene)
        self.assertEqual(len(array.shape), 2)
        self.assertEqual(array.shape[0], self._task.scene.height)
        self.assertEqual(array.shape[1], self._task.scene.width)

    def test_render_with_input(self):
        scene = simulator.simulate_task_with_input(self._task,
                                                   self._box_user_input,
                                                   steps=1).sceneList[0]
        array = simulator.scene_to_raster(scene)
        self.assertEqual(len(array.shape), 2)
        self.assertEqual(array.shape[0], self._task.scene.height)
        self.assertEqual(array.shape[1], self._task.scene.width)

    def test_add_input_and_simulate_strided(self):
        steps = 10
        full_results = simulator.simulate_task_with_input(self._task,
                                                          self._box_user_input,
                                                          stride=1,
                                                          steps=steps)
        strided_results = simulator.simulate_task_with_input(
            self._task, self._box_user_input, stride=3, steps=steps)
        self.assertEqual(len(full_results.sceneList), steps)
        self.assertEqual(len(strided_results.sceneList), math.ceil(steps / 3))
        self.assertEqual(len(full_results.solvedStateList), steps)
        self.assertEqual(len(strided_results.solvedStateList),
                         math.ceil(steps / 3))
        for i in range(0, steps, 3):
            self.assertEqual(full_results.sceneList[i],
                             strided_results.sceneList[i // 3])
            self.assertEqual(full_results.solvedStateList[i],
                             strided_results.solvedStateList[i // 3])

    def test_batched_magic_ponies(self):
        steps = 61
        workers = 3
        is_solved, _, images = simulator.batched_magic_ponies(
            [self._task] * 100, [self._box_compressed_user_input] * 100,
            workers, steps)
        self.assertEqual(len(is_solved), 100)
        self.assertEqual(len(images), 100)
        self.assertEqual(images[0].shape, (2, 256, 256))
        self.assertEqual(images[1].shape, (2, 256, 256))


if __name__ == '__main__':
    unittest.main()
