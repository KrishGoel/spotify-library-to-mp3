import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import os

from dotenv import load_dotenv
load_dotenv()

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
redirect_uri = 'http://localhost:8000/callback'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope='playlist-read-private'))

user_info = sp.current_user()
user_id = user_info['id']

offset = 0

if not os.path.exists('playlists.json'):
	with open('playlists.json', 'w') as json_file:
		json.dump([], json_file)

if not os.path.exists('songs.json'):
	with open('songs.json', 'w') as json_file:
		json.dump([], json_file)

while True:
	user_playlists = sp.current_user_playlists(limit=50, offset=offset)

	if not user_playlists['items']:
		break

	for playlist in user_playlists['items']:
		playlist_name = playlist['name']
		playlist_creator_id = playlist['owner']['id']
		playlist_creator_name = playlist['owner']['display_name']

		if playlist_creator_id != user_id:
			continue

		with open('playlists.json', 'r') as json_file:
			unique_playlists = json.load(json_file)

		if not any(p['name'] == playlist_name for p in unique_playlists):
			playlist_tracks = []
			total_tracks = playlist['tracks']['total']
			repeat_tracks = 0

			while len(playlist_tracks) < total_tracks:
				results = sp.playlist_tracks(playlist['id'], offset=len(playlist_tracks))
				playlist_tracks.extend(results['items'])

			unique_playlists.append({
				'name': playlist_name,
				'creator': playlist_creator_name,
				'num_songs': total_tracks
			})

			with open('playlists.json', 'w') as json_file:
				json.dump(unique_playlists, json_file, indent=4)

			with open('songs.json', 'r') as json_file:
				unique_tracks = json.load(json_file)

			for track in playlist_tracks:
				try:
					track_name = track['track']['name']
					artists = ', '.join([artist['name'] for artist in track['track']['artists']])
					duration_ms = track['track']['duration_ms']

					if not any(t['name'] == track_name for t in unique_tracks):
						unique_tracks.append({
							'name': track_name,
							'artists': artists,
							'duration_ms': duration_ms / 1000,
							'playlist_name': playlist_name
						})
						print(f"Added '{track_name}' by {artists} from '{playlist_name}'")
					else:
						repeat_tracks += 1
				except (TypeError, KeyError):
					pass

			with open('songs.json', 'w') as json_file:
				json.dump(unique_tracks, json_file, indent=4)

	offset += 50

print(f"Success! All playlists scanned.")