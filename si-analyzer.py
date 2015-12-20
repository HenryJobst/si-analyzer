import argparse
import requests
import time
from time import strftime
#from time import time
#from html import HTML

from bs4 import BeautifulSoup

def sorter(value):
    return value[1].tm_min * 60 + value[1].tm_sec

parser = argparse.ArgumentParser(description='Analyze SI times.')
parser.add_argument('url')
parser.add_argument('-l', '--local',  action='store_true', help='url is a local file')
parser.add_argument('-t', '--type', choices=['course', 'age', 'all'], default='all', help='group times by all, age group, course, default: all')
parser.add_argument('-m', '--merge', action='store_true', help='merge control post sequences, eg. 110-111 with 111-110')
parser.add_argument('--proxy')
parser.add_argument('--version', action='version', version='%(prog)s 0.1')
parser.add_argument('-n', '--name', nargs='+')

args = parser.parse_args()

if args.proxy != '':
    proxies = {
        'http' : args.proxy
    }
else:
    proxies = {}

file=None
document = ''

if args.local == True:
    file = open(args.url, 'r')
    document = file.read()
else:
    r = requests.get(args.url, proxies=proxies)
    document = r.text

soup = BeautifulSoup(document, 'html5lib')

#print(soup.prettify())

print(soup.title.string)

siTimes = {}

for cElem in soup.find_all(id='c00'): # find courses
    course = cElem.text.split('(')[0].strip()

    sElem = cElem.parent.parent

    for tElem in sElem.find_all_next('table'):
        #print(rElem)
        if tElem.find(id='c00') is not None:
            break
        nameElem = tElem.find(id='c11')
        clubElem = tElem.find(id='c13')
        ageGroupElem = tElem.find(id='c14')
        name = None
        club = None
        ageGroup = None
        if nameElem != None:
            name = nameElem.contents[0].string
        if clubElem != None:
            club = clubElem.contents[0].string
        if ageGroupElem != None:
            ageGroup = ageGroupElem.contents[0].string

        if name != None:
            #print(name, ageGroup, club, sep=':')
            controlls = ['Start']
            times = ['0:00']
            ssiElem = tElem.find_next('table').tbody
            trs = ssiElem.find_all('tr')
            if len(trs) < 3:
                continue
            for controll in trs[0]:
                controllString = controll.string
                if controllString == None:
                    continue
                if controllString.find('*') != -1:
                    continue
                controllString = controllString.split('(')[0]
                controlls.append(controllString)
            for stime in trs[2]:
                timeString = stime.string
                if timeString == None:
                    continue
                parsedTime = time.strptime(timeString, "%M:%S")
                times.append(parsedTime)

            for i in range(1, len(controlls)):
                #print(i, controlls[i-1], controlls[i], times[i])
                values = [(name, ageGroup, club), times[i], True]
                keyTuple1 = (controlls[i-1], controlls[i])
                if keyTuple1 not in siTimes:
                    siTimes[keyTuple1] = []
                siTimes[keyTuple1].append(values)

processed = {}
nameTimes = {}

htmlpage = HTML()

for item in sorted(siTimes.items(), key=lambda t: t[0][0]+t[0][1]):
    key = item[0]
    if args.merge and (key[::-1] in processed):
        continue
    values = item[1]
    if args.merge:
        reverseKey = (key[1], key[0])
        if reverseKey in siTimes:
            reverseValues = list(siTimes[reverseKey])
            for value in reverseValues:
                value[2] = False
                values.append(value)

    nameFound = {}
    if args.name:
        for name in args.name:
            nameFound[name] = [False, 0]
        for value in values:
            for name in nameFound.keys():
                if value[0][0].find(name) != -1:
                    nameFound[name] = [True, 0]
        allNamesFound = True
        for nameElem in nameFound.items():
            if not nameElem[1][0]:
                allNamesFound = False
                break
        if not allNamesFound:
            continue

    allValues = sorted(values, key=sorter)
    print()
    print(key[0], '->', key[1])
    print()

    place = 0
    placeOffset = 0
    lastTime = None
    bestTime = None
    for value in allValues:
        actualName = value[0][0]
        sign = ''
        if value[2] == False:
            sign = '<'
        stime = value[1]
        if lastTime is None or lastTime != stime:
            place = place + placeOffset + 1
            placeOffset = 0
        else:
            placeOffset = placeOffset + 1

        oneNameFound = False
        if len(nameFound) <  2:
            oneNameFound = True
        for name in nameFound:
            if actualName.find(name) != -1:
                oneNameFound = True
                break
        if oneNameFound:
            diffTime = None
            actualRuntime = (value[1].tm_min * 60 + value[1].tm_sec)
            if bestTime is not None:
                bestTimeRuntime = (bestTime.tm_min * 60 + bestTime.tm_sec)
                diffTime = actualRuntime - bestTimeRuntime
            diffString = ' ' * 8
            if diffTime is not None and diffTime != 0:
                diffString = '(+{0:02}:{1:02})'.format(diffTime//60, diffTime%60)
            print('{:3}.'.format(place), strftime('%M:%S', value[1]), diffString, '{:1}'.format(sign), actualName)
            if actualName in nameTimes:
                nameTimes[actualName] += actualRuntime
            else:
                nameTimes[actualName] = actualRuntime
        lastTime = stime
        if bestTime is None:
            bestTime = stime
    processed[key] = True

if len(nameTimes) > 0 and len(nameFound) > 1:
    maxNameLen = 0
    for nameElem in nameTimes.items():
        nameLen = len(nameElem[0])
        if nameLen > maxNameLen:
            maxNameLen = nameLen
    print()
    print('=' * 50)
    bestTime = None
    for nameElem in sorted(nameTimes.items(), key=lambda t: t[1]):
        diffTime = None
        if bestTime is not None:
            diffTime = nameElem[1] - bestTime
        diffString = ' ' * 8
        if diffTime is not None and diffTime != 0:
            diffString = '(+{0:02}:{1:02})'.format(diffTime//60, diffTime%60)
        print(nameElem[0].ljust(maxNameLen), ':', '{0:02}:{1:02}'.format(nameElem[1]//60, nameElem[1]%60), diffString)
        if bestTime is None:
            bestTime = nameElem[1]
    print('=' * 50)

if file != None:
    file.close()

#print(htmlpage)

#print(args.type)
#print(args.merge)

