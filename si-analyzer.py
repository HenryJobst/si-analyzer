import argparse
import requests
import time
from time import strftime
#from time import time
import sys

from lxml import etree as ET
from lxml.builder import E
import html

from bs4 import BeautifulSoup

################# functions ################################

def sorter(value):
    return value[1].tm_min * 60 + value[1].tm_sec

def parseHTML(soup, siTimes, titleString):

    titleString = soup.title.string
    print(titleString)

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
                controlls = ['000']
                times = ['0:00']
                ssiElem = tElem.find_next('table').tbody
                #print(ssiElem)
                trs = ssiElem.find_all('tr')
                rowBlocks = len(trs)//3
                if  rowBlocks < 1:
                    continue
                for rowBlock in range(rowBlocks):
                    for controll in trs[rowBlock*3]:
                        controllString = controll.string
                        if controllString == None:
                            continue
                        if controllString.find('*') != -1:
                            continue
                        controllString = controllString.split('(')[0]
                        if controllString == 'Ziel':
                            controllString = '999'
                        try:
                            int(controllString)
                        except ValueError:
                            continue
                        controlls.append(controllString)

                    for stime in trs[rowBlock*3+2]:
                        if stime.find_all(id='rb') == None:
                            break
                        timeString = stime.string
                        if timeString == None:
                            continue
                        try:
                            time.strptime(timeString, "%M:%S")
                        except ValueError:
                            continue
                        times.append(time.strptime(timeString, "%M:%S"))

                for i in range(1, len(controlls)):
                    #print(i, controlls[i-1], controlls[i], times[i])
                    values = [(name, ageGroup, club), times[i], True]
                    keyTuple1 = (controlls[i-1], controlls[i])
                    if keyTuple1 not in siTimes:
                        siTimes[keyTuple1] = []
                    siTimes[keyTuple1].append(values)

def inSeconds(value):
    return value.tm_hour * 3600 + value.tm_min * 60 + value.tm_sec;

def parseTimeFmt(timeString, format):
    try:
        time.strptime(timeString, format)
        return True
    except ValueError:
        return False

def parseTime(timeString):
    if parseTimeFmt(timeString, "%H:%M:%S") == True:
        return "%H:%M:%S"
    elif parseTimeFmt(timeString, "%M:%S") == True:
        return "%M:%S"
    return None

def parseTimeWithMispunch(timeString):
    if timeString == None:
        print ('[EE]: timeString is empty', sElem)
        return None
    parseFmt = parseTime(timeString)
    if parseFmt == None:
        if timeString == '-----':
            return None # mispunch
        if timeString == '0.00':
            return None # mispunch
        print ('[WW]: timeString is not convertible to a time', timeString)
        return None
    return time.strptime(timeString, parseFmt)

def parseXML203(soup, siTimes, titleString):

    #print("parseXML203")
    titleString = "???"

    for pElem in soup.find_all('personresult'):
        ageGroup = pElem.parent.classshortname.contents[0].string
        name = pElem.person.personname.family.contents[0].string + ', ' + pElem.person.personname.given.contents[0].string
        club = pElem.club.shortname.contents[0].string
        birthDate = '-'
        if pElem.person.birthdate.date and len(pElem.person.birthdate.date.contents) > 0:
            birthDate = pElem.person.birthdate.date.contents[0].string
        #print(name, ageGroup, club, sep=':')

        startTime = time.strptime(pElem.result.starttime.clock.contents[0].string, "%H:%M:%S")
        finishTime = None
        if pElem.result.finishtime.clock.contents:
             finishTime = time.strptime(pElem.result.finishtime.clock.contents[0].string, "%H:%M:%S")
        runTimeString = None
        if pElem.result.time.contents:
            runTimeString = pElem.result.time.contents[0].string
        #status = pElem.result.competitorstatus

        controlls = ['000']
        times = ['0:00']

        lastTime = None

        for sElem in pElem.find_all('splittime'):
            sequenceNumber = sElem['sequence']

            controlCode = sElem.controlcode.contents[0].string
            try:
                int(controlCode)
            except ValueError:
                continue

            timeString = sElem.time.contents[0].string

            actualRunTime = parseTimeWithMispunch(timeString)
            if actualRunTime == None:
                continue

            #print('->', controlCode, ' : ', time.asctime(actualRunTime))

            splitTime = None
            if lastTime != None:
                tDiff = time.mktime(actualRunTime) - time.mktime(lastTime)
                #print(tDiff)
                splitTime = time.localtime(tDiff)
            else:
                splitTime = time.localtime(time.mktime(actualRunTime))

            if splitTime == None:
                continue;

            lastTime = actualRunTime

            #print('<-', controlCode, ' :: ', time.asctime(splitTime))

            controlls.append(controlCode)
            times.append(splitTime)

        controlls.append('999')
        if lastTime != None and runTimeString:
            runTime = parseTimeWithMispunch(runTimeString)
            if runTime != None:
                times.append(time.localtime(time.mktime(runTime)-time.mktime(lastTime)))
            elif finishTime:
                times.append(time.localtime(time.mktime(finishTime)-time.mktime(startTime)))
        elif finishTime:
            times.append(time.localtime(time.mktime(finishTime)-time.mktime(startTime)))


        for i in range(1, len(controlls)):
            if i > (len(times) - 1):
                continue
            #print(i, controlls[i-1], controlls[i], times[i])
            values = [(name, ageGroup, club), times[i], True]
            keyTuple1 = (controlls[i-1], controlls[i])
            if keyTuple1 not in siTimes:
                siTimes[keyTuple1] = []
            siTimes[keyTuple1].append(values)

        #break

def createReport(siTimes, args, titleString):

    #######
    # structure: of siTimes
    #
    # map value by key where key is tuple of 2 controls (fromControl, toControl), value is a tuple of 3 elements,
    # where first is tuple of (name, ageGroup, club), second array of times and third a boolean if direction of controls
    # is forward
    #
    #######
    processed = {}
    nameTimes = {}

    htmlpage = E.html()
    htmlpage.append(
        E.head(
            E.title(titleString),
            E.link({'rel':'stylesheet', 'type':'text/css', 'href':'si-analyzer.css'})
        )
    )
    body = E.body()
    body.append(
        E.div({'id':'page_header'},
            E.table(
                E.tr(
                    E.th({'id':'event_name'}, E.nobr(titleString)),
                    E.th({'id':'date_time'}, E.nobr(strftime('%d.%m.%Y %H:%M Uhr', time.localtime())))
                ),
                E.tr(
                    E.th({'id':'page_name'}, E.nobr("Zwischenzeitenauswertung")),
                    E.th({'id':'creation_text'}, E.nobr("erzeugt mit SI-Analyzer von Henry Jobst"))
                )
            )
        )
    )

    ntrow = None
    navtable = E.table({'id':'navtable'})
    nav = E.nav({'id':'navi'})
    header = E.header()
    nav.append(navtable)
    header.append(E.h2("Übersicht"))
    header.append(nav)
    body.append(header)
    sisection = E.section()
    sisection.append(E.h2("Zeiten"))
    body.append(sisection)

    lastkey0 = None

    for item in sorted(siTimes.items(), key=lambda t: t[0][0]+t[0][1]):
        key = item[0]
        #print('#:', key)
        if args.merge and (key[::-1] in processed):
            continue
        values = item[1]
        #print('#:', values)
        if args.merge:
            reverseKey = (key[1], key[0])
            if reverseKey in siTimes:
                reverseValues = list(siTimes[reverseKey])
                for value in reverseValues:
                    value[2] = False
                    values.append(value)

        valueCount = len(values)
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

        key0 = key[0]
        key1 = key[1]
        if key0 == '000':
            key0 = 'Start'
        if key1 == '999':
            key1 = 'Ziel'

        keyString = key0 + '->' + key1
        print()
        print(keyString)
        print()

        splits_div = E.div({'id':'splits'})
        sisection.append(splits_div)
        anchor = "A_{}".format(key0+key1)
        table = E.table({'id': anchor})
        splits_div.append(table)

        arrow = "&nbsp;&hArr;&nbsp;"
        if not args.merge or key0 == "Start" or key1 == "Ziel":
            arrow = "&nbsp;&rArr;&nbsp;"

        table.append(
            E.colgroup(E.col({'width':'25'}), E.col({'width':'35'}), E.col({'width':'60'}), E.col({'width':'20'}), E.col({'width':'250'})))
        table.append(
            E.tr(
                E.th(key0 + html.unescape(arrow) + key1 + ' ({})'.format(valueCount), {'colspan':'5', 'id':'top'})
            )
        )

        if lastkey0 == None or lastkey0 != key0:
            lastkey0 = key0
            ntrow = E.tr()
            navtable.append(ntrow)

        navtd = E.td(
                    E.a(key0 + html.unescape(arrow) + key1 + ' ({})'.format(valueCount), {'href' : '#{}'.format(anchor)} )
                )

        ntrow.append(navtd)

        place = 0
        placeOffset = 0
        lastTime = None
        bestTime = None
        for value in allValues:
            actualName = value[0][0]
            sign = ''
            html_sign = ''
            if value[2] == False:
                html_sign = html.unescape('&nbsp;&lArr;&nbsp;')
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
                tableRow = E.tr()
                tableRow.append(E.td('{:3}.'.format(place)))
                tableRow.append(E.td(strftime('%M:%S', value[1])))
                tableRow.append(E.td(diffString))
                tableRow.append(E.td('{:1}'.format(html_sign)))
                tableRow.append(E.td(actualName))
                table.append(tableRow)
                if actualName in nameTimes:
                    nameTimes[actualName] += actualRuntime
                else:
                    nameTimes[actualName] = actualRuntime
            lastTime = stime
            if bestTime is None:
                bestTime = stime
        processed[key] = True
        table.append(E.tr(E.td({'colspan':'5'}, E.a(html.unescape("&uarr;"), {'href':'#navi'}))))

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

    htmlpage.append(body)

    if args.ofile:
        ofile = open('{}.html'.format(args.ofile), 'w')
        ofile.write(ET.tostring(htmlpage, pretty_print=True).decode('utf-8'))
        ofile.close()

    #print(args.type)
    #print(args.merge)


############################# main program #######################################

parser = argparse.ArgumentParser(description='Analyze SI times.')
parser.add_argument('url')
parser.add_argument('-l', '--local',  action='store_true', help='url is a local file')
parser.add_argument('-t', '--type', choices=['course', 'age', 'all'], default='all', help='group times by all, age group, course, default: all')
parser.add_argument('-i', '--inputformat', choices=['html', 'xml203', 'xml300'], default='html', help='input file format, default: html')
parser.add_argument('-m', '--merge', action='store_true', help='merge control post sequences, eg. 110-111 with 111-110')
parser.add_argument('--proxy')
parser.add_argument('--version', action='version', version='%(prog)s 0.1')
parser.add_argument('-n', '--name', nargs='+')
parser.add_argument('-o', '--ofile', help='switch and filename for html output')

args = parser.parse_args()

print(args.name)

if args.proxy != '':
    proxies = {
        'http' : args.proxy
    }
else:
    proxies = {}

file=None
document = ''

if args.local == True:
    file = open(args.url, 'r', encoding = "ISO-8859-1")
    document = file.read()
else:
    r = requests.get(args.url, proxies=proxies)
    document = r.text

soup = BeautifulSoup(document, 'lxml') #html5lib')

pfile = open('debug.html', 'w', encoding = "ISO-8859-1")
pfile.write(soup.prettify())
pfile.close()

siTimes = {}
titleString = ""

if args.inputformat == 'html':
    parseHTML(soup, siTimes, titleString)
elif  args.inputformat == 'xml203':
    parseXML203(soup, siTimes, titleString)

if len(siTimes):
    createReport(siTimes, args, titleString)


