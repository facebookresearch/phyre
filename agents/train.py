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
"""General train/eval loop for a single agent on a single train/test split.

The script:
  * Finds all knows agents - all subclasses for offline_agents.Agent in the
    included files.
  * Loads train/dev or train/test task split for the specified seed and tier.
    By default a dev split is used. Set --use-test-split=1 got get get the
    final, (train + dev)/test split.
  * Initializes the agent from the commandline flags.
  * Trains the agent on the train part.
  * Evaluates the agents on eval part.
  * Saves the evalution results to `output_dir`/results.json. The file will
    contain a dictionary with all evaluation metrics. The most important one,
    AUCCESS@100 is saved with key "target_metric".


See offline_agents for example agents.
"""
from typing import Tuple
import argparse
import json
import logging
import os
import sys

import phyre

import offline_agents


def get_train_test(eval_setup_name: str, fold_id: int, use_test_split: bool
                  ) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    train, dev, test = phyre.get_fold(eval_setup_name, fold_id)
    if use_test_split:
        return train + dev, test
    else:
        return train, dev


def main_with_seed(eval_setup_name, fold_id, use_test_split,
                   max_test_attempts_per_task, output_dir, agent_type,
                   **agent_kwargs):
    train_task_ids, eval_task_ids = get_train_test(eval_setup_name, fold_id,
                                                   use_test_split)

    agent_kwargs['tier'] = phyre.eval_setup_to_action_tier(eval_setup_name)
    agent = find_all_agents()[agent_type]

    # It's fine to use eval_task_ids iff it's dev.
    dev_tasks_ids = None if use_test_split else eval_task_ids

    logging.info('Starting training')
    state = agent.train(train_task_ids,
                        output_dir=output_dir,
                        dev_tasks_ids=dev_tasks_ids,
                        **agent_kwargs)

    logging.info('Starting eval')
    evaluation = agent.eval(state,
                            eval_task_ids,
                            max_test_attempts_per_task,
                            output_dir=output_dir,
                            **agent_kwargs)

    num_tasks = len(eval_task_ids)
    results = {}
    results['num_eval_tasks'] = num_tasks
    results['metrics'] = evaluation.compute_all_metrics()
    results['args'] = sys.argv
    results['parsed_args'] = dict(
        agent_kwargs=agent_kwargs,
        main_kwargs=dict(eval_setup_name=eval_setup_name,
                         fold_id=fold_id,
                         use_test_split=use_test_split,
                         agent_type=agent_type,
                         max_test_attempts_per_task=max_test_attempts_per_task,
                         output_dir=output_dir))
    print(results['parsed_args'])
    results['target_metric'] = (results['metrics']['independent_solved_by_aucs']
                                [max_test_attempts_per_task])
    logging.info('FINAL: %s', results['target_metric'])

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    out_path = os.path.join(output_dir, 'results.json')
    with open(out_path, 'w') as stream:
        json.dump(results, stream)


def main(fold_id, fold_id_list, **kwargs):
    assert (fold_id is None) != (fold_id_list is None)
    if fold_id_list is not None:
        base_output_dir = kwargs['output_dir']
        for seed in fold_id_list.split(','):
            kwargs['output_dir'] = os.path.join(base_output_dir, seed)
            logging.info('Runing with seed=%s and output folder %s', seed,
                         kwargs['output_dir'])
            main_with_seed(fold_id=int(seed), **kwargs)
    else:
        main_with_seed(fold_id=fold_id, **kwargs)


def find_all_agents():

    def yield_subclsses(base):
        for cls in base.__subclasses__():
            if not cls.__abstractmethods__:
                yield cls
            yield from yield_subclsses(cls)

    return {cls.name(): cls for cls in yield_subclsses(offline_agents.Agent)}


def parse_and_log_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--use-test-split',
        type=int,
        default=0,
        help='If false, will test on validation. Otherwise will train on'
        ' train+validation and evaluate on test.')
    parser.add_argument('--eval-setup-name',
                        required=True,
                        choices=phyre.MAIN_EVAL_SETUPS)
    fold_args = parser.add_mutually_exclusive_group(required=True)
    fold_args.add_argument(
        '--fold-id',
        type=int,
        help='Fold id to use. Mutually exclusive with `--fold-id-list`.')
    fold_args.add_argument(
        '--fold-id-list',
        type=str,
        help='Comma separared list of folds. If set, will call itself with each'
        ' seed. Results for each seed will be stored to a separate subfolder of'
        ' outputdir')
    parser.add_argument('--output-dir',
                        required=True,
                        help='Folder to save itermidiate files and results.')

    group = parser.add_argument_group('General agent options')
    group.add_argument('--simulation-cache-size',
                       type=int,
                       help='Size of the simulation cache to use.')
    group.add_argument(
        '--max-train-actions',
        type=int,
        help='If set, will use only the specified number of actions from the'
        ' simulation cache.')
    group.add_argument(
        '--max-test-attempts-per-task',
        type=int,
        default=phyre.MAX_TEST_ATTEMPTS,
        help='Do at most this many attempts per task during evaluation.')

    agent_dict = find_all_agents()
    parser.add_argument('--agent-type',
                        required=True,
                        choices=agent_dict.keys())
    for cls in agent_dict.values():
        cls.add_parser_arguments(parser)

    parsed_args = parser.parse_args()

    if parsed_args.max_test_attempts_per_task > phyre.MAX_TEST_ATTEMPTS:
        parser.error('--max-test-attempts-per-task cannot be greater than %s' %
                     phyre.MAX_TEST_ATTEMPTS)

    print('Args:', ' '.join(sys.argv))
    logging.info('Args: %s', ' '.join(sys.argv))
    print('Parsed args:', parsed_args)
    logging.info('Parsed args: %s', vars(parsed_args))

    return parsed_args


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s %(levelname)-8s'
                                ' {%(module)s:%(lineno)d} %(message)s'),
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S')

    main(**vars(parse_and_log_args()))
