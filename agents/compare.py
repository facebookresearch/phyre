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
"""Tool to compare results of experiments.
E.g., to compare a set of runs dqn_10k and dqn_10k_act1024 in
results/final/ run the following:
    python agents/compare.py --agent-paths
        results/final/dqn_10k results/final/dqn_10k_act1024
This will compute the AUCCESS and percentage of test tasks solved by 100
attempts, and run significance tests between the results of each pair of agents.
"""

import argparse
import json
import os
import pathlib

import numpy as np
import scipy.stats

import phyre


def compare(agent_paths):
    eval_setups = [each.stem for each in agent_paths[0].iterdir()]
    auccess = {agent_dir: [] for agent_dir in agent_paths}
    ind_solved_by = {agent_dir: [] for agent_dir in agent_paths}
    for eval_setup in eval_setups:
        try:
            auccess = {agent_dir: [] for agent_dir in agent_paths}
            ind_solved_by = {agent_dir: [] for agent_dir in agent_paths}
            seeds = set(
                [each.stem for each in (agent_paths[0] / eval_setup).iterdir()])
            for agent_dir in agent_paths:
                for seed in (agent_dir / eval_setup).iterdir():
                    with open(seed / 'results.json') as f:
                        results = json.load(f)
                    auccess[agent_dir].append(
                        results['metrics']['independent_solved_by_aucs'][100])
                    ind_solved_by[agent_dir].append(
                        results['metrics']['independent_solved_by'][100])
                    assert seed.stem in seeds, f'Seed {seed}, not in {seeds}'

            print(f'\n\n-----------{eval_setup}----------------')
            print(f'Evaluated on {len(seeds)} seeds: {seeds}')
            for agent_dir in agent_paths:
                print('\nPath for agent is', agent_dir)
                agent_auccess = np.array(auccess[agent_dir])
                agent_ind_solved_by = np.array(ind_solved_by[agent_dir])

                print('AUCCESS')
                print(
                    f'\tMean: {round(agent_auccess.mean(), 3)}\n',
                    f'\tSTD: {round(agent_auccess.std(), 3)}',
                )
                for other_agent in set(agent_paths) - set([agent_dir]):
                    sig_test = scipy.stats.wilcoxon(
                        agent_auccess,
                        y=np.array(auccess[other_agent]),
                        alternative='greater',
                    )
                    print(
                        '\tIs this agent\'s AUCCESS significantly higher than',
                        f'{other_agent}?\n\t\t{sig_test.pvalue < 0.01},',
                        f'p-value: {round(sig_test.pvalue, 4)}')

                print('% Independently solved at 100 attempts')
                print(
                    f'\tMean: {round(agent_ind_solved_by.mean(), 3)}\n',
                    f'\tSTD: {round(agent_ind_solved_by.std(), 3)}',
                )

        except Exception as e:
            print('Error comparing results for', eval_setup)
            print(e)
            continue


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--agent-paths',
        nargs='+',
        type=pathlib.Path,
        required=True,
        help='List of directories containing agents\' training results')
    parsed_args = parser.parse_args()
    compare(parsed_args.agent_paths)
