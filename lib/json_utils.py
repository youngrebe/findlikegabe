import json

def uploadToken(token: str):
    token = {"token": token}

    with open("./config/token.json", "w") as file:
        json.dump(token, file, indent=4)

def loadToken():
    with open('./config/token.json', 'r') as file:
        data = json.load(file)

    return data["token"]