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

import math
import unittest

import phyre.metrics

TASKS = ('task0', 'task1')


class ClevrEnvTest(unittest.TestCase):

    def testBuildersWork(self):
        raise unittest.case.SkipTest
        manager = phyre.TaskManager()
        for name, builder in phyre.metrics.EVAL_SETUP_BUILDERS.items():
            print('Building', name)
            eval_setup = builder(manager)
            _assert_valid_eval_setup(eval_setup)

    def testMainEvalSetupsExist(self):
        for eval_setup in phyre.metrics.MAIN_EVAL_SETUPS:
            self.assertIn(eval_setup, phyre.metrics.list_eval_setups())

    def testGetTatsIdsInTierBall(self):
        self.assertGreater(len(phyre.metrics.get_task_ids_in_tier('ball')), 0)

    def testRandomEvalSetup(self):
        self.assertGreater(len(phyre.metrics.ball_single_instance_tiny()), 0)

    def testEvaluatorLog(self):
        evaluator = phyre.metrics.Evaluator(TASKS)
        self.assertEqual(len(evaluator), 0)
        self.assertEqual(evaluator.task_ids, TASKS)
        self.assertEqual(evaluator.task_ids[0], TASKS[0])
        self.assertEqual(evaluator.task_ids[1], TASKS[1])
        for i in range(100):
            self.assertEqual(evaluator.maybe_log_attempt(0, 1), True)
        for i in range(100):
            self.assertEqual(evaluator.maybe_log_attempt(1, 1), True)
        # Test invalid input
        self.assertEqual(evaluator.maybe_log_attempt(1, 0), False)
        self.assertEqual(len(evaluator), 200)
        self.assertEqual(evaluator.get_attempts_for_task(0), 100)
        self.assertEqual(evaluator.get_attempts_for_task(1), 100)
        self.assertEqual(
            evaluator._log,
            [('task0', phyre.SimulationStatus.SOLVED) for i in range(100)] +
            [('task1', phyre.SimulationStatus.SOLVED) for i in range(100)])
        self.assertRaises(Exception, lambda: evaluator.log_attempt(1, 1))

    def testComputeMetrics(self):
        evaluator = phyre.metrics.Evaluator(TASKS)
        for i in range(20):
            evaluator.maybe_log_attempt(0, 1 if i == 0 else -1)
        for i in range(20):
            evaluator.maybe_log_attempt(1, 1 if i == 11 else -1)
        metrics = phyre.metrics.compute_metrics(evaluator._log)
        self.assertEqual(metrics['independent_solved_by'][1], 1)
        self.assertEqual(metrics['independent_solved_by'][10], 1)
        self.assertEqual(metrics['independent_solved_by'][20], 2)
        self.assertEqual(metrics['global_solved_by'][100], 2)
        self.assertEqual(metrics['independent_solved_by_aucs'][1], 1)
        self.assertEqual(metrics['independent_solved_by_aucs'][2], 1)
        self.assertEqual(metrics['independent_solved_by_aucs'][11], 1)
        # First solution + second solution.
        num = (math.log(13) - math.log(1)) + (math.log(13) - math.log(12))
        denom = math.log(13)
        print(metrics['independent_solved_by_aucs'][:20])
        self.assertEqual(metrics['independent_solved_by_aucs'][12], num / denom)

    def testComputeNormalizedMetrics(self):
        evaluator = phyre.metrics.Evaluator(TASKS)
        for i in range(20):
            evaluator.maybe_log_attempt(0, 1 if i == 0 else -1)
        for i in range(20):
            evaluator.maybe_log_attempt(1, 1 if i == 11 else -1)
        with self.assertLogs('phyre.metrics', level='WARNING') as log_results:
            metrics = evaluator.compute_all_metrics()
        self.assertEqual(metrics['independent_solved_by'][1], 0.5)
        self.assertEqual(metrics['independent_solved_by'][10], 0.5)
        self.assertEqual(metrics['independent_solved_by'][20], 1.0)
        self.assertEqual(metrics['global_solved_by'][100], 1.0)
        self.assertEqual(metrics['independent_solved_by_aucs'][1], 0.5)
        self.assertEqual(metrics['independent_solved_by_aucs'][2], 0.5)
        self.assertEqual(metrics['independent_solved_by_aucs'][11], 0.5)
        # First solution + second solution.
        num = (math.log(13) - math.log(1)) + (math.log(13) - math.log(12))
        denom = math.log(13)
        print(metrics['independent_solved_by_aucs'][:20])
        self.assertEqual(metrics['independent_solved_by_aucs'][12],
                         num / denom / 2.)
        self.assertSequenceEqual(log_results.output, [
            'WARNING:phyre.metrics:Used 20.000000 attempts per task instead of'
            ' maximum allowed 100.000000. That probably indicate a bug'
            ' in evaluation loop.'
        ])

    def testComputeMetricsEmpty(self):
        evaluator = phyre.metrics.Evaluator(TASKS)
        with self.assertLogs('phyre.metrics', level='WARNING') as log_results:
            auccesss = evaluator.get_auccess()
        self.assertEqual(auccesss, 0.0)
        self.assertSequenceEqual(log_results.output, [
            'WARNING:phyre.metrics:Computing metrics for empty evaluation'
            ' log!',
            'WARNING:phyre.metrics:Used 0.000000 attempts per task instead of'
            ' maximum allowed 100.000000. That probably indicate a bug'
            ' in evaluation loop.'
        ])

    def testDevSet(self):
        train_task_ids = [f'task{i}' for i in range(10)]
        base_eval_setup = [(train_task_ids, [])]
        _assert_valid_eval_setup(base_eval_setup)
        dev_eval_setup = phyre.metrics.create_dev_set(base_eval_setup,
                                                      train_share=0.8,
                                                      seed=0)
        _assert_valid_eval_setup(dev_eval_setup)
        self.assertEqual(len(dev_eval_setup), 1)
        self.assertEqual(len(dev_eval_setup[0][0]), 8)  # Eight train tasks.
        self.assertEqual(len(dev_eval_setup[0][1]), 1)  # Single eval group.
        self.assertEqual(len(dev_eval_setup[0][1][0]), 2)  # Two eval tasks.
        dev_eval_setup2 = phyre.metrics.create_dev_set(base_eval_setup,
                                                       train_share=0.8,
                                                       seed=2)
        self.assertNotEqual(dev_eval_setup, dev_eval_setup2)


def _assert_valid_eval_setup(eval_setup):
    assert isinstance(eval_setup, (list, tuple)), type(eval_setup)
    for train_group in eval_setup:
        assert isinstance(train_group, (list, tuple))
        assert len(train_group) == 2
        train_ids, eval_groups = train_group
        assert isinstance(train_ids, (list, tuple)), type(train_ids)
        assert all(isinstance(task, str) for task in train_ids)
        assert isinstance(eval_groups, (list, tuple))
        for eval_ids in eval_groups:
            assert isinstance(eval_ids, (list, tuple)), type(eval_ids)
            assert all(isinstance(task, str) for task in eval_ids)
    return eval_setup
