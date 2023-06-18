from flask import Flask, request, redirect, session, render_template
from spotipy.oauth2 import SpotifyOAuth
import os
from spotipy import Spotify
from dotenv import load_dotenv

#load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Spotify OAuth setup
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="user-library-read user-top-read playlist-modify-public user-read-recently-played user-follow-read",
    cache_path=None,
    show_dialog=True
)

# Function to handle pagination
def get_all_items(sp, endpoint, *args, **kwargs):
    items = []
    results = endpoint(*args, **kwargs)

    while True:
        items.extend(results['items'])
        if results['next']:
            results = sp.next(results)
        else:
            break

    return items

@app.route('/')
def index():
    token_info = session.get("token_info", None)
    if token_info:
        # User is already authenticated
        return redirect('/home')
    else:
        # User is not authenticated
        return render_template('index.html')

# Login route
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# Callback route
@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect('/home')

# Home route
@app.route('/home')
def home():
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect('/login')
    sp = Spotify(auth=token_info['access_token'])

    # Fetch user's top tracks
    top_tracks = get_all_items(sp, sp.current_user_top_tracks)
    top_tracks_info = [
        {'name': track['name'], 'artists': ', '.join([artist['name'] for artist in track['artists']]), 'image': track['album']['images'][0]['url']} 
        for track in top_tracks
    ]

    # Fetch user's top artists
    top_artists = get_all_items(sp, sp.current_user_top_artists)
    artist_names = [artist['name'] for artist in top_artists]
    artist_ids = [artist['id'] for artist in top_artists]

    # Select seed tracks and artists
    seed_tracks = [track['id'] for track in top_tracks[:2]]
    seed_artists = artist_ids[:3]

    # Get recommendations
    recommendations = sp.recommendations(seed_tracks=seed_tracks, seed_artists=seed_artists)
    recommended_track_info = [
        {'name': track['name'], 'artists': ', '.join([artist['name'] for artist in track['artists']]), 'image': track['album']['images'][0]['url']} 
        for track in recommendations['tracks']
    ]
    # Return parsed data
    return render_template(
        'home.html', 
        top_tracks=top_tracks_info, 
        top_artists=artist_names, 
        recommended_tracks=recommended_track_info
    )

# Refresh token if needed
@app.before_request
def refresh_token():
    if session.get('token_info'):
        if sp_oauth.is_token_expired(session['token_info']):
            session['token_info'] = sp_oauth.refresh_access_token(session['token_info']['refresh_token'])

if __name__ == '__main__':
    app.run(debug=True)

