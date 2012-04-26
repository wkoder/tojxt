'''
Created on Jul 9, 2010
@author: Moises Osorio
'''
import urllib
import httplib

from problem import Problem
from run import Run
from user import User

TOJ_HOST = "acm.tju.edu.cn"

def _readURL(url):
    f = urllib.urlopen(url)
    s = f.read()
    html = ""
    while s:
        html += unicode(s, "Latin1")
        s = f.read()
    f.close()
    return html

def _getContent(line, start, fwd = 1, look = ""):
    if fwd:
        if look == "":
            look = "<"
        end = line.find(look, start)
        return line[start : end]
    
    if look == "":
        look = ">"
    end = start
    while line[end] != look:
        end -= 1
    return line[end+1 : start+1]

def parseProblems(volume):
    url = "http://%s/toj/list%d.html" % (TOJ_HOST, volume)
    html = _readURL(url)
    lines = html.split('\n')
    
    problems = list()
    for line_pos in xrange(28, len(lines)):
        token = lines[line_pos]
        if token.find("p") != 0:
            break
        problem = Problem()
        
        token2 = token[ : : -1]
        
        endRatio = token2.find('"')
        startRatio = token2.find('"', endRatio+1)
        endTitle = token2.find('"', startRatio+1)
        
        startTitle = token.find('"')
        endTitle = len(token) - endTitle - 1
        endRatio = len(token) - endRatio - 1
        startRatio = len(token) - startRatio - 1
        
        problem.title = token[startTitle+1:endTitle].replace("\\", "")
        ratio = token[startRatio+1:endRatio]
        try:
            problem.ratio = float(ratio) / 100.0
        except:
            None
        
        token = token[0:startTitle] + token[endTitle+1:startRatio] + token[endRatio+1:len(token)-1]
        params = token.split(",")
        
        problem.id = int(params[2])
        problem.accepted = int(params[5])
        problem.submitted = int(params[6])
        
        problems.append(problem)
        
    return problems

def parseUserRuns(user, fromRunID = -1):
    url = "http://%s/toj/status.php?user=%s" % (TOJ_HOST, user)
    if fromRunID >= 0:
        url += "&start=%d" % fromRunID
    
    html = _readURL(url)
    lines = html.split('\n')
    
    runs = list()
    for linePos in xrange(18, len(lines)-5, 5):
        token = lines[linePos]
        if token.find("</table") == 0:
            break
        
        run = Run()
        run.id = int(_getContent(token, 31))
        
        token = lines[linePos+1]
        run.submitTime = _getContent(token, 4)
        if token.find("Compilation Error") >= 0:
            run.status = "Compilation Error"
        else:
            run.status = _getContent(token, len(token)-17, 0)
        
        token = lines[linePos+2]
        run.problemId = int(_getContent(token, 27))
        run.language = _getContent(token, 44)
        
        token = lines[linePos+3]
        timeStr = _getContent(token, len(token)-13)
        run.time = int(timeStr[0]) * 60000 + int(timeStr[2:4]) * 1000 + int(timeStr[5:7]) * 10
        
        token = lines[linePos+4]
        kb = _getContent(token, 4)
        run.memory = int(kb[ : len(kb)-1])
        run.userId = _getContent(token, len(token)-15, 0)
        
        runs.append(run)
        
    return runs

def parseUsers(fromRank):
    fromRank -= 1
    url = "http://%s/toj/ranklist.php?start=%d" % (TOJ_HOST, fromRank)
    html = _readURL(url)
    lines = html.split('\n')
    
    users = list()
    linePos = 29
    while linePos < len(lines):
        token = lines[linePos]
        if token.find("</table>") == 0:
            break
        
        user = User()
        user.name = _getContent(token, len(token)-10, 0)
        user.rank = (linePos - 29) / 3 + fromRank + 1
        end = len(token) - 17 - len(user.name)
        user.id = _getContent(token, end, 0, "\"")
        user.id = user.id[5 : ]
        user.country = _getContent(token, end - len(user.id) - 25, 0, "\"").title()
        
        token = lines[linePos+1]
        while lines[linePos+2].find("<td>") != 0:
            token += lines[linePos+2]
            linePos += 1
        user.solved = int(_getContent(token, len(token)-17, 0))
        
        token = lines[linePos+2]
        end = len(token) - 11
        ratio = _getContent(token, end, 0)
        if ratio != "??":
            user.ratio = float(ratio)
        end -= len(ratio) + 9
        perc = _getContent(token, end, 0)
        end -= 13 + len(perc)
        user.submitted = int(_getContent(token, end, 0))
        
        users.append(user)
        linePos += 3
        
    return users

def parseContests():
    url = "http://%s/toj/pindex.html" % TOJ_HOST
    html = _readURL(url)
    lines = html.split('\n')
    
    contests = list()
    for linePos in xrange(15, len(lines)-3):
        token = lines[linePos]
        if token.find("<tr><td><a href=") != 0:
            continue
        
        end = len(token) - 10
        if token.rstrip().endswith("</table>"):
            end -= 8
        contest = _getContent(token, end, 0).strip()
        contests.append(contest)
    
    return contests

def parseContest(contest):
    contest = contest.lower()
    CURRENT = "</td><td align=center>"
    NEXT = "</a></font></td>"
    url = "http://%s/toj/search_process.php?s=%s" % (TOJ_HOST, contest.replace(" ", "+"))
    html = _readURL(url)
    lines = html.split('\n')
    problemIds = list()
    for linePos in xrange(12, len(lines)):
        current = lines[linePos]
        currentPos= current.find(CURRENT);
        if currentPos < 0:
            break
        nextLine = lines[linePos+1]
        token = current[currentPos+len(CURRENT) : ] + nextLine[ : nextLine.find(NEXT)]

        cont = _getContent(token, len(token)-1, 0)
        if cont.lower() != contest:
            print "We removed %s because it had a different source" % cont
            continue
        
        problemId = _getContent(token, 0)
        problemIds.append(problemId)
        
    return problemIds

def postVirtualContest(userId, password, title, description, startDate, endDate, problemIds):
    params = {"user_id" : userId, "passwd" : password, "title" : title, "desc" : description, "stime" : startDate, "etime" : endDate}
    for i in xrange(len(problemIds)):
        name = "p%s" % chr(ord("A") + i)
        params[name] = problemIds[i]

    conn = httplib.HTTPConnection(TOJ_HOST, timeout=10)
    try:
        conn.request("post", "", urllib.urlencode(params))
        response = conn.getresponse()
        responseData = response.read()
        if not "" in responseData:
            reason = responseData # TODO
            raise Exception("Could not create virtual contest: %s" % reason)
    finally:
        conn.close()
    