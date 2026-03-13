class FRIEND:
    def __init__(self, steamID, timestamp):
        self.steamID = steamID
        self.friend_since = timestamp

class SUMMARY:
    def __init__(self, steamID, status, nickname, date, avatar):
        self.steamID = steamID
        self.status = status
        self.since = date
        self.nickname = nickname
        self.avatar = avatar

class COMMENT:
    def __init__(self, authorID, publishedAt, text):
        self.authorID = authorID
        self.text = text
        self.publishedAt = publishedAt

class NICKNAME:
    def __init__(self, nickname, date):
        self.nickname = nickname
        self.date = date

class REALNAME:
    def __init__(self, realname, date):
        self.realname = realname
        self.date = date

class URL:
    def __init__(self, url, date):
        self.url = url
        self.date = date

class AVATAR:
    def __init__(self, url, date):
        self.url = url
        self.date = date

class CONNECTION:
    def __init__(self, steamID, date):
        self.steamID = steamID
        self.since = date