import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import os
from dotenv import load_dotenv
from googlesearch import search
import re

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

		playlist_name = re.sub(r'[^\x00-\x7F]+', '', playlist_name)

		if not any(p['name'] == playlist_name for p in unique_playlists):
			print(f"Playlist found: {playlist_name} by {playlist_creator_name}")
			include_playlist = input("Include this playlist? (Y/N): ").strip().lower()
			if include_playlist == 'y':
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
						artists = ', '.join([artist['name'] for artist in track['track']['artists'][:2]])
						album_name = track['track']['album']['name']
						duration_ms = track['track']['duration_ms']

						track_name = re.sub(r'[^\x00-\x7F]+', '', track_name)
						artists = re.sub(r'[^\x00-\x7F]+', '', artists)
						album_name = re.sub(r'[^\x00-\x7F]+', '', album_name)

						if not any(t['name'] == track_name for t in unique_tracks):
							unique_tracks.append({
								'name': track_name,
								'artists': artists,
								'album_name': album_name,
								'duration_ms': duration_ms / 1000,
								'playlist_name': playlist_name
							})
							print(f"Added '{track_name}' by {artists} from '{playlist_name}' (Album: {album_name})")
						else:
							repeat_tracks += 1
					except (TypeError, KeyError):
						pass

				with open('songs.json', 'w') as json_file:
					json.dump(unique_tracks, json_file, indent=4)

	offset += 50

print(f"Success! All playlists scanned.")

def findYoutubeLink(song_name, artist_name, album_name=None):
	query = f"{song_name} {album_name} {artist_name} Official YouTube"
	
	search_result = list(search(query, num=1, stop=1, pause=2))

	if search_result and "youtube.com/watch" in search_result[0]:
		return search_result[0]

	return None

with open('songs.json', 'r') as json_file:
	songs_data = json.load(json_file)

for song_info in songs_data:
	if "youtube_link" in song_info and song_info["youtube_link"]:
		continue

	song_name = song_info["name"]
	artist_name = song_info["artists"]
	album_name = song_info["album_name"]

	song_name = re.sub(r'[^\x00-\x7F]+', '', song_name)
	artist_name = re.sub(r'[^\x00-\x7F]+', '', artist_name)
	album_name = re.sub(r'[^\x00-\x7F]+', '', album_name)

	print(f"Searching for {song_name} by {artist_name} ({album_name})")

	youtube_link = findYoutubeLink(song_name, artist_name, album_name)

	if youtube_link:
		song_info["youtube_link"] = youtube_link
		print(f"Found YouTube link: {youtube_link}")

	with open('songs.json', 'w') as json_file:
		json.dump(songs_data, json_file, indent=4)

import pytube

def download_song(youtube_link, song_name, album_name):
	try:
		yt = pytube.YouTube(youtube_link)

		audio_stream = yt.streams.filter(only_audio=True).first()

		os.makedirs("downloaded-songs", exist_ok=True)

		song_name = re.sub(r'[^\x00-\x7F]+', '', song_name)
		album_name = re.sub(r'[^\x00-\x7F]+', '', album_name)

		file_path = os.path.join("downloaded-songs", f"{song_name}.mp4")

		if os.path.exists(file_path):
			print(f"Skipping download for {yt.title}. File already exists.")
		else:
			audio_file = audio_stream.download(output_path="./downloaded-songs", filename=f"{song_name}.mp4")
			print(f"Downloaded: {yt.title}")
	except Exception as e:
		print(f"Error downloading {youtube_link}: {str(e)}")

if __name__ == "__main__":
	with open('songs.json', 'r') as json_file:
		songs_data = json.load(json_file)

	for song_info in songs_data:
		youtube_link = song_info.get("youtube_link")
		album_name = song_info.get("album_name")

		if youtube_link:
			download_song(youtube_link, song_info["name"], album_name)
		else:
			print(f"No YouTube link found for {song_info['name']} by {song_info['artists']}")