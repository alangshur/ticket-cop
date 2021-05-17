import configparser

config = configparser.ConfigParser()
config.read('../config/ticketmaster.ini')

consumer_key = config['credentials']['consumer_key']
consumer_secret = config['credentials']['consumer_secret']