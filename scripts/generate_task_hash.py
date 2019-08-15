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

import phyre.loader
import phyre.settings


def main(template_ids):
    template_dict = phyre.loader.load_compiled_template_dict()
    print('Loading hashes')
    hashes = {}
    if phyre.settings.TASK_CHECKSUM.exists() and template_ids != 'all':
        with phyre.settings.TASK_CHECKSUM.open() as f:
            hashes = json.load(f)
    print('Hashing templates')
    template_ids = (template_ids.split(',')
                    if template_ids != 'all' else template_dict.keys())
    for template_id in template_ids:
        new_hash = phyre.util.compute_tasks_hash(template_dict[template_id])
        hashes[template_id] = new_hash
    with open(phyre.settings.TASK_CHECKSUM, 'w') as f:
        json.dump(hashes, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--template-ids',
        dest='template_ids',
        required=True,
        help='Comma separated list of template ids to hash. Use "all" to'
        ' hash all templates')
    main(**vars(parser.parse_args()))
