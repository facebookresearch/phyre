# Phyre task framework

This doc goes addresses the following questions:

* What is a task
* How to create new task or template
* How to check solvability of new tasks
* Interface to load tasks outside of the main tiers


## Task internals

On a conceptual level, a task is a triple `(scene, goal, meta)`. Scene is the collections of all the objects present in the task. Goal defines a condition that must be satisfied for the task to be considered solved. It contains a pair of objects on the scene and relation, e.g., `touching` or `inside`.
Meta information includes unique task id and a tier the task belongs. The former looks like `XXXXX:YYY`; we use the same first part to group tasks created by a single task script.
The tier is simply a string that we use to group the tasks, e.g., tier `BALL` tasks that could be solved with a single ball in the standard Phyre benchmark and tier `VIRTUAL_TOOLS` contains tasks imported from [The Tools Challenge](https://sites.google.com/view/virtualtoolsgame).

On physical level, a task is a struct of type [Task](../src/if/task.thrift#37).
We use Thrift to all scenes, and goals, and everything so that we can use them from both C++ and Python.
The struct counts all the information about the task, but it's cumbersome to construct this object manually, i.e., to define coordinates and shapes of all the bodies in a scene.
Instead, we have a simple python interface that shields users from the thrift.
Probably, the only reason to go to thrift is to check what kind of goals are available.

## Task scripts

Task script is a python that constructs a task or a series of similar tasks (task template), i.e., adds all scene objects and defines the goal. Code to handle task scripts is located in [src/python/phyre/creator](../src/python/phyre/creator) and all task scripts are in [data/task_scripts/main](../data/task_scripts/main).

Here is an example of a task scripts for task template `00000` (see [demo](https://player.phyre.ai/#/task/00000:000)).

```python
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    # Define sets of values for each hyper parameter of the task.
    ball1_x=np.linspace(0.05, 0.95, 19),
    ball2_x=np.linspace(0.05, 0.95, 19),
    ball1_r=np.linspace(0.06, 0.12, 3),
    ball2_r=np.linspace(0.06, 0.12, 3),
    height=np.linspace(0.2, 0.8, 5),
)
# This function is called with some combination of values from the list above.
def build_task(C, ball1_x, ball2_x, ball1_r, ball2_r, height):

    # Task definition is symmetric.
    if ball2_x <= ball1_x:
        # Raising the exception skips this set of hyperparameters.
        raise creator_lib.SkipTemplateParams

    # Add two balls.
    ball1 = C.add(
        'dynamic ball',
        scale=ball1_r,
        center_x=ball1_x * C.scene.width,
        bottom=height * C.scene.height)
    ball2 = C.add(
        'dynamic ball',
        scale=ball2_r,
        center_x=ball2_x * C.scene.width,
        bottom=height * C.scene.height)
    if (ball2.left - ball1.right) < max(ball1_r, ball2_r) * C.scene.width:
        raise creator_lib.SkipTemplateParams
    if ball1.left <= 0:
        raise creator_lib.SkipTemplateParams
    if ball2.right >= C.scene.width - 1:
        raise creator_lib.SkipTemplateParams

    # Create the goal.
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    # Define a tier for the task.
    C.set_meta(C.SolutionTier.BALL)
```

The only defined function, `build_task`, defines how to build a task given a `TaskCreator` [object](https://github.com/facebookresearch/phyre/blob/master/src/python/phyre/creator/creator.py#L23) and set of hyperparameters for this specific instance of the task.
`creator_lib.define_task_template` will call `build_task` to create some number of tasks from the cartesian product of ranges for all the hyperparameters. By default, up `100` instances are created. To make tasks more diverse we select a random subset of parameters from the set rather than the first 100 elements.

To a new object use `C.add`. It takes a string description of the object and the scale of the object. Description is 2 words: `(static|dynamic) <object type>`. Object type is one of ball, bar, jar, and standingsticks. These are the standard objects used in the main Phyre tiers.
There are two ways to define a custom shape. Either by adding it to [shapes.py](https://github.com/facebookresearch/phyre/blob/master/src/python/phyre/creator/shapes.py) or by specifying its shape directly as a convex polygon (`C.add_convex_polygon`) or a union of convex polygons (`C.add_multipolygons`).

The function returns `Body` [object](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/python/phyre/creator/creator.py#L261). It could be used to move the body, e.g., `ball1.set_right(C.scene.width)` will push the object to the corner, or to query object position, e.g., `ball2.set_center_x(ball1.center_x)` will align the objects horizontally. Refer to the methods of the class for the full interface.

After a scene is created we define the goal of the task using `C.update_task`. It takes a couple of bodies and a list relation that must be simultaneously satisfied to a task considered to be solved. You can find the full list [here](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/if/task.thrift#L25-L33).

Finally, we define a tier for the task. To avoid typos we use named constants for tiers as defined in [constants.py](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/python/phyre/creator/constants.py#L72-L83).

To define the task one has to rebuild tasks and start the viz server in **dev** mode:

```
make generate_tasks  # Only needed when new task scripts are added.
python -m phyre.server --mode dev --port 30303
```

Open http://localhost:30303 to see all the tasks.

Note, the snippet above assumes that you build the phyre [source](https://github.com/facebookresearch/phyre/blob/master/INSTALLATION.md#installation-from-source) rather than from this pip package.


### Importing tasks from Tools format

It is possible to import tasks created from Tools Challenge format into the phyre. Note that due to different settings for friction and gravity the solvability of tasks may change. The following an example of importing a JSON definition of level.

```python
import numpy as np
import phyre.creator as creator_lib
import phyre.virtual_tools

# Path to a definition of a level, such as https://github.com/k-r-allen/tool-games/blob/master/environment/Trials/Original/Basic.json.
JSON_PATH = "..."


@creator_lib.define_task_template(noop=[None])
def build_task(C, noop):
    del noop  # Unused template parameters.

    with open(JSON_PATH) as stream:
        task_dict = json.load(stream)

    # Will convert the task.
    phyre.virtual_tools.translate_to_phyre(C, task_dict["world"]

    # Define a tier for the task.
    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
```

## Solvability checking

As a task script generates hundreds of different random sets hyperparameters, it is almost impossible to cherry-pick ones that result in solvable tasks.
Phyre contains several tools to aid with task selection.

The simplest tool is task bruteforcer. It could be invoked like that:

```
python src/python/bruteforce_solutions_in_tier.py \
    --action-tier-name ball \
    --task-prefix 000 \
    --max-attempts 1000000
```

The bruteforcer will load all task with id `000XX:YYY`, i.e., tasks in the `BALL` tier and try to solve using at most 1M random single ball solutions:

```
2020-06-24 15:40:01 INFO     {bruteforce_solutions_in_tier:64} Found 1200 tasks matching 01
2020-06-24 15:40:13 INFO     {bruteforce_solutions_in_tier:81} Solved 01000:170 in 6 attempts
2020-06-24 15:40:13 INFO     {bruteforce_solutions_in_tier:81} Solved 01000:158 in 1 attempts
2020-06-24 15:40:13 INFO     {bruteforce_solutions_in_tier:81} Solved 01000:049 in 3 attempts
2020-06-24 15:40:13 INFO     {bruteforce_solutions_in_tier:81} Solved 01000:014 in 3 attempts
2020-06-24 15:40:13 INFO     {bruteforce_solutions_in_tier:81} Solved 01000:117 in 10 attempts
2020-06-24 15:40:13 INFO     {bruteforce_solutions_in_tier:81} Solved 01000:148 in 7 attempts
...
```

This will give a quick estimate. But for automatic selection of the task one has to do more thorough eval using so called *eval stats*. Eval stats contain information about solvability of a task in all 2 action tiers (ball, two balls, and ramp) for every task in a template. By default, eval stats are computed for `200` task instances, i.e., for 2 times more tasks that we normally do. In doing so we can guarantee that there are at least `100` tasks that are actually solvable. Eval stats also contain the solutions for each task so that one can play them in the `viz`.

Use the following command to compute eval stats:
```
python src/python/phyre/eval_task_complexity.py \
  --template-id XXXXX \
  --log-dir logs/XXXXX \
  --num-workers 10
```

Once it is done, one can annotate a task script with `search_params` parameter to select tasks with some solvability, e.g., `BALL:GOOD_STABLE` (tasks that have single ball solution) or `BALL:IMPOSSIBLE`. See example for [task00000](https://github.com/facebookresearch/phyre/blob/master/data/task_scripts/main/task00000.py#L26).

# Load arbitrary task

Use the following code to a dictionary from task id to a task that contains tasks from all the tiers:
```python
import phyre.loader
all_tasks = phyre.loader.load_compiled_task_dict()
```
