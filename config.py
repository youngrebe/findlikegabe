from lib import api
from lib import json_utils

print("❗ No steam api token? Get it from this link (the domain doesn't matter): https://steamcommunity.com/dev/apikey \n")
token = input("✨ Input your steam-api token: ")

if api.IsTokenValid(token) == True:
    json_utils.uploadToken(token)
    print("🎉 Your token is valid! You can start researching profiles.")
else:
    print("⛔ Your token is not valid! Get it from this link: https://steamcommunity.com/dev/apikey")

summarie = api.GetPlayerSummary(76561199600183443)