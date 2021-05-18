from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import configparser
import os


class SlackBot:

    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        config = configparser.ConfigParser()
        config.read('../config/slack.ini')
        oauth_token = config['credentials']['oauth_token']
        self.client = WebClient(token=oauth_token)
        
    def send_message(self, channel, text):
        try:
            if not self.test_mode:
                self.client.chat_postMessage(
                    channel=channel, 
                    text=text
                )
        except Exception as e:
            print(e)