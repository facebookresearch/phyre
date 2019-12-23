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

import glob
import logging
import os

import phyre.loader
import phyre.eval_task_complexity
import phyre.settings


def main(verbose):
    if verbose:
        logging.basicConfig(format=('%(asctime)s %(levelname)-8s'
                                    ' {%(module)s:%(lineno)d} %(message)s'),
                            level=logging.DEBUG,
                            datefmt='%Y-%m-%d %H:%M:%S')
    print('Creator lib:', phyre.eval_task_complexity.CREATOR_HASH)
    print('Loading all tasks')
    task_scripts = phyre.loader.load_task_scripts_from_folder()

    all_task_ids = []
    outdated = []
    not_computed = []
    expected_eval_files = []
    for task_id, fpath, module in task_scripts:
        if module.build_task.defines_single_task:
            continue
        eval_fpath = phyre.eval_task_complexity.get_evaluation_path(fpath)
        expected_eval_files.append(os.path.realpath(eval_fpath))
        all_task_ids.append(task_id)
        if phyre.eval_task_complexity.does_evaluation_need_update(fpath):
            if os.path.exists(eval_fpath):
                outdated.append(task_id)
            else:
                not_computed.append(task_id)

    print('Found %d template tasks' % len(all_task_ids))
    print('Need to update: %d' % len(outdated))
    print('Need to compute: %d' % len(not_computed))
    print('Good: %d' % (len(all_task_ids) - len(not_computed) - len(outdated)))

    all_eval_path = set(
        map(os.path.realpath, glob.glob(phyre.settings.TASK_EVAL_DIR + '/*')))
    rogue_files = all_eval_path.difference(expected_eval_files)
    if not rogue_files:
        print('No rogue files')
    else:
        print('Found rogue:\n', *rogue_files)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    main(**vars(parser.parse_args()))
