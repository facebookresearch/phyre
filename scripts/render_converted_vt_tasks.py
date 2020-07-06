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
import json
import os

import matplotlib.pyplot as plt

import phyre
import phyre.creator as creator_lib
import phyre.settings
import phyre.simulator
import phyre.virtual_tools as vt_converter

PHYRE_SCALE = vt_converter.PHYRE_SCALE
VT_SCALE = vt_converter.VT_SCALE

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("dst", help="Where to save images for each level")
    dst_dir = parser.parse_args().dst

    actions = {
        'Basic': [60, 500, 50],
        'Bridge': [300, 50, 40],
        'Catapult': [400, 500, 30],
        'Falling_A': [310, 200, 20],
        'Gap': [350, 150, 40],
        'Launch_A': [100, 540, 50],
        'Launch_B': [70, 540, 30],
        'Prevention_A': [475, 355, 30],
        'Prevention_B': [475, 355, 30],
        'SeeSaw': [320, 45, 35],
        'Table_A': [405, 35, 30],
        'Table_B': [310, 55, 40],
        'Unbox': [530, 500, 50]
    }  #'Towers_B':[230, 550, 40], 'Towers_A':[325, 550, 40],
    json_dir = str(phyre.settings.VIRTUAL_TOOLS_DIR / 'Original/')
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    for tnm in actions.keys():
        print(tnm)
        with open(os.path.join(json_dir, tnm + '.json'), 'r') as f:
            btr = json.load(f)

        pgw = vt_converter.translate_to_phyre(creator_lib.creator.TaskCreator(),
                                              btr['world'])
        if tnm in actions.keys():
            pgw.add('dynamic ball',
                    scale=actions[tnm][-1] * 2 / VT_SCALE,
                    center_x=actions[tnm][0] * PHYRE_SCALE / VT_SCALE,
                    center_y=actions[tnm][1] * PHYRE_SCALE / VT_SCALE)

        raw_sc = phyre.simulator.simulate_scene(pgw.scene)
        sc = raw_sc[::100]
        print('finished simulation, ', len(sc), ' timesteps')
        fig, axs = plt.subplots(2, len(sc) // 2, figsize=(20, 10))
        fig.tight_layout()
        plt.subplots_adjust(hspace=0.2, wspace=0.2)
        for i, (ax, s) in enumerate(zip(axs.flatten(), sc)):
            img = phyre.simulator.scene_to_raster(s)
            ax.title.set_text(f'Timestep {i}')
            good_img = phyre.observations_to_float_rgb(img)
            ax.imshow(good_img)
        plt.savefig(dst_dir + '/' + tnm + '_dynamic_action.png')
        plt.close()