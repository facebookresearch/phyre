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

import joblib

import phyre.loader
import phyre.settings
import phyre.simulation_cache


def main_tier(tier, task_ids, num_actions):
    task_ids = sorted(task_ids)

    input_dir = (phyre.simulation_cache.get_partial_cache_folder(num_actions) /
                 tier)
    output_dir = (phyre.simulation_cache.get_cache_folder(num_actions) / tier)
    output_dir.mkdir(exist_ok=True, parents=True)
    all_simulations = {}
    for task_id in task_ids:
        tpl = task_id.split(':')[0]
        sim_path = input_dir / tpl / f'{task_id}.gz'
        assert sim_path.exists(), sim_path
        all_simulations[task_id] = joblib.load(sim_path)
    actions = joblib.load(input_dir / phyre.simulation_cache.ACTION_FILE_NAME)
    cache = dict(statuses_per_task=all_simulations, actions=actions)
    joblib.dump(cache, output_dir / phyre.simulation_cache.CACHE_FILE_NAME)


def main(num_actions):
    task_dict = phyre.loader.load_compiled_task_dict()
    task_ids_per_tier = {'ball': [], 'two_balls': []}
    for action_tier, task_tiers in phyre.simulation_cache.TIERS.items():
        for task_id, task in task_dict.items():
            if task.tier in task_tiers:
                task_ids_per_tier[action_tier].append(task_id)

    for tier, task_ids in task_ids_per_tier.items():
        main_tier(tier, task_ids, num_actions)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-actions',
                        type=int,
                        default=phyre.simulation_cache.DEFAULT_NUM_ACTIONS)
    main(**vars(parser.parse_args()))
