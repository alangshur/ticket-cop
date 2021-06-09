from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime
from comms.slack import SlackBot
import pandas as pd
import configparser
import traceback
import requests
import time


### INPUTS ###
EVENT_CLASSIFICATION = 'music'
EVENT_COUNTRY_CODE = 'US'
REFRESH_RATE_SECS = 30 * 60

### CREDENTIALS ###
config = configparser.ConfigParser()
config.read('../config/ticketmaster.ini')
CONSUMER_KEY = config['credentials']['consumer_key']
BASE_URL = config['urls']['base_events_url']

### SETUP ###
slack = SlackBot(test_mode=True)
tz = gettz('America/New_York')


def scan_pubic_sales(time_threshold_hours=1):

    # get timezone dt
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
            event_id = event['id']
            event_name = event['name']
            event_dt = parser.parse(event['dates']['start']['dateTime'])
            event_url = event['url']

            if 'public' in event['sales']:
                sale = event['sales']['public']
                sale_name = 'public'
                sale_start_dt = parser.parse(sale['startDateTime'])
                sale_end_dt = parser.parse(sale['endDateTime'])
                sale_started = bool(dt_now_utc >= sale_start_dt)
                sale_ended = bool(dt_now_utc >= sale_end_dt)
                sale_in_progress = bool(sale_started and not sale_ended)
                if not sale_started: sale_status = 'not_started'
                elif sale_in_progress: sale_status = 'in_progress'
                elif sale_ended: sale_status = 'over'
                public_sale_data.append({
                    'event_id': event_id,
                    'event_name': event_name,
                    'event_url': event_url,
                    'event_dt': event_dt,
                    'sale_starts_in': pd.Timedelta(sale_start_dt - dt_now_utc),
                    'sale_start_dt': sale_start_dt,
                    'sale_end_dt': sale_end_dt,
                    'sale_status': sale_status
                })

            if 'presales' in event['sales']:
                for presale in event['sales']['presales']:
                    sale_name = presale['name']
                    sale_start_dt = parser.parse(presale['startDateTime'])
                    sale_end_dt = parser.parse(presale['endDateTime'])
                    sale_started = bool(dt_now_utc >= sale_start_dt)
                    sale_ended = bool(dt_now_utc >= sale_end_dt)
                    sale_in_progress = bool(sale_started and not sale_ended)
                    if not sale_started: sale_status = 'not_started'
                    elif sale_in_progress: sale_status = 'in_progress'
                    elif sale_ended: sale_status = 'over'
                    presale_data.append({
                        'event_id': event_id,
                        'event_name': event_name,
                        'event_url': event_url,
                        'event_dt': event_dt,
                        'sale_name': sale_name,
                        'sale_starts_in': pd.Timedelta(sale_start_dt - dt_now_utc),
                        'sale_start_dt': sale_start_dt,
                        'sale_end_dt': sale_end_dt,
                        'sale_status': sale_status
                    })

        except Exception as e:
            print(e)

    if len(public_sale_data) == 0: return None
    else:
        public_sale_df = pd.DataFrame.from_records(public_sale_data)
        public_sale_df = public_sale_df[public_sale_df.sale_status == 'not_started']
        public_sale_df = public_sale_df[(public_sale_df.sale_starts_in.dt.days) < 1 & (public_sale_df.sale_starts_in.dt.days) < 1]
        public_sale_df = public_sale_df.sort_values(by='sale_starts_in', ascending=True)

        public_sale_df.index = public_sale_df.event_id
        public_sale_df = public_sale_df[['event_name', 'sale_starts_in', 'event_url']]
        return public_sale_df


print('Launching TM sales scanning bot.')
slack.send_message('tm-sales-scans', '*Info*: Launching TM sales scanning bot.')


try:
    while True:
        upcoming_sales_df = scan_pubic_sales()
        print(upcoming_sales_df)
        time.sleep(REFRESH_RATE_SECS)

except KeyboardInterrupt: 
    pass
except Exception as e: 
    traceback.print_exc()
    slack.send_message('tm-sales-scans', '*Error*: Internal server error in TM sales scanning bot.')


print('\nShutting down TM sales scanning bot.')
slack.send_message('tm-sales-scans', '*Info*: Shutting down TM sales scanning bot.')