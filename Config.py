import configparser


class Config:
    def __init__(self, fileName):
        self.config = configparser.ConfigParser()
        self.config.read(fileName)

    def figshare_config(self):
        return self.config['figshare_api']

    def system_config(self):
        return self.config['system']

    def add_setting(self, name, value, section='system'):
        self.config[section][name] = str(value)
