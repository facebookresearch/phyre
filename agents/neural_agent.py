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
"""This library contains actual implementation of the DQN agent."""
from typing import Optional, Sequence, Tuple
import glob
import logging
import os
import time

import numpy as np
import torch

import nets
import phyre

AUCCESS_EVAL_TASKS = 200
XE_EVAL_SIZE = 10000

TaskIds = Sequence[str]
NeuralModel = torch.nn.Module
TrainData = Tuple[torch.Tensor, torch.Tensor, torch.Tensor, phyre.
                  ActionSimulator, torch.Tensor]


def create_balanced_eval_set(cache: phyre.SimulationCache, task_ids: TaskIds,
                             size: int, tier: str) -> TrainData:
    """Prepares balanced eval set to run through a network.

    Selects (size // 2) positive (task, action) pairs and (size // 2)
    negative pairs and represents them in a compact formaer

    Returns a tuple
        (task_indices, is_solved, selected_actions, simulator, observations).

        Tensors task_indices, is_solved, selected_actions, observations, all
        have lengths size and correspond to some (task, action) pair.
        For any i the following is true:
            is_solved[i] is true iff selected_actions[i] solves task
            task_ids[task_indices[i]].
    """
    task_ids = tuple(task_ids)
    data = cache.get_sample(task_ids)
    actions = data['actions']
    # Array [num_tasks, num_actions].
    simulation_statuses = data['simulation_statuses']

    flat_statuses = simulation_statuses.reshape(-1)
    [positive_indices
    ] = (flat_statuses == int(phyre.SimulationStatus.SOLVED)).nonzero()
    [negative_indices
    ] = (flat_statuses == int(phyre.SimulationStatus.NOT_SOLVED)).nonzero()

    half_size = size // 2
    rng = np.random.RandomState(42)
    positive_indices = rng.choice(positive_indices, half_size)
    negative_indices = rng.choice(negative_indices, half_size)

    all_indices = np.concatenate([positive_indices, negative_indices])
    selected_actions = torch.FloatTensor(actions[all_indices % len(actions)])
    is_solved = torch.LongTensor(flat_statuses[all_indices].astype('int')) > 0

    all_task_indices = np.arange(len(task_ids)).repeat(actions.shape[0])
    positive_task_indices = all_task_indices[positive_indices]
    negative_task_indices = all_task_indices[negative_indices]
    task_indices = torch.LongTensor(
        np.concatenate([positive_task_indices, negative_task_indices]))

    simulator = phyre.initialize_simulator(task_ids, tier)
    observations = torch.LongTensor(simulator.initial_scenes)
    return task_indices, is_solved, selected_actions, simulator, observations


def compact_simulation_data_to_trainset(action_tier_name: str,
                                        actions: np.ndarray,
                                        simulation_statuses: Sequence[int],
                                        task_ids: TaskIds) -> TrainData:
    """Converts result of SimulationCache.get_data() to pytorch tensors.

    The format of the output is the same as in create_balanced_eval_set.
    """
    invalid = int(phyre.SimulationStatus.INVALID_INPUT)
    solved = int(phyre.SimulationStatus.SOLVED)

    task_indices = np.repeat(np.arange(len(task_ids)).reshape((-1, 1)),
                             actions.shape[0],
                             axis=1).reshape(-1)
    action_indices = np.repeat(np.arange(actions.shape[0]).reshape((1, -1)),
                               len(task_ids),
                               axis=0).reshape(-1)
    simulation_statuses = simulation_statuses.reshape(-1)

    good_statuses = simulation_statuses != invalid
    is_solved = torch.LongTensor(
        simulation_statuses[good_statuses].astype('uint8')) == solved
    action_indices = action_indices[good_statuses]
    actions = torch.FloatTensor(actions[action_indices])
    task_indices = torch.LongTensor(task_indices[good_statuses])

    simulator = phyre.initialize_simulator(task_ids, action_tier_name)
    observations = torch.LongTensor(simulator.initial_scenes)
    return task_indices, is_solved, actions, simulator, observations


def build_model(network_type: str, **kwargs) -> NeuralModel:
    """Builds a DQN network by name."""
    if network_type == 'resnet18':
        model = nets.ResNet18FilmAction(
            kwargs['action_space_dim'],
            fusion_place=kwargs['fusion_place'],
            action_hidden_size=kwargs['action_hidden_size'],
            action_layers=kwargs['action_layers'])
    elif network_type == 'simple':
        model = nets.SimpleNetWithAction(kwargs['action_space_dim'])
    else:
        raise ValueError('Unknown network type: %s' % network_type)
    return model


def get_latest_checkpoint(output_dir: str) -> Optional[str]:
    known_checkpoints = sorted(glob.glob(os.path.join(output_dir, 'ckpt.*')))
    if known_checkpoints:
        return known_checkpoints[-1]
    else:
        return None


def load_agent_from_folder(agent_folder: str) -> NeuralModel:
    last_checkpoint = get_latest_checkpoint(agent_folder)
    assert last_checkpoint is not None, agent_folder
    logging.info('Loading a model from: %s', last_checkpoint)
    last_checkpoint = torch.load(last_checkpoint)
    model = build_model(**last_checkpoint['model_kwargs'])
    model.load_state_dict(last_checkpoint['model'])
    model.to(nets.DEVICE)
    return model


def finetune(
        model: NeuralModel,
        data: Sequence[Tuple[int, phyre.SimulationStatus, Sequence[float]]],
        simulator: phyre.ActionSimulator, learning_rate: float,
        num_updates: int) -> None:
    """Finetunes a model on a small new batch of data.

    Args:
        model: DQN network, e.g., built with build_model().
        data: a list of tuples (task_index, status, action).
        learning_rate: learning rate for Adam.
        num_updates: number updates to do. All data is used for every update.
    """

    data = [x for x in data if not x[1].is_invalid()]
    if not data:
        return
    task_indices, statuses, actions = zip(*data)
    if len(set(task_indices)) == 1:
        observations = np.expand_dims(simulator.initial_scenes[task_indices[0]],
                                      0)
    else:
        observations = simulator.initial_scenes[task_indices]

    is_solved = torch.tensor(statuses, device=model.device) > 0
    observations = torch.tensor(observations, device=model.device)
    actions = torch.tensor(actions, device=model.device)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    model.train()
    for _ in range(num_updates):
        optimizer.zero_grad()
        model.ce_loss(model(observations, actions), is_solved).backward()
        optimizer.step()


def refine_actions(model, actions, single_observarion, learning_rate,
                   num_updates, batch_size, refine_loss):
    observations = torch.tensor(single_observarion,
                                device=model.device).unsqueeze(0)
    actions = torch.tensor(actions)

    refined_actions = []
    model.eval()
    preprocessed = model.preprocess(observations)
    preprocessed = {k: v.detach() for k, v in preprocessed.items()}
    for start in range(0, len(actions), batch_size):
        action_batch = actions[start:][:batch_size].to(model.device)
        action_batch = torch.nn.Parameter(action_batch)
        optimizer = torch.optim.Adam([action_batch], lr=learning_rate)
        losses = []
        for _ in range(num_updates):
            optimizer.zero_grad()
            logits = model(None, action_batch, preprocessed=preprocessed)
            if refine_loss == 'ce':
                loss = model.ce_loss(logits, actions.new_ones(len(logits)))
            elif refine_loss == 'linear':
                loss = -logits.sum()
            else:
                raise ValueError(f'Unknown loss: {refine_loss}')
            loss.backward()
            losses.append(loss.item())
            optimizer.step()
        action_batch = torch.clamp_(action_batch.data, 0, 1)
        refined_actions.append(action_batch.cpu().numpy())
    refined_actions = np.concatenate(refined_actions, 0).tolist()
    return refined_actions


def train(output_dir,
          action_tier_name,
          task_ids,
          cache,
          train_batch_size,
          learning_rate,
          max_train_actions,
          updates,
          negative_sampling_prob,
          save_checkpoints_every,
          fusion_place,
          network_type,
          balance_classes,
          num_auccess_actions,
          eval_every,
          action_layers,
          action_hidden_size,
          cosine_scheduler,
          dev_tasks_ids=None):

    logging.info('Preprocessing train data')

    training_data = cache.get_sample(task_ids, max_train_actions)
    task_indices, is_solved, actions, simulator, observations = (
        compact_simulation_data_to_trainset(action_tier_name, **training_data))

    logging.info('Creating eval subset from train')
    eval_train = create_balanced_eval_set(cache, simulator.task_ids,
                                          XE_EVAL_SIZE, action_tier_name)
    if dev_tasks_ids is not None:
        logging.info('Creating eval subset from dev')
        eval_dev = create_balanced_eval_set(cache, dev_tasks_ids, XE_EVAL_SIZE,
                                            action_tier_name)
    else:
        eval_dev = None

    logging.info('Tran set: size=%d, positive_ratio=%.2f%%', len(is_solved),
                 is_solved.float().mean().item() * 100)

    assert not balance_classes or (negative_sampling_prob == 1), (
        balance_classes, negative_sampling_prob)

    device = nets.DEVICE
    model_kwargs = dict(network_type=network_type,
                        action_space_dim=simulator.action_space_dim,
                        fusion_place=fusion_place,
                        action_hidden_size=action_hidden_size,
                        action_layers=action_layers)
    model = build_model(**model_kwargs)
    model.train()
    model.to(device)
    logging.info(model)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    if cosine_scheduler:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,
                                                               T_max=updates)
    else:
        scheduler = None
    logging.info('Starting actual training for %d updates', updates)

    rng = np.random.RandomState(42)

    def train_indices_sampler():
        indices = np.arange(len(is_solved))
        if balance_classes:
            solved_mask = is_solved.numpy() > 0
            positive_indices = indices[solved_mask]
            negative_indices = indices[~solved_mask]
            positive_size = train_batch_size // 2
            while True:
                positives = rng.choice(positive_indices, size=positive_size)
                negatives = rng.choice(negative_indices,
                                       size=train_batch_size - positive_size)
                positive_size = train_batch_size - positive_size
                yield np.concatenate((positives, negatives))
        elif negative_sampling_prob < 1:
            probs = (is_solved.numpy() * (1.0 - negative_sampling_prob) +
                     negative_sampling_prob)
            probs /= probs.sum()
            while True:
                yield rng.choice(indices, size=train_batch_size, p=probs)
        else:
            while True:
                yield rng.choice(indices, size=train_batch_size)

    last_checkpoint = get_latest_checkpoint(output_dir)
    batch_start = 0
    if last_checkpoint is not None:
        logging.info('Going to load from %s', last_checkpoint)
        last_checkpoint = torch.load(last_checkpoint)
        model.load_state_dict(last_checkpoint['model'])
        optimizer.load_state_dict(last_checkpoint['optim'])
        rng.set_state(last_checkpoint['rng'])
        batch_start = last_checkpoint['done_batches']
        if scheduler is not None:
            scheduler.load_state_dict(last_checkpoint['scheduler'])

    def print_eval_stats(batch_id):
        logging.info('Start eval')
        eval_batch_size = train_batch_size * 4
        stats = {}
        stats['batch_id'] = batch_id + 1
        stats['train_loss'] = eval_loss(model, eval_train, eval_batch_size)
        if eval_dev:
            stats['dev_loss'] = eval_loss(model, eval_dev, eval_batch_size)
        if num_auccess_actions > 0:
            logging.info('Start AUCCESS eval')
            stats['train_auccess'] = _eval_and_score_actions(
                cache, model, eval_train[3], num_auccess_actions,
                eval_batch_size, eval_train[4])
            if eval_dev:
                stats['dev_auccess'] = _eval_and_score_actions(
                    cache, model, eval_dev[3], num_auccess_actions,
                    eval_batch_size, eval_dev[4])

        logging.info('__log__: %s', stats)

    report_every = 125
    logging.info('Report every %d; eval every %d', report_every, eval_every)
    if save_checkpoints_every > eval_every:
        save_checkpoints_every -= save_checkpoints_every % eval_every

    print_eval_stats(0)

    losses = []
    last_time = time.time()
    observations = observations.to(device)
    actions = actions.pin_memory()
    is_solved = is_solved.pin_memory()
    for batch_id, batch_indices in enumerate(train_indices_sampler(),
                                             start=batch_start):
        if batch_id >= updates:
            break
        if scheduler is not None:
            scheduler.step()
        model.train()
        batch_task_indices = task_indices[batch_indices]
        batch_observations = observations[batch_task_indices]
        batch_actions = actions[batch_indices].to(device, non_blocking=True)
        batch_is_solved = is_solved[batch_indices].to(device, non_blocking=True)

        optimizer.zero_grad()
        loss = model.ce_loss(model(batch_observations, batch_actions),
                             batch_is_solved)
        loss.backward()
        optimizer.step()
        losses.append(loss.mean().item())
        if save_checkpoints_every > 0:
            if (batch_id + 1) % save_checkpoints_every == 0:
                fpath = os.path.join(output_dir, 'ckpt.%08d' % (batch_id + 1))
                logging.info('Saving: %s', fpath)
                torch.save(
                    dict(
                        model_kwargs=model_kwargs,
                        model=model.state_dict(),
                        optim=optimizer.state_dict(),
                        done_batches=batch_id + 1,
                        rng=rng.get_state(),
                        scheduler=scheduler and scheduler.state_dict(),
                    ), fpath)
        if (batch_id + 1) % eval_every == 0:
            print_eval_stats(batch_id)
        if (batch_id + 1) % report_every == 0:
            speed = report_every / (time.time() - last_time)
            last_time = time.time()
            logging.debug(
                'Iter: %s, examples: %d, mean loss: %f, speed: %.1f batch/sec,'
                ' lr: %f', batch_id + 1, (batch_id + 1) * train_batch_size,
                np.mean(losses[-report_every:]), speed, get_lr(optimizer))
    return model.cpu()


def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']


def eval_loss(model, data, batch_size):
    task_indices, is_solved, actions, _, observations = data
    losses = []
    observations = observations.to(model.device)
    with torch.no_grad():
        model.eval()
        for i in range(0, len(task_indices), batch_size):
            batch_task_indices = task_indices[i:i + batch_size]
            batch_observations = observations[batch_task_indices]
            batch_actions = actions[i:i + batch_size]
            batch_is_solved = is_solved[i:i + batch_size]
            loss = model.ce_loss(model(batch_observations, batch_actions),
                                 batch_is_solved)
            losses.append(loss.item() * len(batch_task_indices))
    return sum(losses) / len(task_indices)


def eval_actions(model, actions, batch_size, observations):
    scores = []
    with torch.no_grad():
        model.eval()
        preprocessed = model.preprocess(
            torch.LongTensor(observations).unsqueeze(0))
        for batch_start in range(0, len(actions), batch_size):
            batch_end = min(len(actions), batch_start + batch_size)
            batch_actions = torch.FloatTensor(actions[batch_start:batch_end])
            batch_scores = model(None, batch_actions, preprocessed=preprocessed)
            assert len(batch_scores) == len(batch_actions), (
                batch_actions.shape, batch_scores.shape)
            scores.append(batch_scores.cpu().numpy())
    return np.concatenate(scores)


def _eval_and_score_actions(cache, model, simulator, num_actions, batch_size,
                            observations):
    actions = cache.action_array[:num_actions]
    indices = np.random.RandomState(1).permutation(
        len(observations))[:AUCCESS_EVAL_TASKS]
    evaluator = phyre.Evaluator(
        [simulator.task_ids[index] for index in indices])
    for i, task_index in enumerate(indices):
        scores = eval_actions(model, actions, batch_size,
                              observations[task_index]).tolist()

        _, sorted_actions = zip(
            *sorted(zip(scores, actions), key=lambda x: (-x[0], tuple(x[1]))))
        for action in sorted_actions:
            if (evaluator.get_attempts_for_task(i) >= phyre.MAX_TEST_ATTEMPTS):
                break
            status = simulator.simulate_action(task_index,
                                               action,
                                               need_images=False).status
            evaluator.maybe_log_attempt(i, status)
    return evaluator.get_aucess()
