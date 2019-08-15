
<p align="center"><img width="70%" src="imgs/phyre_logo.jpg" /></p>

[![GitHub license](https://img.shields.io/badge/license-Apache-blue.svg)](https://github.com/facebookresearch/phyre/blob/master/LICENSE)
[![CircleCI](https://circleci.com/gh/facebookresearch/phyre.svg?style=svg)](https://circleci.com/gh/facebookresearch/phyre)

**PHYRE** is a benchmark for physical reasoning.

It provides a set of physics puzzles in a simulated 2D world. Each puzzle
has a goal state (e.g., *make the green ball touch the blue wall*) and an
initial state in which the goal is not satisfied (see the figure below). A
puzzle can be solved by placing one or more new bodies in the environment
such that when the physical simulation is run the goal is satisfied. An agent
playing this game must solve previously unseen puzzles in as few attempts as
possible.

![phyre](imgs/phyre_tasks.gif)

You can explore the tasks and try to solve them using the [demo](http://player.phyre.ai/) and jump straight into [jupyter notebook](examples/01_phyre_intro.ipynb).


# Getting started

## Installation
The recommended way to install the PHYRE is by using a [Conda](https://docs.conda.io/en/latest/) package manager.

```(bash)
git clone https://github.com/facebookresearch/phyre.git
cd phyre
conda env create -f env.yml
source activate phyre
pip install -e src/python
```

 To check that the installation was successful, run `python -m phyre.server` and open http://localhost:30303. That should start a local demo server.

 Alternatively, we provide a [Dockerfile](Dockerfile) that builds the package in a controlled environment.

## Notebooks
We provide jupyter notebooks that show [how to use PHYRE API](examples/01_phyre_intro.ipynb) to run simulations and evaluate a random agent and [how to use simulation cache](examples/02_memoized_agent.ipynb) to train agents faster.
In order to run the notebooks, you may need to install additional python dependencies with `pip install -r requirements.examples.txt`.

## Training an agent
We provide a set of baseline agents that are described in the paper.
In order to run them, you need to install additional python dependencies with `pip install -r requirements.agents.txt`.

All the agents are located in `agents/` folder. The entry point is `train.py`
that will train an agent on specified eval setup with a specified fold.
E.g., the following command will train a memoization agent:

```(bash)
python agents/train.py \
    --output-dir=results/ball_cross_template/0 \
    --eval-setup-name=ball_cross_template \
    --fold-id=0 \
    --mem-rerank-size 100 \
    --agent-type=memoize
```

File `run_experiment.py` contains groups of experiments, e.g, sweeping over number of update for DQN-O or training agents on all seeds and eval setups. And `train_all_baseline.sh` starts experiments to train all baseline algorithms in the paper.

# License
PHYRE is released under the Apache license. See [LICENSE](LICENSE) for additional details.


# Citation

If you use PHYRE in your experiments, please cite it:

```bibtex
@inproceedings{bakhtin2019phyre,
  title = {PHYRE: A New Benchmark for Physical Reasoning},
  author = {Anton Bakhtin and Laurens van der Maaten and Justin Johnson and Laura Gustafson and Ross Girshick},
  year = {2019},
}
```
