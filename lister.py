import requests
import json
import sys
import time
import sqlite3
import getpass

PROJECTS_FILE = 'projectList.json'
MAX_REQ_PER_HOUR = 5000
connection = None

def downloadList(username, password, since=""):
    #CURRENT MAX VALUE OF SINCE: https://api.github.com/repositories?since=44257649
    setupDatabase()
    if since == "":
        since = str(getLastStoredProj())
    sess = requests.session()

    startTime = time.gmtime()
    nextLink = "https://api.github.com/repositories?since="+since
    response = sess.get(nextLink, auth=(username, password))
    print(nextLink)
    storeProject(response.content.decode("utf-8"))
    nextLink = response.links["next"]['url']
    i = 0
    while response.headers['link'] is not None:
        responseWait(response)
        retryCount = 0
        while retryCount < 10:
            try:
                response = sess.get(nextLink, auth=(username, password))
                break
            except:
                retryCount += 1

        print(nextLink + " " + response.headers["X-RateLimit-Remaining"] + " requests remaining")
        i += storeProject(response.content.decode("utf-8"))
        nextLink = response.links["next"]['url']
        if i % 1000 == 0:
            pass
            #print(str(i) + "projects processed in " + str(time.gmtime()-startTime))

def setupDatabase():
    global connection
    connection = sqlite3.connect("githubData.db")
    connection.cursor().execute("CREATE TABLE IF NOT EXISTS repos (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, owner_name TEXT, description TEXT)")
    connection.commit()

def getLastStoredProj():
    global connection
    cur = connection.cursor()
    cur.execute("SELECT MAX(proj_id) FROM repos")
    result = cur.fetchone()
    return result[0]

def storeProject(segment):
    global connection
    jTree = json.loads(segment)
    i = 0
    for proj in jTree:
        projID = proj["id"]
        projName = proj["name"]
        projOwner = proj["owner"]["login"]
        descrip = proj["description"]
        cmd = "INSERT INTO repos (proj_id, name, owner_name, description) VALUES(?, ?, ?, ?)"
        connection.cursor().execute(cmd, (int(projID), str(projName), str(projOwner), str(descrip)))
        connection.commit()
        i += 1
        print(".", end="", flush=True)
    print("")
    return i
    #f=open('projectList.json', 'a', encoding="utf-8")
    #f.write(segment)
    #f.write("\n")
    #f.close()

def getRateLimitStatus(username=None, password=None):
    sess = requests.session()
    response = None
    if not username is None:
        response = requests.get("https://api.github.com/rate_limit", auth=(username, password))
    else:
        response = requests.get("https://api.github.com/rate_limit")
    return response

def responseWait(response):
    remainingRequests = int(response.headers["X-RateLimit-Remaining"])
    nextReqPeriod = int(response.headers["X-RateLimit-Reset"])
    #periodLimit = int(response.headers["X-RateLimit-Limit"])
    #stop requesting and wait until next request period to avoid exceptions
    if remainingRequests < 5:
        print("Remaining requests: " + remainingRequests)
        while time.gmtime() < nextReqPeriod:
            print("Waiting for next request period at " + time.gmtime(nextReqPeriod))
            time.sleep(15)
    time.sleep(60*60/MAX_REQ_PER_HOUR) #Should work to auto-limit 5000 requests/hr

def main():

    if len(sys.argv)==3:
        downloadList(sys.argv[1], getpass.getpass(), sys.argv[2])
    elif len(sys.argv)==2:
        downloadList(sys.argv[1], getpass.getpass())
    else:
        print("Usage: lister.py username [startPage]")
    f=open('projectList.json', 'r')
    jsonTree = json.loads(f.readlines())
    for proj in jsonTree:
        print(proj['name'])

main()