from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import configparser
import os


class SlackBot:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('../config/slack.ini')
        oauth_token = config['credentials']['oauth_token']
        self.client = WebClient(token=oauth_token)
        
    def send_message(self, channel, text):
        try:
            self.client.chat_postMessage(
                channel=channel, 
                text=text
            )
        except Exception as e:
            print(e)