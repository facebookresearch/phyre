#!/bin/bash -e
# Downloads DQN checkpoints for all sees from PHYRE paper.

DST_ROOT=$(realpath $(dirname $0)/..)

for seed in $(seq 0 9); do
    for tpl in ball_cross_template ball_within_template two_balls_cross_template two_balls_within_template; do
        for fname in ckpt.00100000 results.json; do
            path="results/finals/dqn_10k/$tpl/$seed/$fname"
            if [ ! -f "$DST_ROOT/$path" ]; then
                mkdir -p "$(dirname "$DST_ROOT/$path")"
                wget "https://dl.fbaipublicfiles.com/phyre/$path" -O "$DST_ROOT/$path"
            fi
        done
    done
done

echo "All done: $DST_ROOT"