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
"""Utilities to work with levels from Virtual Tools project.

https://arxiv.org/abs/1907.09620
"""
import collections
import json
import numpy as np

import phyre.creator as creator_lib
from phyre.creator import constants
import phyre.settings

VT_SCALE = 600.
PHYRE_SCALE = constants.SCENE_WIDTH


def _isleft(spt, ept, testpt):
    seg1 = (ept[0] - spt[0], ept[1] - spt[1])
    seg2 = (testpt[0] - spt[0], testpt[1] - spt[1])
    cross = seg1[0] * seg2[1] - seg1[1] * seg2[0]
    return cross > 0


def rotate(vec, angle):
    """Rotate the vector by angle_radians radians."""
    cos = np.cos(angle)
    sin = np.sin(angle)
    x = vec[0] * cos - vec[1] * sin
    y = vec[0] * sin + vec[1] * cos
    return np.array([x, y])


def segs2poly(seglist, r):
    vlist = [np.array(v) for v in seglist]
    # Start by figuring out the initial edge (ensure ccw winding)
    iseg = vlist[1] - vlist[0]
    ipt = vlist[0]
    iang = np.arctan2(iseg[1], iseg[0])
    if iang <= (-np.pi / 4.) and iang >= (-np.pi * 3. / 4.):
        # Going downwards
        prev1 = (ipt[0] - r, ipt[1])
        prev2 = (ipt[0] + r, ipt[1])
    elif iang >= (np.pi / 4.) and iang <= (np.pi * 3. / 4.):
        # Going upwards
        prev1 = (ipt[0] + r, ipt[1])
        prev2 = (ipt[0] - r, ipt[1])
    elif iang >= (-np.pi / 4.) and iang <= (np.pi / 4.):
        # Going rightwards
        prev1 = (ipt[0], ipt[1] - r)
        prev2 = (ipt[0], ipt[1] + r)
    else:
        # Going leftwards
        prev1 = (ipt[0], ipt[1] + r)
        prev2 = (ipt[0], ipt[1] - r)

    polylist = []
    for i in range(1, len(vlist) - 1):
        pi = vlist[i]
        pim = vlist[i - 1]
        pip = vlist[i + 1]
        sm = pim - pi
        sp = pip - pi
        # Get the angle of intersection between two lines
        angm = np.arctan2(sm[1], sm[0])  #.angle
        angp = np.arctan2(sp[1], sp[0])  #.angle
        angi = (angm - angp) % (2 * np.pi)
        # Find the midpoint of this angle and turn it back into a unit vector
        angn = (angp + (angi / 2.)) % (2 * np.pi)
        if angn < 0:
            angn += 2 * np.pi
        #unitn = np.array([1.0, 0.0])#pm.Vec2d.unit()
        unitn = np.array([np.cos(angn), np.sin(angn)])
        #unitn.angle = angn
        xdiff = r if unitn[0] >= 0 else -r
        ydiff = r if unitn[1] >= 0 else -r
        next3 = (pi[0] + xdiff, pi[1] + ydiff)
        next4 = (pi[0] - xdiff, pi[1] - ydiff)
        # Ensure appropriate winding -- next3 should be on the left of next4
        if _isleft(prev2, next3, next4):
            tmp = next4
            next4 = next3
            next3 = tmp
        curr_poly = [prev1, prev2, next3, next4]
        curr_poly.reverse()
        polylist.append(curr_poly)
        prev1 = next4
        prev2 = next3

    # Finish by figuring out the final edge
    fseg = vlist[-2] - vlist[-1]
    fpt = vlist[-1]
    fang = np.arctan2(fseg[1], fseg[0])  #.angle
    if fang <= (-np.pi / 4.) and fang >= (-np.pi * 3. / 4.):
        # Coming from downwards
        next3 = (fpt[0] - r, fpt[1])
        next4 = (fpt[0] + r, fpt[1])
    elif fang >= (np.pi / 4.) and fang <= (np.pi * 3. / 4.):
        # Coming from upwards
        next3 = (fpt[0] + r, fpt[1])
        next4 = (fpt[0] - r, fpt[1])
    elif fang >= (-np.pi / 4.) and fang <= (np.pi / 4.):
        # Coming from rightwards
        next3 = (fpt[0], fpt[1] - r)
        next4 = (fpt[0], fpt[1] + r)
    else:
        # Coming from leftwards
        next3 = (fpt[0], fpt[1] + r)
        next4 = (fpt[0], fpt[1] - r)
    curr_poly = [prev1, prev2, next3, next4]
    curr_poly.reverse()
    polylist.append(curr_poly)
    return polylist


def add_container(pgw,
                  points,
                  width,
                  dynamic,
                  goal_container=False,
                  flip_lr=False):
    ## Containers are described by sets of segments in Virtual Tools
    ## Convert to set of multipolygons for PHYRE
    ptlist = points
    r = width / 2
    polylist = segs2poly(ptlist, r)
    if flip_lr:
        polylist = flip_left_right(polylist)
    ## Since PHYRE does not allow "inside" relations, need to add an extra bar to the bottom
    ## of the container to mimic this behavior
    ## Assumes containers consist of 3 segments
    if goal_container:
        vertices = polylist[1]
        leftmost = min([v[0] for v in vertices])
        bottom = min([v[1] for v in vertices])
        rightmost = max([v[0] for v in vertices])
        top = max([v[1] for v in vertices])

        extra_poly = [[leftmost + width, bottom + width * 2],
                      [leftmost + width, top + width * 2],
                      [rightmost - width, top + width * 2],
                      [rightmost - width, bottom + width * 2]]
        extra_poly.reverse()
        bottom_bid = pgw.add_convex_polygon(
            convert_phyre_tools_vertices(extra_poly), False)
    else:
        bottom_bid = None

    ## Rescale coordinates appropriately
    converted_polylist = [
        convert_phyre_tools_vertices(poly) for poly in polylist
    ]
    bid = pgw.add_multipolygons(polygons=converted_polylist, dynamic=dynamic)

    return bottom_bid, bid


def convert_phyre_tools_vertices(verts_list):
    ## Rescale vertices to PHYRE coordinates
    all_verts = []
    for verts in verts_list:
        new_verts = tuple([v * PHYRE_SCALE / VT_SCALE for v in verts])
        all_verts.append(new_verts)
    return all_verts


def add_box(pgw, bbox, dynamic, flip_lr=False):
    ## Add box given by bounding box info
    verts = [[bbox[0], bbox[1]], [bbox[0], bbox[-1]], [bbox[2], bbox[-1]],
             [bbox[2], bbox[1]]]

    if flip_lr:
        verts = flip_left_right(verts)
    verts.reverse()
    bid = pgw.add_convex_polygon(convert_phyre_tools_vertices(verts), dynamic)
    return bid


def flip_left_right(coordinates, maxX=VT_SCALE):
    ##Flip scene around x

    ##Flip one number
    if type(coordinates) != list and type(coordinates) != tuple:
        return maxX - coordinates  #flip single float/integer

    ##Flip coordinates (x, y)
    if type(coordinates[0]) != list and type(coordinates[0]) != tuple:
        if type(coordinates) == tuple:
            return tuple([maxX - coordinates[0], coordinates[1]])
        else:
            return [maxX - coordinates[0], coordinates[1]]
    else:
        #Flip list of coordinates (x,y)
        if type(coordinates[0][0]) != list:
            all_coords = []
            for coords in coordinates:
                all_coords.append(flip_left_right(coords))
            all_coords.reverse()
            return all_coords
        else:
            #Flip list of list of coordinates (x,y)
            all_coords = []
            for coords in coordinates:
                all_coords.append(flip_left_right(coords))
            return all_coords


def translate_to_phyre(C, world_description):
    d = world_description
    pgw = C

    ## d is assumed to be a dictionary in Virtual Tools level format
    ## please
    gcond = d['gcond']
    all_ids = {}
    for nm, o in d['objects'].items():
        if nm[0] != '_':
            density = o['density']
            dynamic = density == 1.0
            if dynamic:
                add_str = "dynamic "
            else:
                add_str = "static "

            if o['type'] == 'Poly':
                vertices = o['vertices']
                vertices.reverse()
                bid = pgw.add_convex_polygon(
                    convert_phyre_tools_vertices(vertices), dynamic)

            elif o['type'] == 'Ball':
                add_str = add_str + 'ball '
                center_x = o['position'][0] * PHYRE_SCALE / VT_SCALE
                center_y = o['position'][1] * PHYRE_SCALE / VT_SCALE
                bid = pgw.add(add_str,
                              scale=o['radius'] * 2 / VT_SCALE,
                              center_x=center_x,
                              center_y=center_y)

            elif o['type'] == 'Container':
                bid, bbid = add_container(pgw,
                                          o['points'],
                                          o['width'],
                                          dynamic,
                                          goal_container=gcond['goal'] == nm)

            elif o['type'] == 'Compound':
                polys = o['polys']

                for p in polys:
                    p.reverse()

                converted_polylist = [
                    convert_phyre_tools_vertices(poly) for poly in polys
                ]
                bid = pgw.add_multipolygons(polygons=converted_polylist,
                                            dynamic=dynamic)

            elif o['type'] == 'Goal':
                vertices = o['vertices']
                vertices.reverse()
                bid = pgw.add_convex_polygon(
                    convert_phyre_tools_vertices(vertices), dynamic)
            else:
                raise Exception("Invalid object type for PHYRE given: ",
                                o['type'])
            all_ids[nm] = bid

    if gcond['type'] == 'SpecificInGoal' and gcond['goal'] != 'Floor' and gcond[
            'goal'] != 'Ground':
        container_id = all_ids[gcond['goal']]
        pgw.update_task(body1=all_ids[gcond['obj']],
                        body2=container_id,
                        relationships=[pgw.SpatialRelationship.TOUCHING])

    elif gcond['type'] == 'SpecificTouch' or (
            gcond['type'] == 'SpecificInGoal' and
        (gcond['goal'] == 'Floor' or gcond['goal'] == 'Ground')):
        pgw.update_task(body1=all_ids[gcond['obj']],
                        body2=all_ids[gcond['goal']],
                        relationships=[pgw.SpatialRelationship.TOUCHING])
    else:
        raise Exception("Invalid goal type for PHYRE given: ", gcond['type'])
    return pgw


def convert_all_tasks(task_prefix="01"):
    whitelistes_tasks = (
        "Basic",
        "Bridge",
        "Catapult",
        "Falling_A",
        "Gap",
        "Launch_A",
        "Launch_B",
        "Prevention_A",
        "Prevention_B",
        "SeeSaw",
        "Table_A",
        "Table_B",
        "Unbox",
    )
    tasks = collections.OrderedDict()
    for i, name in enumerate(whitelistes_tasks):
        json_path = phyre.settings.VIRTUAL_TOOLS_DIR / "Original" / f"{name}.json"
        with json_path.open() as stream:
            description = json.load(stream)
        task_creator = translate_to_phyre(creator_lib.creator.TaskCreator(),
                                          description["world"])
        task = task_creator.task
        task.taskId = f"{task_prefix}{i:03d}:000"
        task.tier = constants.SolutionTier.VIRTUAL_TOOLS.name
        tasks[task.taskId] = task
    return tasks
