from fake_useragent import UserAgent
from comms.slack import SlackBot
from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime
import traceback
import requests
import time
import json


def humanbytes(B):
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)
    GB = float(KB ** 3)
    TB = float(KB ** 4)

    if B < KB:
        return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B/KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B/MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B/GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B/TB)


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
                    slack.send_message('tixr-scans', '*ALERT*: New sales data posted for {} at {} on {}.'.format(event['name'], event['venue']['name'], event['date']))
                    slack.send_message('tixr-scans-raw', '```\n{}```'.format(json.dumps(event, indent=2)))

    return events_data


warning_stop_threshold = 5
warning_increment = 1
no_warning_decrement = 0.25
warning_stack = 0
max_avg_group_time = 10
sleep_time = 5
update_interval = 1000
it = 0

total_processed_data = 0
total_warnings = 0
daily_processed_data = 0
daily_warnings = 0
current_day = datetime.now(gettz('America/New_York')).strftime('%m-%d-%Y')

ua = UserAgent()
slack = SlackBot(test_mode=False)
past_events_data = {
    '160': None,   # LIV nightclub
    '161': None   # Story nightclub
}

print('Launching Tixr scanning bot.')
slack.send_message('tixr-scans', '*Info*: Launching Tixr scanning bot.')

try:
    while True:
        it += 1
        cur_time = datetime.now(gettz('America/New_York'))
        print('\rIteration: {} | Time: {}'.format(it, cur_time.strftime('%m-%d-%Y %H:%M:%S EDT')), end='')

        if cur_time.strftime('%m-%d-%Y') != current_day:
            current_day = cur_time.strftime('%m-%d-%Y')
            daily_processed_data = 0
            daily_warnings = 0
        
        if it % update_interval == 0:
            update_msg = \
                '*Update*:\n' + \
                'Time: {}\n'.format(cur_time.strftime('%m-%d-%Y %H:%M:%S EDT')) + \
                'Total processed data: {}\n'.format(humanbytes(total_processed_data)) + \
                'Total warnings: {}\n'.format(total_warnings) + \
                'Daily processed data: {}\n'.format(humanbytes(daily_processed_data)) + \
                'Daily warnings: {}'.format(daily_warnings)

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
                slack.send_message('tixr-scans', '*Warning*: Bot received {} status for group {}.'.format(status, group_id))
                warning_stack += warning_increment
                total_warnings += 1
                daily_warnings += 1
            else:
                response_size = len(response.content)
                total_processed_data += response_size
                daily_processed_data += response_size

                try: 
                    events_content = response.json()
                    past_events_data[group_id] = load_snapshot(
                        events_content,
                        past_events_data[group_id], 
                        slack
                    )
                except:
                    slack.send_message('tixr-scans', '*Warning*: Bot could not parse response for group {}.'.format(group_id))
                    warning_stack += warning_increment
                    total_warnings += 1
                    daily_warnings += 1

        if warning_stack > warning_stop_threshold:
            slack.send_message('tixr-scans', '*Error*: Bot reached warning threshold.')
            break
        else:
            warning_stack = max(0, warning_stack - no_warning_decrement)

        stop_time = time.time()
        avg_group_time = (stop_time - start_time) / len(past_events_data)
        if avg_group_time > max_avg_group_time:
            slack.send_message('tixr-scans', '*Warning*: Bot averaged {} seconds per group.'.format(round(avg_group_time, 3)))
            total_warnings += 1
            daily_warnings += 1

        time.sleep(sleep_time)

except KeyboardInterrupt: 
    pass
except Exception as e: 
    traceback.print_exc()
    slack.send_message('tixr-scans', '*Error*: Internal server error in Tixr scanning bot.')

print('\nShutting down Tixr scanning bot.')
slack.send_message('tixr-scans', '*Info*: Shutting down Tixr scanning bot.')