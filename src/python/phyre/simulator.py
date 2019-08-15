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

"""A thin wrapper around c++ simulator bindings to handle Thrift objects."""
import copy
import numpy as np
from thrift import TSerialization
from thrift.protocol import TBinaryProtocol

import phyre.interface.scene.ttypes as scene_if
import phyre.interface.task.ttypes as task_if
from phyre import creator
from phyre import simulator_bindings

DEFAULT_MAX_STEPS = simulator_bindings.DEFAULT_MAX_STEPS
STEPS_FOR_SOLUTION = simulator_bindings.STEPS_FOR_SOLUTION
DEFAULT_STRIDE = simulator_bindings.FPS

FACTORY = TBinaryProtocol.TBinaryProtocolAcceleratedFactory()


def serialize(obj):
    return TSerialization.serialize(obj, protocol_factory=FACTORY)


def deserialize(obj, pickle):
    return TSerialization.deserialize(obj, pickle, protocol_factory=FACTORY)


def build_user_input(points=None, rectangulars=None, balls=None):
    points, rectangulars, balls = _prepare_user_input(points, rectangulars,
                                                      balls)
    user_input = scene_if.UserInput(
        flattened_point_list=points.flatten().tolist(), balls=[], polygons=[])
    for start in range(0, len(rectangulars), 8):
        rect = rectangulars[start:start + 8]
        vertices = []
        for i in range(4):
            vertices.append(
                scene_if.Vector(rect[2 * i] - rect[0],
                                rect[2 * i + 1] - rect[1]))
        user_input.polygons.append(
            scene_if.PolygonWithPosition(
                vertices=vertices,
                position=scene_if.Vector(rect[0], rect[1]),
                angle=0,
            ))
    for start in range(0, len(balls), 3):
        ball = balls[start:start + 3]
        user_input.balls.append(
            scene_if.CircleWithPosition(
                position=scene_if.Vector(ball[0], ball[1]), radius=ball[2]))
    return user_input


def simulate_scene(scene, steps=DEFAULT_MAX_STEPS):
    serialized_scenes = simulator_bindings.simulate_scene(
        serialize(scene), steps)
    scenes = [deserialize(scene_if.Scene(), b) for b in serialized_scenes]
    return scenes


def simulate_task(task, steps=DEFAULT_MAX_STEPS, stride=DEFAULT_STRIDE):
    result = simulator_bindings.simulate_task(serialize(task), steps, stride)
    return deserialize(task_if.TaskSimulation(), result)


def check_for_occlusions(task, user_input, keep_space_around_bodies=True):
    """Returns true if user_input occludes scene objects."""
    if not isinstance(task, bytes):
        task = serialize(task)
    if isinstance(user_input, scene_if.UserInput):
        return simulator_bindings.check_for_occlusions_general(
            task, serialize(user_input), keep_space_around_bodies)
    else:
        points, rectangulars, balls = _prepare_user_input(*user_input)
        return simulator_bindings.check_for_occlusions(
            task, points, rectangulars, balls, keep_space_around_bodies)


def add_user_input_to_scene(scene, user_input, keep_space_around_bodies=True):
    """Converts user input to objects in the scene.

    Args:
        scene: scene_if.Scene.
        user_input: scene_if.UserInput or a triple (points, rectangulars, balls).
        keep_space_around_bodies: bool, if True extra empty space will be
            enforced around scene bodies.

    Returns:
        task_simulation: task_if.TaskSimulation.
    """
    if not isinstance(user_input, scene_if.UserInput):
        user_input = build_user_input(*user_input)

    return deserialize(
        scene_if.Scene(),
        simulator_bindings.add_user_input_to_scene(
            serialize(scene), serialize(user_input), keep_space_around_bodies))


def simulate_task_with_input(task,
                             user_input,
                             steps=DEFAULT_MAX_STEPS,
                             stride=DEFAULT_STRIDE,
                             keep_space_around_bodies=True):
    """Check a solution for a task and return SimulationResult.

    This is un-optimized version of magic_ponies that should be used for
    debugging or vizualization purposes only.
    """
    if not isinstance(user_input, scene_if.UserInput):
        user_input = build_user_input(*user_input)

    # Creating a shallow copy.
    task = copy.copy(task)
    task.scene = add_user_input_to_scene(task.scene, user_input,
                                         keep_space_around_bodies)
    return simulate_task(task, steps, stride)


def scene_to_raster(scene):
    """Convert scene to a integer array height x width containing color codes.
    """
    pixels = simulator_bindings.render(serialize(scene))
    return np.array(pixels).reshape((scene.height, scene.width))


def _deep_flatten(iterable):
    if isinstance(iterable, (tuple, list, np.ndarray)):
        for i in iterable:
            yield from _deep_flatten(i)
    else:
        yield iterable


def _prepare_user_input(points, rectangulars, balls):
    if points is None:
        points = np.empty([0], np.int32)
    elif isinstance(points, np.ndarray):
        assert points.dtype == np.int32, points.dtype
    else:
        points = np.array(points, np.int32)
    # Make sure the array always has shape (N, 2) even when N is 0.
    points = points.reshape((-1, 2))
    if rectangulars is None:
        rectangulars = []
    else:
        rectangulars = tuple(_deep_flatten(rectangulars))
        assert len(rectangulars) % 8 == 0
    if balls is None:
        balls = []
    else:
        balls = tuple(_deep_flatten(balls))
        assert len(balls) % 3 == 0
    return points, rectangulars, balls


def magic_ponies(task,
                 user_input,
                 steps=DEFAULT_MAX_STEPS,
                 stride=DEFAULT_STRIDE,
                 keep_space_around_bodies=True,
                 with_times=False):
    """Check a solution for a task and return intermidiate images.

    Args:
        task: task_if.Task or bytes, in the latter case a serialzed task is
            expected.
        user_input: scene_if.UserInput or a triple(points, rectangulars, balls)
            points: None or a list or an array of points. Should be of shape
                (N, 2). In the latter case is assumed to be in
                row-major format.
            rectangulars: A list of lists of 4 verticies. Each
                vertix should be a pair of floats. Vertices must be on positive
                order and must form a convex polygon. Otherwise the input
                will be deemed invalid.
            balls: A list of triples (x, y, radius).
        steps: Maximum number of steps to simulate for.
        stride: Stride for the returned image array. Negative values will
            produce not images.
        keep_space_around_bodies: bool, if True extra empty space will be
            enforced around scene bodies.
        with_times: A boolean flag indicating whether timing info is required.

    Returns:
        A tuple (is_solved, had_occlusions, images) if with_times is False.
            is_solved: bool.
            had_occlusions: bool.
            images a numpy arrays of shape (num_steps, height, width).
        A tuple (is_solved, had_occlusions, images, simulation_time, pack_time)
                if with_times is set.
            simulation_time: time spent inside C++ code to unpack and simulate.
            pack_time: time spent inside C++ code to pack the result.
    """
    if isinstance(task, bytes):
        serialized_task = task
        height, width = creator.SCENE_HEIGHT, creator.SCENE_WIDTH
    else:
        serialized_task = serialize(task)
        height, width = task.scene.height, task.scene.width

    if isinstance(user_input, scene_if.UserInput):
        is_solved, had_occlusions, packed_images, sim_time, pack_time = (
            simulator_bindings.magic_ponies_general(serialized_task,
                                                    serialize(user_input),
                                                    keep_space_around_bodies,
                                                    steps, stride))
    else:
        points, rectangulars, balls = _prepare_user_input(*user_input)
        is_solved, had_occlusions, packed_images, sim_time, pack_time = (
            simulator_bindings.magic_ponies(
                serialized_task, points, rectangulars, balls,
                keep_space_around_bodies, steps, stride))

    packed_images = np.array(packed_images, dtype=np.uint8)

    images = packed_images.reshape((-1, height, width))
    if with_times:
        return is_solved, had_occlusions, images, sim_time, pack_time
    else:
        return is_solved, had_occlusions, images


def batched_magic_ponies(tasks,
                         user_inputs,
                         num_workers,
                         steps=DEFAULT_MAX_STEPS,
                         stride=DEFAULT_STRIDE,
                         keep_space_around_bodies=True,
                         with_times=False):
    del num_workers  # Not used.
    return tuple(
        zip(*[
            magic_ponies(
                t,
                ui,
                steps=steps,
                stride=stride,
                keep_space_around_bodies=keep_space_around_bodies,
                with_times=with_times) for t, ui in zip(tasks, user_inputs)
        ]))
