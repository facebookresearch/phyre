# Simulation details

This docs describes how we store and represent tasks and simulations and how one can go beyond `ActionSimulator` interface.

## Data structures

Phyre uses the [Box2d](https://box2d.org/) engine under the hood for all the simulations.
To make it possible to access tasks and simulation results in C++, Python, and JavaScript, we use [Thrift](http://thrift.apache.org/) for cross-language representation of all data structures.

The three most important structures are Scene (defined in [scene.thrift](../src/if/scene.thrif)), Task and TaskSimulation (both are in [task.thrift](../src/if/task.thrif)).
Scene contains all objects that should be a part of simulation, i.e., it contains both the bodies from task definition and bodies added by the user. Task contains a scene and the definition of the goal of task, i.e., a relation that should hold for the to be considered solved. Finally, TaskSimulation contains positions of all objects at every timestamp. It also contains information on whether the goal condition was satisfied at any point of time and whether the task is deemed solved.

A simple way to see how the task object look like, is to load and print arbitrary task:

```python console
>>> import phyre.loader
>>> all_tasks = phyre.loader.load_compiled_task_dict()
>>> all_tasks["00000:000"]
Task(taskId='00000:000', scene=Scene(bodies=[Body(position=Vector(x=128.0, y=-2.5), bodyType=1, angle=0.0, ...
```


## Simulation interface

The low level interface lives in [simulator.py][https://github.com/facebookresearch/phyre/blob/master/src/python/phyre/simulator.py] and [simulator_bidings.cc](https://github.com/facebookresearch/phyre/blob/master/src/simulator/simulator_bindings.cpp). The former is a thin wrapper over the latter. Below are the main function you may use.

```python
simulate_scene(
    scene: scene_if.Scene,
    steps: int = DEFAULT_MAX_STEPS
    ) -> List[scene_if.Scene]
```
Runs a simulation on a given scene for a given number of steps and retuns a list of scenes. Note, this function tasks Scene rather than Task and therefore does not do any checks for solvability.


```python
simulate_task(
    task: task_if.Task,
    steps: int = DEFAULT_MAX_STEPS,
    stride: int = DEFAULT_STRIDE
) -> task_if.TaskSimulation
```
Runs a simulation on the task and returns a `TaskSimulation` object. The `stride` parameter allows to reduce the output size by skipping some frames. By default `stride` is equal FPS (60), i.e., we return one scene per second.


```python
scene_to_raster(scene: scene_if.Scene) -> np.ndarray
```

Converts the scene to an integer array height x width containing color codes. The color codes are copied from the `color` attribute of `Body` objects in the `Scene`.


```python
add_user_input_to_scene(
    scene: scene_if.Scene,
    user_input: scene_if.UserInput,
    keep_space_around_bodies: bool = True,
    allow_occlusions: bool = False
) -> scene_if.Scene
```

Adds user input objects to the scene, i.e., populates `scene.user_input_bodies`. If `allow_occlusions` is False and some user input input bodies occlude scene bodies, then these will be ignored. Note, that you can populate this field manualle with arbitrary `scene.Body`'s.

These functions are the core of the simulator inteface. `ActionSimulator.simulate_action` is essentially a fused combination of functions above.

## Tinkering with the physics

To make generalization in the Phyre dataset feasible we use the parameters for all simulations and bodies. This includes [FPS](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/simulator/task_utils.h#L25), precision of [collision resolving](https://github.com/facebookresearch/phyre/blob/master/src/simulator/task_utils.h#L27-L28), [gravity](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/simulator/thrift_box2d_conversion.cpp#L28), [density](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/simulator/thrift_box2d_conversion.cpp#L29), [friction and restitution](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/simulator/thrift_box2d_conversion.cpp#L30-L37) and [damping factors](https://github.com/facebookresearch/phyre/blob/08643a271b7f0b1e9dddfb38bfab6e8501326d2b/src/simulator/thrift_box2d_conversion.cpp#L38-L46). However, as everything is Thrift, it's easy to add required parameters per object or per task in Python, and use it in C++. The same goes the other way, i.e., if you want to get more data, e.g., speeds of the objects, you can add them to `TaskSimulation` in C++ and use in Python. Feel free to open an issue, if you need help with that.
