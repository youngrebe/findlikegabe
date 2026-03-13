from .models import COMMENT

def GetCommentsAuthorIDS(comments: list):
    ids = []
    for comment in comments:
        ids.append(comment.authorID)

    ids = list(set(ids))
    return ids

def GetFriendsIDS(friends: list):
    ids = []
    for friend in friends:
        ids.append(friend.steamID)

    ids = list(set(ids))
    return ids