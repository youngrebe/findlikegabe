import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from . import json_utils
from .models import FRIEND, COMMENT
from .steamhistory import GetProfileHistory

STEAM_API_TOKEN = json_utils.loadToken()

# ======== SYNC ======== #

def IsTokenValid(token: str):
    url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={token}&steamids=76561198842603734"
    response = requests.get(url)
    return response.status_code == 200

def GetSteamID(url: str):
    custom_id = url.split("/id/")[-1]
    url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={STEAM_API_TOKEN}&vanityurl={custom_id}"
    response = requests.get(url)
    data = response.json()
    return data["response"]["steamid"]

def GetPlayerSummary(steamID: str):
    url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_TOKEN}&steamids={steamID}"
    response = requests.get(url)
    data = response.json()
    return data["response"]["players"][0]

def GetProfileArchive(steamID: str):
    return GetProfileHistory(steamID)

def GetProfileComments(steamID: str):
    steamID = int(steamID)
    comments = []

    url = f"https://steamcommunity.com/comment/Profile/render/{steamID}/-1/?start=0&count=1"
    response = requests.get(url)
    data = response.json()

    success = data.get("success", False)
    error_msg = data.get("error", "")
    total_count = data.get("total_count", 0)

    if not success or error_msg == "This profile is private." or total_count == 0:
        return []

    choise = ""
    if total_count > 1000:
        choise = input("❗ Target has over 1,000 comments, take first 1,000? (Y/N): ")
    if choise != "N":
        total_count = min(total_count, 1000)

    def parse_html(html):
        soup = BeautifulSoup(html, "html.parser")
        result = []
        for block in soup.find_all("div", class_="commentthread_comment"):
            author_tag = block.find("a", class_="commentthread_author_link")
            id3 = author_tag.get("data-miniprofile")
            author_id = str(int(id3) + 76561197960265728)
            timestamp_tag = block.find("span", class_="commentthread_comment_timestamp")
            unix_time = timestamp_tag["data-timestamp"]
            text_tag = block.find("div", class_="commentthread_comment_text")
            comment_text = text_tag.get_text(separator="\n").strip()
            result.append(COMMENT(author_id, unix_time, comment_text))
        return result

    if total_count <= 700:
        response = requests.get(f"https://steamcommunity.com/comment/Profile/render/{steamID}/-1/?start=0&count={total_count}")
        return parse_html(response.json()["comments_html"])

    iterations = (total_count + 699) // 700
    for i in range(iterations):
        response = requests.get(f"https://steamcommunity.com/comment/Profile/render/{steamID}/-1/?start={i * 700}&count=700")
        comments.extend(parse_html(response.json()["comments_html"]))

    return comments

# ======== ASYNC ======== #

FRIENDLIST_URL = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={token}&steamid={steamID}&relationship=friend"

async def _fetch_friendlist(session, steamID, retries=3):
    """
    Single request → returns (is_public, friends).
    - False, [] → private
    - None, []  → failed after retries (skip safely)
    - True, [...] → success
    """
    url = FRIENDLIST_URL.format(token=STEAM_API_TOKEN, steamID=steamID)
    for attempt in range(retries):
        try:
            async with session.get(url) as resp:
                if resp.status == 401:
                    return False, []
                if resp.status == 429:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                text = await resp.text()
                if not text.strip():
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                import json
                data = json.loads(text)
                friends = [
                    FRIEND(f["steamid"], f["friend_since"])
                    for f in data.get("friendslist", {}).get("friends", [])
                ]
                return True, friends
        except Exception:
            await asyncio.sleep(1 * (attempt + 1))
    return None, []

async def _fetch_summaries_chunk(session, ids, retries=3):
    url = (
        f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
        f"?key={STEAM_API_TOKEN}&steamids={','.join(map(str, ids))}"
    )
    for attempt in range(retries):
        try:
            async with session.get(url) as resp:
                if resp.status == 429:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                text = await resp.text()
                if not text.strip():
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                import json
                data = json.loads(text)
                return data.get("response", {}).get("players", [])
        except Exception:
            await asyncio.sleep(1 * (attempt + 1))
    return []

# ======== PUBLIC ======== #

def IsFriendlistPublic(steamID):
    async def _run():
        async with aiohttp.ClientSession() as session:
            is_public, _ = await _fetch_friendlist(session, steamID)
            return bool(is_public)
    return asyncio.run(_run())

def GetFriendlist(steamID):
    async def _run():
        async with aiohttp.ClientSession() as session:
            _, friends = await _fetch_friendlist(session, steamID)
            return friends
    return asyncio.run(_run())

async def GetPlayerSummariesAsync(steamIDs):
    if not steamIDs:
        return []
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_summaries_chunk(session, steamIDs[i:i + 100]) for i in range(0, len(steamIDs), 100)]
        chunks = await asyncio.gather(*tasks)
    result = []
    for chunk in chunks:
        result.extend(chunk)
    return result

def GetPlayerSummaries(steamIDs):
    return asyncio.run(GetPlayerSummariesAsync(steamIDs))

# ======== HANDSHAKES ======== #

async def _check_and_get(session, steamID, target_steamID):
    is_public, friends = await _fetch_friendlist(session, steamID)
    if not is_public:
        return None
    return steamID, friends

async def _run_handshake(candidate_ids, target_steamID, collect_friend_ids=False):
    found_friends = []
    collected_ids = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=30)) as session:
        tasks = [_check_and_get(session, sid, target_steamID) for sid in candidate_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if result is None or isinstance(result, Exception):
            continue
        steamID, friends = result
        for friend in friends:
            if friend.steamID == target_steamID:
                found_friends.append(FRIEND(steamID, friend.friend_since))
        if collect_friend_ids:
            collected_ids.extend([f.steamID for f in friends])

    if collect_friend_ids:
        return found_friends, collected_ids
    return found_friends

async def resolve_handshake_1(commentator_ids, target_steamID):
    return await _run_handshake(commentator_ids, target_steamID, collect_friend_ids=True)

async def resolve_handshake_2(candidate_ids, target_steamID):
    return await _run_handshake(candidate_ids, target_steamID, collect_friend_ids=True)

async def resolve_handshake_3(candidate_ids, target_steamID):
    return await _run_handshake(candidate_ids, target_steamID, collect_friend_ids=False)
