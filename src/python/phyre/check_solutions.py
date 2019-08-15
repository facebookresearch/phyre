#!/usr/bin/env python
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
import os

from thrift import TSerialization

import phyre.interface.task.ttypes as task_if
import phyre.server
import phyre.settings
import phyre.simulator
import phyre.util


def yield_is_solution(task_fname, solutions_fnames):
    with (phyre.settings.TASK_DIR / task_fname).open('rb') as stream:
        task = TSerialization.deserialize(task_if.Task(), stream.read())
    for solution_fname in solutions_fnames:
        solution = phyre.util.load_user_input(
            str(phyre.settings.SOLUTION_DIR / solution_fname))
        yield phyre.simulator.magic_ponies(task, solution)[0]


def main():

    def group_by_keys(fnames):
        d = collections.defaultdict(list)
        for fname in fnames:
            key = fname.split('.')[0]
            d[key].append(fname)
        return d

    tasks = group_by_keys(os.listdir(str(phyre.settings.TASK_DIR)))
    solutions = group_by_keys(os.listdir(str(phyre.settings.SOLUTION_DIR)))
    print(f'Found {len(tasks)} tasks and {len(solutions)} solutions')

    n_weird = n_nosolution = n_wrong = n_correct = 0
    for key in sorted(set(tasks) | set(solutions)):
        if not key in tasks:
            print(f'{key}: WARNING! Have solutions, but not tasks!')
            n_weird += 1
        elif key not in solutions:
            print(f'{key}: no solutions')
            n_nosolution += 1
        else:
            key_tasks = tasks[key]
            key_solutions = solutions[key]
            print(f'{key}: checking solution ...', end=' ', flush=True)
            assert len(key_tasks) == 1, key_tasks
            for is_valid in yield_is_solution(key_tasks[0], key_solutions):
                if is_valid:
                    print('GOOD', flush=True, end=' ')
                    n_correct += 1
                else:
                    print('BAD', flush=True, end=' ')
                    n_wrong += 1
            print('')
    print('Stats: weird=%d nosolution=%d correct=%d wrong=%d' %
          (n_weird, n_nosolution, n_correct, n_wrong))


if __name__ == '__main__':
    main()
