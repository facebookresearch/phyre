// Copyright (c) Facebook, Inc. and its affiliates.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import React, { Component } from 'react';
import Konva from "konva";
import { Stage, Layer, Circle, Shape } from 'react-konva';

export const RESOLUTION = 2;
const DRAW_COLOR = window.Color.LIGHT_RED;

const MIN_RADIUS = 5;
const DEFAULT_RADIUS = 10;

export const DrawMode = {
  FREE: 'Free',
  BALL: 'Ball',
};

function getColor(thrift_color) {
  let kColorMap = {};
  kColorMap[window.Color.WHITE] = "white";
  kColorMap[window.Color.BLACK] = "black";
  kColorMap[window.Color.GRAY] = "#b9cad2";

  kColorMap[window.Color.RED] = "#f34f46";
  kColorMap[window.Color.GREEN] = "#6bcebb";
  kColorMap[window.Color.BLUE] = "#1877f2";
  kColorMap[window.Color.PURPLE] = "#4b4aa4";
  kColorMap[window.Color.LIGHT_RED] = "#fcdfe3";
  return kColorMap[thrift_color];
}

class Polygon extends Component {
  render() {
    const vertices = this.props.vertices;
    const base_point = this.props.base_point;
    const angle = this.props.angle;
    return (
      <Shape
        fill={this.props.fill}
        sceneFunc={function (ctx) {
          ctx.translate(base_point.x, base_point.y);
          ctx.rotate(angle);
          ctx.beginPath();
          for (let i in vertices) {
            if (i === 0) {
              ctx.moveTo(vertices[0].x, vertices[0].y);
            } else {
              ctx.lineTo(vertices[i].x, vertices[i].y);
            }
          }
          ctx.closePath();
          // Konva specific method
          ctx.fillStrokeShape(this);
        }}
      />
    );
  }
}


function buildBodyShapes(body, step) {
  let shape_objects = [];
  for (let i = 0; body.shapes && i < body.shapes.length; ++i) {
    const shape = body.shapes[i];
    const fill = getColor(body.color);
    const key = step + "_" + i;
    if (shape.polygon) {
      shape_objects.push(<Polygon
        key={key}
        fill={fill}
        angle={body.angle}
        base_point={body.position}
        vertices={shape.polygon.vertices} />);
    } else if (shape.circle) {
      shape_objects.push(<Circle
        key={key}
        fill={fill}
        radius={shape.circle.radius}
        x={body.position.x}
        y={body.position.y} />);
    } else {
      console.error("Unknown shape", body, shape);
    }
  }
  return shape_objects;
}

function buildUserInputShapes(polygons, balls) {
  let shape_objects = [];
  for (let i in polygons) {
    const key = "user_input_poly" + i;
    shape_objects.push(<Polygon
      key={key}
      fill={getColor(DRAW_COLOR)}
      angle={0}
      base_point={{x: 0, y: 0}}
      vertices={polygons[i].vertices} />);
  }
  for (let i in balls) {
    const key = "user_input_ball" + i;
    shape_objects.push(<Circle
      key={key}
      fill={getColor(DRAW_COLOR)}
      radius={balls[i].radius}
      x={balls[i].position.x}
      y={balls[i].position.y} />);
  }
  return shape_objects;
}

var UserInput = {
  MAX_X: 10000,

  encode: function(pos) {
    return (
      Math.floor(pos.x / RESOLUTION)
      + Math.floor(pos.y / RESOLUTION) * this.MAX_X);
  },

  decode: function(code) {
    return {
      x: code % this.MAX_X,
      y: Math.floor(code / this.MAX_X)};
  }
};


export class Canvas extends Component {

  constructor(props) {
    super(props);
    this.state = {user_balls: [], user_polygons: []};
  }

  componentDidMount() {
    let stage = this.refs.stage.getStage();
    let layer = this.refs.user_input_layer;
    // Whether mouse is pressed.
    var is_paint = false;
    // Where the mouse was pressed down.
    var first_click;
    // Where the mouse was pressed last time.
    var last_click;
    // Object to alter in BALL mode.
    var active_object_id = -1;
    var active_object_offset;
    var object_resizing = false;
    var resize_ratio = 1;
    // What kind of drawing actions to track.
    var draw_mode = DrawMode.BALL;

    var canvas = document.createElement('canvas');
    canvas.width = stage.width();
    canvas.height = stage.height();
    var image = new Konva.Image({
        image: canvas,
        x : 0,
        y : 0,
    });
    layer.add(image);
    stage.draw();
    var context = canvas.getContext('2d');
    // Configure free drawing.
    context.strokeStyle = getColor(DRAW_COLOR);
    context.lineJoin = "round";
    context.lineWidth = 7;

    const toCanvasCoord = function(point) {
      // Convert canvas coordinates to scene coordinates.
      const x = point.x * RESOLUTION;
      const y = (Math.floor(stage.height() / RESOLUTION) - 1 - point.y) * RESOLUTION;
      return {x: x, y: y};
    }

    const toRealCoord = function(point) {
      // Convert scene coordinates to canvas coordinates.
      const x = point.x / RESOLUTION;
      const y = Math.floor(stage.height() /RESOLUTION) - (point.y / RESOLUTION + 1);
      return {x: x, y: y};
    }

    const computeLength = function(x, y) {
      return Math.sqrt(x * x + y * y);
    }

    const computeDistance = function(point1, point2) {
      return computeLength(point1.x - point2.x, point1.y - point2.y);
    }

    const isInside = function(ball, point) {
      return computeDistance(ball.position, point) <= ball.radius;
    }

    this.getImageData = function() {
      // Get a mask with user-filled pixels.
      return context.getImageData(0, 0, stage.width(), stage.height());
    };

    this.setUserInput = function(user_input) {
      // Initialize from a UserInput object.
      const flat_points = user_input.flattened_point_list;
      let points = [];
      for (let i = 0; i < flat_points.length; i += 2) {
        points.push(toCanvasCoord({x: flat_points[i], y: flat_points[i + 1]}));
      }

      context.globalCompositeOperation = 'source-over';
      for (let i in points) {
        context.fillStyle = getColor(DRAW_COLOR);
        context.fillRect(
          points[i].x,
          points[i].y,
          RESOLUTION,
          RESOLUTION);
      }
      layer.draw();
      console.log("Loaded " + points.length + " points, ",
        user_input.polygons.length + " polygons and " + user_input.balls.length
        + " balls.");
      this.setState({
        user_polygons: user_input.polygons,
        user_balls: user_input.balls},
        () => this.props.onUserInputChanged(),
        )
    }

    this.cleanUserInput = function() {
      this.setUserInput({flattened_point_list: [], polygons: [], balls: []});
    }

    this.setDrawMode = function(new_draw_mode) {
      draw_mode = new_draw_mode;
    }

    this.addRenderedImage = function(image) {
      // Draw a fixed image on the canvas.
      context.globalCompositeOperation = 'source-over';
      var idx = 0;
      for (var y = 0; y < image.height; ++y) {
        for (var x = 0; x < image.width; ++x) {
          const value = image.values[idx];
          ++idx;
          if (value) {
            const canvas_point = toCanvasCoord({x: x, y: y});
            context.fillStyle = getColor(value);
            context.fillRect(
              canvas_point.x,
              canvas_point.y,
              RESOLUTION,
              RESOLUTION);
          }
        }
      }
      layer.draw();
    }

    stage.on('contentMousedown.proto', function(e) {
      if (this.props.allow_drawing){
        is_paint = true;
        first_click = stage.getPointerPosition();
        last_click = first_click;
        if (draw_mode === DrawMode.BALL) {
          // Create a ball at the start position.
          const first_click_real = toRealCoord(first_click);
          active_object_id = -1;
          for (let i in this.state.user_balls) {
            if (isInside(this.state.user_balls[i], first_click_real)) {
              active_object_id = i;
              break;
            }
          }
          if (e.evt.metaKey) {
            // Delete mode.
            if (active_object_id !== -1) {
              let new_user_balls = [];
              for (let i in this.state.user_balls) {
                if (i !== active_object_id) {
                  new_user_balls.push(this.state.user_balls[i])
                }
              }
              this.setState({user_balls: new_user_balls})
            }
            active_object_id = -1;
            return;
          }
          if (e.evt.shiftKey) {
            // Resize mode.
            if (active_object_id !== -1) {
              const active_object = this.state.user_balls[active_object_id];
              object_resizing = true;
              const distance = computeDistance(first_click_real, active_object.position);
              resize_ratio = Math.max(0.5, distance / active_object.radius);
            }
            return;
          }
          let active_object;
          if (active_object_id === -1) {
            active_object = new window.CircleWithPosition({
              position: new window.Vector(first_click_real),
              radius: DEFAULT_RADIUS,
            });
            let new_user_balls = this.state.user_balls.slice(0);
            new_user_balls.push(active_object);
            const max_balls = window.phyre_config.max_balls;
            if (max_balls && new_user_balls.length > max_balls) {
              // Drop first ball to maintain max size.
              new_user_balls.shift();
            }
            active_object_id = new_user_balls.length - 1;
            this.setState({user_balls: new_user_balls})
            active_object_offset = {x: 0, y: 0};
          } else {
            active_object = this.state.user_balls[active_object_id];
          }
          // Saving first_click as if user clicked at the center of the ball.
          active_object_offset = {
            x: first_click_real.x - active_object.position.x,
            y: first_click_real.y - active_object.position.y
          };
          this.props.onUserInputChanged();
        }
      }
    }.bind(this));

    let stopDrawing = function () {
        is_paint = false;
        active_object_id = -1;
        object_resizing = false;
    };

    stage.on('contentMouseup.proto', stopDrawing);

    stage.on('contentMouseout.proto', stopDrawing);

    stage.on('contentMousemove.proto', function(e) {
      if (!this.props.allow_drawing) return;
      if (draw_mode === DrawMode.FREE) {
        if (!is_paint) return;
        const pos = stage.getPointerPosition();
        if (e.evt.metaKey) {
          context.globalCompositeOperation = 'destination-out';
        } else {
          context.globalCompositeOperation = 'source-over';
        }
        context.beginPath();
        context.moveTo(last_click.x, last_click.y);
        context.lineTo(pos.x, pos.y);
        context.closePath();
        context.stroke();
        last_click = pos;
      } else {
        if (active_object_id !== -1) {
          let pos = toRealCoord(stage.getPointerPosition());
          let new_user_balls = this.state.user_balls.slice(0);
          if (object_resizing) {
            const active_object = new_user_balls[active_object_id]
            active_object.radius = Math.max(
              MIN_RADIUS, computeDistance(active_object.position, pos) / resize_ratio);
          } else {
            pos.x -= active_object_offset.x;
            pos.y -= active_object_offset.y;

            new_user_balls[active_object_id].position.x = pos.x;
            new_user_balls[active_object_id].position.y = pos.y;
          }
          this.setState({user_balls: new_user_balls})
        }
      }
      layer.draw();
    }.bind(this));
  }

  getUserInput() {
    const image_data = this.getImageData();
    let user_input_map = {};
    var offset = 0;
    for (var y = 0; y < image_data.height; ++y) {
      for (var x = 0; x < image_data.width; ++x) {
        const value = image_data.data[offset + 3];
        if (value > 57) {
          user_input_map[UserInput.encode({x: x, y: image_data.height - 1 - y})] = 1;
        }
        offset += 4;  // RGBA
      }
    }
    let flat_user_points = [];
    for (var code in user_input_map) {
      const point = UserInput.decode(code);
      flat_user_points.push(point.x);
      flat_user_points.push(point.y);
    }
    const user_input = new window.UserInput({
      flattened_point_list: flat_user_points,
      polygons: this.state.user_polygons,
      balls: this.state.user_balls});
    return user_input;
  }

  render() {
    const bodies = this.props.scene.bodies;
    const user_input_bodies = this.props.scene.user_input_bodies;
    if (!bodies) {
      return <div>World is empty!</div>
    }
    let shapes = [];
    {
      let body_shapes = buildUserInputShapes(
        this.state.user_polygons, this.state.user_balls);
      for (let j = 0; j < body_shapes.length; ++j) {
        shapes.push(body_shapes[j]);
      }
    }
    const all_bodies = bodies.concat(user_input_bodies ? user_input_bodies : []);
    for (let i = 0; i < all_bodies.length; ++i) {
      let body_shapes = buildBodyShapes(all_bodies[i], i);
      for (let j = 0; j < body_shapes.length; ++j) {
        shapes.push(body_shapes[j]);
      }
    }
    const scale = this.props.scale || RESOLUTION;
    return (
      <Stage ref="stage" width={this.props.width * scale} height={this.props.height * scale}>
        <Layer ref="user_input_layer" />
        <Layer ref="scene_layer" offsetY={this.props.height} scaleY={-1 * scale} scaleX={scale}>
          {shapes}
        </Layer>
      </Stage>
    );
  }
}
