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
"""Toolst to run sets of experiments for the paper: from ablations to the finals.

E.g., to train all final, i.e., tested on test rather than dev,  run the follwing:
    python agents/run_experiment.py \
        --use-test-split 1 --arg-generator finals --num-seeds 10

Note, that this will train everything locally. And each model will be trained
40 times (4 generalization settings and 10 seeds). To paralellize on the
cluster one should define a matching Executor and pass it to main() instead
of the DummyExecutor.
"""

from typing import Callable, Sequence, Tuple
import logging
import pathlib
import shutil

import phyre

Args = Tuple[str, ...]
ExperimentInfo = Tuple[str, Args]
ArgGenerator = Callable[[int, bool, str], Sequence[ExperimentInfo]]

ROOT_DIR = pathlib.Path(__file__).parent.parent / 'results'
RESULTS_DEV = ROOT_DIR / 'dev'
RESULTS_FINAL = ROOT_DIR / 'final'

ARG_GENERATORS = {}

DQN_BASE_NAME = 'dqn_10k'
DQN_BASE_ARGS: Args = (
    '--agent-type=dqn',
    '--dqn-save-checkpoints-every=10000',
    '--dqn-updates=100000',
    '--dqn-cosine-scheduler=1',
    '--dqn-learning-rate=3e-4',
    '--dqn-train-batch-size=64',
    '--dqn-balance-classes=1',
    '--dqn-rank-size=10000',
    '--dqn-eval-every=10000',
    '--dqn-num-auccess-actions=10000',
    '--dqn-eval-every=10000',
)


def _register_arg_generator(func: ArgGenerator) -> ArgGenerator:
    name = func.__name__
    if name.endswith('_args'):
        name = name.rsplit('_', 1)[0]
    if name.startswith('get_'):
        name = name.split('_', 1)[-1]
    ARG_GENERATORS[name] = func
    return func


@_register_arg_generator
def get_base_dqn_args(seed: int, use_test_split: bool,
                      eval_setup: str) -> Sequence[ExperimentInfo]:
    """Trains a DQN agent.

    The trained model is evaluated with different parameters in other runs.
    """
    del seed  # Unused.
    del eval_setup  # Unused.
    args = DQN_BASE_ARGS
    if not use_test_split:
        args += ('--dqn-num-auccess-actions=10000',)
    return [(DQN_BASE_NAME, args)]


@_register_arg_generator
def get_dqn_ablation_args(seed: int, use_test_split: bool,
                          eval_setup: str) -> Sequence[ExperimentInfo]:
    """Trains different modifications of DQN architecture."""
    del seed  # Unused.
    del eval_setup  # Unused.
    base_args = DQN_BASE_ARGS + ('--dqn-num-auccess-actions=10000',)
    assert not use_test_split, 'Sweeps should be ran on dev set'
    args = [
        ('dqn_10k_nobalance', base_args + ('--dqn-balance-classes=0',)),
        ('dqn_10k_act1024', base_args + ('--dqn-action-hidden-size=1024',)),
        ('dqn_10k_act1024_2', base_args + (
            '--dqn-action-hidden-size=1024',
            '--dqn-action-layers=2',
        )),
        ('dqn_10k_fuse_first', base_args + ('--dqn-fusion-place=first',)),
        ('dqn_10k_fuse_all', base_args + ('--dqn-fusion-place=all',)),
        ('dqn_10k_fuse_last_single',
         base_args + ('--dqn-fusion-place=last_single',)),
    ]
    return args


@_register_arg_generator
def get_baselines_args_per_rank_size(seed: int, use_test_split: bool,
                                     eval_setup: str
                                    ) -> Sequence[ExperimentInfo]:
    """Trains random and optimal agents for number of actions to "rank"."""
    assert not use_test_split, 'Sweeps should be ran on dev set'
    del seed  # Unused.
    del use_test_split  # Unused.
    del eval_setup  # Unused.
    args = []

    for train_size in 10, 100, 1000, 10000, 100000:
        args.append(
            (f'optimal_{train_size}', ('--agent-type=oracle',
                                       f'--oracle-rank-size={train_size}')))
        args.append((f'random_{train_size}', (
            '--agent-type=random',
            f'--max-test-attempts-per-task={min(100, train_size)}',
        )))
    return args


@_register_arg_generator
def get_finals_args(seed: int, use_test_split: bool,
                    eval_setup: str) -> Sequence[ExperimentInfo]:
    """Trains final models with the best parameters for each generalization setting."""
    args = []

    args.append(('random', ('--agent-type=random',)))

    args.append(('object_prior', ('--agent-type=object_prior',)))

    dqn_load_from = get_output_dir(DQN_BASE_NAME, use_test_split, seed,
                                   eval_setup)
    if not dqn_load_from.exists():
        raise RuntimeError(
            'Cannot find a base DQN model to initialize from. Train'
            f' {DQN_BASE_NAME} first')
    dqn_base_args = DQN_BASE_ARGS + ('--dqn-load-from', str(dqn_load_from))

    dqn_ranks = dict(
        ball_cross_template='--dqn-rank-size=1000',
        ball_within_template='--dqn-rank-size=10000',
        two_balls_cross_template='--dqn-rank-size=100000',
        two_balls_within_template='--dqn-rank-size=100000',
    )
    args.append(('dqn_rank_optimal', dqn_base_args + (dqn_ranks[eval_setup],)))

    dqn_onlines = dict(
        ball_cross_template='--dqn-finetune-iterations=5',
        ball_within_template='--dqn-finetune-iterations=0',
        two_balls_cross_template='--dqn-finetune-iterations=5',
        two_balls_within_template='--dqn-finetune-iterations=0',
    )
    args.append(
        ('dqn_rank_optimal_online',
         dqn_base_args + (dqn_ranks[eval_setup], dqn_onlines[eval_setup])))

    mem_ranks = dict(
        ball_cross_template='--mem-rerank-size=1000',
        ball_within_template='--mem-rerank-size=1000',
        two_balls_cross_template='--mem-rerank-size=1000',
        two_balls_within_template='--mem-rerank-size=100000',
    )
    args.append(
        ('mem_rank_optimal', ('--agent-type=memoize', mem_ranks[eval_setup])))

    mem_onlines = dict(
        ball_cross_template='--mem-test-simulation-weight=10',
        ball_within_template='--mem-test-simulation-weight=0',
        two_balls_cross_template='--mem-test-simulation-weight=1',
        two_balls_within_template='--mem-test-simulation-weight=0',
    )
    args.append(('mem_rank_optimal_online',
                 ('--agent-type=memoize', mem_ranks[eval_setup],
                  mem_onlines[eval_setup])))
    return args


@_register_arg_generator
def get_rank_and_online_sweep_args(seed: int, use_test_split: bool,
                                   eval_setup: str) -> Sequence[ExperimentInfo]:
    """Sweeps number of actions to rank and "onlineness" for DQN and MEM."""
    assert not use_test_split, 'Sweeps should be ran on dev set'
    args = []
    for rank in 10, 100, 1000, 10000, 100000:
        args.append((f'mem_rank_{rank}', (f'--mem-rerank-size={rank}',
                                          '--agent-type=memoize')))

    # Optimal rank from the run above.
    mem_ranks = dict(
        ball_cross_template='--mem-rerank-size=1000',
        ball_within_template='--mem-rerank-size=1000',
        two_balls_cross_template='--mem-rerank-size=1000',
        two_balls_within_template='--mem-rerank-size=100000',
    )
    for weight in 0, 0.5, 1, 10, 100, 1000, 10000:
        args.append((f'mem_rank_optimal_online_{weight}',
                     (mem_ranks[eval_setup], '--agent-type=memoize',
                      f'--mem-test-simulation-weight={weight}')))

    dqn_load_from = get_output_dir(DQN_BASE_NAME, use_test_split, seed,
                                   eval_setup)
    if not dqn_load_from.exists():
        raise RuntimeError(
            'Cannot find a base DQN model to initialize from. Train'
            f' {DQN_BASE_NAME} first')
    dqn_base_args = DQN_BASE_ARGS + ('--dqn-load-from', str(dqn_load_from))

    for rank in 10, 100, 1000, 10000, 100000:
        args.append(
            (f'dqn_rank_{rank}', dqn_base_args + (f'--dqn-rank-size={rank}',)))

    # Optimal rank from the run above.
    dqn_ranks = dict(
        ball_cross_template='--dqn-rank-size=1000',
        ball_within_template='--dqn-rank-size=10000',
        two_balls_cross_template='--dqn-rank-size=100000',
        two_balls_within_template='--dqn-rank-size=100000',
    )
    for num_updates in 0, 1, 5, 10, 20:
        args.append((f'dqn_rank_optimal_online_{num_updates}', dqn_base_args + (
            dqn_ranks[eval_setup],
            f'--dqn-finetune-iterations={num_updates}',
        )))
    return args


def get_output_dir(agent: str, use_test_split: bool, seed: int,
                   eval_setup: str) -> pathlib.Path:
    result_dir = RESULTS_FINAL if use_test_split else RESULTS_DEV
    return result_dir / agent / eval_setup / str(seed)


def run(args: Args):
    import subprocess
    subprocess.check_call(args)


def generate_tasks(num_seeds: int, use_test_split: bool,
                   arg_generator: ArgGenerator
                  ) -> Sequence[Tuple[Args, str, pathlib.Path]]:
    tasks = []
    split_tag = 'final' if use_test_split else 'dev'
    for eval_setup in phyre.MAIN_EVAL_SETUPS:
        for seed in range(num_seeds):
            for experiment_name, agent_args in arg_generator(
                    seed, use_test_split, eval_setup):
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


class DummyExecutor():
    """Exector that runs jobs locally in the main thread."""

    def update_parameters(self, *args, **kwargs):
        pass

    def submit(self, func, *args, **kwargs):
        """Submit the function for execution."""
        logging.info('Dummy run %s %s %s', func, args, kwargs)
        res = func(*args, **kwargs)

        class Result():
            """Dummy class to emulate future."""

            job_id = -1

            def result(self):
                return res

        return Result()


def main(params, executor):
    if params.num_seeds is None:
        params.num_seeds = 10 if params.use_test_split else 3
    tasks = generate_tasks(params.num_seeds, bool(params.use_test_split),
                           ARG_GENERATORS[params.arg_generator])

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
    parser.add_argument('--num-seeds', type=int)
    parser.add_argument('--use-test-split', type=int, required=True)
    parser.add_argument('--arg-generator',
                        required=True,
                        choices=ARG_GENERATORS.keys())
    main(parser.parse_args(), DummyExecutor())
