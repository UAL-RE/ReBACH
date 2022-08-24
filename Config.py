import configparser

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('.env.ini')

    def figshare_config(self):
        return self.config['figshare_api']

    def system_config(self):
        return self.config['system']
