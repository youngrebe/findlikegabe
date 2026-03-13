import asyncio
from lib import api
from lib.models import CONNECTION, FRIEND, COMMENT, NICKNAME, REALNAME, URL, AVATAR, SUMMARY
from lib import utils
from report import generate_report
from datetime import datetime

# ======== BASE ======== #
FRIENDS = []
CONNECTIONS = []
COMMENTS = []

# ======== SUMMARY ======== #
print("❗ If you are from Russia or you have problems with collecting data from the archive, turn on the VPN!")
target_steamID = input("\n👻 Enter your target's ID: ")
target_summary = api.GetPlayerSummary(target_steamID)
target_avatar = target_summary["avatarfull"]
target_nickname = target_summary["personaname"]
target_creation_date = target_summary.get("timecreated", None)

print("\n✅ SUMMARY")

# ======== ARCHIVE ======== #
ARCHIVE_NICKNAMES, ARCHIVE_REAL_NAMES, ARCHIVE_URLS, ARCHIVE_AVATARS = api.GetProfileArchive(target_steamID)
print("✅ ARCHIVE")

# ======== COMMENTS ======== #
COMMENTS = api.GetProfileComments(target_steamID)
for comment in COMMENTS:
    CONNECTIONS.append(CONNECTION(comment.authorID, comment.publishedAt))

print("\n✅ COMMENTS")
# ======== FRIENDS ======== #
IS_FRIENDLIST_PUBLIC = api.IsFriendlistPublic(target_steamID)
if IS_FRIENDLIST_PUBLIC == True:
    FRIENDS = api.GetFriendlist(target_steamID)
for friend in FRIENDS:
    CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))

print("✅ FRIENDS")
# ======== HANDSHAKES ======== #
async def run_handshakes():
    global FRIENDS, CONNECTIONS
    if IS_FRIENDLIST_PUBLIC:
        return
    # ======== 1 HANDSHAKE ======== #
    commentator_ids = utils.GetCommentsAuthorIDS(COMMENTS)
    print(f"\n🤝 1 HANDSHAKE — checking {len(commentator_ids)} commentators...")
    found_friends_1, commentator_friend_ids = await api.resolve_handshake_1(commentator_ids, target_steamID)
    for friend in found_friends_1:
        FRIENDS.append(friend)
        CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))
    print(f"✅ 1 HANDSHAKE - found {len(found_friends_1)} friends\n")
    # ======== 2 HANDSHAKE ======== #
    known_ids = {f.steamID for f in FRIENDS} | {target_steamID}
    candidates_2 = list(set(commentator_friend_ids) - known_ids)
    print(f"🤝 2 HANDSHAKE - checking {len(candidates_2)} candidates...")
    found_friends_2, candidate_friend_ids_2 = await api.resolve_handshake_2(candidates_2, target_steamID)
    for friend in found_friends_2:
        FRIENDS.append(friend)
        CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))
    print(f"✅ 2 HANDSHAKE - found {len(found_friends_2)} friends\n")
    # ======== 3 HANDSHAKE ======== #
    known_ids = {f.steamID for f in FRIENDS} | {target_steamID}
    candidates_3 = list(set(candidate_friend_ids_2) - known_ids)
    print(f"🤝 3 HANDSHAKE - checking {len(candidates_3)} candidates...")
    found_friends_3 = await api.resolve_handshake_3(candidates_3, target_steamID)
    for friend in found_friends_3:
        FRIENDS.append(friend)
        CONNECTIONS.append(CONNECTION(friend.steamID, friend.friend_since))
    print(f"✅ 3 HANDSHAKE - found {len(found_friends_3)} friends")

asyncio.run(run_handshakes())
# ======== SET ======== #
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
)