import json
import sys
import time
import sqlite3
import getpass
from timeit import default_timer as timer

import requests

MAX_REQ_PER_HOUR = 5000
connection = None


def downloadList(username, password, since=""):
    # CURRENT MAX VALUE OF SINCE: https://api.github.com/repositories?since=44257649
    setupDatabase()
    if since == "":
        since = str(getLastStoredProj())
    sess = requests.session()

    start_time = timer()
    next_link = "https://api.github.com/repositories?since=" + since
    response = sess.get(next_link, auth=(username, password))
    responseWait(response)
    while response.status_code == 401:
        print(response)
        password = getpass.getpass()
        response = sess.get(next_link, auth=(username, password))
    print(next_link)
    storeProject(response.content.decode("utf-8"))
    next_link = response.links["next"]['url']
    i = 0
    while response.headers['link'] is not None:
        responseWait(response)
        retry_count = 0
        while retry_count < 10:
            try:
                response = sess.get(next_link, auth=(username, password))
                break
            # TODO get rid of this retry and add real error handling
            except:
                retry_count += 1

        print(next_link + " " + response.headers["X-RateLimit-Remaining"] + " requests remaining")
        i += storeProject(response.content.decode("utf-8"))
        next_link = response.links["next"]['url']
        elapsed_time = timer() - start_time
        print(str(i) + " projects processed in " + str(elapsed_time) + " seconds")
        print("rate: " + str(i / elapsed_time) + " repos/second")


def setupDatabase():
    global connection
    connection = sqlite3.connect("githubData.db")
    cmd = "CREATE TABLE IF NOT EXISTS repos (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, owner_name TEXT, description TEXT)"
    connection.cursor().execute(cmd)
    connection.commit()


def getLastStoredProj():
    global connection
    cur = connection.cursor()
    cur.execute("SELECT MAX(proj_id) FROM repos")
    result = cur.fetchone()
    return result[0]


# https://docs.python.org/2/library/sqlite3.html#sqlite3.Cursor.executemany
def storeProject(segment):
    global connection
    j_tree = json.loads(segment)
    i = 0
    proj_tuples = []
    for proj in j_tree:
        proj_id = proj["id"]
        proj_name = proj["name"]
        proj_owner = proj["owner"]["login"]
        descrip = proj["description"]
        proj_tuples.append((proj_id, proj_name, proj_owner, descrip))
        i += 1

    cmd = "INSERT INTO repos (proj_id, name, owner_name, description) VALUES(?, ?, ?, ?)"
    connection.cursor().executemany(cmd, proj_tuples)
    connection.commit()
    print("")
    return i


def getRateLimitStatus(username=None, password=None):
    if username is not None:
        response = requests.get("https://api.github.com/rate_limit", auth=(username, password))
    else:
        response = requests.get("https://api.github.com/rate_limit")
    return response


def responseWait(response):
    remaining_requests = int(response.headers["X-RateLimit-Remaining"])
    next_request_period = int(response.headers["X-RateLimit-Reset"])
    # periodLimit = int(response.headers["X-RateLimit-Limit"])
    # stop requesting and wait until next request period to avoid exceptions
    if remaining_requests < 5:
        print("Remaining requests: " + str(remaining_requests))
        while int(time.time()) < next_request_period:
            print("Waiting for next request period at " + str(time.gmtime(next_request_period).tm_hour) + ":" + str(
                time.gmtime(next_request_period).tm_min))
            time.sleep(15)
            # time.sleep(next_request_period - time.time()) #no user feedback, but better(?)


def main():
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        print("Usage: lister.py username [startPage]")
        username = str(input("Enter your username"))

    downloadList(username, getpass.getpass())
    # TODO do something cool with this data


main()
