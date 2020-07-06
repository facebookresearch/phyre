#!/usr/bin/env python3
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

import collections
import concurrent.futures
import lzma
import os

from thrift import TSerialization

import phyre.eval_task_complexity
import phyre.interface.task.ttypes as task_if
import phyre.loader
import phyre.settings
import phyre.simulator


def _save_task(task_id, thrift_task, target_folder):
    target_path = os.path.join(target_folder, f'task{task_id}.bin')
    with open(target_path, 'wb') as stream:
        stream.write(TSerialization.serialize(thrift_task))
    return task_id


def main(src_folder, target_folder, save_single_pickle, with_eval_stats):
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    if with_eval_stats:
        eval_stats = phyre.eval_task_complexity.load_all_eval_stats()
    else:
        eval_stats = None
    tasks = phyre.loader.load_tasks_from_folder(src_folder,
                                                eval_stats=eval_stats)

    if save_single_pickle:
        per_file = collections.defaultdict(list)
        for task in tasks.values():
            per_file[phyre.loader.task_id_to_pickle(task.taskId)].append(task)
        for fname, task_collection in per_file.items():
            task_collection = task_if.TaskCollection(
                tasks=sorted(task_collection, key=lambda task: task.taskId))
            path = os.path.join(target_folder, fname)
            with lzma.open(path, 'w') as stream:
                stream.write(phyre.simulator.serialize(task_collection))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(_save_task, task_id, thrift_task, target_folder)
                for task_id, thrift_task in tasks.items()
            ]
            for future in futures:
                task_id = future.result()
                print("Saved task", task_id)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('src_folder', help='Folder with "taskXXX.py" files')
    parser.add_argument('target_folder')
    parser.add_argument(
        '--save-single-pickle',
        action='store_true',
        help='If set, tasks will be grouped by tiers and pickled')
    parser.add_argument('--with-eval-stats',
                        action='store_true',
                        help='Use eval stats when possible')
    main(**vars(parser.parse_args()))
