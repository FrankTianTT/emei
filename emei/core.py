import os
import h5py
import urllib.request

from abc import ABC, abstractmethod
from gym import Env
import numpy as np
from tqdm import tqdm
from emei.offline_info import URL_INFOS
from collections import defaultdict

DATASET_PATH = os.path.expanduser('~/.emei/offline_data')


class EmeiEnv(ABC, Env):
    def __init__(self):
        """
        Abstract class for all Emei environments to better support model-based RL and offline RL.
        """
        # for freezable
        self.frozen_state = None
        # for downloadable
        env_name = self.__class__.__name__[:-3]
        self.offline_dataset_names = []
        if env_name in URL_INFOS:
            self.data_url = URL_INFOS[env_name]
            self.offline_dataset_names = []
            for param in self.data_url:
                for dataset in self.data_url[param]:
                    self.offline_dataset_names.append("{}-{}".format(param, dataset))

    @abstractmethod
    def freeze(self):
        """
        Freeze the environment, for rollout-test or query.
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    def unfreeze(self):
        """
        Unfreeze the environment, back to normal interaction.
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    def _set_state_by_obs(self, obs):
        """
        Set model state by observation, only for MDPs.
        :param obs: single observation
        :return: None
        """
        raise NotImplementedError

    def single_query(self, obs, action):
        self.freeze()
        self._set_state_by_obs(obs)
        next_obs, reward, done, info = self.step(action)
        self.unfreeze()
        return next_obs, reward, done, info

    def query(self, obs, action):
        """
        Give the environment's reflection to single or batch query.
        :param obs: single or batch observations.
        :param action: single or batch action.
        :return: single or batch (next-obs, reward, done, terminal).
        """
        if len(obs.shape) == 1:  # single obs
            assert len(action.shape) == 1
            return self.single_query(obs, action)
        else:
            next_obs_list, reward_list, done_list, info_list = [], [], [], []
            for i in range(obs.shape[0]):
                next_obs, reward, done, info = self.single_query(obs[i], action[i])
                next_obs_list.append(next_obs)
                reward_list.append(reward)
                done_list.append(done)
                info_list.append(info)
            return np.array(next_obs_list), np.array(reward_list), np.array(done_list), np.array(info_list)

    @abstractmethod
    def get_batch_reward_by_next_obs(self, next_obs, pre_obs=None, action=None):
        pass

    @abstractmethod
    def get_batch_terminal_by_next_obs(self, next_obs, pre_obs=None, action=None):
        pass

    def get_reward_by_next_obs(self, next_obs, pre_obs=None, action=None):
        """
        Return the reward of single or batch next-obs.
        :param next_obs: single or batch observations.
        :return: single or batch reward.
        """
        if len(next_obs.shape) == 1:  # single obs
            next_obs = next_obs.reshape(1, next_obs.shape[0])
            if pre_obs is not None:
                pre_obs = pre_obs.reshape(1, pre_obs.shape[0])
            if action is not None:
                action = action.reshape(1, action.shape[0])
            return float(self.get_batch_reward_by_next_obs(next_obs, pre_obs, action)[0, 0])
        else:
            return self.get_batch_reward_by_next_obs(next_obs, pre_obs, action)

    def get_terminal_by_next_obs(self, next_obs, pre_obs=None, action=None):
        """
        Return the terminal of single or batch next-obs.
        :param next_obs: single or batch observations.
        :return: single or batch terminal.
        """
        if len(next_obs.shape) == 1:  # single obs
            next_obs = next_obs.reshape(1, next_obs.shape[0])
            if pre_obs is not None:
                pre_obs = pre_obs.reshape(1, pre_obs.shape[0])
            if action is not None:
                action = action.reshape(1, action.shape[0])
            return bool(self.get_batch_terminal_by_next_obs(next_obs, pre_obs, action)[0, 0])
        else:
            return self.get_batch_terminal_by_next_obs(next_obs, pre_obs, action)

    @property
    def dataset_names(self):
        return self.offline_dataset_names

    def get_dataset(self, dataset_name):
        assert dataset_name in self.offline_dataset_names

        joint_pos = dataset_name.find("-")
        param, dataset_type = dataset_name[:joint_pos], dataset_name[joint_pos + 1:]
        url = self.data_url[param][dataset_type]
        h5path = download_dataset_from_url(url)

        data_dict = {}
        with h5py.File(h5path, 'r') as dataset_file:
            for k in tqdm(get_keys(dataset_file), desc="load datafile"):
                try:  # first try loading as an array
                    data_dict[k] = dataset_file[k][:]
                except ValueError as e:  # try loading as a scalar
                    data_dict[k] = dataset_file[k][()]

        # Run a few quick sanity checks
        for key in ['observations', 'observations', 'actions', 'rewards', 'terminals', "timeouts"]:
            assert key in data_dict, 'Dataset is missing key %s' % key

        return data_dict

    def get_sequence_dataset(self, dataset_name):
        dataset = self.get_dataset(dataset_name)
        N = dataset['rewards'].shape[0]
        data = defaultdict(lambda: defaultdict(list))

        sequence_num = 0
        for i in range(N):
            done_bool = bool(dataset['terminals'][i])
            final_timestep = dataset['timeouts'][i]

            for k in dataset:
                data[sequence_num][k].append(dataset[k][i])

            if done_bool or final_timestep:
                sequence_num += 1
        return data


def get_keys(h5file):
    """
    Get the keys of h5-file.
    :param h5file: binary file of h5 format.
    :return: keys.
    """
    keys = []

    def visitor(name, item):
        if isinstance(item, h5py.Dataset):
            keys.append(name)

    h5file.visititems(visitor)
    return keys


def filepath_from_url(dataset_url: str) -> str:
    """
    Return the data file path corresponding to the url.
    :param dataset_url: web url.
    :return: local file path.
    """
    env_name, param, dataset_name = dataset_url.split('/')[-3:]
    os.makedirs(os.path.join(DATASET_PATH, env_name, param), exist_ok=True)
    dataset_filepath = os.path.join(DATASET_PATH, env_name, param, dataset_name)
    return dataset_filepath


def download_dataset_from_url(dataset_url: str) -> str:
    """
    Return the data file path corresponding to the url, downloads if it does not exist.
    :param dataset_url: web url.
    :return: local file path.
    """
    dataset_filepath = filepath_from_url(dataset_url)
    if not os.path.exists(dataset_filepath):
        print('Downloading dataset:', dataset_url, 'to', dataset_filepath)
        urllib.request.urlretrieve(dataset_url, dataset_filepath)
    if not os.path.exists(dataset_filepath):
        raise IOError("Failed to download dataset from %s" % dataset_url)
    return dataset_filepath
