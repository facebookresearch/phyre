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
import sys

import phyre
import phyre.action_mappers
import phyre.eval_task_complexity
import phyre.loader


def main(main_tiers_only):
    print('Loading eval stats')
    eval_stats = phyre.eval_task_complexity.load_all_eval_stats(-1)
    print('Loading tasks')
    all_tasks = phyre.loader.load_compiled_task_dict()

    print('Initializing simulators')
    if main_tiers_only:
        simulators = {}
        for tier in phyre.action_mappers.MAIN_ACITON_MAPPERS:
            simulators[tier] = phyre.ActionSimulator([
                t for t in all_tasks.values() if t.tier.lower() == tier.lower()
            ], tier)
    else:
        simulators = {
            tier: phyre.ActionSimulator(all_tasks.values(), tier)
            for tier in ('ball', 'two_balls', 'ramp')
        }

    print('Running eval')
    bad = set()
    for template_id, template_stats in eval_stats.items():
        print(template_id)
        for tier, tier_stats in template_stats['solutions'].items():
            if tier not in simulators:
                continue
            sim = simulators[tier]
            for task_id, actions in tier_stats.items():
                if task_id not in sim.task_ids:
                    continue
                for i, action in enumerate(actions):
                    status = sim.simulate_action(sim.task_ids.index(task_id),
                                                 action,
                                                 need_images=False).status
                    if status != phyre.SimulationStatus.SOLVED:
                        print('Found bad solution for', task_id, tier, status,
                              i)
                        bad.add((template_id, tier))
                        break
    print(sorted(bad))
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--main-tiers-only', action='store_true')
    main(**vars(parser.parse_args()))
