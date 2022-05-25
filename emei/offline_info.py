ROOT_PATH = r"http://114.212.20.185/emei/offline_data"
ENV_NAMES = ["ContinuousCartPoleHolding", "ContinuousCartPoleSwingUp", "ContinuousChargedBallCentering",
             "BoundaryInvertedPendulumHolding", "ReboundInvertedPendulumHolding",
             "BoundaryInvertedPendulumSwingUp", "ReboundInvertedPendulumSwingUp",]
DATASETS = ["random", "medium", "expert", "medium-replay", "expert-replay"]
params = ["freq_rate=1&time_step=0.02"]

URL_INFOS = {}
for env_name in ENV_NAMES:
    URL_INFOS[env_name] = {}
    for param in params:
        URL_INFOS[env_name][param] = {}
        for dataset in DATASETS:
            URL_INFOS[env_name][param][dataset] = "{}/{}-v0/freq_rate=1&time_step=0.02/{}-{}-v0.h5".format(
                ROOT_PATH, env_name, dataset, env_name)