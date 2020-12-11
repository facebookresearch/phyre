# OGRE dataset

Contains code to reproduce agent baselines from  OGRE dataset. See the [paper](https://github.com/orlrworkshop/orlrworkshop.github.io/raw/master/pdf/ORLR_9.pdf) for details.

## Abstract

If an agent understands how to reason about some objects, can it generalize this understanding to new objects that it has never seen before?
We propose the **Object-based Generalization for Reasoning Environment (OGRE)** for testing object generalization in the context of *creative reasoning* and *efficient acting*.

OGRE emphasizes evaluating agents by how efficiently they solve novel creative reasoning tasks, not just how well they can predict the future.
OGRE provides two levels of generalization: generalization over reasoning strategies with familiar objects, and generalization over new object types that still share similar material properties to those in training.


<p align="center"><img width="70%" src="../imgs/ogre.png" /></p>

<p style="padding: 0 20px;">

<b>A Top:</b> an example of a level within the training set of OGRE. Black and purple objects are static; objects with any other color are dynamic and subject to gravity. Actions are single balls at a position (`x`, `y`) with radius `r`, depicted as a red ball which falls under gravity once placed. Agents can observe the outcomes of these actions for a large set of training levels. Bottom: other example levels that might be included in training.

<b>B:</b> cross-template testing includes levels that use the same object representations, but require different kinds of strategies to succeed.

<b>C:</b> cross-dataset testing includes a set of levels from the Virtual Tools environment, which represents both goals and object shapes differently.

</p>

## Explore the tasks

You can explore all the task in the [PHYRE player](https://player.phyre.ai/)

## Agents

Cross-dataset generalization is implemented as a generaralization tier in PHYRE framework referred to as `ball_phyre_to_tool`. Please see the [API documentaion](https://phyre.ai/docs/evaluator.html) for more details.

We provide code that runs the baselines from PHYRE dataset and also newly added Object-Oriented Random Agent on cross-template and cross-dataset settings.
To launch all evals download pre-trained checkpoints with `bash download_dqn_ckps.sh` and run `python agents/run_experiments_ogre.py`.
See PHYRE's [README](README.md) for details of DQN training.
