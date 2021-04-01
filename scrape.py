import argparse
import json
import pandas as pd
import sys

from beepy import beep
from datetime import datetime
from pathlib import Path
from time import sleep
from urllib.request import urlopen


DATA_JSON_PATH = 'https://www.cvs.com/immunizations/covid-19-vaccine/immunizations/covid-19-vaccine.vaccine-status.{}.json?vaccineinfo'
SCRIPT_DIR = Path(__file__).parent.resolve()


def get_available_cities(data):
    return filter(lambda city: data[city] == 'Available', data)


def record(availabilities, args):
    # create output dir if needed
    outdir = SCRIPT_DIR / 'past_availabilities'
    outdir.mkdir(exist_ok=True)
    prev_availabilities = sorted(outdir.glob('*.csv'))

    # write latest availabilities to file
    timestamp = datetime.now().isoformat('.')
    outf = outdir / (timestamp.replace(':', '.') + '.csv')
    availabilities.to_csv(outf, index=False)

    # compare latest availabilities to previous,
    # optionally beeping if new locations detected
    if not prev_availabilities:
        if not args.quiet_all: beep(sound=6)
        return
    else:
        prev_availabilities = pd.read_csv(prev_availabilities[-1])

        if availabilities.equals(prev_availabilities):
            return
        else:
            if not args.quiet_all: beep(sound=6)


def scrape(state):
    state_json = DATA_JSON_PATH.format(state)

    with urlopen(state_json) as j:
        response = json.load(j)['responsePayloadData']['data']

    if response:
        return {city['city'].title() : city['status'] for city in response[state]}
    else:
        return None


def main():
    parser = argparse.ArgumentParser(
                      description='scrape public data on open COVID-19 '
                      'vaccination appointments, filter by distance, and '
                      'write results to a file')
    parser.add_argument('-i', '--interval_mins',
                        default=10,
                        type=int,
                        help='integer duration in minutes to sleep between '
                             'scrapes')
    quiets = parser.add_mutually_exclusive_group()
    quiets.add_argument('-q', '--quiet',
                        action='store_true',
                        help='surpress sounds, except those announcing '
                             'availabilities at new locations')
    quiets.add_argument('-Q', '--quiet_all',
                        action='store_true',
                        help='surpress all sounds')
    args = parser.parse_args()

    n_scrapes = 1
    interval_secs = args.interval_mins * 60

    cities_df = pd.read_csv(SCRIPT_DIR / 'utils' / 'uszips_mine.csv')

    while True:

        try:

            availabilities = []

            # scrape availability data from web and filter out fully booked
            for state, cities in cities_df.groupby('state'):
                data = scrape(state)
                if data is None:
                    continue
                available_cities = get_available_cities(data)
                cities = cities.loc[cities.city.isin(available_cities)]
                if not cities.empty:
                    availabilities.append(cities)

            # announce and record availabilities, if any
            print(n_scrapes, f"scrape{'s' if n_scrapes > 1 else ''} complete", end='')
            if availabilities:
                availabilities = (pd.concat(availabilities)
                                    .sort_values(by='distance')
                                    .astype({'distance' : int})
                                    .reset_index(drop=True))
                n = len(availabilities)
                print('\t--\t', n, f"AVAILABILIT{'Y' if n == 1 else 'IES'}!!")
                if not any([args.quiet, args.quiet_all]):
                    beep(sound=0)
                record(availabilities, args)
            else:
                print()

            # pause before repeating loop, displaying status
            m = args.interval_mins
            print('sleeping for', m, 'minute' + ('' if m == 1 else 's'))
            for i in range(interval_secs):
                mins = int((interval_secs - i) / 60)
                secs = round((interval_secs - i) % 60)
                end = '\n' if i+1 == interval_secs else '\r'
                print(f'{mins:0>2} min {secs:0>2} sec remaining', end=end)
                sleep(1)
            n_scrapes += 1

        except KeyboardInterrupt:

            print('Exiting...')
            break


if __name__ == '__main__':
    main()
