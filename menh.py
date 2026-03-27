import requests
import cohere
import os
import random
from cohere import ClientV2

# ==== CONFIG ====
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REDIRECT_URI = ""  
geoAPI_KEY = ""

co = ClientV2(os.getenv("COHERE_API_KEY"))

address = input("Enter your city and state and country: ")
print()
# Scopes allow access to more than just public playlists
def get_spotify_token(client_id, client_secret):
    auth_url = "https://accounts.spotify.com/api/token"
    auth_response = requests.post(
        auth_url,
        data={'grant_type': 'client_credentials'},  # must be form-data
        auth=(client_id, client_secret)            # correct way to send creds
    )

    if auth_response.status_code != 200:
        print("Failed to authenticate with Spotify:", auth_response.json())
        return None
    
    return auth_response.json()['access_token']

# ==== PLAYLIST DICTIONARY ====
BASE_PLAYLISTS = {
    "mixed": "796V2wqisW3fxD782FmGlh",
    "main_character": "5ig3xAJ18skkwAHLonx3Ln",
    "gym": "7B38UeZC9xohvf1iehQYfP",
    "calm": "3MelsVnZV5g03wyiJsybHk",
    "sad": "6ffBF0hREjEMqQ3yqsiOYK",
    "rap": "52rW9nNdH3F276trDJlHnu",
    "hindi": "2OfgmNnL4SRR8H7ZxNvZvm",
    "love": "37i9dQZF1DX7rOY2tZUw1k",
    "happy": "6a1v9M8uTtrcI5h7YwF8QO",
    "angry": "7B38UeZC9xohvf1iehQYfP",
    "motivated": "37i9dQZF1EIeBQQL9SHmkZ",
}

OPPOSITE_MOODS = {
    "sad": "happy",
    "happy": "sad",
    "angry": "calm",
    "calm": "angry",
    "love": "rap",
    "rap": "love",
    "mixed": "motivated",
    "motivated": "mixed",
    "hindi": "happy",
    "main_character": "calm",
    "gym": "calm"
}

# ==== HELPER ====
def extract_playlist_id(playlist):
    """Ensure we always extract clean Spotify playlist IDs"""
    if playlist and len(playlist) == 22 and " " not in playlist:
        return playlist
    return playlist.split("/")[-1].split("?")[0]

# ==== SPOTIFY HELPERS ====
def get_playlist_tracks(token, playlist_id):
    playlist_id = extract_playlist_id(playlist_id)  # ✅ Ensure ID is clean
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}
    tracks = []
    while url:
        r = requests.get(url, headers=headers)
        data = r.json()

        if "error" in data:
            print()
            break

        if "items" not in data:
            print()
            break

        for item in data["items"]:
            if item["track"] and item["track"].get("id"):
                tracks.append(item["track"]["id"])

        url = data.get("next")

    return set(tracks)

def find_matching_playlists(token, reference_tracks, query, top_n=2):
    url = f"https://api.spotify.com/v1/search?q={query}&type=playlist&limit=20"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    data = r.json()

    matches = []
    for p in data.get("playlists", {}).get("items", []):
        if not p or not p.get("id"):
            continue

        pid = p.get("id")
        pname = p.get("name", "Unknown")
        owner = p.get("owner", {}).get("display_name", "Unknown")
        external_url = p.get("external_urls", {}).get("spotify", "")

        try:
            tracks = get_playlist_tracks(token, pid)
            overlap = len(reference_tracks & tracks)
            similarity = overlap / len(reference_tracks) if reference_tracks else 0
            matches.append((similarity, pname, owner, external_url))
        except Exception:
            continue

    matches.sort(reverse=True, key=lambda x: x[0])
    return [m for m in matches if m[0] >= 0.5][:top_n]

# ==== EMOTION DETECTION + RESPONSE ====
def detect_emotions_and_response(text):
    

    emo_prompt = f"""
    Detect the main emotion of this user message in one word 
    (sad, happy, angry, calm, love, rap, mixed, motivated, main_character, gym).
    Message: "{text}"
    """
    emo_response = co.chat(
        model= 'command-a-03-2025',
        messages=[
            {
                "role": "user",
                "content": emo_prompt
            }
        ]
    )

    emotion= emo_response.message.content[0].text
    print("The detected emotion is:", emotion)
    resp_prompt = f"""
    The user said: "{text}"
    Write a short empathetic reply (1–2 sentences). 
    Do not mention 'emotion'.
    """
    resp_response = co.chat(
        model="command-a-03-2025",
        messages=[
            {
                "role": "user",
                "content": resp_prompt
            }
        ]
    )
    reply = resp_response.message.content[0].text

    return emotion, reply

# ==== MAIN ====

user_input = input("How are you feeling today? ")

# Step 1: Detect emotion & AI reply
main_emotion, ai_reply = detect_emotions_and_response(user_input)
print(ai_reply)

token = get_spotify_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)

# Step 2: Get base playlist
base_playlist = BASE_PLAYLISTS.get(main_emotion)

sp_songs = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
            "content": f"Suggest 3 songs that match the emotion of {main_emotion}. reply only with just the song names and singer and no other text. "
        }
    ]
)
print()
print("Here are some songs for you:\n")
print(sp_songs.message.content[0].text)

print("\nHere are some playlists that you can try:")
if base_playlist:
    base_id = extract_playlist_id(base_playlist)
    print(f"🎵\nhttps://open.spotify.com/playlist/{base_id}")
    base_tracks = get_playlist_tracks(token, base_id)
    matches = find_matching_playlists(token, base_tracks, main_emotion, top_n=2)
    for sim, pname, owner, url in matches:
        print(f"- 🔎 Similar vibe → {pname} by {owner} ({sim:.0%} match) → {url}")

# Step 3: Get opposite playlist
opposite_emotion = OPPOSITE_MOODS.get(main_emotion)
if opposite_emotion:
    opposite_playlist = BASE_PLAYLISTS.get(opposite_emotion)
    if opposite_playlist:
        opp_id = extract_playlist_id(opposite_playlist)
        print(f"\nhttps://open.spotify.com/playlist/{opp_id}")
        opp_tracks = get_playlist_tracks(token, opp_id)
        opp_matches = find_matching_playlists(token, opp_tracks, opposite_emotion, top_n=2)
        for sim, pname, owner, url in opp_matches:
            print(f"- 🔎 Opposite vibe → {pname} by {owner} ({sim:.0%} match) → {url}")

#GEOAPIFY

print("Here are some places you can visit:")
geo_output = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
           "content": f"From this message: {user_input}, tell me exactly 2 places each from the categories that are mentioned that I can visit in {address}. Only return the names of the places and their addresses. Make sure to not mention the subcategory names" 
        }
    ]
)      
gout = geo_output.message.content[0].text
print(gout)

movsug = "Suggest 3 movie that matches the emotion of " + main_emotion + ". reply only with just the movie names and no other text. NO NEED TO MENTION THE MOOD "
opmovsug = "Suggest one movie opposite to the emotion of " + main_emotion + ". reply only with just the movie names and no other text. "

mov_response = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
            "content": movsug
        }
    ]
)
opmov_response = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
            "content": opmovsug
        }
    ]
)
print()
print("Movies you should try:\n")
print()
print(mov_response.message.content[0].text)
print(f"4. {opmov_response.message.content[0].text}")

#BOOKS

booksug = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
           "content": f"Suggest 4 books that matches the emotion of {main_emotion}. reply only with just the book names and no other text. NO NEED TO MENTION THE MOOD " 
        }
    ]
)

print("\nBooks you should try:\n")
print(booksug.message.content[0].text)
print()

#FOOD

food_sug = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
           "content": f"Suggest 4 dishes that matches the emotion of {main_emotion}. reply only with just the dish names and no other text. NO NEED TO MENTION THE MOOD " 
        }
    ]
)

print("Dishes you should try:\n")
print(food_sug.message.content[0].text)
print()

#ACTIVITIES

act_sug = co.chat(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
           "content": f"Suggest 4 activities that matches the emotion of {main_emotion}. reply only with just the activity names and no other text. NO NEED TO MENTION THE MOOD " 
        }
    ]
)

print("Activities you should try:\n")
print(act_sug.message.content[0].text)
