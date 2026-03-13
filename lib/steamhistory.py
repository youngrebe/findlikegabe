from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from .models import NICKNAME, REALNAME, URL, AVATAR
import time

# ======== REQUESTS ======== #
INFO_XPATH = "//span[@class='break-all ']"
TIMESTAMP_XPATH = "//span[@class='text-xs text-gray-400 sm:ml-4 flex-shrink-0']"
AVATAR_XPATH = "//img[@class='block w-full h-full object-cover']"
AVATAR_TIMESTAMP_XPATH = "//p[@class='mt-2 text-xs']"
ERROR_XPATH = "//p[@class='text-error']"
    
def isError(DRIVER):
    try:
        DRIVER.find_element(By.XPATH, ERROR_XPATH)
        return True
    except NoSuchElementException:
        return False

def GetProfileNicknames(DRIVER: object, steamID: str):
    nicknames = []
    DRIVER.get(f"https://steamhistory.net/history/0/{steamID}")

    if isError(DRIVER) is True: return []

    nicknames_block = DRIVER.find_elements(By.XPATH, INFO_XPATH)
    timestamps_block = DRIVER.find_elements(By.XPATH, TIMESTAMP_XPATH)

    for nickname, timestamp in zip(nicknames_block, timestamps_block):
        nicknames.append(NICKNAME(nickname.text, timestamp.text))

    return nicknames

def GetProfileRealNames(DRIVER: object, steamID: str):
    real_names = []
    DRIVER.get(f"https://steamhistory.net/history/1/{steamID}")

    if isError(DRIVER) is True: return []

    real_names_block = DRIVER.find_elements(By.XPATH, INFO_XPATH)
    timestamps_block = DRIVER.find_elements(By.XPATH, TIMESTAMP_XPATH)

    for real_name, timestamp in zip(real_names_block, timestamps_block):
        real_names.append(REALNAME(real_name.text, timestamp.text))

    return real_names

def GetProfileURLS(DRIVER: object, steamID: str):
    urls = []
    DRIVER.get(f"https://steamhistory.net/history/2/{steamID}")

    if isError(DRIVER) is True: return []

    url_block = DRIVER.find_elements(By.XPATH, INFO_XPATH)
    timestamps_block = DRIVER.find_elements(By.XPATH, TIMESTAMP_XPATH)

    for url, timestamp in zip(url_block, timestamps_block):
        urls.append(URL(url.text, timestamp.text))

    return urls

def GetProfileAvatars(DRIVER: object, steamID: str):
    avatars = []
    DRIVER.get(f"https://steamhistory.net/history/3/{steamID}")

    if isError(DRIVER) is True: return []

    avatar_block = DRIVER.find_elements(By.XPATH, AVATAR_XPATH)
    timestamps_block = DRIVER.find_elements(By.XPATH, AVATAR_TIMESTAMP_XPATH)

    for avatar, timestamp in zip(avatar_block, timestamps_block):
        avatars.append(AVATAR(avatar.get_attribute("src"), timestamp.text))

    return avatars

def GetProfileHistory(steamID: str):
    OPTIONS = Options()
    OPTIONS.add_argument("--headless")

    DRIVER = webdriver.Chrome(options=OPTIONS)
    nicknames = GetProfileNicknames(DRIVER, steamID)
    real_names = GetProfileRealNames(DRIVER, steamID)
    urls = GetProfileURLS(DRIVER, steamID)
    avatars = GetProfileAvatars(DRIVER, steamID)

    DRIVER.quit()

    return nicknames, real_names, urls, avatars
    