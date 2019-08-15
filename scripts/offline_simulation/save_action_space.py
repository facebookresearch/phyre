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
import numpy as np

import phyre.action_mappers
import phyre.simulation_cache


def main(num_actions):
    data_folder = phyre.simulation_cache.get_partial_cache_folder(num_actions)

    for tier, action_mapper in phyre.action_mappers.ACTION_MAPPERS.items():
        if tier not in phyre.action_mappers.MAIN_ACITON_MAPPERS:
            continue
        rng = np.random.RandomState(seed=phyre.simulation_cache.ACTION_SEED)
        all_actions = [
            action_mapper().sample(rng=rng) for _ in range(num_actions)
        ]
        all_actions = np.array(all_actions, 'float32')
        tier_folder = data_folder / tier
        tier_folder.mkdir(exist_ok=True, parents=True)
        path = tier_folder / phyre.simulation_cache.ACTION_FILE_NAME
        print('Saving path', path)
        joblib.dump(all_actions, path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-actions',
                        type=int,
                        default=phyre.simulation_cache.DEFAULT_NUM_ACTIONS)
    main(**vars(parser.parse_args()))
