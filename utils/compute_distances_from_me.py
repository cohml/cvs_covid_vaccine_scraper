import pandas as pd
import sys

from geopy.distance import geodesic
from pathlib import Path


UTILS = Path(__file__).parent.resolve()
ZIPS_INFILE = UTILS / 'uszips_all.csv'
ZIPS_OUTFILE = UTILS / 'uszips_mine.csv'


def compute_distances_from_me(cities_df, my_zip):

    def compute_distance(other_city, my_city):
        other_city = other_city[['lat', 'lng']].values
        return round(geodesic(other_city, my_city).mi, 1)

    # get approx. coordinates of my location
    my_city = (cities_df.zip == my_zip)
    my_city = cities_df.loc[my_city, ['lat', 'lng']].mean().values

    # compute approx. distances from my location
    cities_df['distance'] = cities_df.apply(compute_distance,
                                            args=(my_city,),
                                            axis=1)

    return cities_df[['zip', 'distance', 'city', 'state']]


def filter_cities_by_distance(cities_df, my_radius):
    return (cities_df.loc[cities_df.distance <= my_radius]
                     .sort_values(by='distance')
                     .groupby(['city', 'state'])
                     .first()
                     .reset_index()
                     .sort_values(by=['state', 'city', 'distance']))


def get_cities_df(zips_infile):
    return (pd.read_csv(zips_infile)
              .rename(columns={'state_id' : 'state'})
              .loc[:, ['city', 'state', 'zip', 'lat', 'lng']])


def main():
    if len(sys.argv) < 3:
        print('Please pass your zip code and driving radius (miles) as the '
              'first and second args, respectively.\nExiting...')
        sys.exit(1)

    my_zip, my_radius, *_ = map(int, sys.argv[1:])

    cities_df = get_cities_df(ZIPS_INFILE)
    cities_df = compute_distances_from_me(cities_df, my_zip)
    cities_df = filter_cities_by_distance(cities_df, my_radius)
    cities_df.to_csv(ZIPS_OUTFILE, index=False)


if __name__ == '__main__':
    main()
