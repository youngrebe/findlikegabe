import asyncio
import argparse
import aiohttp
from bs4 import BeautifulSoup
from lib import api
from lib.models import CONNECTION, FRIEND, COMMENT, NICKNAME, REALNAME, URL, AVATAR, SUMMARY
from lib import utils
from report import generate_report
from datetime import datetime

# ======== ARGS ======== #
parser = argparse.ArgumentParser(description="Steam OSINT tool")
parser.add_argument("--id", dest="steamID", required=True, help="Target Steam ID")
args = parser.parse_args()
target_steamID = args.steamID

# ======== BASE ======== #
FRIENDS = []
CONNECTIONS = []
COMMENTS = []

# ======== SUMMARY ======== #
target_summary = api.GetPlayerSummary(target_steamID)
target_avatar = target_summary["avatarfull"]
target_nickname = target_summary["personaname"]
target_creation_date = target_summary.get("timecreated", None)

print("\n[+] SUMMARY")

# ======== ARCHIVE ======== #
ARCHIVE_NICKNAMES, ARCHIVE_REAL_NAMES, ARCHIVE_URLS, ARCHIVE_AVATARS = api.GetProfileArchive(target_steamID)
print("[+] ARCHIVE")

# ======== COMMENTS ======== #
COMMENTS = api.GetProfileComments(target_steamID)
for comment in COMMENTS:
    CONNECTIONS.append(CONNECTION(comment.authorID, comment.publishedAt))

print("\n[+] COMMENTS")

# ======== FRIENDS ======== #
IS_FRIENDLIST_PUBLIC = api.IsFriendlistPublic(target_steamID)
if IS_FRIENDLIST_PUBLIC == True:
    FRIENDS = api.GetFriendlist(target_steamID)
for friend in FRIENDS:
    CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))

print("[+] FRIENDS")

# ======== HANDSHAKES ======== #
async def run_handshakes():
    global FRIENDS, CONNECTIONS
    if IS_FRIENDLIST_PUBLIC:
        return
    commentator_ids = utils.GetCommentsAuthorIDS(COMMENTS)
    print(f"\n[-] 1 HANDSHAKE — checking {len(commentator_ids)} commentators...")
    found_friends_1, commentator_friend_ids = await api.resolve_handshake_1(commentator_ids, target_steamID)
    for friend in found_friends_1:
        FRIENDS.append(friend)
        CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))
    print(f"[+] 1 HANDSHAKE - found {len(found_friends_1)} friends\n")

    known_ids = {f.steamID for f in FRIENDS} | {target_steamID}
    candidates_2 = list(set(commentator_friend_ids) - known_ids)
    print(f"[-] 2 HANDSHAKE - checking {len(candidates_2)} candidates...")
    found_friends_2, candidate_friend_ids_2 = await api.resolve_handshake_2(candidates_2, target_steamID)
    for friend in found_friends_2:
        FRIENDS.append(friend)
        CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))
    print(f"[+] 2 HANDSHAKE - found {len(found_friends_2)} friends\n")

    known_ids = {f.steamID for f in FRIENDS} | {target_steamID}
    candidates_3 = list(set(candidate_friend_ids_2) - known_ids)
    print(f"[-] 3 HANDSHAKE - checking {len(candidates_3)} candidates...")
    found_friends_3 = await api.resolve_handshake_3(candidates_3, target_steamID)
    for friend in found_friends_3:
        FRIENDS.append(friend)
        CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))
    print(f"[+] 3 HANDSHAKE - found {len(found_friends_3)} friends")

asyncio.run(run_handshakes())

# ======== DEDUPLICATE ======== #
seen = set()
unique_connections = []
for conn in CONNECTIONS:
    if conn.steamID not in seen:
        seen.add(conn.steamID)
        unique_connections.append(conn)
CONNECTIONS = unique_connections

seen = set()
unique_friends = []
for friend in FRIENDS:
    if friend.steamID not in seen:
        seen.add(friend.steamID)
        unique_friends.append(friend)
FRIENDS = unique_friends

# ======== SUMMARIES ======== #
async def fetch_all_summaries():
    friends_summaries, connections_summaries = await asyncio.gather(
        api.GetPlayerSummariesAsync(utils.GetFriendsIDS(FRIENDS)),
        api.GetPlayerSummariesAsync(utils.GetFriendsIDS(CONNECTIONS)),
    )
    return friends_summaries, connections_summaries

summaries_of_friends, summaries_of_connections = asyncio.run(fetch_all_summaries())

friends_map = {s["steamid"]: s for s in summaries_of_friends}
connections_map = {s["steamid"]: s for s in summaries_of_connections}

FRIEND_SUMMARIES = []
CONNECTION_SUMMARIES = []

for friend in FRIENDS:
    s = friends_map.get(friend.steamID)
    if s:
        FRIEND_SUMMARIES.append(SUMMARY(s["steamid"], "friend", s["personaname"], datetime.fromtimestamp(int(friend.friend_since)).strftime('%Y-%m-%d %H:%M'), s["avatarfull"]))

for conn in CONNECTIONS:
    s = connections_map.get(conn.steamID)
    if s:
        CONNECTION_SUMMARIES.append(SUMMARY(s["steamid"], "connection", s["personaname"], datetime.fromtimestamp(int(conn.since)).strftime('%Y-%m-%d %H:%M'), s["avatarfull"]))

# ======== TARGET'S COMMENTS ON CONNECTIONS ======== #
# Go through every found friend/connection profile,
# fetch their comments, find ones authored by the target.

def _parse_comments_html(html):
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for block in soup.find_all("div", class_="commentthread_comment"):
        try:
            author_tag = block.find("a", class_="commentthread_author_link")
            id3 = author_tag.get("data-miniprofile")
            author_id = str(int(id3) + 76561197960265728)
            timestamp_tag = block.find("span", class_="commentthread_comment_timestamp")
            unix_time = timestamp_tag["data-timestamp"]
            text_tag = block.find("div", class_="commentthread_comment_text")
            comment_text = text_tag.get_text(separator="\n").strip()
            result.append(COMMENT(author_id, unix_time, comment_text))
        except Exception:
            continue
    return result

async def _fetch_target_comments_on_profile(session, profile_steamID, target_id, semaphore, retries=3):
    """Fetch up to 200 comments from profile_steamID, return those by target_id."""
    url = f"https://steamcommunity.com/comment/Profile/render/{profile_steamID}/-1/?start=0&count=1"
    async with semaphore:
        for attempt in range(retries):
            try:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    data = await resp.json(content_type=None)
                    if not data.get("success") or data.get("total_count", 0) == 0:
                        return []
                    fetch_count = min(data["total_count"], 200)
                    fetch_url = f"https://steamcommunity.com/comment/Profile/render/{profile_steamID}/-1/?start=0&count={fetch_count}"
                    async with session.get(fetch_url) as r2:
                        d2 = await r2.json(content_type=None)
                        all_comments = _parse_comments_html(d2.get("comments_html", ""))
                        return [
                            (profile_steamID, c)
                            for c in all_comments
                            if c.authorID == target_id
                        ]
            except Exception:
                await asyncio.sleep(1 * (attempt + 1))
    return []

async def _find_target_comments():
    all_profile_ids = list({s.steamID for s in FRIEND_SUMMARIES + CONNECTION_SUMMARIES})
    semaphore = asyncio.Semaphore(15)
    print(f"\n[-] Scanning {len(all_profile_ids)} profiles for target's comments...")
    async with aiohttp.ClientSession() as session:
        tasks = [
            _fetch_target_comments_on_profile(session, pid, target_steamID, semaphore)
            for pid in all_profile_ids
        ]
        chunks = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for chunk in chunks:
        if isinstance(chunk, Exception) or not chunk:
            continue
        results.extend(chunk)
    return results  # list of (profile_steamID, COMMENT)

TARGET_COMMENTS_ON_CONNECTIONS = asyncio.run(_find_target_comments())
print(f"[+] Found {len(TARGET_COMMENTS_ON_CONNECTIONS)} comments left by target on connections' profiles")

# ======== REPORT ======== #
generate_report(
    target_steamID,
    target_nickname,
    target_avatar,
    target_creation_date,
    ARCHIVE_NICKNAMES,
    ARCHIVE_REAL_NAMES,
    ARCHIVE_URLS,
    ARCHIVE_AVATARS,
    FRIEND_SUMMARIES,
    CONNECTION_SUMMARIES,
    COMMENTS,
    TARGET_COMMENTS_ON_CONNECTIONS,
)
