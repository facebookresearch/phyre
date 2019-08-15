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

from phyre.viz_server import handler
from phyre import loader
from phyre import simulator
from phyre.interface.scene import ttypes as scene_if


class ServerTest(unittest.TestCase):
    """Simple test to check that server methods do not die."""

    def setUp(self):
        config = dict(mode=handler.DEV_MODE, max_balls=0)
        self._first_task_id = min(loader.load_compiled_task_dict())
        self._handler = handler.ServiceHandler(config, test_mode=True)

    def test_list_tasks(self):
        self.assertTrue(len(self._handler.list_task_tier_map('')), 1)
        self.assertTrue(len(self._handler.list_task_tier_map('00000:')), 1)
        self.assertTrue(len(self._handler.list_task_tier_map('00001:')), 0)

    def test_get_tasl_from_id(self):
        self._handler.get_task_from_id(self._first_task_id)

    def test_simulate_task(self):
        sim = self._handler.simulate_task_by_id(self._first_task_id,
                                                user_input=scene_if.UserInput(),
                                                dilate=False).simulation
        self.assertEqual(len(sim.sceneList),
                         1 + (simulator.DEFAULT_MAX_STEPS - 1) // 3)

    def test_render(self):
        meta_task = self._handler.get_task_from_id('00000:000')
        self._handler.render(meta_task.task.scene)

    def test_load_evaluation_data(self):
        self._handler.load_evaluation_data('')
        self._handler.load_evaluation_data('00000:')


if __name__ == '__main__':
    unittest.main()
