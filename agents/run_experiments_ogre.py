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
"""Tools to apply models trained for PHYRE-B cross tpl to PHYRE-Tools."""

from typing import Callable, Sequence, Tuple
import logging
import pathlib
import shutil
import sys

from run_experiment import get_finals_args, get_output_dir, run, Args, DummyExecutor
import phyre


def arg_generator_tools(seed):
    args = get_finals_args(seed,
                           use_test_split=1,
                           eval_setup="ball_cross_template")
    return args


def generate_tasks() -> Sequence[Tuple[Args, str, pathlib.Path]]:
    num_seeds = 10
    use_test_split = 1
    tasks = []
    split_tag = 'final' if use_test_split else 'dev'
    for eval_setup in ["ball_cross_template", "ball_phyre_to_tools"]:
        for seed in range(num_seeds):
            for experiment_name, agent_args in arg_generator_tools(seed):
                output_dir = get_output_dir(experiment_name, use_test_split,
                                            seed, eval_setup)
                args = (
                    'python',
                    'agents/train.py',
                    f'--use-test-split={int(use_test_split)}',
                    f'--output-dir={output_dir}',
                    f'--eval-setup-name={eval_setup}',
                    f'--fold-id={seed}',
                )
                key = f'{split_tag}_{eval_setup}_{seed}_{experiment_name}'
                tasks.append((args + agent_args, key, output_dir))
    return tasks


def main(params, executor):
    tasks = generate_tasks()

    futures = []
    for args, key, output_dir in tasks:
        logging.info('Starting %s: %s', key, str(output_dir))
        if output_dir.exists():
            if list(output_dir.iterdir()):
                logging.info('Already exists. Skipping')
                continue
            else:
                shutil.rmtree(str(output_dir))
        output_dir.mkdir(parents=True)
        job = executor.submit(run, args)
        with (output_dir / 'jobid').open('w') as stream:
            print(job.job_id, file=stream)
        logging.info('Job id: %s', job.job_id)
        futures.append((output_dir, key, job))

    for output_dir, key, job in futures:
        logging.info('Waiting for %s', key)
        job.result()


if __name__ == "__main__":
    logging.basicConfig(format=('%(asctime)s %(levelname)-8s'
                                ' {%(module)s:%(lineno)d} %(message)s'),
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S')

    import argparse
    parser = argparse.ArgumentParser()
    main(parser.parse_args(), DummyExecutor())
