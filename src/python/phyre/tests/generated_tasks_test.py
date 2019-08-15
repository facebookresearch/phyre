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

import json
import unittest

import phyre.loader
import phyre.settings


class GeneratedTaskTestCase(unittest.TestCase):
    """Generated tasks checksum matches."""

    def test_task_checksum_matches(self):
        template_dict = phyre.loader.load_compiled_template_dict()
        with phyre.settings.TASK_CHECKSUM.open() as f:
            hashes = json.load(f)
        for template_id, template_tasks in template_dict.items():
            new_hash = phyre.util.compute_tasks_hash(template_tasks)
            assert new_hash == hashes[template_id], (
                'Hash of tasks for template '
                f'{template_id} doesn\'t match')
        assert template_dict.keys() == hashes.keys(), (
            f'Found template ids {set(hashes.keys() - template_dict.keys())}'
            ' in hashed tasks not in generated tasks')


if __name__ == '__main__':
    unittest.main()
