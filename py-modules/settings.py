import os
import yaml

home_dir = os.path.expanduser("~")


default_config = {
    "work-dir": os.path.join(home_dir, "ipykee/workdir/"),
    "project-dir": os.path.join(home_dir, "ipykee/projects/"),
    "ipython-url": "127.0.0.1:8080",
    "git-media-path": os.path.join(home_dir, "ipykee/git-media-data/")
}

config_path = os.path.join(os.path.expanduser("~"), ".ipykee.cfg")


def create_dirs(config):
    for dirname in [config['work-dir'], config['project-dir'], config['git-media-path']]:
        if not os.path.isdir(dirname):
            os.makedirs(dirname)


class Settings(object):
    def __init__(self):
        self.__config = default_config
        try:
            with open(config_path, "r") as tmp:
                self.__config.update(yaml.load(tmp))
        except:
            self.__config = {}
            self.set_config(default_config)
        create_dirs(self.__config)

    def refresh_config(self):
        with open(config_path, "r") as tmp:
            self.__config = yaml.load(tmp)
        create_dirs(self.__config)

    def set_config(self, new_options):
        self.__config.update(new_options)
        with open(config_path, "w") as tmp:
            yaml.dump(self.__config, tmp)
        create_dirs(self.__config)

    def __getitem__(self, option):
        return self.__config[option]

    def __repr__(self):
        return repr(self.__config)
