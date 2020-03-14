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
"""Set of tools for visualizing observations and simulations.

"""
from typing import Optional, Tuple
import imageio
import numpy as np


def _hex_to_ints(hex_string):
    hex_string = hex_string.strip('#')
    return (
        int(hex_string[0:2], 16),
        int(hex_string[2:4], 16),
        int(hex_string[4:6], 16),
    )


WAD_COLORS = np.array(
    [
        [255, 255, 255],  # White.
        _hex_to_ints('f34f46'),  # Red.
        _hex_to_ints('6bcebb'),  # Green.
        _hex_to_ints('1877f2'),  # Blue.
        _hex_to_ints('4b4aa4'),  # Purple.
        _hex_to_ints('b9cad2'),  # Gray.
        [0, 0, 0],  # Black.
        _hex_to_ints('fcdfe3'),  # Light red.
    ],
    dtype=np.uint8)

SOLVE_STATUS_COLORS = np.array(
    [
        (121, 6, 4),  # Cherry.
        (11, 102, 35),  # Green.
    ],
    dtype=np.uint8)


def _to_float(img):
    return np.array(img, dtype=np.float) / 255.


def observations_to_float_rgb(scene: np.ndarray,
                              user_input: Tuple[Tuple[int, int], ...] = (),
                              is_solved: Optional[bool] = None) -> np.ndarray:
    """Convert an observation as returned by a simulator to an image."""
    return _to_float(observations_to_uint8_rgb(scene, user_input, is_solved))


def observations_to_uint8_rgb(scene: np.ndarray,
                              user_input: Tuple[Tuple[int, int], ...] = (),
                              is_solved: Optional[bool] = None) -> np.ndarray:
    """Convert an observation as returned by a simulator to an image."""
    base_image = WAD_COLORS[scene]
    for y, x in user_input:
        if 0 <= x < base_image.shape[1] and 0 <= y < base_image.shape[0]:
            base_image[x, y] = [255, 0, 0]
    base_image = base_image[::-1]
    if is_solved is not None:
        color = SOLVE_STATUS_COLORS[int(is_solved)]
        line = np.tile(color.reshape((1, 1, 3)), (5, base_image.shape[1], 1))
        line[:, :5] = WAD_COLORS[0]
        line[:, -5:] = WAD_COLORS[0]
        base_image = np.concatenate([line, base_image], 0)

    return base_image


def save_observation_series_to_gif(batched_observation_series,
                                   fpath,
                                   solved_states=None):
    """Saves a list of arrays of intermediate scenes as a gif."""
    max_steps = max(len(img) for img in batched_observation_series)
    images_per_step = []
    for step in range(max_steps):
        images_for_step = []
        for i, images in enumerate(batched_observation_series):
            real_step = min(len(images) - 1, step)
            if solved_states is None:
                solved = None
            else:
                solved = solved_states[i]
            images_for_step.append(
                observations_to_uint8_rgb(images[real_step], is_solved=solved))
        images_for_step = np.concatenate(images_for_step, axis=1)
        images_per_step.append(images_for_step)

    imageio.mimwrite(fpath, images_per_step, format="gif")


def compose_gifs_compact(input_fpathes, output_fpath):
    """Create progressin for first and last frames over time."""
    first_and_last_per_batch_id = []
    for fname in input_fpathes:
        data = imageio.mimread(fname)
        data = np.concatenate([data[0], data[-1]], axis=0)
        first_and_last_per_batch_id.append(data)
    if first_and_last_per_batch_id:
        imageio.mimwrite(output_fpath, first_and_last_per_batch_id)


def compose_gifs(input_fpathes, output_fpath):
    """Concatenate and sync all gifs."""
    all_data = []
    for fname in input_fpathes:
        all_data.append(imageio.mimread(fname))
    max_timestamps = max(len(data) for data in all_data)

    def _pad(data):
        return data + [data[-1]] * (max_timestamps - len(data))

    all_data = np.concatenate([_pad(data) for data in all_data], 1)
    imageio.mimwrite(output_fpath, all_data)
