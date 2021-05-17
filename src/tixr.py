from fake_useragent import UserAgent
from comms.slack import SlackBot
from dateutil import parser
from dateutil.tz import gettz
import requests
import time
import json


def load_snapshot(events_content, past_events_data, slack):
    
    events_data = {}
    for event in events_content:

        sales_data = {}
        sales = event['sales']
        for sale in sales:
            category = sale['category']
            
            sales_data[str(sale['id'])] = {
                'id': sale['id'],
                'category': sale['category'],
                'type': sale['type'],
                'status': sale['status'],
                'max_tickets': sale['maxTicketsAllowed'],
                'delivery_type': sale['deliveryType'],
                'seating_type': sale['seatingType'],
                'name': sale['tiers'][0]['name'],
                'price': float(sale['tiers'][0]['price']),
                'active': sale['tiers'][0]['active']
            }

            if category == 'GA':
                sales_data[str(sale['id'])]['sex'] = sale['tiers'][0]['name'].split(' ')[0].lower()
                sales_data[str(sale['id'])]['tier'] = int(sale['tiers'][0]['name'].split(' ')[-1])

        events_data[str(event['id'])] = {
            'id': event['id'],
            'group_id': event['groupId'],
            'date': parser.parse(
                timestr=event['formattedStartDate'], 
                tzinfos={'EDT': gettz('America/New_York')}
            ).strftime('%m-%d-%Y'),
            'name': event['name'],
            'venue': event['venue']['name'],
            'tz': event['venue']['timezone'],
            'status': event['status'],
            'sale_start': event['saleWindowStart'],
            'sale_end': event['saleWindowEnd'],
            'sales_data': sales_data
        }

    if past_events_data is not None:
        event_ids = list(events_data.keys())
        past_event_ids = list(past_events_data.keys())
        for event_id in event_ids:
            if event_id in past_event_ids:
                event = events_data[event_id]
                past_event = past_events_data[event_id]
                if len(event['sales_data']) != len(past_event['sales_data']):
                    slack.send_message('tixr-scans', 'New sales data posted for {} at {} on {}.'.format(event['name'], event['venue']['name'], event['date']))
                    slack.send_message('tixr-scans-raw', '```\n{}```'.format(json.dumps(event, indent=2)))

    return events_data


warning_stop_threshold = 5
warning_increment = 1
no_warning_decrement = 0.25
warning_stack = 0
max_avg_group_time = 10
sleep_time = 5

ua = UserAgent()
slack = SlackBot()
past_events_data = {
    '160': None,   # LIV nightclub
    '161': None   # Story nightclub
}

print('Launching Tixr scanning bot.')
slack.send_message('tixr-scans', 'Launching Tixr scanning bot.')

try:
    while True:
        start_time = time.time()
        for group_id in past_events_data:
        
            proxies = {'http' : 'http://adlproxy:proxypassword15@us.proxy.iproyal.com:12323'} 
            response = requests.get(
                url='https://www.tixr.com/api/groups/{}/events'.format(group_id), 
                headers={'User-Agent': ua.random}, 
                proxies=proxies
            )

            status = response.status_code
            if response.status_code != 200:
                slack.send_message('tixr-scans', 'Warning: Bot received {} status for group {}.'.format(status, group_id))
                warning_stack += warning_increment
            else:
                events_content = response.json()
                past_events_data[group_id] = load_snapshot(
                    events_content, 
                    past_events_data[group_id], 
                    slack
                )

        if warning_stack > warning_stop_threshold:
            slack.send_message('tixr-scans', 'Error: Bot reached warning threshold.')
            break
        else:
            warning_stack = max(0, warning_stack - no_warning_decrement)

        stop_time = time.time()
        avg_group_time = (stop_time - start_time) / len(past_events_data)
        if avg_group_time > max_avg_group_time:
            slack.send_message('tixr-scans', 'Warning: Bot averaged {} seconds per group.'.format(round(avg_group_time, 3)))
        
        time.sleep(sleep_time)

except KeyboardInterrupt: 
    pass
except Exception as e: 
    print('Internal error: ' + str(e))
    slack.send_message('tixr-scans', 'Error: Internal server error in Tixr scanning bot.')

print('Shutting down Tixr scanning bot.')
slack.send_message('tixr-scans', 'Shutting down Tixr scanning bot.')