#!/usr/bin/env bash
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

set -e
set -u
set -p

cd "$(dirname "$0")/.."

readonly DEV_SEEDS=3
readonly FINAL_SEEDS=10
readonly DQN_BASE_NAME='dqn_10k'
readonly EVAL_SETUPS='ball_cross_template ball_within_template
two_balls_cross_template two_balls_within_template'

readonly RUN_EXPERIMENT_SCRIPT=${RUN_EXPERIMENT_SCRIPT:-"agents/run_experiment.py"}


wait_for_results() {
    local base_dir=$1
    local num_seeds=$2
    for eval_setup in $EVAL_SETUPS; do
        for seed in $(seq 0 $(( $num_seeds - 1 )) ); do
            local path="$base_dir/$eval_setup/$seed/results.json"
            while :; do
                if [ -f "$path" ]; then
                    break
                else
                    echo "Waiting for $path. Will sleep for 5min"
                    sleep 5m
                fi
            done
        done
    done
}


python $RUN_EXPERIMENT_SCRIPT --use-test-split 0 --arg-generator base_dqn --num-seeds $DEV_SEEDS
python $RUN_EXPERIMENT_SCRIPT --use-test-split 0 --arg-generator baselines_args_per_rank_size --num-seeds $DEV_SEEDS
wait_for_results "results/dev/$DQN_BASE_NAME" $DEV_SEEDS
python $RUN_EXPERIMENT_SCRIPT --use-test-split 0 --arg-generator dqn_ablation --num-seeds $DEV_SEEDS
python $RUN_EXPERIMENT_SCRIPT --use-test-split 0 --arg-generator rank_and_online_sweep --num-seeds $DEV_SEEDS

python $RUN_EXPERIMENT_SCRIPT --use-test-split 1 --arg-generator base_dqn --num-seeds $FINAL_SEEDS
wait_for_results "results/final/$DQN_BASE_NAME" $FINAL_SEEDS
python $RUN_EXPERIMENT_SCRIPT --use-test-split 1 --arg-generator finals --num-seeds $FINAL_SEEDS
