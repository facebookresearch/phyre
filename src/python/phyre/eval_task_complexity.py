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
"""A scrict compute evaluation stats for a task template.

Evaluation stats contains number of attempts required to find a solution by
random search as well as the list of a few solutions.

To compute the stats run:

  python eval_task_complexity.py --template-id 00100

"""
import collections
import enum
import functools
import itertools
import json
import logging
import multiprocessing
import os
import pickle
import signal
import sys

import joblib
import scipy.stats

import phyre.action_mappers
import phyre.action_simulator
import phyre.compute_solution_power
import phyre.loader
import phyre.settings
import phyre.util

CREATOR_HASH = phyre.util.compute_creator_hash()

INVALID_INPUT = phyre.action_simulator.SimulationStatus.INVALID_INPUT
NOT_SOLVED = phyre.action_simulator.SimulationStatus.NOT_SOLVED
UNSTABLY_SOLVED = phyre.action_simulator.SimulationStatus.UNSTABLY_SOLVED
STABLY_SOLVED = phyre.action_simulator.SimulationStatus.STABLY_SOLVED
SOLVED = phyre.action_simulator.SimulationStatus.SOLVED

MIN_VALID_ATTEMPTS = 10000
# Tasks that have a probability to be solved that is likely to be higher than
# this threshold are considered GOOD. Tasks that have a probability to be
# solved that is likely to be lower than twice this threshold are considered
# BAD.
SOLVABILITY_THRESHOLD_PROBS = {
    'ball': 1e-5,
    'two_balls': 1e-6,
    'ramp': 1e-5,
}
P_VALUE = 0.05
# For solvable tasks collect at least this many solutions.
MIN_SOLUTIONS = 3
# Action number i is computed as (i % ACTION_POOL_SIZE) action in
# ACTION_POOL_SIZE actions generated with seed (1000 + i // ACTION_POOL_SIZE).
ACTION_POOL_SIZE = 10000

MAX_SOLUTIONS_TO_KEEP = 5
VERSION = '8'
STATS = frozenset([
    'status_counts', 'flags', 'solutions', 'unstable_solutions',
    'solution_power'
])


class Flags(enum.Enum):
    """Flags defining solvability of task in tier."""
    GOOD_STABLE = enum.auto()
    GOOD = enum.auto()
    BAD_STABLE = enum.auto()
    BAD = enum.auto()
    IMPOSSIBLE = enum.auto()
    # Less than 10 attempts on average.
    TRIVIAL = enum.auto()


class LoadingMode(enum.Enum):
    """Loading mode for eval stats."""
    FIRST_SOLUTION_ONLY = enum.auto()
    FULL = enum.auto()


def _worker(args):
    return _eval_single_task(*args)


def _get_actions(action_simulator, start, num_actions):
    action_pool = start // ACTION_POOL_SIZE
    assert (start + num_actions - 1) // ACTION_POOL_SIZE == action_pool, (
        ACTION_POOL_SIZE, start, num_actions)

    actions = action_simulator.build_discrete_action_space(ACTION_POOL_SIZE,
                                                           seed=1000 +
                                                           action_pool)
    actions = actions[start % ACTION_POOL_SIZE:][:num_actions]
    return actions


def _eval_single_task(task, action_tier_name, start, num_attempts):
    """Evalute the task on attmepts random action from tier."""
    task_id = task.taskId
    action_simulator = phyre.ActionSimulator([task], action_tier_name)
    actions = _get_actions(action_simulator, start, num_attempts)
    statuses = collections.defaultdict(int)
    stable_solutions, unstable_solutions = [], []
    for action in actions:
        status = action_simulator.simulate_action(0,
                                                  action,
                                                  need_images=False,
                                                  stable=True).status
        statuses[status] += 1
        if status == STABLY_SOLVED:
            stable_solutions.append(action.tolist())
        if status == UNSTABLY_SOLVED:
            unstable_solutions.append(action.tolist())
    return dict(task_id=task_id,
                tier=action_tier_name,
                stable_solutions=stable_solutions[:MAX_SOLUTIONS_TO_KEEP],
                unstable_solutions=unstable_solutions[:MAX_SOLUTIONS_TO_KEEP],
                statuses=statuses)


def compute_flags(tier, status_counts):
    """Given status counts run statisical tests and return a list of labels."""
    total_attempts = sum(status_counts.values())
    valid_attempts = total_attempts - status_counts[INVALID_INPUT]
    stable_solution_attempts = status_counts[STABLY_SOLVED]
    solution_attempts = status_counts[UNSTABLY_SOLVED] + stable_solution_attempts

    flags = {}
    threshold = SOLVABILITY_THRESHOLD_PROBS[tier]
    for suffix, count in [('', solution_attempts),
                          ('_stable', stable_solution_attempts)]:
        flags[f'good{suffix}'] = scipy.stats.binom_test(
            count, n=valid_attempts, p=threshold,
            alternative='greater') < P_VALUE
        flags[f'bad{suffix}'] = scipy.stats.binom_test(
            count, n=valid_attempts, p=2 * threshold,
            alternative='less') < P_VALUE

    if not solution_attempts:
        flags[f'impossible'] = True

    if stable_solution_attempts / max(total_attempts, 1) >= 0.1:
        flags['trivial'] = True

    return frozenset(getattr(Flags, k.upper()) for k, v in flags.items() if v)


class TaskEvaller():
    """Supervisor that runs evals in chunks until everything is computed."""

    def __init__(self,
                 tasks,
                 min_valid_attempts,
                 num_workers,
                 simulate_worker_size,
                 reject_ball_solvable=False,
                 warp_size=240):
        self.min_valid_attempts = min_valid_attempts
        self.simulate_worker_size = simulate_worker_size
        self.reject_ball_solvable = reject_ball_solvable
        self.warp_size = warp_size

        assert ACTION_POOL_SIZE % simulate_worker_size == 0

        stats_per_task_tier = {}
        for tier in phyre.action_mappers.ACTION_MAPPERS:
            for task in tasks:
                stats_per_task_tier[task.taskId, tier] = dict(
                    status_counts={
                        status: 0 for status in phyre.SimulationStatus
                    },
                    solutions=[],
                    unstable_solutions=[],
                )
        done_task_tier = set()

        self._task_id_to_tasks = {task.taskId: task for task in tasks}
        self._state = {
            'stats_per_task_tier': stats_per_task_tier,
            'done_task_tier': done_task_tier
        }
        self._pool = multiprocessing.Pool(
            num_workers if num_workers > 0 else None)

    def __del__(self):
        self._pool.close()

    def step(self):
        """Schedule a chunk of evaluation jobs."""
        done_simulations_per_task_tier = {}
        for key, stats in self._state['stats_per_task_tier'].items():
            if key in self._state['done_task_tier']:
                continue
            counts = sum(stats['status_counts'].values())
            done_simulations_per_task_tier[key] = counts
        num_unresolved_task_tier_pairs = len(done_simulations_per_task_tier)
        if self.reject_ball_solvable:
            # First compute stats for ball tier.
            ball_only = {
                k: v
                for k, v in done_simulations_per_task_tier.items()
                if k[1] == 'ball'
            }
            if ball_only:
                done_simulations_per_task_tier = ball_only
        simluation_tasks = []
        for key in itertools.cycle(list(done_simulations_per_task_tier)):
            start = done_simulations_per_task_tier[key]
            done_simulations_per_task_tier[key] += self.simulate_worker_size
            task_id, tier = key
            simluation_tasks.append((self._task_id_to_tasks[task_id], tier,
                                     start, self.simulate_worker_size))
            if len(simluation_tasks) >= self.warp_size:
                break

        logging.info(
            'Starting simulation chunk with %d items. Total unresolved tasks:'
            ' %s. Simulations_done: %d', len(simluation_tasks),
            num_unresolved_task_tier_pairs,
            sum(
                sum(x['status_counts'].values())
                for x in self._state['stats_per_task_tier'].values()))

        for result in self._pool.imap(_worker, simluation_tasks):
            key = (result['task_id'], result['tier'])
            if key in self._state['done_task_tier']:
                # We scheduled a simulation task, but already got enough data.
                # So just ignoring this bit to be agnostic of warp_size.
                continue
            # Note, we may "overshoot" here: update stats that are already complete.
            stats = self._state['stats_per_task_tier'][key]
            for status, count in result['statuses'].items():
                stats['status_counts'][status] += count
            stats['solutions'].extend(result['stable_solutions'])
            del stats['solutions'][MAX_SOLUTIONS_TO_KEEP:]
            stats['unstable_solutions'].extend(result['unstable_solutions'])
            del stats['unstable_solutions'][MAX_SOLUTIONS_TO_KEEP:]
            self._update_done_stats(*key)

        return self.done()

    def _update_done_stats(self, task_id, action_tier):
        """Update a set of "done" tasks after new data for task_id and action_tier."""
        key = (task_id, action_tier)
        status_counts = self._state['stats_per_task_tier'][key]['status_counts']

        valid_attempts = sum(
            status_counts.values()) - status_counts[INVALID_INPUT]
        if valid_attempts < self.min_valid_attempts:
            return

        flags = compute_flags(action_tier, status_counts)

        if not ({Flags.GOOD, Flags.BAD} & flags):
            return
        if not ({Flags.GOOD_STABLE, Flags.BAD_STABLE} & flags):
            return
        num_solved = status_counts[UNSTABLY_SOLVED] + status_counts[
            STABLY_SOLVED]
        if Flags.GOOD in flags and num_solved < MIN_SOLUTIONS:
            return
        if (Flags.GOOD_STABLE in flags and
                status_counts[STABLY_SOLVED] < MIN_SOLUTIONS):
            return

        self._state['done_task_tier'].add(key)

        logging.info('Done simulation for %s. Stats: %s. Flags: %s', key,
                     status_counts, flags)

        # If reject_ball_solvable, add task ids for ball solved task to
        # done_task_tiers_reasons.
        solved_by_ball = (action_tier == 'ball' and Flags.GOOD_STABLE in flags)
        if self.reject_ball_solvable and solved_by_ball:
            for tier in phyre.action_mappers.ACTION_MAPPERS:
                tier_key = (task_id, tier)
                if tier_key in self._state['done_task_tier']:
                    continue
                logging.info(
                    'Removing %s. Solved by ball and reject_ball_solvable is'
                    ' True', tier_key)
                self._state['done_task_tier'].add(tier_key)

    def done(self):
        """Checks whether evaluation for all jobs is done."""
        return len(self._state['done_task_tier']) == len(
            self._state['stats_per_task_tier'])

    def result(self):
        """Returns evaluation results."""
        assert self.done()
        return self._state['stats_per_task_tier']

    def maybe_load(self, checkpoint_path):
        """If checkpoint is provided will load evaluation state."""
        if checkpoint_path is not None and os.path.exists(checkpoint_path):
            logging.info('Loading %s', checkpoint_path)
            with open(checkpoint_path, 'rb') as stream:
                self._state = pickle.load(stream)
            # Re-compute done_task_tier.
            self._state['done_task_tier'] = set()
            for key in self._state['stats_per_task_tier']:
                self._update_done_stats(*key)

    def maybe_save(self, checkpoint_path):
        """If checkpoint is provided will save evaluation state."""
        if checkpoint_path is not None:
            tmp_path = checkpoint_path + '.tmp'
            with open(tmp_path, 'wb') as stream:
                pickle.dump(self._state, stream)
            os.rename(tmp_path, checkpoint_path)


def load_all_eval_stats(num_workers=None, mode=LoadingMode.FULL):
    """Load all computed up-to-date eval stats.

    Args:
        num_workers: None or int, num workers to use for loading. If None
          will load in the main thread.
        mode: LoadingMode, defines a subset of fields to load.

    Returns:
        dict of dicts:
            template_id -> tasl_id -> eval_stats
    """
    known_template_ids = [
        x.split('.')[0]
        for x in os.listdir(str(phyre.settings.TASK_EVAL_DIR))
        if x.endswith('.json')
    ]
    local_maybe_load_evaluation = functools.partial(maybe_load_evaluation,
                                                    mode=mode)
    if num_workers is None:
        eval_stats = {}
        for template_id in known_template_ids:
            eval_stats[template_id] = local_maybe_load_evaluation(template_id)
    else:
        num_workers = num_workers if num_workers > 0 else None
        with multiprocessing.Pool(num_workers) as pool:
            eval_stats = pool.map(local_maybe_load_evaluation,
                                  known_template_ids)
        eval_stats = dict(zip(known_template_ids, eval_stats))

    eval_stats = {k: v for k, v in eval_stats.items() if v is not None}
    return eval_stats


def _clean_stats(per_tier_stats, tier):
    stats = {}
    counts = {
        phyre.SimulationStatus(int(k)): v
        for k, v in per_tier_stats['status_counts'].items()
    }
    counts[SOLVED] = counts[UNSTABLY_SOLVED] + counts[STABLY_SOLVED]
    stats['status_counts'] = counts
    stats['flags'] = compute_flags(tier, counts)
    stats['solutions'] = per_tier_stats['solutions']
    stats['unstable_solutions'] = per_tier_stats['unstable_solutions']
    return stats


def maybe_load_evaluation(template_id, mode=LoadingMode.FULL):
    """Loads evaluation file if up-to-date."""
    task_path = str(phyre.settings.TASK_SCRIPTS_DIR / f'task{template_id}.py')
    if not os.path.exists(task_path):
        logging.warning('Rogue eval file for %s', template_id)
        return None
    if does_evaluation_need_update(task_path):
        return None
    with open(get_evaluation_meta_path(task_path)) as stream:
        eval_data = json.load(stream)
    eval_data.update(joblib.load(get_evaluation_path(task_path)))
    if mode == LoadingMode.FULL:
        solution_power = joblib.load(
            phyre.compute_solution_power.get_solution_power_path(task_path))
    else:
        solution_power = None

    if mode == LoadingMode.FULL:
        needed_stats = STATS
    elif mode == LoadingMode.FIRST_SOLUTION_ONLY:
        needed_stats = ('solutions',)
    else:
        raise ValueError('Unknown loading mode: %s' % mode)

    final_eval_data = {
        stat: {tier: {} for tier in phyre.action_mappers.ACTION_MAPPERS
              } for stat in STATS
    }
    for task, per_task_stats in eval_data['eval_stats'].items():
        for tier, per_tier_stats in per_task_stats.items():
            for stat_name, value in _clean_stats(per_tier_stats, tier).items():
                final_eval_data[stat_name][tier][task] = value
    if solution_power is not None:
        for tier in phyre.action_mappers.ACTION_MAPPERS:
            final_eval_data['solution_power'][tier][
                'task_ids'] = solution_power['task_ids']
            final_eval_data['solution_power'][tier][
                'actions_on_tasks'] = solution_power[f'{tier}_actions_on_tasks']
    final_eval_data = {k: final_eval_data[k] for k in needed_stats}
    if mode == LoadingMode.FIRST_SOLUTION_ONLY:
        for per_task_solution_list in final_eval_data['solutions'].values():
            for solution_list in per_task_solution_list.values():
                solution_list[:] = solution_list[:1]
    return final_eval_data


def maybe_load_status_counts(template_id):
    eval_stats = maybe_load_evaluation(template_id)
    if eval_stats is None:
        return None
    status_counts = {}
    for tier, tier_stats in eval_stats['status_counts'].items():
        for task_id, task_stats in tier_stats.items():
            if task_id not in status_counts:
                status_counts[task_id] = {}
            status_counts[task_id][tier] = {
                phyre.SimulationStatus(int(k)): v
                for k, v in task_stats.items()
            }
    return status_counts


def load_instance_status_counts(task_instance_id):
    template_id = task_instance_id.split(':')[0]
    counts = maybe_load_status_counts(template_id)
    if counts is None:
        return None
    else:
        return counts.get(task_instance_id)


def get_task_id_slurm(log_dir):
    assert 'SLURM_ARRAY_TASK_ID' in os.environ
    task_list_fpath = os.path.join(log_dir, 'task_list')
    with open(task_list_fpath) as stream:
        task_list = stream.read().split()
    return task_list[int(os.environ['SLURM_ARRAY_TASK_ID'])]


def get_evaluation_path(task_path):
    task_id = os.path.basename(task_path).split('.')[0][4:]
    return str(phyre.settings.TASK_EVAL_DIR / task_id) + '.lzma'


def get_evaluation_meta_path(task_path):
    task_id = os.path.basename(task_path).split('.')[0][4:]
    return str(phyre.settings.TASK_EVAL_DIR / task_id) + '.meta.json'


def does_evaluation_need_update(task_path):
    return does_eval_stats_need_update(
        task_path
    ) or phyre.compute_solution_power.does_solution_power_need_update(task_path)


def does_eval_stats_need_update(task_path):
    _, _, task_script = phyre.loader.load_task_script(task_path)
    task_script_version = task_script.build_task.get_version()
    logging.debug('Task script version: %s', task_script_version)
    creator_version = CREATOR_HASH
    logging.debug('Creator lib version: %s', creator_version)
    eval_meta_fpath = get_evaluation_meta_path(task_path)
    eval_fpath = get_evaluation_path(task_path)
    logging.debug(eval_meta_fpath)
    if os.path.exists(eval_meta_fpath) and os.path.exists(eval_fpath):
        logging.debug('Found existing eval file')
        with open(eval_meta_fpath) as stream:
            eval_data = json.load(stream)
        if eval_data.get('evaluator_version', '1') != VERSION:
            logging.debug('Computed with old version of eval_task_complexity')
            return True
        if task_script_version != eval_data.get('task_script_version', '1'):
            logging.debug('Computed for old task (%s)',
                          eval_data.get('task_script_version', '1'))
            return True
        logging.debug('The eval results up to date')
        return False
    else:
        return True


def sig_handler(signum, frame):
    """USR1 signal handler that requeues the job."""
    del frame  # Unused.
    logging.warning('Signal handler called with signal %s', signum)
    prod_id = int(os.environ['SLURM_PROCID'])
    if 'SLURM_ARRAY_JOB_ID' in os.environ:
        job_id = '%s_%s' % (os.environ['SLURM_ARRAY_JOB_ID'],
                            os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        job_id = os.environ['SLURM_JOB_ID']
    if prod_id == 0:
        logging.warning('Requeuing job %s', job_id)
        os.system('scontrol requeue %s' % job_id)
    else:
        logging.warning('Not the master process, no need to requeue.')
    sys.exit(-1)


def term_handler(signum, frame):
    """Dummy TERM signal handler that does nothing."""
    del frame  # Unused.
    logging.warning('Signal handler called with signal %s', signum)
    logging.warning('Bypassing SIGTERM.')


def init_signal_handler():
    """Handle signals sent by SLURM for time limit / pre-emption."""
    signal.signal(signal.SIGUSR1, sig_handler)
    signal.signal(signal.SIGTERM, term_handler)
    logging.warning('Signal handler installed.')


def maybe_recompute_solution_power(template_id, task_path, num_workers):
    if not phyre.compute_solution_power.does_solution_power_need_update(
            task_path):
        return
    logging.info('Stale solution power. Recomputing for: %s', template_id)
    # Reading eval meta.
    eval_meta_fpath = get_evaluation_meta_path(task_path)
    assert os.path.exists(eval_meta_fpath), (
        f'Eval-meta path does not exist for {task_path}')
    with open(eval_meta_fpath) as stream:
        eval_meta = json.load(stream)
    # Reading main eval data.
    eval_fpath = get_evaluation_path(task_path)
    assert os.path.exists(eval_fpath), (
        f'Eval-stats path does not exist for {task_path}')
    eval_data = joblib.load(eval_fpath)
    phyre.compute_solution_power.save_solution_power(template_id, eval_meta,
                                                     eval_data, task_path,
                                                     num_workers)


def main(template_id, log_dir, force, interactive, **simulate_kwargs):
    if template_id is None:
        assert log_dir is not None, 'Provide --template-id or --log-dir'
        init_signal_handler()
        template_id = get_task_id_slurm(log_dir)
    # Compute the hash before starting the eval.
    logging.info('Task template id: %s', template_id)

    phyre.settings.TASK_EVAL_DIR.mkdir(parents=True, exist_ok=True)
    _, task_path, task_script = phyre.loader.load_task_script(template_id)

    if not does_eval_stats_need_update(task_path) and not interactive:
        if force:
            logging.warning('Oh, wait a sec, force mode, will rewrite')
        else:
            return maybe_recompute_solution_power(
                template_id, task_path, simulate_kwargs['num_workers'])
    tasks = task_script.build_task.build_tasks_for_search(template_id)
    logging.info('Built %d task instances.', len(tasks))
    search_params = task_script.build_task.search_params
    logging.info('Search params: %s', search_params)
    task_script_hash = phyre.util.compute_file_hash(task_path)

    if log_dir:
        checkpoint_path = os.path.join(log_dir, f'{template_id}.cpkt')
    else:
        checkpoint_path = None

    evaller = TaskEvaller(
        tasks,
        reject_ball_solvable='BALL:GOOD_STABLE' in search_params.excluded_flags,
        **simulate_kwargs)
    evaller.maybe_load(checkpoint_path)
    while not evaller.done():
        evaller.step()
        evaller.maybe_save(checkpoint_path)

    eval_stats_task_tier = evaller.result()
    eval_stats = collections.defaultdict(dict)
    for (task_id, tier), stats in eval_stats_task_tier.items():
        stats['status_counts'] = {
            int(k): v for k, v in stats['status_counts'].items()
        }
        eval_stats[task_id][tier] = stats

    eval_fpath = get_evaluation_path(task_path)
    eval_meta_fpath = get_evaluation_meta_path(task_path)
    # Clean up simulate_kwargs from not essential flags.
    clean_simulate_kwargs = simulate_kwargs.copy()
    del clean_simulate_kwargs['num_workers']
    meta = dict(evaluator_version=VERSION,
                task_script_hash=task_script_hash,
                task_script_version=task_script.build_task.get_version(),
                creator_hash=CREATOR_HASH,
                simulate_kwargs=clean_simulate_kwargs)
    eval_data = dict(eval_stats=eval_stats)

    if interactive:
        # Remove solutions.
        for ball_solvable_filter in True, False:
            if ball_solvable_filter:
                print('BALL-solvable')
            else:
                print('BALL-NOT-solvable')
            for task_id, task_stats in eval_stats.items():
                ball_solvable = (
                    task_stats['ball']['status_counts'][STABLY_SOLVED] +
                    task_stats['ball']['status_counts'][UNSTABLY_SOLVED]) > 0
                if ball_solvable_filter != ball_solvable:
                    continue
                print('===', task_id, end=' ')
                for tier, stats in task_stats.items():
                    stats = stats['status_counts']
                    print(tier,
                          stats[STABLY_SOLVED],
                          stats[UNSTABLY_SOLVED],
                          stats[INVALID_INPUT],
                          stats[NOT_SOLVED],
                          end='\t')
                print()
    else:
        # Serialize to string first to type-check.
        json.dumps(eval_data, indent=2)
        logging.info('Saving %s', eval_fpath)
        joblib.dump(eval_data, eval_fpath, compress=('lzma', 6))
        # Meta is written at the end.
        with open(eval_meta_fpath, 'w') as stream:
            json.dump(meta, stream)

    # Since we updated eval stats, we need to recompute solution power
    phyre.compute_solution_power.save_solution_power(
        template_id,
        meta,
        eval_data,
        task_path,
        num_workers=simulate_kwargs['num_workers'])


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s %(levelname)-8s'
                                ' {%(module)s:%(lineno)d} %(message)s'),
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S')

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--template-id')
    parser.add_argument('--log-dir')
    parser.add_argument('--num-workers', type=int, default=-1)
    parser.add_argument('--min-valid-attempts',
                        type=int,
                        default=MIN_VALID_ATTEMPTS)
    parser.add_argument('--simulate-worker-size',
                        type=int,
                        default=MIN_VALID_ATTEMPTS)
    parser.add_argument('--interactive', action='store_true')
    main(**vars(parser.parse_args()))
