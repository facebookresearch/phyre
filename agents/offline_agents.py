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
"""Agent interface and example agents.

For train.py to be aware of an agent, it should 1) inherit from Agent class
and 2) the file with the agent code should be imported in train.py.

The agents in this file do not run simulations during training. Instead they
use pre-computed simulation results for a fixed 100k sample of actions. In
that sense, the agents are "offline". See documentation for
`phyre.simulation_cache` for details.

The library contains a AgentWithSimulationCache wrapper to simplify access to
the cache.
"""
from typing import Any, Tuple
import abc
import collections
import heapq
import logging

import numpy as np
import math
import tqdm

import phyre
import neural_agent

State = Any
TaskIds = Tuple[str, ...]


class Agent(metaclass=abc.ABCMeta):
    """Base class for phyre agents.

    The two main methods are train() and eval().

    Train is allowed to do arbitrary number of interactions with the
    simulator on the set of training tasks. At the end of training it returns
    a "state" that represents a trained model.

    At the eval state the agent gets the state and a new set of task ids. It
    can try to solve the tasks in aribtraty order, but can at do at most
    max_attempts_per_task attempts per task. Invalid action, i.e., ones that
    results in obects that intersect, are ignored. Each attempts should be
    logged with phyre.Evaluator. See RandomAgent as an example.

    Both train() and eval() will get all command line flags as keyword
    arguments. Subclasses can either use kwargs or define the list of needed
    arguments manually. See OracleRankingAgent for an example.
    """

    @classmethod
    def add_parser_arguments(cls, parser: "argparse.ArgumentParser") -> None:
        """Add agent's parameters to the argument parser."""
        del parser  # Not used.

    @classmethod
    def name(cls) -> str:
        """Name of the agent for --agent flag."""
        name = cls.__name__
        if name.endswith('Agent'):
            name = name[:-5]
        return name.lower()

    @classmethod
    @abc.abstractmethod
    def train(cls, task_ids: TaskIds, action_tier_name: str, **kwargs) -> State:
        """Train an agent and returns a state."""

    @classmethod
    @abc.abstractmethod
    def eval(cls, state: State, task_ids: TaskIds, max_attempts_per_task: int,
             action_tier_name, **kwargs) -> phyre.Evaluator:
        """Runs evaluation and logs all attemps with phyre.Evaluator."""


class AgentWithSimulationCache(Agent):

    @classmethod
    def train(cls, task_ids: TaskIds, tier: str, **kwargs) -> State:
        cache = phyre.get_default_100k_cache(tier)
        return cls._train_with_cache(cache, task_ids, tier=tier, **kwargs)

    @classmethod
    def _train_with_cache(cls, cache: phyre.SimulationCache, task_ids: TaskIds,
                          tier: str, **kwargs) -> State:
        # In the simplest case the agents uses all cached simulation as its
        # state to make use if it during evaluation.
        return dict(cache=cache)


class RandomAgent(AgentWithSimulationCache):

    @classmethod
    def eval(cls, state: State, task_ids: TaskIds, max_attempts_per_task: int,
             **kwargs) -> phyre.Evaluator:
        cache = state['cache']
        evaluator = phyre.Evaluator(task_ids)
        for i, task_id in enumerate(task_ids):
            statuses = cache.load_simulation_states(task_id)
            valid_statuses = statuses[
                statuses != phyre.simulation_cache.INVALID]
            for status in valid_statuses[:max_attempts_per_task]:
                evaluator.maybe_log_attempt(i, status)
        return evaluator


class PriorRankingAgent(AgentWithSimulationCache):
    """Agent that selects actions that are close to dynamic objects.
    Author: k-r-allen"""

    @classmethod
    def name(cls):
        return 'object_prior'

    @classmethod
    def add_parser_arguments(cls, parser: 'argparse.ArgumentParser') -> None:
        parser = parser.add_argument_group('%s params' % cls.__name__)
        parser.add_argument('--tier',
                            type=str,
                            help='which tier is being used.')

    @classmethod
    def yield_coordinates(cls, body):
        x = body.position.x
        y = body.position.y

        def _rotate(x_in, y_in, radians):
            cos, sin = math.cos(radians), math.sin(radians)
            return x_in * cos - y_in * sin, x_in * sin + y_in * cos

        def _to_absolute(rel_x, rel_y, radians):
            rel_x, rel_y = _rotate(rel_x, rel_y, radians)
            return rel_x + x, rel_y + y

        for shape in body.shapes:
            if shape.circle:
                r = shape.circle.radius
                yield _to_absolute(r, r, radians=0)
                yield _to_absolute(-r, -r, radians=0)
            else:
                assert shape.polygon
                for v in shape.polygon.vertices:
                    yield _to_absolute(v.x, v.y, radians=body.angle)

    @classmethod
    def in_prior(cls, action, bodies):
        '''
      Takes in an action and initial_featurized_objects and returns whether the action
      is in the prior (above or below a dynamic object)
      '''
        for body in bodies:
            if body.bodyType == 1:
                continue
            vertices = [coord for coord in cls.yield_coordinates(body)]
            max_x = (max(coord[0] for coord in vertices) + 5) / 256
            min_x = (min(coord[0] for coord in vertices) - 5) / 256
            if action[0] > min_x and action[0] < max_x:
                return True
        return False

    @classmethod
    def eval(cls, state: State, task_ids: TaskIds, max_attempts_per_task: int,
             tier: str, **kwargs):

        cache = state['cache']
        evaluator = phyre.Evaluator(task_ids)
        simulator = phyre.initialize_simulator(task_ids, tier)

        assert tuple(task_ids) == simulator.task_ids
        for i, task_id in enumerate(task_ids):
            statuses = cache.load_simulation_states(task_id)
            valid_mask = statuses != phyre.simulation_cache.INVALID
            actions, statuses = cache.action_array[valid_mask], statuses[
                valid_mask]
            for action, status in zip(actions, statuses):
                if evaluator.get_attempts_for_task(i) >= max_attempts_per_task:
                    break
                if cls.in_prior(action, simulator._tasks[i].scene.bodies):
                    evaluator.maybe_log_attempt(i, status)
            else:
                print("Not enough actions in prior", task_id,
                      evaluator.get_attempts_for_task(i))

        return evaluator


class MaxHeapWithSideLoad():
    """A max-heap that stores unique keys with priority."""

    def __init__(self, key_priority_pairs):
        self.key_to_entry = {k: [-v, k, 1] for k, v in key_priority_pairs}
        self.heap = list(self.key_to_entry.values())
        heapq.heapify(self.heap)

    def __len__(self):
        return len(self.key_to_entry)

    def pop_key(self, key):
        """Remove key from the heap."""
        entry = self.key_to_entry[key]
        del self.key_to_entry[key]
        entry[-1] = 0
        return entry[1], -entry[0]

    def push(self, key, priority):
        """Push a new key into the heap."""
        assert key not in self.key_to_entry, key
        entry = [-priority, key, 1]
        self.key_to_entry[key] = entry
        heapq.heappush(self.heap, entry)

    def pop_max(self):
        """Get (key, priority) pair with the highest priority."""
        while True:
            priority, key, is_valid = heapq.heappop(self.heap)
            if not is_valid:
                continue
            del self.key_to_entry[key]
            return key, -priority

    def copy(self):
        """Create a clone of the queue."""
        return MaxHeapWithSideLoad(
            [[k, -v] for v, k, is_valid in self.heap if is_valid])


class OracleRankingAgent(AgentWithSimulationCache):
    """Agent that does oracle ranking over a set of actions."""

    @classmethod
    def name(cls):
        return 'oracle'

    @classmethod
    def add_parser_arguments(cls, parser: 'argparse.ArgumentParser') -> None:
        parser = parser.add_argument_group('%s params' % cls.__name__)
        parser.add_argument('--oracle-rank-size',
                            type=int,
                            help='How many actions to consider.')

    @classmethod
    def eval(cls, state: State, task_ids: TaskIds, max_attempts_per_task: int,
             oracle_rank_size: int, **kwargs):
        assert oracle_rank_size
        cache = state['cache']
        evaluator = phyre.Evaluator(task_ids)
        for i, task_id in enumerate(task_ids):
            statuses = cache.load_simulation_states(task_id)[:oracle_rank_size]
            assert len(statuses) == oracle_rank_size, (len(statuses),
                                                       oracle_rank_size)
            if (statuses == phyre.simulation_cache.SOLVED).any():
                evaluator.maybe_log_attempt(i, phyre.SimulationStatus.SOLVED)
            else:
                evaluator.maybe_log_attempt(i,
                                            phyre.SimulationStatus.NOT_SOLVED)
        return evaluator


class MemoizeAgent(AgentWithSimulationCache):

    @classmethod
    def add_parser_arguments(cls, parser: 'argparse.ArgumentParser') -> None:
        parser = parser.add_argument_group('MEM Agent params')
        parser.add_argument(
            '--mem-test-simulation-weight',
            default=0.,
            type=float,
            help='Weight for simulations on test test. Zero weight means that'
            ' test-time data is ignored.')
        parser.add_argument(
            '--mem-rerank-size',
            default=-1,
            type=int,
            help='If positive, will re-rerank only subset of the train actions')
        parser.add_argument('--mem-scoring-type',
                            default='relative',
                            choices=('relative', 'absolute'))
        parser.add_argument(
            '--mem-template-aware',
            default=1,
            type=int,
            help='Whether to train separate agents for each template')

    @classmethod
    def _eval(cls, cache, train_sim_statuses, task_ids, evaluator,
              max_attempts_per_task, mem_test_simulation_weight,
              mem_rerank_size, mem_scoring_type, **kwargs):
        del kwargs  # Unused.

        #action_scores = train_sim_statuses.astype('float32').sum(0)
        if mem_rerank_size > 0:
            train_sim_statuses = train_sim_statuses[:, :mem_rerank_size]
        positive = (train_sim_statuses.astype('float32') > 0).sum(0)
        negative = (train_sim_statuses.astype('float32') < 0).sum(0)
        if mem_scoring_type == 'relative':
            denominators = positive + negative + 1
            action_scores = positive / denominators
        elif mem_scoring_type == 'absolute':
            denominators = positive * 0 + 1
            action_scores = positive - negative
        else:
            raise ValueError(f'Unknown mem_scoring_type={mem_scoring_type}')

        regret_action_heap = MaxHeapWithSideLoad(enumerate(action_scores))

        logging.info('Found %d actions to choose from', len(regret_action_heap))

        logging.info('Starting eval simulation. mem_test_simulation_weight=%f',
                     mem_test_simulation_weight)
        for i, task_id in enumerate(task_ids):
            statuses = cache.load_simulation_states(task_id)
            to_push = []
            while regret_action_heap and evaluator.get_attempts_for_task(
                    i) < max_attempts_per_task:
                action_id, success_rate = regret_action_heap.pop_max()
                status = phyre.SimulationStatus(statuses[action_id])
                evaluator.maybe_log_attempt(i, status)
                if mem_scoring_type == 'relative':
                    if status != 0:
                        successes = success_rate * denominators[action_id]
                        successes += mem_test_simulation_weight * float(
                            status > 0)
                        denominators[action_id] += mem_test_simulation_weight
                        success_rate = successes / denominators[action_id]
                elif mem_scoring_type == 'absolute':
                    success_rate += float(status) * mem_test_simulation_weight
                else:
                    raise ValueError(
                        f'Unknown mem_scoring_type={mem_scoring_type}')
                to_push.append((action_id, success_rate))
            for action, reward in to_push:
                regret_action_heap.push(action, reward)

        logging.info('Collected %s simulation samples for %s tasks',
                     len(evaluator), len(task_ids))

        return evaluator

    @classmethod
    def _train_with_cache(cls, cache, task_ids, tier, **kwargs):
        simulation_statuses = np.stack(
            [cache.load_simulation_states(task_id) for task_id in task_ids], 0)
        return dict(cache=cache,
                    simulation_statuses=simulation_statuses,
                    train_task_ids=task_ids)

    @classmethod
    def eval(cls, state, task_ids, *args, **kwargs):
        mem_template_aware = kwargs.pop('mem_template_aware')

        evaluator = phyre.Evaluator(task_ids)
        cache = state['cache']
        train_statuses = state['simulation_statuses']
        if mem_template_aware:
            train_tpl_ids = frozenset(
                x.split(':')[0] for x in state['train_task_ids'])
            test_tpl_to_ids = collections.defaultdict(list)
            for task_id in task_ids:
                test_tpl_to_ids[task_id.split(':')[0]].append(task_id)
            within_template = (
                frozenset(test_tpl_to_ids) == frozenset(train_tpl_ids))
            if within_template:
                logging.info('Going to build sub-agent for each template id')
                for tpl, task_ids in test_tpl_to_ids.items():
                    indices = [
                        i for i, task_id in enumerate(state['train_task_ids'])
                        if task_id.split(':')[0] == tpl
                    ]
                    cls._eval(cache, train_statuses[indices], task_ids,
                              evaluator, *args, **kwargs)
            else:
                cls._eval(cache, train_statuses, task_ids, evaluator, *args,
                          **kwargs)
        else:
            cls._eval(cache, train_statuses, task_ids, evaluator, *args,
                      **kwargs)
        return evaluator


class DQNAgent(AgentWithSimulationCache):

    EVAL_FLAG_NAMES = ('finetune_iterations', 'eval_batch_size',
                       'refine_iterations', 'refine_loss', 'refine_lr',
                       'rank_size')

    @classmethod
    def name(cls):
        return 'dqn'

    @classmethod
    def add_parser_arguments(cls, parser: 'argparse.ArgumentParser') -> None:
        parser = parser.add_argument_group('%s params' % cls.__name__)
        parser.add_argument('--dqn-train-batch-size', type=int, default=32)
        parser.add_argument('--dqn-updates', type=int, default=1000)
        parser.add_argument('--dqn-save-checkpoints-every',
                            type=int,
                            default=-1,
                            help='How often to save checkpoints')
        parser.add_argument(
            '--dqn-negative-sampling-prob',
            type=float,
            default=1.0,
            help='Relative probability to take negative example during'
            ' training. Value 1.0 means that the sampling is indenependent of'
            ' the label. Lower values will choose negative examples less'
            ' frequently.')
        parser.add_argument(
            '--dqn-balance-classes',
            type=int,
            default=0,
            help='Samples the same number of positives ane negatives for every'
            ' batch.')
        parser.add_argument('--dqn-network-type',
                            choices=('resnet18', 'simple'),
                            default='resnet18',
                            help='type of architecture to use')
        parser.add_argument(
            '--dqn-num-auccess-actions',
            type=int,
            default=0,
            help='If positive will run AUCCESS eval with this number of'
            ' actions.')
        parser.add_argument('--dqn-action-layers', type=int, default=1)
        parser.add_argument('--dqn-action-hidden-size', type=int, default=256)
        parser.add_argument('--dqn-eval-every',
                            type=int,
                            default=1000,
                            help='Eval every this many updates.')
        parser.add_argument('--dqn-cosine-scheduler',
                            type=int,
                            default=0,
                            help='Whether to use cosine scheduler.')
        parser.add_argument('--dqn-fusion-place',
                            choices=('first', 'last', 'all', 'none',
                                     'last_single'),
                            default='last')
        parser.add_argument('--dqn-learning-rate', type=float, default=3e-4)

        # Evaluation time paramters.
        parser.add_argument('--dqn-eval-batch-size', type=int, default=128)
        parser.add_argument(
            '--dqn-rank-size',
            type=int,
            default=-1,
            help='How many options to re-rank for eval. If negative, will use'
            ' train set.')
        parser.add_argument(
            '--dqn-load-from',
            help='If set, will skip the training and load the model from the'
            ' last checkpoint in the folder. Model architecture and training'
            ' params will be ignored.')
        parser.add_argument('--dqn-finetune-iterations',
                            type=int,
                            default=0,
                            help='If set, will fine-tune DQN on test data')
        parser.add_argument('--dqn-refine-iterations',
                            type=int,
                            default=0,
                            help='If set, will refine actions for each task')
        parser.add_argument('--dqn-refine-loss',
                            choices=('ce', 'linear'),
                            default='ce')
        parser.add_argument('--dqn-refine-lr', type=float, default=1e-4)

    @classmethod
    def real_eval(cls, cache, model, actions, task_ids, tier,
                  max_attempts_per_task, eval_batch_size, finetune_iterations,
                  refine_iterations, refine_loss, refine_lr):

        # TODO: move to a flag.
        finetune_lr = 1e-4

        model.cuda()

        simulator = phyre.initialize_simulator(task_ids, tier)
        observations = simulator.initial_scenes
        assert tuple(task_ids) == simulator.task_ids

        logging.info('Ranking %d actions and simulating top %d', len(actions),
                     max_attempts_per_task)
        if refine_iterations > 0:
            logging.info(
                'Will do refining for %d iterations with lr=%e and loss=%s',
                refine_iterations, refine_lr, refine_loss)
        evaluator = phyre.Evaluator(task_ids)
        for task_index in tqdm.trange(len(task_ids)):
            task_id = simulator.task_ids[task_index]
            if refine_iterations > 0:
                refined_actions = neural_agent.refine_actions(
                    model, actions, observations[task_index], refine_lr,
                    refine_iterations, eval_batch_size, refine_loss)
            else:
                refined_actions = actions
            scores = neural_agent.eval_actions(model, refined_actions,
                                               eval_batch_size,
                                               observations[task_index])
            # Order of descendig scores.
            action_order = np.argsort(-scores)
            if not refine_iterations > 0:
                statuses = cache.load_simulation_states(task_id)

            finetune_data = []
            for action_id in action_order:
                if evaluator.get_attempts_for_task(
                        task_index) >= max_attempts_per_task:
                    break
                action = refined_actions[action_id]
                if refine_iterations > 0:
                    status = simulator.simulate_action(task_index,
                                                       action,
                                                       need_images=False,
                                                       need_scenes=False).status
                else:
                    status = phyre.SimulationStatus(statuses[action_id])
                finetune_data.append((task_index, status, action))
                evaluator.maybe_log_attempt(task_index, status)
            if evaluator.get_attempts_for_task(task_index) == 0:
                logging.warning('Made 0 attempts for task %s', task_id)
            if finetune_iterations > 0:
                neural_agent.finetune(model, finetune_data, simulator,
                                      finetune_lr, finetune_iterations)

        return evaluator

    @classmethod
    def _extract_dqn_flags(cls, **kwargs):
        """Extract DQN-related train and test command line flags."""
        train_kwargs, eval_kwargs = {}, {}
        for k, v in kwargs.items():
            if k.startswith('dqn_'):
                flag = k.split('_', 1)[1]
                if flag in cls.EVAL_FLAG_NAMES:
                    eval_kwargs[flag] = v
                else:
                    train_kwargs[flag] = v

        return train_kwargs, eval_kwargs

    @classmethod
    def _train_with_cache(cls, cache, task_ids, tier, dqn_load_from,
                          dev_tasks_ids, max_train_actions, output_dir,
                          **kwargs):
        if dqn_load_from is not None:
            model = neural_agent.load_agent_from_folder(dqn_load_from)
        else:
            train_kwargs, _ = cls._extract_dqn_flags(**kwargs)
            model = neural_agent.train(output_dir,
                                       tier,
                                       task_ids,
                                       cache=cache,
                                       max_train_actions=max_train_actions,
                                       dev_tasks_ids=dev_tasks_ids,
                                       **train_kwargs)
        if max_train_actions:
            num_actions = max_train_actions
        else:
            num_actions = len(cache)
        return dict(model=model, num_actions=num_actions, cache=cache)

    @classmethod
    def eval(cls, state, task_ids, max_attempts_per_task, tier, dqn_rank_size,
             **kwargs):
        model = state['model']
        _, eval_kwargs = cls._extract_dqn_flags(**kwargs)

        if dqn_rank_size < 0:
            dqn_rank_size = state['num_actions']
            logging.warning('Setting rank size to %d', dqn_rank_size)
        actions = state['cache'].action_array[:dqn_rank_size]
        return cls.real_eval(state['cache'], model, actions, task_ids, tier,
                             max_attempts_per_task, **eval_kwargs)
