import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect, render_template
import requests



spotifyClientID = '6ed94440b43b4b369d3194454d3216df'
spotifyClientSecret = '5b91f861ade14088a742c6a91d8fe8df'


app = Flask(__name__, static_folder='static')

app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
app.secret_key = 'sfjsdnfdgn23tk2ngewg2ege3h#3532gf'
TOKEN_INFO = 'token_info'


# gets the token for spotify API to be used properly... refreshes so that it can be permanently used.
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for('login', _external=False))
    
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

# Creates spotify Oauth
def create_spotify_oauth():
    return SpotifyOAuth(
        spotifyClientID,
        spotifyClientSecret,
        redirect_uri = url_for('redirect_page', _external=True),
        scope = 'user-library-read playlist-modify-public playlist-modify-private'
    )

@app.route('/')
def front():  
    return(render_template('frontpage.html'))

# log in the spotify api thingie
@app.route('/login')
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)


# redirects the page to this so that it can redirect to the addPlaylist thingie
# creates new token and refresh and also clears previous sessions
@app.route('/redirect')
def redirect_page():
    session.clear() #ensures previous sessions are cleared
    code = request.args.get('code')
    token_info = create_spotify_oauth().get_access_token(code) #exchanges oauth code for access token
    session[TOKEN_INFO] = token_info
    return redirect('/selections')

@app.route('/selections')
def selections():
    return(render_template('selections.html'))

@app.route('/selections', methods=['POST'])
def form_post():
    litems = []
    for key, val in request.form.items():
        litems.append(val)
    global providedPlaylistName
    global bpmPlaylistName
    global BPM
    global flag
    providedPlaylistName = litems[0]
    bpmPlaylistName = litems[1]
    BPM = int(litems[2])
    flag = litems[3]
    return(redirect('/addPlaylist'))

@app.route('/addPlaylist')

def add_playlist_BPM():
    try:
        token_info = get_token()
    except:
        print("User not logged in")
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_id = sp.current_user()['id']

    saved_bpm_playlist_id = ""
    provided_playlist_id = ""

    

    # creates the playlist
    sp.user_playlist_create(user_id,bpmPlaylistName,True)

    # current_playlist items 
    current_playlists = sp.current_user_playlists()['items']

    # sets the playlist variable names and stuff
    for playlist in current_playlists:
        if(playlist['name'] == providedPlaylistName):
            provided_playlist_id = playlist['id']
        if(playlist['name'] == bpmPlaylistName):
            saved_bpm_playlist_id = playlist['id']
        
    offset = 0
    providedPlaylist = sp.playlist_items(provided_playlist_id)
    while len((sp.playlist_items(provided_playlist_id,None,limit=100,offset=offset))['items']) == 100:
        pagingPlaylist = sp.playlist_items(provided_playlist_id,None,limit=100,offset=100+offset)
        for each in pagingPlaylist['items']:
            providedPlaylist['items'].append(each)
        offset += 100
    



    # Looks at the user's playlist that they provide (providedPlaylist) and adds the tracks based on the BPM thing i set there
    song_uris = []
    for song in providedPlaylist['items']:
        response = requests.get(
            'https://api.spotify.com/v1/audio-features/'+song['track']['id'],

            headers={
                "Authorization": f"Bearer {token_info['access_token']}"
            },
        )

        # idk why the json_resp is none now when it was working earlier (????)
        # fix tmrw ? 
        json_resp = response.json()
        song_uri = song['track']['uri']


        # check for which thing insert
        if flag == "lower":
            if json_resp["tempo"] <= BPM:
                song_uris.append(song_uri)
        
        if flag == "higher":
            if json_resp["tempo"] >= BPM:
                song_uris.append(song_uri)

        if len(song_uris) == 100:
            sp.user_playlist_add_tracks(user_id, saved_bpm_playlist_id, song_uris, None)
            song_uris = []

    sp.user_playlist_add_tracks(user_id, saved_bpm_playlist_id, song_uris, None)


    # if playlist MIA.
    if not provided_playlist_id:
        return "Playlist not found"
    
    return ('done')

# stuff after so it goes to a completion page
# @app.route('/complete')
# def complete():
#     return(render_template('complete.html'))

# @app.route('/complete', methods=['POST'])
    
app.run(debug=True)