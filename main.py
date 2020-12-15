import urllib.request, urllib.error, urllib.parse, json
from flask import Flask, render_template, request, session, redirect, url_for

# import modules for data store
from google.cloud import ndb

client = ndb.Client()

app = Flask(__name__)

from apikey import CLIENT_ID, CLIENT_SECRET
app.secret_key = CLIENT_SECRET


# Storage
class SpotifyUserKeyData(ndb.Model):
    userid = ndb.StringProperty(required=True)
    access_token = ndb.StringProperty(required=True)
    refresh_token = ndb.StringProperty(required=False)


# Helper functions

# Borrow sean's example in s18
def spotifyurlfetch(url, access_token, params=None):
    headers = {'Authorization': 'Bearer ' + access_token}
    req = urllib.request.Request(
        url=url,
        data=params,
        headers=headers
    )
    response = urllib.request.urlopen(req)
    return response.read()


# Handler Function

# Pages for app
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/comparingOutput")
def analysis():
    if 'user_id' in session:
        with client.context():
            user = SpotifyUserKeyData.query().filter(SpotifyUserKeyData.userid == session['user_id']).get()
    else:
        user = None

    if user != None:
        # if logged in, get their personalization and profile
        userTopArtist = "https://api.spotify.com/v1/me/top/artists"
        userTopTracks = "https://api.spotify.com/v1/me/top/tracks"

        userprofile = json.loads(spotifyurlfetch('https://api.spotify.com/v1/me', user.access_token))
        artistUserResponse = json.loads(spotifyurlfetch(userTopArtist, user.access_token))
        userTopArtist = artistUserResponse['items']
        tracksUserResponse = json.loads(spotifyurlfetch(userTopTracks, user.access_token))
        userTopTracks = tracksUserResponse['items']

        minhProfile = json.loads(spotifyurlfetch("https://api.spotify.com/v1/users/minh.dos", user.access_token))
        minhTopArtistsResponse = json.load(open("minhTopArtists.json", "r"))
        minhTopArtists = minhTopArtistsResponse['items']
        minhTopTracksResponse = json.load(open("minhTopTracks.json", "r"))
        minhTopTracks = minhTopTracksResponse['items']

        #analysis
        # get a list of names of artist and tracks for me and name {name: {popuarity: 34, genre: }, name:{}}
        minhArtistsDict = {}
        for artistInfo in minhTopArtists:
            if artistInfo['name'] not in minhArtistsDict:
                minhArtistsDict[artistInfo['name']] = {}
                minhArtistsDict[artistInfo['name']]['genres'] = artistInfo['genres']
                minhArtistsDict[artistInfo['name']]['images'] = artistInfo['images']
                minhArtistsDict[artistInfo['name']]['artistlink'] = artistInfo['external_urls']['spotify']

        userArtistsDict = {}
        for artistInfo in userTopArtist:
            if artistInfo['name'] not in userArtistsDict:
                userArtistsDict[artistInfo['name']] = {}
                userArtistsDict[artistInfo['name']]['genres'] = artistInfo['genres']
                userArtistsDict[artistInfo['name']]['images'] = artistInfo['images']
                userArtistsDict[artistInfo['name']]['artistlink'] = artistInfo['external_urls']['spotify']


        # [song1, song2] or {title song: {artist_name: ariana, song_preview: some link}}
        minhTracksDict = {}
        for tracksInfo in minhTopTracks:
            # artist = tracksInfo['artists'][0]['name']
            if tracksInfo['name'] not in minhTracksDict:
                minhTracksDict[tracksInfo['name']] = {}
                if tracksInfo['preview_url'] is None:
                    minhTracksDict[tracksInfo['name']]['song_preview'] = tracksInfo['external_urls']['spotify']
                else:
                    minhTracksDict[tracksInfo['name']]['song_preview'] = tracksInfo['preview_url']

        userTracksDict = {}
        for tracksInfo in userTopTracks:
            if tracksInfo['name'] not in userTracksDict:
                userTracksDict[tracksInfo['name']] = {}
                if tracksInfo['preview_url'] is None:
                    userTracksDict[tracksInfo['name']]['song_preview'] = tracksInfo['external_urls']['spotify']
                else:
                    userTracksDict[tracksInfo['name']]['song_preview'] = tracksInfo['preview_url']

        compatibilityOfArtists = 0  #15 artists
        compatibilityOfTracks = 0  #20 tracks

        totalSongsOfUser = 0
        if tracksUserResponse['total'] >= tracksUserResponse['limit']:
            totalSongsOfUser = tracksUserResponse['limit']
        elif tracksUserResponse['total'] < tracksUserResponse['limit']:
            totalSongsOfUser = tracksUserResponse['total']

        totalArtistsOfUser = 0
        if artistUserResponse['total'] >= artistUserResponse['limit']:
            totalArtistsOfUser = artistUserResponse['limit']
        elif artistUserResponse['total'] < artistUserResponse['limit']:
            totalArtistsOfUser = artistUserResponse['total']

        for artist in minhArtistsDict.keys():
            if artist in userArtistsDict.keys():
                compatibilityOfArtists += 1

        for track in minhTracksDict.keys():
            if track in userTracksDict.keys():
                compatibilityOfTracks += 1


        percentTracks = (compatibilityOfTracks / totalSongsOfUser) * 100.0
        percentArtist = (compatibilityOfArtists / totalArtistsOfUser) * 100.0
        avgCompatibilityPercent = (percentTracks + percentArtist) / 2

        #creating a variable that determine percentage
        #use a for loop to compare
        # store result into that variable created and multiply by 100
        #also store the images url



    return render_template("userOutput.html", user=user, percentTracks=percentTracks, percentArtist=percentArtist,
                            avgCompatibilityPercent=avgCompatibilityPercent, minhTracksDict=minhTracksDict,
                            minhArtistsDict=minhArtistsDict, userTracksDict=userTracksDict,
                            userArtistsDict=userArtistsDict, minhProfile=minhProfile, userProfile=userprofile)


# # need Oauth before handling
# # Definitely reference on Sean's example on doing OAUTH with Spotify
# # Sorry that it might be looking similar, and I borrowed it from s18
@app.route("/auth/login")
def login_handler():
    # yes login in
    argumentsSpotify = {}
    argumentsSpotify['client_id'] = CLIENT_ID
    verification_code = request.args.get("code")

    if verification_code:
        argumentsSpotify["client_secret"] = CLIENT_SECRET
        argumentsSpotify["grant_type"] = 'authorization_code'
        argumentsSpotify["code"] = verification_code
        argumentsSpotify['redirect_uri'] = request.base_url
        somedata = urllib.parse.urlencode(argumentsSpotify).encode("utf-8")

        tokenurl = "https://accounts.spotify.com/api/token"
        req = urllib.request.Request(tokenurl)
        tokenresponse = urllib.request.urlopen(req, data=somedata)
        tokenresponse_dict = json.loads(tokenresponse.read())
        access_token = tokenresponse_dict["access_token"]
        refresh_token = tokenresponse_dict["refresh_token"]
        userprofile = json.loads(spotifyurlfetch('https://api.spotify.com/v1/me', access_token))

        # some user into storage
        userid = str(userprofile["id"])
        with client.context():
            someuser = SpotifyUserKeyData.query().filter(SpotifyUserKeyData.userid == userid).get()
            if someuser == None:
                someuser = SpotifyUserKeyData(
                    userid=userid,
                    access_token=access_token,
                    refresh_token=refresh_token)
            else:
                someuser.userid = userid
                someuser.access_token = access_token
                someuser.refresh_token = refresh_token

            someuser.put()

        session['user_id'] = someuser.userid
        return redirect(url_for('analysis'))
    else:
        # not logged in
        argumentsSpotify['redirect_uri'] = request.base_url
        argumentsSpotify['response_type'] = "code"
        argumentsSpotify['scope'] = "user-read-email user-read-private user-top-read"
        argumentsSpotify['show_dialog'] = True
        AuthUrl = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(argumentsSpotify)

        return redirect(AuthUrl)


# Log out in the next page
@app.route("/auth/logout")
def logout_handler():
    session.pop('user_id')
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)



