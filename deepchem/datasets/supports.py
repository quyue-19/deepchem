"""
Sample supports from datasets.
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import numpy as np
from deepchem.datasets import NumpyDataset

def get_task_dataset_minus_support(dataset, support, task):
  """Gets data for specified task, minus support points.

  Useful for evaluating model performance once trained (so that
  test compounds can be ensured distinct from support.)

  Parameters
  ----------
  dataset: deepchem.datasets.Dataset
    Source dataset.
  support: deepchem.datasets.Dataset
    The support dataset
  task: int
    Task number of task to select.
  """
  support_ids = set(support.ids)
  non_support_inds = [ind for ind in range(len(dataset))
                      if dataset.ids[ind] not in support_ids]

  # Remove support indices
  X = dataset.X[non_support_inds]
  y = dataset.y[non_support_inds]
  w = dataset.w[non_support_inds]
  ids = dataset.ids[non_support_inds]

  # Get task specific entries
  w_task = w[:, task]
  X_task = X[w_task != 0]
  y_task = y[w_task != 0, task]
  ids_task = ids[w_task != 0]
  # Now just get weights for this task
  w_task = w[w_task != 0, task]

  return NumpyDataset(X_task, y_task, w_task, ids_task)

def get_task_dataset(dataset, task):
  """Selects out entries for a particular task."""
  X, y, w, ids = dataset.X, dataset.y, dataset.w, dataset.ids
  # Get task specific entries
  w_task = w[:, task]
  X_task = X[w_task != 0]
  y_task = y[w_task != 0, task]
  ids_task = ids[w_task != 0]
  # Now just get weights for this task
  w_task = w[w_task != 0, task]

  return NumpyDataset(X_task, y_task, w_task, ids_task)

def get_task_test(dataset, batch_size, task, replace=True):
  """Gets test set from specified task.

  Samples random subset of size batch_size from specified task of dataset.
  Ensures that sampled points have measurements for this task.
  """
  w_task = dataset.w[:, task]
  X_task = dataset.X[w_task != 0]
  y_task = dataset.y[w_task != 0]
  ids_task = dataset.ids[w_task != 0]
  # Now just get weights for this task
  w_task = dataset.w[w_task != 0]

  inds = np.random.choice(np.arange(len(X_task)), batch_size, replace=replace)
  X_batch = X_task[inds]
  y_batch = np.squeeze(y_task[inds, task])
  w_batch = np.squeeze(w_task[inds, task])
  ids_batch = ids_task[inds]
  return NumpyDataset(X_batch, y_batch, w_batch, ids_batch)

def get_task_support(dataset, n_pos, n_neg, task, replace=True):
  """Generates a support set purely for specified task.
  
  Parameters
  ----------
  datasets: deepchem.datasets.Dataset
    Dataset from which supports are sampled.
  n_pos: int
    Number of positive samples in support.
  n_neg: int
    Number of negative samples in support.
  task: int
    Index of current task.
  replace: bool, optional
    Whether or not to use replacement when sampling supports.

  Returns
  -------
  list
    List of NumpyDatasets, each of which is a support set.
  """
  y_task = dataset.y[:, task]

  # Split data into pos and neg lists.
  pos_mols = np.where(y_task == 1)[0]
  neg_mols = np.where(y_task == 0)[0]

  # Get randomly sampled pos/neg indices (with replacement)
  pos_inds = pos_mols[np.random.choice(len(pos_mols), (n_pos), replace=replace)]
  neg_inds = neg_mols[np.random.choice(len(neg_mols), (n_neg), replace=replace)]

  # Handle one-d vs. non one-d feature matrices
  one_dimensional_features = (len(dataset.X.shape) == 1)
  if not one_dimensional_features:
    X_trial = np.vstack(
        [dataset.X[pos_inds], dataset.X[neg_inds]])
  else:
    X_trial = np.concatenate(
        [dataset.X[pos_inds], dataset.X[neg_inds]])
  y_trial = np.concatenate(
      [dataset.y[pos_inds, task], dataset.y[neg_inds, task]])
  w_trial = np.concatenate(
      [dataset.w[pos_inds, task], dataset.w[neg_inds, task]])
  ids_trial = np.concatenate(
      [dataset.ids[pos_inds], dataset.ids[neg_inds]])
  return NumpyDataset(X_trial, y_trial, w_trial, ids_trial)

class SupportGenerator(object):
  """ Generate support sets from a dataset.

  Iterates over tasks and trials. For each trial, picks one support from
  each task, and returns in a randomized order
  """
  def __init__(self, dataset, tasks, n_pos, n_neg, n_trials, replace):
    """
    Parameters
    ----------
    dataset: deepchem.datasets.Dataset
      Holds dataset from which support sets will be sampled.
    tasks: list
      Indices of tasks from which supports are sampled.
      TODO(rbharath): Can this be removed.
    n_pos: int
      Number of positive samples
    n_neg: int
      Number of negative samples.
    n_trials: int
      Number of passes over tasks to make. In total, n_tasks*n_trials
      support sets will be sampled by algorithm.
    replace: bool
      Whether to use sampling with or without replacement.
    """
      
    self.tasks = tasks
    self.n_tasks = len(tasks)
    self.n_trials = n_trials
    self.dataset = dataset
    self.n_pos = n_pos
    self.n_neg = n_neg
    self.replace = replace

    # Init the iterator
    self.perm_tasks = np.random.permutation(self.tasks)
    # Set initial iterator state
    self.task_num = 0
    self.trial_num = 0

  def __iter__(self):
    return self

  # TODO(rbharath): This is generating data from one task at a time. Is it
  # wrong to have batches that mix information from multiple tasks?
  def next(self):
    """Sample next support.

    Supports are sampled from the tasks in a random order. Each support is
    drawn entirely from within one task.
    """
    if self.trial_num == self.n_trials:
      raise StopIteration
    else:
      task = self.perm_tasks[self.task_num]  # Get id from permutation
      #support = self.supports[task][self.trial_num]
      support = get_task_support(
          self.dataset, n_pos=self.n_pos, n_neg=self.n_neg, task=task,
          replace=self.replace)
      # Increment and update logic
      self.task_num += 1
      if self.task_num == self.n_tasks:
        self.task_num = 0  # Reset
        self.perm_tasks = np.random.permutation(self.tasks)  # Permute again
        self.trial_num += 1  # Upgrade trial index

      return (task, support)

  __next__ = next # Python 3.X compatibility
