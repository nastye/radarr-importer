import json
import os
import re

import requests
import tmdbsimple as tmdb

###################
## FILL THESE IN ## 
###################

tmdb.API_KEY = 'tmdb api key goes here'
radarr_host = 'localhost'
radarr_port = '7878'
radarr_api_key = 'radarr api key goes here'
radarr_base_path = 'leave blank if no base path is set'
radarr_movies_dir = '/movies'
local_movies_dir = '/mnt/movies'
max_retries = 6

##########################
## DONT TOUCH PAST HERE ##
##      VERY FRAGILE    ##
##########################

radarr_socket = radarr_host + ':' + radarr_port
radarr_api_path = radarr_base_path + '/api/v3/movie'

movies = os.listdir(local_movies_dir)
movies_pattern = re.compile('^(.*) \((\d+)\)$')

r = requests.get('http://{}{}?apikey={}'.format(radarr_socket, radarr_api_path,
                                                radarr_api_key))

if not r.ok:
    exit()

radarr_movies = json.loads(r.text)
count_new = 0
count_failed = 0
count_existing = 0


def radarr_add_movie(movie, year, tmdb_result):

    global count_new
    global count_failed
    global count_existing

    for existing_movie in radarr_movies:
        if existing_movie['tmdbId'] == tmdb_result['id']:
            print('{} already exists in radarr'.format(movie))
            count_existing += 1
            return

    payload = {
        'title': tmdb_result['title'],
        'qualityProfileId': '4',
        'titleSlug':
        tmdb_result['title'].lower() + '-' + str(tmdb_result['id']),
        'monitored': 'true',
        'tmdbId': tmdb_result['id'],
        'year': year,
        'rootFolderPath': radarr_movies_dir,
        'hasFile': 'true',
        'minimumAvailability': 'announced',
        'addOptions': {}
    }

    num_retries = 0
    while num_retries < max_retries:
        if num_retries > 0:
            print('retrying...')
        try:
            r = requests.post('http://{}{}?apikey={}'.format(
                radarr_socket, radarr_api_path, radarr_api_key),
                              headers={'Content-Type': 'application/json'},
                              data=json.dumps(payload),
                              timeout=10)

            if not r.ok:
                for error in json.loads(r.text):
                    print(error)
                    count_failed = count_failed + 1
                    return

            count_new += 1
            print('{} was added successfully'.format(movie))
            return
        except requests.exceptions.ReadTimeout:
            print('timeout whilde adding {}'.format(movie))
            num_retries += 1

    count_failed += 1


for dir in movies:
    match = movies_pattern.match(dir)
    if match:
        print(match.group(1), match.group(2))
        resp = tmdb.Search().movie(query=match.group(1), year=match.group(2))
        if resp['total_results'] == 0:
            print('no matches found for {}'.format(match.group(1)))
            continue
        if resp['total_results'] == 1:
            #print('found one match for {}'.format(match.group(1)))
            radarr_add_movie(match.group(1), match.group(2),
                             resp['results'][0])
        if resp['total_results'] > 1:
            #print('found multiple matches for {}'.format(match.group(1)))
            radarr_add_movie(match.group(1), match.group(2),
                             resp['results'][0])
    print('---')

print('duplicates:', count_existing)
print('new:', count_new)
print('failed:', count_failed)
print('folders processed:' count_existing + count_new + count_failed)
