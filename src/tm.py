from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime
import configparser
import requests

### INPUTS
EVENT_CLASSIFICATION = 'music'
COUNTRY_CODE = 'US'

# get timezone dt
tz = gettz('America/New_York')
dt_now = datetime.utcnow().astimezone(tz)

# get credentials
config = configparser.ConfigParser()
config.read('../config/ticketmaster.ini')
consumer_key = config['credentials']['consumer_key']
consumer_secret = config['credentials']['consumer_secret']

# build base query
base_query = 'https://app.ticketmaster.com/discovery/v2/events.json?countryCode=US&classificationName=music&apikey={}'.format(consumer_key)


## TODO:
# - build adaptive event query
# - only allows us to pull 1000 items per query and 200 items per request 
# - make a shifting date window of <1000 items per window where we do 5 requests per window of 200 items each






respone = requests.get(
    url='https://app.ticketmaster.com/discovery/v2/events.json?countryCode=US&classificationName=sport&apikey={}'.format(consumer_key)
)

data = respone.json()
events_data = data['_embedded']['events']
public_sale_data = []
presale_data = []

# for event in events_data:
#     try:
#         event_name = event['name']
#         event_dt = parser.parse(event['dates']['start']['dateTime']).astimezone(tz)

#         if 'public' in event['sales']:
#             sale = event['sales']['public']
#             sale_name = 'public'
#             sale_start_dt = parser.parse(sale['startDateTime']).astimezone(tz)
#             sale_end_dt = parser.parse(sale['endDateTime']).astimezone(tz)
#             sale_started = bool(dt_now >= sale_start_dt)
#             sale_ended = bool(dt_now >= sale_end_dt)
#             sale_in_progress = bool(sale_started and not sale_ended)
#             if not sale_started: sale_status = 'not_started'
#             elif sale_in_progress: sale_status = 'in_progress'
#             elif sale_ended: sale_status = 'over'
#             public_sale_data.append({
#                 'event_name': event_name,
#                 'event_dt': event_dt,
#                 'sale_start_dt': sale_start_dt,
#                 'sale_end_dt': sale_end_dt,
#                 'sale_status': sale_status
#             })

#         if 'presales' in event['sales']:
#             for presale in event['sales']['presales']:
#                 sale_name = presale['name']
#                 sale_start_dt = parser.parse(presale['startDateTime']).astimezone(tz)
#                 sale_end_dt = parser.parse(presale['endDateTime']).astimezone(tz)
#                 sale_started = bool(dt_now >= sale_start_dt)
#                 sale_ended = bool(dt_now >= sale_end_dt)
#                 sale_in_progress = bool(sale_started and not sale_ended)
#                 if not sale_started: sale_status = 'not_started'
#                 elif sale_in_progress: sale_status = 'in_progress'
#                 elif sale_ended: sale_status = 'over'
#                 presale_data.append({
#                     'event_name': event_name,
#                     'event_dt': event_dt,
#                     'sale_name': sale_name,
#                     'sale_start_dt': sale_start_dt,
#                     'sale_end_dt': sale_end_dt,
#                     'sale_status': sale_status
#                 })

#                 # print presale less than a week away
#                 if sale_status == 'not_started' and (sale_start_dt - dt_now).days < 14:
#                     print('******* UPCOMING PRESALE *******')
#                     print('Event: {}'.format(event_name))
#                     print('Event date: {}'.format(event_dt.strftime('%Y-%m-%d')))
#                     print('Sale name: {}'.format(sale_name))
#                     print('Opens in: {} days'.format((sale_start_dt - dt_now).days))
#                     print('********************************')
#                     print('\n\n\n')

#     except:
#         pass