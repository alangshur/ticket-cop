from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime
import configparser
import requests

### INPUTS
EVENT_CLASSIFICATION = 'music'
EVENT_COUNTRY_CODE = 'US'

# get credentials
config = configparser.ConfigParser()
config.read('../config/ticketmaster.ini')
CONSUMER_KEY = config['credentials']['consumer_key']
BASE_URL = config['urls']['base_events_url']

# get timezone dt
tz = gettz('America/New_York')
dt_now_utc = datetime.utcnow()
dt_now = dt_now_utc.astimezone(tz)

events_data = []
page_num = 0

while True:

    query_params = {
        'apikey': CONSUMER_KEY,

        'size': 200,
        'page': page_num,

        'classificationName': EVENT_CLASSIFICATION,
        'countryCode': EVENT_COUNTRY_CODE,

        'sort': 'date,asc',
        'startDateTime': dt_now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'onsaleOnAfterStartDate': dt_now_utc.strftime('%Y-%m-%d'),

        'includeTBA': 'no',
        'includeTBD': 'no',
        'includeTest': 'no'
    }

    response = requests.get(
        url=BASE_URL,
        params=query_params
    )

    contents = response.json()
    total_pages = contents['page']['totalPages']
    events_data.extend(contents['_embedded']['events'])
    if total_pages == page_num + 1: break
    else: page_num += 1

public_sale_data = []
presale_data = []

for event in events_data:
    try:
        event_name = event['name']
        event_dt = parser.parse(event['dates']['start']['dateTime']).astimezone(tz)

        if 'public' in event['sales']:
            sale = event['sales']['public']
            sale_name = 'public'
            sale_start_dt = parser.parse(sale['startDateTime']).astimezone(tz)
            sale_end_dt = parser.parse(sale['endDateTime']).astimezone(tz)
            sale_started = bool(dt_now >= sale_start_dt)
            sale_ended = bool(dt_now >= sale_end_dt)
            sale_in_progress = bool(sale_started and not sale_ended)
            if not sale_started: sale_status = 'not_started'
            elif sale_in_progress: sale_status = 'in_progress'
            elif sale_ended: sale_status = 'over'
            public_sale_data.append({
                'event_name': event_name,
                'event_dt': event_dt,
                'sale_start_dt': sale_start_dt,
                'sale_end_dt': sale_end_dt,
                'sale_status': sale_status
            })

        if 'presales' in event['sales']:
            for presale in event['sales']['presales']:
                sale_name = presale['name']
                sale_start_dt = parser.parse(presale['startDateTime']).astimezone(tz)
                sale_end_dt = parser.parse(presale['endDateTime']).astimezone(tz)
                sale_started = bool(dt_now >= sale_start_dt)
                sale_ended = bool(dt_now >= sale_end_dt)
                sale_in_progress = bool(sale_started and not sale_ended)
                if not sale_started: sale_status = 'not_started'
                elif sale_in_progress: sale_status = 'in_progress'
                elif sale_ended: sale_status = 'over'
                presale_data.append({
                    'event_name': event_name,
                    'event_dt': event_dt,
                    'sale_name': sale_name,
                    'sale_start_dt': sale_start_dt,
                    'sale_end_dt': sale_end_dt,
                    'sale_status': sale_status
                })

                # print presale less than a week away
                if sale_status == 'not_started' and (sale_start_dt - dt_now).days < 14:
                    print('******* UPCOMING PRESALE *******')
                    print('Event: {}'.format(event_name))
                    print('Event date: {}'.format(event_dt.strftime('%Y-%m-%d')))
                    print('Sale name: {}'.format(sale_name))
                    print('Opens in: {} days'.format((sale_start_dt - dt_now).days))
                    print('********************************')
                    print('\n\n\n')

    except:
        pass