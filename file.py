from math import pow, sqrt
from urllib2 import urlopen
from urllib import urlencode
from datetime import datetime as dt
import json
import sys
import time
import re

# Configuration for the Google Sheet interaction
__SHEET_URL = "##SET TO GOOGLE API URL##"

_MATCH_GOV = re.compile(r'\$government_(.*);', re.IGNORECASE)
_MATCH_SEC = re.compile(r'\$system_security_(.*);', re.IGNORECASE)
_MATCH_ECO = re.compile(r'\$economy_(.*);', re.IGNORECASE)

# Interested in activity around Disci (16.03125, 97.59375, -29.59375)
_LOCATION_X = 16.03125
_LOCATION_Y = 97.59375
_LOCATION_Z = -29.59375
_RANGE_SQUARED = 60**2 # 100 Light Years

# Cache mechanism that attempts to prevent duplicate updates
#  While ideally we wanted the Google Sheet to prevent duplicates, this is
#  actually very difficult to achieve due to a lack of optimised search functionality.
#  Instead we'll attempt to prevent duplicates within a single instance and
#  the sheet will handle selecting appropriate entries due to complexities such
#  as the BGS Tick Date and whether we trust data around the tick time which
#  can change 'on a whim'.
# This 'cache' is date-keyed, but we enforce only having an entry for today (which
#  ensures automatic clean-up if we continue to execute over several days).
# The key (date) maps to a single map which maps System Name to a List of Faction
#  Influence and State values, which we use to determine if there has been a change
#  that we need to communicate to the Google Sheet.
_CACHE_BY_DATE = {}

def ConsumeFSDJump(event):
    """Consumes the FSDJump event provided by Journal,
        extracting the factions and influence levels.
    """
    # Extract the StarPos to confirm we're interested
    (starPosX, starPosY, starPosZ) = event["StarPos"]
    starDist2 = pow(_LOCATION_X-starPosX,2)+pow(_LOCATION_Y-starPosY,2)+pow(_LOCATION_Z-starPosZ,2)
    if starDist2 > _RANGE_SQUARED:
        return
    # Determine if the timestamp is considered relevant
    timestamp = event["timestamp"]
    eventDate = timestamp[0:10]
    eventTime = timestamp[11:19]
    todayDate = dt.utcnow().strftime("%Y-%m-%d")
    if eventDate != todayDate:
        print "Event discarded as not today: %s" % eventDate
        return
    # Interested, so we gather information we want to publish
    starName = event["StarSystem"]
    # Nothing else below here guaranteed to be available
    systemFaction = event.get("SystemFaction", "")
    systemAllegiance = event.get("SystemAllegiance", "")
    systemSecurity = event.get("SystemSecurity", "")
    systemGovernment = event.get("SystemGovernment", "")
    systemEconomy = event.get("SystemEconomy", "")
    distance = sqrt(starDist2)
    # Grab the list of factions, if available
    factionList = event.get("Factions", [])
    # Sort by descending influence (just in case)
    factionList = sorted(factionList, key=lambda faction: float(faction["Influence"]), reverse=True)

    print "%s %s (%.1fly) %s" % (timestamp, starName, distance, systemFaction)
    for faction in factionList:
        print " %s at %.1f%% in state %s" % (faction["Name"],faction["Influence"]*100,faction["FactionState"])

    # Only want to update if we have factions to report on...
    if len(factionList) > 0:
        # Create the update
        update = CreateUpdate(timestamp, starName, systemFaction, factionList)
        update["EventDate"] = eventDate
        update["EventTime"] = eventTime
        # Add the other useful information
        update["Distance"] = distance
        if len(systemAllegiance) > 0:
            update["SystemAllegiance"] = systemAllegiance
        if len(systemSecurity) > 0 and _MATCH_SEC.match(systemSecurity) is not None:
            update["SystemSecurity"] = _MATCH_SEC.match(systemSecurity).group(1)
        if len(systemGovernment) > 0 and _MATCH_GOV.match(systemGovernment) is not None:
            update["SystemGovernment"] = _MATCH_GOV.match(systemGovernment).group(1)
        if len(systemEconomy) > 0 and _MATCH_ECO.match(systemEconomy) is not None:
            update["SystemEconomy"] = _MATCH_ECO.match(systemEconomy).group(1)
        # Send the update, if Cache says we need to
        if CheckCache(eventDate, starName, factionList):
            SendUpdate(update)
            # Update the Cache Entry (after send so we have definitely send)
            CacheUpdate(eventDate, starName, factionList)

def CheckCache(eventDate, starName, factionList):
    # If the cache doesn't have an entry for today, clear it and add empty
    if eventDate not in _CACHE_BY_DATE:
        _CACHE_BY_DATE.clear()
        _CACHE_BY_DATE[eventDate] = {}
        return True
    # If the cache of stars doesn't have this star, we should send
    starCache = _CACHE_BY_DATE[eventDate]
    if starName not in starCache:
        return True
    # Need to check if the cache entry matches what we want to send
    if starCache[starName] != factionList:
        return True
    # Cache matches supposed update, so no need to send
    return False

def CacheUpdate(eventDate, starName, factionList):
    starCache = _CACHE_BY_DATE[eventDate]
    starCache[starName] = factionList

def CreateUpdate(timestamp, starName, systemFaction, factionList):
    """Formats the information for the upload to the Google Sheet."""
    data = { "Timestamp": timestamp, "StarSystem": starName, "SystemFaction": systemFaction }
    data["SystemAllegiance"] = ""
    data["SystemSecurity"] = ""
    data["SystemGovernment"] = ""
    data["SystemEconomy"] = ""
    factionNo = 1
    for faction in factionList:
        prefix = "Faction{:d}".format(factionNo)
        data[prefix+"Name"] = faction["Name"]
        data[prefix+"Influence"] = faction["Influence"]
        data[prefix+"State"] = faction["FactionState"]
        data[prefix+"Allegiance"] = faction["Allegiance"]
        data[prefix+"Government"] = faction["Government"]
        factionNo = factionNo + 1
    return data

def SendUpdate(dictionary):
    """Posts the specified dictionary to the Google Sheet."""
    data = urlencode(dictionary)
    response = urlopen(__SHEET_URL, data)
    success = response.getcode()
    response.close()
    return (success == 200)
    
def main():
    """Main method that reads file for update."""
    fileName = sys.argv[1]
    print "Checking file: %s" % fileName
    with open(fileName, "r") as file:
        for line in file:
            __content = json.loads(line)
            # Only interested in FSDJump event currently
            if __content["event"] == "FSDJump":
                ConsumeFSDJump(__content)
                sys.stdout.flush()

# Enable command line execution
if __name__ == '__main__':
    main()
