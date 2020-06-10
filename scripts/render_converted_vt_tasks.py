import os
from phyre.simulator import scene_to_raster
import phyre.virtual_tools as vt_converter
import json
import phyre
import phyre.settings
import matplotlib.pyplot as plt

PHYRE_SCALE = vt_converter.PHYRE_SCALE
VT_SCALE = vt_converter.VT_SCALE
if __name__ == '__main__':

    actions = {'Basic':[60, 500, 50], 'Bridge':[300, 50, 40],
    'Catapult':[400, 500, 30], 'Falling_A':[310, 200, 20], 'Gap':[350, 150, 40],
    'Launch_A':[100, 540, 50], 'Launch_B':[70, 540, 30], 'Prevention_A':[475, 355, 30],
    'Prevention_B':[475, 355, 30], 'SeeSaw':[320, 45, 35], 'Table_A':[405, 35, 30],
    'Table_B':[310, 55, 40], 'Unbox':[530, 500, 50]}#'Towers_B':[230, 550, 40], 'Towers_A':[325, 550, 40], 
    json_dir = str(VIRTUAL_TOOLS_DIR / 'Original/')
    if not os.path.exists('/phyre_images/'):
        os.makedirs('/phyre_images/')
    for tnm in actions.keys():
        print(tnm)
        with open(os.path.join(json_dir, tnm+'.json'),'r') as f:
            btr = json.load(f)

        pgw = vt_converter.translateToPhyre(btr['world'])
        if tnm in actions.keys():
            pgw.add('dynamic ball', scale=actions[tnm][-1]*2/VT_SCALE,
                center_x=actions[tnm][0]*PHYRE_SCALE/VT_SCALE, center_y=actions[tnm][1]*PHYRE_SCALE/VT_SCALE)

        raw_sc = phyre.simulator.simulate_scene(pgw.scene)
        sc = raw_sc[::100]
        print('finished simulation, ', len(sc), ' timesteps')
        fig, axs = plt.subplots( 2, len(sc)//2, figsize=(20, 10))
        fig.tight_layout()
        plt.subplots_adjust(hspace=0.2, wspace=0.2)
        for i, (ax, s) in enumerate(zip(axs.flatten(), sc)):
            img = scene_to_raster(s)
            ax.title.set_text(f'Timestep {i}')
            good_img = phyre.observations_to_float_rgb(img)
            ax.imshow(good_img)
        plt.savefig('/phyre_images/'+tnm+'_dynamic_action.png')
        plt.close()