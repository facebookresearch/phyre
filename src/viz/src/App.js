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
import { Button, Message } from 'semantic-ui-react';
import { Dimmer, Divider, Loader, Header, Segment, Label } from 'semantic-ui-react';
import { Canvas, RESOLUTION, DrawMode } from './canvas';
import './App.css';

let cache = {};


function getRpcUrl() {
  let base;
  if (window.location.port === '3000') {
    // Poor man dev mode detection.
    base = 'http://localhost:30303';
  } else {
    base = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port;
  }
  return base + '/rpc';
}

function trim(task_id) {
  if (!task_id) return task_id;
  return task_id.replace(/:$/, '');
}

function getClient(name) {
  const transport = new window.Thrift.TXHRTransport(getRpcUrl() + '/' + name);
  const protocol = new window.Thrift.TJSONProtocol(transport);
  const client = new window.TaskServiceClient(protocol);
  return client[name].bind(client);
}

function cachedThriftCall(name, arg, callback) {
  const key = name + '__' + String(arg);
  if (cache[key]) {
    return callback(cache[key]);
  } else {
    function callback_wrapper(result) {
      cache[key] = result;
      callback(result);
    }
    console.log('call', name, arg)
    getClient(name)(arg, callback_wrapper);
  }
}


function ifdev(button, alternative) {
  if (!alternative) {
    alternative = "";
  }
  return window.phyre_config.mode === 'dev' ? button : alternative;
}

function ifproddev(button, alternative) {
  if (!alternative) {
    alternative = "";
  }
  return window.phyre_config.mode === 'dev' || window.phyre_config.mode === 'prod' ? button : alternative;
}

 function getStateForUrl() {
    const pieces = window.location.hash.split('/');
    let template_id = null;
    let task_index = null;
    if (pieces.length === 3 && pieces[1] === 'task') {
      const task_id = pieces[2];
      const task_pieces = task_id.split(":");
      template_id = task_pieces[0];
      if (task_pieces.length === 2 && task_pieces[1]) {
        task_index = task_pieces[1];
      }
    }
    return {tempate_id: template_id, task_index: task_index};
  }

function setTitle() {
  function detectTitle() {
    const state = getStateForUrl();
    if (state.task_index) return 'PHYRE - Task ' + state.tempate_id + ':' + state.task_index;
    if (state.tempate_id) return 'PHYRE - Template ' + state.tempate_id;
    return 'PHYRE Player';
  }
  document.title = detectTitle();
}

function navigate(new_hash) {
  window.history.pushState(null, null, new_hash);
  setTitle();
}

function filterTaskIds(all_task_ids, task_id_prefix) {
  // Get a list a task_ids filtered by state.task_id_prefix.
  let task_ids = [];
  for (let i in all_task_ids) {
    const task_id = all_task_ids[i];
    if (!task_id.startsWith(task_id_prefix)) {
      continue;
    }
    if (task_id.includes(':') && !task_id_prefix) {
      const task_id_short = task_id.replace(/:.*/, ':');
      if (task_ids.length === 0 || task_ids[task_ids.length - 1] !== task_id_short) {
        task_ids.push(task_id_short)
      }
    } else {
      task_ids.push(task_id);
    }
  }
  return task_ids;
}

class ThumbBlock extends Component {
  constructor(props) {
    super(props);
    this.state = {scenes_for_thumbs: {}};
  }

  componentDidMount() {
    this.reload();
  }

  reload(task_ids, quazi_task_id_to_task_id) {
    if (!task_ids) {
      task_ids = this.props.task_ids;
    }
    if (!quazi_task_id_to_task_id) {
      quazi_task_id_to_task_id = this.props.quazi_task_id_to_task_id;
    }
    this.setState({last_task_set: task_ids});
    let selected_img_task_ids = [];
    let selected_task_ids = [];

    for (let i in task_ids) {
      const task_id = task_ids[i];
      const img_task_id = quazi_task_id_to_task_id[task_id];
      if(this.state.scenes_for_thumbs[task_id]) {
         continue;
      }
      selected_img_task_ids.push(img_task_id);
      selected_task_ids.push(task_id);
    }
    cachedThriftCall('get_task_thumbs', selected_img_task_ids, (tasks) => {
      if (!this.maybeReportThriftError(tasks)) {
        this.setState(prevState => {
          let newState = Object.assign({}, prevState);
          newState.scenes_for_thumbs = Object.assign({}, newState.scenes_for_thumbs);
          for (let i in selected_task_ids) {
            newState.scenes_for_thumbs[selected_task_ids[i]] = tasks[i];
          }
          return newState;
        });
      }
    });
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.task_ids !== this.state.last_task_set) {
      this.reload(nextProps.task_ids, nextProps.quazi_task_id_to_task_id);
    }
  }

  onTaskSelectorClick(task_id) {
    return this.props.onTaskSelectorClick(task_id);
  }

  maybeReportThriftError(maybe_exception) {
    return this.props.maybeReportThriftError(maybe_exception);
  }

  renderThumbCanvas(task_id) {
    if (!this.state.scenes_for_thumbs[task_id]) {
      return <Dimmer active> <Loader /> </Dimmer>
    }
    const img = this.state.scenes_for_thumbs[task_id].img;
    return <img alt={"Task: " + task_id} src={"data:image/png;base64," + img} />
  }

  formatEvalData(task_id) {
    if (window.phyre_config.mode === 'demo') {
      return "";
    }
    if (!this.props.evaluation_data[task_id]) {
      return "no eval data";
    }
    const data = this.props.evaluation_data[task_id];
    if (data.percent_ball != null) {
      return (
        "B:" + data.percent_ball + "%"
        + " 2B:" + data.percent_two_balls + "%"
        + ifdev(" R:" + data.percent_ramp + "%")
      );
    } else {
      return (
        "B" + ifdev("(" + data.flag_ball + ")") + ":" + data.attempts_to_solve_ball
        + " 2B" + ifdev("(" + data.flag_two_balls + ")") + ":" + data.attempts_to_solve_two_balls
        + ifdev(" R(" + data.flag_ramp + "):" + data.attempts_to_solve_ramp)
      );
    }
  }

  numTasks(task_id) {
    if (!task_id.endsWith(':')) {
      return "";
    }
    if (!this.props.evaluation_data[task_id]) {
      return "?";
    }
    return '+' + this.props.evaluation_data[task_id].num_tasks;
  }

  render() {
    let thumbs = this.props.task_ids.map((task_id) =>
      <div onClick={() => this.onTaskSelectorClick(task_id)} className="ThumbCanvas" key={task_id}>
        {this.renderThumbCanvas(task_id)}
        <div className="ThumbCanvasCaption"><span className='TaskName'>
            {ifproddev("", "Task ")}
            {trim(task_id)}
          </span>
          {ifproddev(this.numTasks(task_id))}
          <div className="ThumbEvalData">{this.formatEvalData(task_id)}</div>
          <div className="ThumbCanvasCaptionExtra">
            {ifdev(this.state.scenes_for_thumbs[task_id] && this.state.scenes_for_thumbs[task_id].extra)}
          </div>
        </div>
      </div>);
    return <div className="ThumbWrapper">
      {this.props.caption ? <Divider horizontal><Header as='h3'>{this.props.caption}</Header>
        {this.props.subcaption ? <Header as='h4'>{this.props.subcaption}</Header>: ""}
      </Divider> : ""}
      {thumbs}
    </div>
  }
}

class WorldWithControls extends Component {
  constructor(props) {
    super(props);
    this.state = this.getZeroState();
  }

  getZeroState() {
    return {
      task_id_prefix: "",
      error: null,
      task_ids: null,
      interval: null,
      evaluation_data: null,
     };
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.template_id !== this.props.template_id) {
      this.reset(nextProps.template_id);
    }
  }

  reset(new_template_id) {
    const template_id = new_template_id === undefined ? this.props.template_id : new_template_id;
    let zero_state = this.getZeroState();
    if (template_id) {
      zero_state['task_id_prefix'] = template_id + ":";
    }
    this.setState(zero_state);
    cachedThriftCall('list_task_tier_map', template_id, (task_id_to_tier) => {
      if (!this.maybeReportThriftError(task_id_to_tier)) {
        let task_ids = [];
        let quazi_task_id_to_task_id = {};
        let num_teasks_in_tempalte = {};
        for (let task_id in task_id_to_tier) {
          quazi_task_id_to_task_id[task_id] = task_id;
          const template_id = task_id.split(':')[0] + ':';
          if (!quazi_task_id_to_task_id[template_id]) {
            quazi_task_id_to_task_id[template_id] = task_id;
          }
          if (!num_teasks_in_tempalte[template_id]) {
            num_teasks_in_tempalte[template_id] = 0;
          }
          num_teasks_in_tempalte[template_id]++;
          task_ids.push(task_id);
        }
        this.setState(prevState => ({
                task_ids: task_ids,
                task_id_to_tier: task_id_to_tier,
                num_teasks_in_tempalte: num_teasks_in_tempalte,
                quazi_task_id_to_task_id: quazi_task_id_to_task_id
        }), ()=> {
          if (this.state.scenes_for_thumbs != null) {
            this.onLoadTaskThumbsClick();
          }
        });
      }
    });
    if (window.phyre_config.mode === 'demo') {
      this.setState({evaluation_data: {}});
    } else {
      cachedThriftCall('load_evaluation_data', template_id || "", (evaluation_data) => {
        if (!this.maybeReportThriftError(evaluation_data)) {
          console.log(template_id, evaluation_data);
          this.setState({evaluation_data: evaluation_data});
        }
      });
    }
  }

  componentDidMount() {
    this.reset();
    if (this.props.template_id) {
      this.onTaskSelectorClick(this.props.template_id + ':');
    }
  }

  maybeReportThriftError(maybe_exception) {
    if (maybe_exception.message) {
        this.setState(prevState => ({error: maybe_exception.message}));
        return true;
    }
    return false;
  }

  onTaskSelectorClick(task_id) {
    const target_hash = '#/task/' + task_id;
    navigate(target_hash);
    this.props.setStateForUrl();
  }

  getTaskIds() {
    return filterTaskIds(this.state.task_ids, this.state.task_id_prefix);
  }

  getTaskIdsPerTier() {
    const task_ids = this.getTaskIds();
    let task_ids_per_tier = {};
    for (let i in task_ids) {
      const task_id = task_ids[i];
      const tier = this.state.task_id_to_tier[this.state.quazi_task_id_to_task_id[task_id]];
      if (!task_ids_per_tier[tier]) {
        task_ids_per_tier[tier] = [];
      }
      task_ids_per_tier[tier].push(task_id);
    }
    return task_ids_per_tier;
  }

  renderLoadingStatus(text) {
    return <Segment><Dimmer active><Loader content={text} /></Dimmer></Segment>;
  }

  renderStatus() {
    if (this.state.error) {
      return <div><h2>Thrift service return error message</h2><h3>{this.state.error}</h3></div>;
    }
    if (this.state.task_ids === null || this.state.evaluation_data === null) {
      return this.renderLoadingStatus("Loading tasks...");
    }
    let tier_to_tasks = this.getTaskIdsPerTier();
    let tier_rank = function(tier_name) {
      if (tier_name === 'BALL') return '0' + tier_name;
      if (tier_name === 'TWO_BALLS') return '1' + tier_name;
      if (tier_name === 'RAMP') return '2' + tier_name;
      if (tier_name.startsWith('PRE_')) return '5' + tier_name;
      return '9' + tier_name;
    }
    let tier_cmp = function(a, b) { return tier_rank(a) < tier_rank(b) ? -1 : 1; }
    let blocks = Object.keys(tier_to_tasks).sort(tier_cmp).map((tier) => {
      const caption = this.state.task_id_prefix
        ? "Tasks in task template " + trim(this.state.task_id_prefix)
        : "Tier: " + tier;
      const subcaption = this.state.task_id_prefix ? "" : {
        BALL: 'Tasks in this tier can be solved with a single ball.',
        TWO_BALLS: 'Tasks in this tier can be solved with two balls.',
      }[tier]
      return <ThumbBlock
          key={tier}
          caption={caption}
          subcaption={subcaption}
          task_ids={tier_to_tasks[tier]}
          quazi_task_id_to_task_id={this.state.quazi_task_id_to_task_id}
          num_teasks_in_tempalte={this.state.num_teasks_in_tempalte}
          evaluation_data={this.state.evaluation_data}
          maybeReportThriftError={this.maybeReportThriftError.bind(this)}
          onTaskSelectorClick={this.onTaskSelectorClick.bind(this)}
        />;
    });
    return <div>{blocks}</div>;
  }

  renderHeader() {
    if (window.phyre_config.mode !== 'demo') {
      return "";
    }
    if (this.state.task_id_prefix.endsWith(':')) {
      return <Message className='dataset_info'>
      <p>
        Below are 100 modifications of a single task. These minor
        modifications let us benchmark a weak form of "within-template"
        generalization as opposed to a more challenging "cross-template"
        generalization.
        See{" "}
        <a href="https://research.fb.com/publications/phyre-a-new-benchmark-for-physical-reasoning/">the paper</a>
        {" "}for details.
        </p>
      <p>
        Click any task to try to solve or see a pre-computed solution.
      </p>
    </Message>
    }
    return <Message className='dataset_info'>
      <b><a href="http://phyre.ai">PHYRE</a></b> is a benchmark for physical reasoning.
      <p>
      It
      consists of physical-reasoning tasks that an agent has to solve by performing
      an action. The tasks are seperated into two tiers by the kind of action
      needed. Each tier has 25 task templates and each template has 100 tasks.
      Click on a task template below to see the tasks and try to solve the
      them. See <a href="https://github.com/facebookresearch/phyre">our repository</a> for details.
      </p>
    </Message>
  }

  render() {
    return <div>
      {this.renderHeader()}
      <div className="World-status">{this.renderStatus()}</div>
    </div>;
  }
}

class Teaser extends Component {
  constructor(props) {
    super(props);
    this.state = {show: false};
  }

  render() {
    if (!this.state.show) {
      return <span style={{cursor:"pointer"}} onClick={() => this.setState({show: true})}>
        <b>{this.props.caption}</b>
        (click to see)
      </span>;
    } else {
      return <div>
        <b>{this.props.caption}: </b>
        {this.props.text}
      </div>;
    }
  }
}

class TaskView extends Component {
  constructor(props) {
    super(props);
    this.state = this.getZeroState();
  }

  componentDidMount() {
    this.reloadLevel();
  }

  componentWillUnmount() {
    if (this.state.interval) {
      window.clearInterval(this.state.interval);
    }
  }

  getZeroState() {
    return {
      task_id: this.props.task_id,
      draw_mode: DrawMode.BALL,
      simulation_requested: false,
      has_user_input: false,
      meta_task: null,
      error: null,
      task_ids: null,
      interval: null,
      task_simulation: null,
      rendered_imgs: null,
      show_user_input_buttons: true,
     };
  }

  reloadLevel() {
    if (this.state.interval) {
      window.clearInterval(this.state.interval);
    }
    this.setState(this.getZeroState());

    getClient('get_task_from_id')(this.props.task_id, meta_task => {
      if (!this.maybeReportThriftError(meta_task)) {
        console.log('meta', meta_task);
        this.setState({meta_task: meta_task}, function() {
          this.refs.canvas.setDrawMode(this.state.draw_mode);
          if (window.phyre_config.mode !== 'dev') {
            if (this.getLastAction()) {
              console.log('Reload');
              this.refs.canvas.setUserInput(this.getLastAction());
            }
          }
        });
      }
    });
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.task_id !== this.state.task_id) {
      this.setState({task_id: nextProps.task_id}, this.reloadLevel);
    }
  }

  saveSolution() {
    getClient('save_solution')(
      this.state.meta_task.task.taskId,
      this.refs.canvas.getUserInput(),
      (msg) => {
        if (!msg || !this.maybeReportThriftError(msg)) {
          console.log("Saved");
        }
      });
  }

  tick() {
    this.setState(prevState => ({cycle_id: prevState.cycle_id + 1}));
  }

  getLastAction() {
    if (this.state.meta_task && this.state.meta_task.task.taskId === window.last_action_task_id) {
      return window.last_action;
    }
  }

  onSimulationLoaded(task_simulation_meta) {
    if (!this.maybeReportThriftError(task_simulation_meta)) {
      const task_simulation = task_simulation_meta.simulation;
      console.log(task_simulation.sceneList[0]);
      const ui_status = task_simulation.sceneList[0].user_input_status;
      this.setState({
        task_simulation: task_simulation,
        rendered_imgs: task_simulation_meta.rendered_imgs,
        has_occlusion: ui_status === window.UserInputStatus.NO_OCCLUSIONS ? "no" : "yes",
        start_ts: Date.now(),
        cycle_id: 0,
        interval: setInterval(() => this.tick(), 1000 / 20)
      });
    }
  }

  onSimulationRequestClick(use_last_input, dilate) {
    this.setState({simulation_requested: true});
    if (use_last_input) {
      getClient('simulate_task_with_last_input')(
        this.state.meta_task.task, this.onSimulationLoaded.bind(this));
    } else {
      const user_input = this.refs.canvas.getUserInput();
      window.last_action = user_input;
      window.last_action_task_id = this.state.meta_task.task.taskId;
      // If not set, assume dilate is true.
      dilate = dilate === false ? false : true;
      getClient('simulate_task_by_id')(
        this.state.meta_task.task.taskId, user_input, dilate, this.onSimulationLoaded.bind(this));
    }
  }

  onLoadLastInputClick() {
    if (window.phyre_config.mode === 'dev') {
      getClient('get_last_input')((user_input) => {
        this.setState({show_user_input_buttons: false});
        if (!this.maybeReportThriftError(user_input)) {
          this.refs.canvas.setUserInput(user_input);
        }
      });
    } else {
      this.setState({show_user_input_buttons: false});
      if (this.getLastAction()) {
        this.refs.canvas.setUserInput(this.getLastAction());
      }
    }
  }

  onLoadEvalSolutionClick(tier_name) {
    const task_id = this.state.task_id;
    this.setState({show_user_input_buttons: false, loading_solution: true});
    getClient('get_eval_user_input')(task_id, tier_name, (user_input) => {
      if (!this.maybeReportThriftError(user_input)) {
        this.refs.canvas.setUserInput(user_input);
        this.setState({loading_solution: false})
      }
    });
  }

  onLoadSolutionClick() {
    this.setState({show_user_input_buttons: false});
    this.refs.canvas.setUserInput(this.state.meta_task.task.solutions[0]);
  }

  onUserInputChanged() {
    const user_input = this.refs.canvas.getUserInput();
    const is_empty =
      user_input.polygons.length === 0 &&
      user_input.balls.length === 0 &&
      user_input.flattened_point_list.length === 0;
    this.setState({ has_user_input: !is_empty });
  }
  onCleanActions() {
    this.refs.canvas.cleanUserInput();
  }
  maybeReportThriftError(maybe_exception) {
    if (maybe_exception.message) {
        this.setState({error: maybe_exception.message});
        return true;
    }
    return false;
  }

  renderLoadingStatus(text) {
    return <Segment><Dimmer active><Loader content={text} /></Dimmer></Segment>;
  }

  toggleShowRender() {
    if (this.state.show_render) {
      this.refs.canvas.refs.user_input_layer.hide();
      this.refs.canvas.refs.scene_layer.show();
    } else {
      this.refs.canvas.refs.user_input_layer.show();
      this.refs.canvas.refs.scene_layer.hide();
    }
    this.setState(prevState => ({show_render: !prevState.show_render}));
  }

  renderTierSolutionButton() {
    if (!this.state.show_user_input_buttons) {
      return "";
    }
    const data = this.state.meta_task.eval_data;
    if (!data) {
      return "";
    }
    function getButton(code){
      // In demo mode we'll have at most one solution. So we can call the button just demo.
      const button = <Button key={code} onClick={this.onLoadEvalSolutionClick.bind(this, code)}>
          {ifproddev(code, 'Load solution')}
        </Button>;
      return button;
    }

    return data["known_solutions"].map(code => getButton.bind(this)(code));
  }

  renderHeader() {
    if (window.phyre_config.mode !== 'demo') return "";
    return <Message className='dataset_info'>
      <p>
        Each task has a <b>goal</b> and an <b>initial scene</b>. The agent intoduces
        one or more balls to the scene and then the simulation starts. The agent
        {" "}<i>wins</i>{" "} if during the simulation the condition is met for 3
        seconds or more.
      </p>
      <p>
        Below you can either load a pre-computed solution or try to solve the
        task yourself by adding balls to the scene with the mouse.
      </p>
    </Message>
  }

  renderDescription(verbose) {
    const meta_task = this.state.meta_task;
    let description = [<span key="descr">{meta_task.task.description}<br /></span>];


    if (verbose) {
      if (meta_task.template_params) {
        description.push(ifdev(<Teaser key="tpl" caption="Template params" text={meta_task.template_params} />))
      }
      if (meta_task.text_eval_info) {
        description.push(ifproddev(<Teaser key="eval_stats" caption="Eval stats" text={meta_task.text_eval_info} />))
      }
    }
    if (window.phyre_config.mode === 'demo') {
      description = meta_task.task.description;
      if (meta_task.task.tier === "BALL") {
        description = "Add one ball to " + description.toLowerCase();
      } else {
        description = "Add two balls to " + description.toLowerCase();
      }
    }
    const body = ifproddev(
      <div className='status-description'>
        <b>Task ({ this.state.task_id}):</b> {description}<br /></div>,
      <div className='status-description'>
        <div><b>Goal:</b> {description}</div></div>
    );
    return body
  }

  renderDrawingInstructions() {
    let help_text;
    let icon;
    if (this.state.draw_mode === DrawMode.FREE) {
      help_text = "Click on canvas and hold to create an object. Click with command on to erase.";
      icon = "paint brush";
    } else {
      help_text = "Click on canvas to create a ball. Hold command to erase. Hold shift to resize.";
      icon = "circle";
    }
    if (window.phyre_config.mode === 'demo') {
      return <div className="instructions"><b>Try it yourself.</b> {help_text}</div>
    }
    return (
      <div>
      <Label>
        {ifproddev(<Button icon={icon} onClick={this.toggleDrawMode.bind(this)} />)}
        <span>{help_text}</span>
      </Label>
      </div>
    );
  }

  toggleDrawMode() {
    const new_draw_mode =
      (this.state.draw_mode === DrawMode.FREE) ?
      DrawMode.BALL : DrawMode.FREE;
    this.setState({draw_mode: new_draw_mode},
      () => this.refs.canvas.setDrawMode(new_draw_mode)
    );
  }

  renderStatus() {
    if (this.state.error) {
      return <div><h2>Thrift service return error message</h2><h3>{this.state.error}</h3></div>;
    }
    if (this.state.meta_task === null) {
      return this.renderLoadingStatus('Loading the scene...');
    }
    if (this.state.loading_solution) {
      return this.renderLoadingStatus('Loading solution...');
    }
    if (!this.state.simulation_requested) {
      const if_actions_on = (button) => (this.state.show_user_input_buttons ? button : "");
      const if_solution_on = (button) => if_actions_on(this.state.meta_task.task.solutions ? button : "");
      const if_has_user_input = (button) => if_actions_on(this.state.has_user_input ? button : "");
      const if_last_input = (button) => ifdev(
        button,
        this.getLastAction() ? button : ""
      );
      const proddev_version = <div>
        {this.renderDescription(true)}
        <div className='load_action_wrapper'>
          {if_actions_on("Load action:")}
          <Button.Group>
            {if_actions_on(if_last_input(<Button onClick={this.onLoadLastInputClick.bind(this)}>Last</Button>))}
            {ifdev(if_solution_on(<Button onClick={this.onLoadSolutionClick.bind(this)}>Solution</Button>))}
            {this.renderTierSolutionButton()}
          </Button.Group>
        </div>
        <Button.Group>
          <Button primary onClick={this.onSimulationRequestClick.bind(this, false, false)}>Go!</Button>
          {ifdev(<Button onClick={this.onSimulationRequestClick.bind(this, false, true)}>Go Dilate!</Button>)}
          {ifdev(if_actions_on(<Button onClick={this.onSimulationRequestClick.bind(this, true, false)}>w/ last</Button>))}
        </Button.Group>
        {this.renderDrawingInstructions()}
      </div>;
      const demo_version = <div>
          {this.renderDescription(true)}
          <Button.Group size="tiny" className='buttonblock'>
            {if_has_user_input(<Button onClick={this.onCleanActions.bind(this)}>Clean actions</Button>)}
            {this.renderTierSolutionButton()}
            <Button primary onClick={this.onSimulationRequestClick.bind(this, false, false)}>Simulate</Button>
          </Button.Group>
          {this.renderDrawingInstructions()}
      </div>;
      return ifproddev(proddev_version, demo_version);
    }
    if (!this.state.task_simulation) {
      return this.renderLoadingStatus('Getting simulation from the server...');
    }
    if (!this.state.task_simulation.sceneList) {
      return <div>
        Empty simulation recieved from the server.<br />
      </div>;
    }
    const tick = this.state.cycle_id % this.state.task_simulation.sceneList.length;
    const fps = Math.floor(this.state.cycle_id * 1000 / (Date.now() - this.state.start_ts));
    const solvedFrame = this.state.task_simulation.solvedStateList[tick]
    const solvedTask = this.state.task_simulation.isSolution
    if (window.phyre_config.mode === 'demo') {
      let demoStatus;
      if (this.state.has_occlusion === "yes") {
        demoStatus =  <span>The action is <b>invalid</b>: it occludes scene bodies.</span>
      } else if (solvedTask) {
          demoStatus = <span>The action <b>solves</b> the task.</span>
      } else {
          demoStatus = <span>The action <b>doesn't solve</b> the task.</span>
      }
      return <div>
        <div className='simulation-result'>
        {demoStatus}
        {" "}Frame: {tick}{ifdev(" Fps: " + fps)}
        </div>
        <Button.Group size="tiny" className='buttonblock'>
          <Button onClick={this.reloadLevel.bind(this)}>Reload level</Button>
        </Button.Group>
        <div className='instructions'>{this.renderDescription(false)}</div>
      </div>;
    }
    return <div>
      {this.renderDescription(false)}
      <div>
      Tick: {tick} Fps: {fps}
      {" "}Solved now: {solvedFrame ? "True" : "False"}
      {" "}<b>(solution={solvedTask ? "yes" : "no"},
      {" "}occlusion={this.state.has_occlusion})</b>
      </div>
      <br />
      <Button onClick={this.reloadLevel.bind(this)}>Reload level</Button>
      {ifdev(<Button onClick={this.saveSolution.bind(this)}>Save solution</Button>)}
    </div>;
  }

  renderRenderedImage() {
    if (this.state.rendered_imgs) {
      const task_id = this.state.meta_task.task_id;
      const tick = this.state.cycle_id % this.state.task_simulation.sceneList.length;
      const rendered_tick = parseInt(tick / 10, 10);
      const img = this.state.rendered_imgs[rendered_tick];
      return <div>
        <h2>Server side rendering (every 10th frame):</h2>
        <img alt={"Task: " + task_id} src={"data:image/png;base64," + img} width="512" height="512" />
      </div>
    }
    if (this.state.meta_task) {
      const task_id = this.state.meta_task.task_id;
      const img = this.state.meta_task.rendered_img;
      return <div>
        <h2>Server side rendering:</h2>
        <img alt={"Task: " + task_id} src={"data:image/png;base64," + img} width="512" height="512" />
      </div>
    }
    return "";
  }

  renderCanvas() {
    if (!this.state.meta_task || !this.state.meta_task.task.scene) return;

    const task = this.state.meta_task.task;

    const width = task.scene.width;
    const height = task.scene.height;
    var scene_id = -1;
    if (this.state.task_simulation && this.state.task_simulation.sceneList) {
      scene_id = this.state.cycle_id % this.state.task_simulation.sceneList.length;
    }
    const current_scene =
      (scene_id === -1)
      ? task.scene
      : this.state.task_simulation.sceneList[scene_id];
    const canvas_style = {
      width: width * RESOLUTION + "px",
      height: height * RESOLUTION + "px",
    }
    return <div className="Canvas" style={ canvas_style }>
      <Canvas
        ref="canvas"
        scene={current_scene}
        width={width}
        height={height}
        onUserInputChanged={this.onUserInputChanged.bind(this)}
        allow_drawing={!this.state.simulation_requested} />
      </div>;
  }

  render() {
    return <div>
      <div className="World-header">{this.renderHeader()}</div>
      <div className="World-status">{this.renderStatus()}</div>
      <div className="World-canvas">{this.renderCanvas()}</div>
      {ifdev(<div className="World-rendered">{this.renderRenderedImage()}</div>)}
    </div>;
  }
}
class App extends Component {
  constructor(props) {
    super(props);
    this.state = getStateForUrl();
  }

  componentDidMount() {
    window.addEventListener('hashchange', this.setStateForUrl.bind(this), false);
    setTitle();
  }

  componentWillUnmount() {
    window.removeEventListener('hashchange', this.setStateForUrl.bind(this), false);
  }

  setStateForUrl() {
    const state = getStateForUrl();
    this.setState(state);
  }

  render() {
    return (
      <div className={"App  mode_" + window.phyre_config.mode}>
        <header className="App-header">
          <h1 className="App-title" onClick={() => {navigate('#'); this.setStateForUrl();}}>PHYRE Player</h1>
        </header>
        {
          (this.state.template_id !== null && this.state.task_index !== null)
          ? <TaskView setStateForUrl={() => this.setStateForUrl()} task_id={this.state.tempate_id + ":" + this.state.task_index} />
          : <WorldWithControls setStateForUrl={() => this.setStateForUrl()} template_id={this.state.tempate_id} />
        }
      </div>
    );
  }
}

export default App;
