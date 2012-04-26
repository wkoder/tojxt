#! /usr/bin/python

'''
Created on Jul 9, 2010
@author: Moises Osorio
'''

import argparse
import time
import getpass

from parsers import *
from persistence import Persistence

VOLUME_SIZE = 100
RUNS_SIZE = 10
RANK_SIZE = 25
USERS_UPDATED = "usersUpdated"
USER_RUN_UPDATED = "runUpdated %s"
PROBLEM_VOLUME_UPDATED = "problemVolumeUpdated"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIANJIN_OFFSET = 13*60

def updateProblems(force=False):
    volume = 0
    if not force:
        lastVolume = persistence.getVar(PROBLEM_VOLUME_UPDATED)
        if lastVolume != None:
            volume = int(lastVolume)
            
    ok = True
    while ok:
        volume += 1
        print "Updating problems volume %d" % volume
        problems = parseProblems(volume)
        for problem in problems:
            persistence.updateProblem(problem)
        
        if len(problems) == VOLUME_SIZE:
            persistence.updateVar(PROBLEM_VOLUME_UPDATED, volume)
        persistence.commit()
        ok = len(problems) > 0

def updateUserRuns(userId, force=False):
    print "Updating runs of user %s" % userId
    lastRunId = -1
    var = USER_RUN_UPDATED % userId
    if not force:
        lastRun = persistence.getVar(var)
        if lastRun != None:
            lastRunId = int(lastRun)
    
    user = persistence.getUser(userId)
    ok = True
    count = persistence.countUserRuns(userId)
    while ok:
        if lastRunId == -1:
            runs = parseUserRuns(userId)
        else:
            runs = parseUserRuns(userId, lastRunId-1)
        
        count += len(runs)
        for run in runs:
            lastRunId = run.id
            if not force and not persistence.updateRun(run):
                ok = False
                lastRunId = -1
                break
        
        persistence.updateVar(var, lastRunId)
        persistence.commit()
        
        ok = ok and len(runs) == RUNS_SIZE
        print "   Completed %.2f%s" % (count / float(user.submitted) * 100, "%")
    
def updateUsers(userIds=[], topRank=1000, force=False):
    if len(userIds) > 0:
        print "Updating users..."
        for userId in userIds:
            updateUserRuns(userId, force)
        
        return
        
    print "Updating top %d users" % topRank
    updated = 0
    if not force:
        lastUpdated = persistence.getVar(USERS_UPDATED)
        if lastUpdated != None:
            updated = int(lastUpdated)
            
    while updated < topRank:
        users = parseUsers(updated+1)
        for user in users:
            persistence.updateUser(user)
        
        updated += len(users)
        persistence.updateVar(USERS_UPDATED, updated)
        persistence.commit()
        
        print "   Completed %.2f%s" % (updated / float(topRank) * 100, "%")
    
        
def updateContest(contest):
    print "Updating contest %s" % contest
    problemIds = parseContest(contest)
    for problemId in problemIds:
        problem = persistence.getProblem(problemId)
        if problem == None:
            print "Problem %d not found. Please update problem data." % problemId
            return
        if problem.source != contest:
            problem.source = contest
            persistence.updateProblem(problem)
            persistence.commit()
    
def updateContests(contests=[], force = False):
    print "Updating contests..."
    if len(contests) == 0:
        contests = parseContests()
    count = 0
    for contest in contests:
        if force or not persistence.existsSource(contest):
            updateContest(contest)
        count += 1
        print "   Completed %.2f%s" % (count / float(len(contests)) * 100, "%")
            
def _showUserHeader(rank=False):
    if rank:
        print "Rank ",
    print "Solved  Submitted  AC Ratio   Ratio  Name                       ID"
    
def _showUser(user, rank=None):
    if rank is not None:
        print "%4d " % rank,
    print "%6d  %9d    %6.2f  %6.2f  %s  %s" % \
        (user.solved, user.submitted, user.getACRatio(), user.ratio, user.name.ljust(25), user.id)
    
def showUsers(userIds):
    _showUserHeader()
    
    for userId in userIds:
        user = persistence.getUser(userId)
        if user == None:
            print "User %s not found. Please update user data." % userId
            return
        _showUser(user)
    
def showProblems(problemIds, highlight):
    _showProblemHeader()
    for problemId in problemIds:
        problem = persistence.getProblem(problemId)
        if problem == None:
            print "Problem %d not found. Please update problem data." % problemId
            return
        
        solvedBy = [userId for userId in highlight if persistence.isSolvedByUser(userId, problemId)]
        _showProblem(problem, solvedBy)

def showRanking(top=100, country=None):
    _showUserHeader(True)
    ranking = persistence.getRanking(top, country)
    for i, user in enumerate(ranking):
        _showUser(user, i+1)

def _showProblemHeader(nameLen=40):
    print "  ID  Solved  Accepted  Submitted  Ratio  %s  Title" % "Source".ljust(nameLen)
    
def _showProblem(problem, solvedBy=[], nameLen=40):
    solved = "Yes" if len(solvedBy) > 0 else ""
    print "%4d %s %9d %10d %6.2f  %s  %s" % (problem.id, solved.rjust(7), problem.accepted, problem.submitted, problem.ratio, problem.source.ljust(nameLen), problem.title)
    
def showContests(contests, highlight=[]):
    for contest in contests:
        nameLen = len(contest)
        _showProblemHeader(nameLen)
        problems = persistence.getContest(contest)
        for problem in problems:
            solvedBy = [userId for userId in highlight if persistence.isSolvedByUser(userId, problem.id)]
            _showProblem(problem, solvedBy, nameLen)
            
def createVirtualContest(user, password, title, description, startDate, duration, problemIds):
    if len(problemIds) < 3:
        print "You have to specify at least 3 problems"
        return
    if duration < 30:
        print "Duration cannot be less than 30"
        return
    
    startDate += TIANJIN_OFFSET * 60
    startDateStr = time.strftime(TIME_FORMAT, time.localtime(startDate))
    endDateStr = time.strftime(TIME_FORMAT, time.localtime(startDate + 60*duration))
    postVirtualContest(user, password, title, description, startDateStr, endDateStr, problemIds)
    print "Virtual contest '%s' has been created" % title

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyzes TJU Online Judge results.")
    parser.add_argument("--update-users", "-uu", nargs="*", 
                        help="updates a list of users, all users if '*' is given")
    parser.add_argument("--update-problems", "-up", action='store_const', const=True, default=False,
                        help="updates all problems")
    parser.add_argument("--update-contests", "-uc", nargs="*", 
                        help="updates all contests")
    parser.add_argument("--show-users", "-u", nargs="*", 
                        help="shows the user statistics")
    parser.add_argument("--show-problems", "-p", nargs="*", 
                        help="shows the problem statistics")
    parser.add_argument("--show-contests", "-c", nargs="*", 
                        help="shows the contest statistics")
    parser.add_argument("--show-ranking", "-r", action='store_const', const=True, default=False,
                        help="shows the ranking")
    parser.add_argument("--highlight", "-hl", nargs="*", 
                        help="highlights the users")
    parser.add_argument("--top", default=1000, type=int, 
                        help="restricts to top TOP users")
    parser.add_argument("--country", 
                        help="restricts to only this country")
    parser.add_argument("--user", 
                        help="current user")
    parser.add_argument("--force", "-f", action='store_const', const=True, default=False, 
                        help="if the update action is going to be forced")

    parser.add_argument("--create-virtual-contest", "-v", nargs="*", 
                        help="creates a virtual contest")
    parser.add_argument("--title",
                        help="title of the contest to create")
    parser.add_argument("--description", 
                        help="description of the contest to create")
    parser.add_argument("--start-date", default="15", 
                        help="sets the contest start date in format '%s', if integer given start date is X minutes from now" % TIME_FORMAT)
    parser.add_argument("--duration", type=int, default=300, 
                        help="sets the contest duration")
    args = parser.parse_args()
    
    persistence = Persistence()
    try:
        if args.update_users is not None:
            if "*" in args.update_users:
                updateUsers([], args.top, args.force)
            else:
                updateUsers(args.update_users, args.top, args.force)
        elif args.update_problems:
            updateProblems(args.force)
        elif args.update_contests is not None:
            if "*" in args.update_contests:
                updateContests([], args.force)
            else:
                updateContests(args.update_contests, args.force)
        elif args.show_users is not None:
            showUsers(args.show_users)
        elif args.show_contests is not None:
            showContests(args.show_contests, args.highlight)
        elif args.show_problems is not None:
            showProblems(args.show_problems, args.highlight)
        elif args.show_ranking:
            showRanking(args.top, args.country)
        elif args.create_virtual_contest is not None:
            try:
                startDate = time.time() + 60 * int(args.start_date)
            except:
                try:
                    startDate = time.mktime(time.strptime(args.start_date, TIME_FORMAT))
                except:
                    print "Start date is not an integer or a date"
                    exit()
            password = getpass.getpass("Password: ")
            createVirtualContest(args.user, password, args.title, args.description, startDate, args.duration, args.create_virtual_contest)
        else:
            parser.print_help()
    finally:
        persistence.close()
    