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

import functools
import logging
import multiprocessing

import phyre.action_simulator
import phyre.loader
import phyre.server
import phyre.settings
import phyre.util


def _eval_single_task(task_id, action_tier_name, attempts):
    tasks = phyre.loader.load_tasks_from_folder(task_id_list=[task_id]).values()
    action_simulator = phyre.action_simulator.ActionSimulator(
        tasks, action_tier_name)
    real_attempts = 0
    for _ in range(attempts):
        action = action_simulator.sample()
        status = action_simulator.simulate_action(0, action).status
        if status == phyre.SimulationStatus.SOLVED:
            return (task_id, action, real_attempts)
        if status != phyre.SimulationStatus.INVALID_INPUT:
            real_attempts += 1
    return (task_id, None, real_attempts)


def get_task_dict(task_prefix):
    if ':' in task_prefix or len(task_prefix) == 5:
        template_id, _, module = phyre.loader.load_task_script(
            task_prefix.split(':')[0])
        task_dict = {
            task.taskId: task for task in module.build_task(template_id)
        }
    else:
        task_dict = phyre.loader.load_tasks_from_folder()
    task_dict = {
        k: v for k, v in task_dict.items() if k.startswith(task_prefix)
    }
    return task_dict


def main(action_tier_name, task_prefix, max_attempts, num_workers,
         save_as_canonical_solution):
    task_dict = get_task_dict(task_prefix)
    logging.info('Found %d tasks matching %s', len(task_dict), task_prefix)
    _worker = functools.partial(_eval_single_task,
                                action_tier_name=action_tier_name,
                                attempts=max_attempts)
    pool = multiprocessing.Pool(num_workers if num_workers > 0 else None)
    total_solved = 0
    action_log = []
    action_simulator = phyre.action_simulator.ActionSimulator(
        task_dict, action_tier_name)
    for task_id, action, real_attempts in pool.imap_unordered(
            _worker, task_dict.keys()):
        action_log.append((task_id, action))
        if action is None:
            logging.info('Failed to solve task %s in %d attempts', task_id,
                         real_attempts)
        else:
            logging.info('Solved %s in %d attempts', task_id, real_attempts)
            total_solved += 1
            if save_as_canonical_solution:
                path = str(phyre.settings.SOLUTION_DIR /
                           ('task%s.solution%02d' % (task_id, 0)))
                logging.info('Saving solution for %s', task_id)
                user_input, _ = action_simulator._get_user_input(action)
                phyre.util.save_user_input(user_input, path)
    pool.close()
    logging.info('Solved: %d/%d', total_solved, len(task_dict))

    if len(task_dict) == 1 and action_log[0][1] is not None:
        path = phyre.server.LAST_INPUT_PATH
        logging.info('Saving the action to %s', path)
        user_input, _ = action_simulator._get_user_input(action_log[0][1])
        phyre.util.save_user_input(user_input, path)


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s %(levelname)-8s'
                                ' {%(module)s:%(lineno)d} %(message)s'),
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S')
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--action-tier-name',
                        required=True,
                        choices=tuple(phyre.ACTION_TIERS))
    parser.add_argument('--task-prefix', required=True)
    parser.add_argument('--max-attempts', type=int, default=4000)
    parser.add_argument('--save-as-canonical-solution', action='store_true')
    parser.add_argument(
        '--num-workers',
        type=int,
        default=-1,
        help='How many parallel simulations to run. Use -1 for use all CPUs')
    main(**vars(parser.parse_args()))
