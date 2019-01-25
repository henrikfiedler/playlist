import sqlite3
import string
import random
import requests
import urllib
import json
import os
from urllib.parse import quote
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)

app.secret_key = "1234abcd"

con = sqlite3.connect('database.db')

c = con.cursor()

#c.execute('CREATE TABLE Lists(playlist_id VARCHAR (16) PRIMARY KEY, playlist_name VARCHAR (255), required_downvotes INTEGER (7), spotify_playlist_id VARCHAR(100), public VARCHAR(20), group_playlist VARCHAR(20), created_at DATE)')
#c.execute('CREATE TABLE Playlist(playlist_id VARCHAR (16), id INTEGER PRIMARY KEY AUTOINCREMENT, titel VARCHAR (100), interpret VARCHAR (100), spotify_uri VARCHAR (100), votes INTEGER (7))')

#c.execute('DROP TABLE Playlist_old')

con.commit()
con.close()


class Song():
    def __init__(self, id, titel, interpret, votes):
        self.id = id
        self.titel = titel
        self.interpret = interpret
        self.votes = votes


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/impressum")
def impressum():
    return render_template("impressum.html")


@app.route("/create", methods=['post'])
def create():

    required_downvotes = str(request.form['downvotes'])
    if required_downvotes != "":
        required_downvotes = int(required_downvotes)
        required_downvotes = - required_downvotes
    else:
        required_downvotes = -5
    playlist_name = request.form['playlist_name']
    public = request.form['public']
    group_playlist = request.form['group_playlist']

    def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    playlist_id = id_generator()

    # Generieren des Codes
    # Insert in DB

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('INSERT INTO Lists(playlist_id, playlist_name, required_downvotes, public, group_playlist, created_at) VALUES (?, ?, ?, ?, ?, CURRENT_DATE)', (playlist_id, playlist_name, required_downvotes, public, group_playlist))
        con.commit()

    return redirect(url_for("get_playlist", playlist_id=playlist_id))


@app.route("/<playlist_id>", methods=['get','post'])
def get_playlist(playlist_id):

    sort = session.get('sort', 'None')

    songs = []

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('SELECT playlist_name, group_playlist, required_downvotes FROM Lists WHERE playlist_id=?', (playlist_id,))
        for i in c:
            playlist_name = i[0]
            group_playlist = i[1]
            required_downvotes = - i[2]
        con.commit()

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        if sort == "id":
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY id ASC', (playlist_id,))
        elif sort == "id_reverse":
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY id DESC', (playlist_id,))
        elif sort == "titel":
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY titel ASC', (playlist_id,))
        elif sort == "titel_reverse":
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY titel DESC', (playlist_id,))
        elif sort == "interpret":
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY interpret ASC', (playlist_id,))
        elif sort == "interpret_reverse":
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY interpret DESC', (playlist_id,))
        else:
            c.execute('SELECT titel, interpret, votes FROM Playlist WHERE playlist_id=? ORDER BY id ASC', (playlist_id,))

        data = c.fetchall()
        a=1
        for i in data:
            song = Song(a, i[0], i[1], i[2])
            a = a+1
            songs.append(song)
            con.commit()


    return render_template("playlist.html", playlist_id=playlist_id, playlist_name=playlist_name, songs=songs, group_playlist=group_playlist, required_downvotes=required_downvotes, sort=sort)

@app.route("/sort", methods=['post'])
def sort():

    sort = request.form['sort']
    playlist_id = request.form['playlist_id']

    session['sort'] = sort

    return redirect(url_for("get_playlist", playlist_id=playlist_id))


@app.route("/add", methods=['post'])
def add_song():
    titel = request.form['titel']
    interpret = request.form['interpret']
    playlist_id = request.form['playlist_id']

    if titel != "":
        with sqlite3.connect("database.db", check_same_thread=False) as con:
            c = con.cursor()
            c.execute('INSERT INTO Playlist (playlist_id, titel, interpret, votes) VALUES(?, ?, ?, 0)',
                      (playlist_id, titel, interpret))
            con.commit()

    return redirect(url_for('get_playlist', playlist_id=playlist_id))

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

@app.route("/delete", methods=['post'])
def delete():
    titel = request.form['delete_titel']
    interpret = request.form['delete_interpret']
    playlist_id = request.form['playlist_id']

    with sqlite3.connect("database.db", check_same_thread=False) as con:
            c = con.cursor()
            c.execute('DELETE From Playlist WHERE playlist_id=? AND titel=? AND interpret=?', (playlist_id, titel, interpret))
            con.commit()


    return redirect(url_for('get_playlist', playlist_id=playlist_id))

@app.route("/downvote", methods=['post'])
def downvote():
    titel = request.form['downvote_titel']
    interpret = request.form['downvote_interpret']
    playlist_id = request.form['playlist_id']

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('SELECT votes from Playlist WHERE playlist_id=? AND titel=? AND interpret=?', (playlist_id, titel, interpret))
        for i in c:
            votes = i[0]
        con.commit()

    if votes <= -4:
        with sqlite3.connect("database.db", check_same_thread=False) as con:
                c = con.cursor()
                c.execute('DELETE From Playlist WHERE playlist_id=? AND titel=? AND interpret=?', (playlist_id, titel, interpret))
                con.commit()

    else:
        votes = votes -1
        with sqlite3.connect("database.db", check_same_thread=False) as con:
                c = con.cursor()
                c.execute('UPDATE Playlist set votes = ? WHERE playlist_id = ?', (votes, playlist_id))
                con.commit()

    return redirect(url_for('get_playlist', playlist_id=playlist_id))

@app.route("/getfile", methods=['post'])
def getfile():

    file = request.files['file']
    playlist_id = request.form['playlist_id']

    data = file.read()
    data = data.decode("utf-8")
    import_songs = []
    songs = data.rstrip().split("\n")
    for i in songs:
        song = i.split("\t")
        import_songs.append(song)

    for i in import_songs:
        titel = i[0]
        interpret = i[1]

        with sqlite3.connect("database.db", check_same_thread=False) as con:
            c = con.cursor()
            c.execute('INSERT INTO Playlist (playlist_id, titel, interpret, votes) VALUES(?, ?, ?, 0)', (playlist_id, titel, interpret))
            con.commit()

    return redirect(url_for('get_playlist', playlist_id=playlist_id))

@app.route("/spotify_code", methods=['post'])
def spotify_code():

    session['playlist_id'] = request.form['playlist_id']

    CLIENT_ID = "44d0a84f959746b5b4edf3fa80112625"
    SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
    CLIENT_SIDE_URL = "http://127.0.0.1"
    PORT = 5000
    REDIRECT_URI = "{}:{}/spotify_token".format(CLIENT_SIDE_URL, PORT)
    SCOPE = "playlist-modify-public playlist-modify-private"

    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        # "state": STATE,
        # "show_dialog": SHOW_DIALOG_str,
        "client_id": CLIENT_ID
    }

    url_args = "&".join(["{}={}".format(key, urllib.parse.quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@app.route("/spotify_token", methods=['get', 'post'])
def spotify_token():

    CLIENT_ID = "44d0a84f959746b5b4edf3fa80112625"
    CLIENT_SECRET = "fc1c0d674813407fa544857a4743b94f"

    code = str(request.args.get('code'))
    token_url = "https://accounts.spotify.com/api/token"
    data = {
        'grant_type': 'authorization_code',
        'code': str(code),
        'redirect_uri': 'http://127.0.0.1:5000/spotify_token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    post_request = requests.post(token_url, data=data)

    response_data = json.loads(post_request.text)
    access_token = response_data['access_token']
    # refresh_token = response_data["refresh_token"]
    # token_type = response_data["token_type"]
    # expires_in = response_data["expires_in"]

    authorization_header = {"Authorization":"Bearer {}".format(access_token)}

    api_url = "https://api.spotify.com/v1"
    user_profile_api_endpoint = "{}/me".format(api_url)
    profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
    profile_data = json.loads(profile_response.text)

    user_id = profile_data['id']
    session['access_token'] = access_token
    session['user_id'] = user_id

    return redirect("/spotify_create_playlist")

@app.route("/spotify_create_playlist")
def spotify_create_playlist():

    access_token = session.get('access_token', 'None')
    user_id = session.get('user_id', 'None')
    playlist_id = session.get('playlist_id', 'None')

    headers = {'Authorization': 'Bearer {}'.format(access_token), 'Content-Type': 'application/json'}

    api_url = "https://api.spotify.com/v1"
    playlist_endpoint = "{}/users/{}/playlists/".format(api_url, user_id)

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('SELECT playlist_name, public FROM Lists WHERE playlist_id=?', (playlist_id,))
        data = c.fetchall()
        for i in data:
            playlist_name = i[0]
            public = i[1]
        con.commit()

    playlist_name = str(playlist_name)
    data = {'name':playlist_name, 'public':public}

    playlist_data = requests.post(playlist_endpoint, data=json.dumps(data), headers=headers)
    response_data = json.loads(playlist_data.text)

    spotify_playlist_id = response_data['id']


    with sqlite3.connect("database.db", check_same_thread=False) as con:
            c = con.cursor()
            c.execute('UPDATE Lists set spotify_playlist_id = ? WHERE playlist_id = ?', (spotify_playlist_id, playlist_id))
            con.commit()
    return redirect("/spotify_get_tracks")

@app.route("/spotify_get_tracks")
def spotify_get_tracks():

    playlist_id = session.get('playlist_id', 'None')

    api_url = "https://api.spotify.com/v1"
    search_endpoint = "{}/search".format(api_url)

    access_token = session.get('access_token', 'None')
    headers = {"Authorization":"Bearer {}".format(access_token)}


    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('SELECT id, titel, interpret FROM Playlist WHERE playlist_id=? ORDER BY id ASC', (playlist_id,))
        data = c.fetchall()
        for i in data:
            id = i[0]
            titel = str(i[1])
            interpret = str(i[2])
            searchquery = titel+" "+interpret
            searchquery.replace(" ", "%")


            params = {'q': searchquery, 'type': 'track', 'limit': 1 }
            tracks_data = requests.get(search_endpoint, headers=headers, params=params)

            response_data = json.loads(tracks_data.text)
            #return str(response_data)
            test = response_data['tracks']['items']
            if test != []:
                spotify_uri = response_data['tracks']['items'][0]['uri']
                c.execute('UPDATE Playlist set spotify_uri = ? WHERE id = ? ', (spotify_uri, id))

        con.commit()

    return redirect("/spotify_add_tracks")


@app.route("/spotify_add_tracks")
def spotify_add_tracks():

    playlist_id = session.get('playlist_id', 'None')

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('SELECT spotify_playlist_id FROM Lists WHERE playlist_id=?', (playlist_id,))
        for i in c:
            data = str(i[0])
        spotify_playlist_id = data
        con.commit()

    api_url = "https://api.spotify.com/v1"
    add_endpoint = "{}/playlists/{}/tracks".format(api_url, spotify_playlist_id)

    access_token = session.get('access_token', 'None')
    headers = {'Authorization': 'Bearer {}'.format(access_token), 'Content-Type': 'application/json'}

    with sqlite3.connect("database.db", check_same_thread=False) as con:
        c = con.cursor()
        c.execute('SELECT spotify_uri FROM Playlist WHERE playlist_id=?', (playlist_id,))
        select = c.fetchall()
        a = 0
        track_load = []
        for i in select:
            if a <= 50:
                track = str(i[0])
                if track != "None":
                    track_load.append(track)
                    a = a+1
            elif a > 50:
                data = {'uris':track_load}
                r = requests.post(add_endpoint, headers=headers, data=json.dumps(data))
                a=0
                track_load = []
        data = {'uris':track_load}
        r = requests.post(add_endpoint, headers=headers, data=json.dumps(data))
        con.commit()

        return redirect(url_for('get_playlist', playlist_id=playlist_id))

if __name__ == '__main__':
    app.run()
