from math import pow, sqrt
from urllib2 import urlopen
from urllib import urlencode
from datetime import datetime as dt
from config import Config
import json
import re
import time

# Logger instance used by the functions in this module
_LOGGER = Config.getLogger("influence")

# Configuration for the Google Sheet interaction
__SHEET_URL = Config.getString('sheet', 'url')
__SHEET_API_KEY = Config.getCrypt('sheet', 'apikey')
__SHEET_RETRIES = Config.getInteger('sheet', 'retries', 3)
__SHEET_RETRY_WAIT = Config.getInteger('sheet', 'retry_wait', 3)
__SHEET_TIMEOUT = Config.getInteger('sheet', 'timeout', 10)
__SHEET_RESPONSE_BUFFER = Config.getInteger('sheet', 'buffer', 512)
_TODAY_ONLY = Config.getBoolean('events', 'today_only', True)

# Interested in activity around a specified location
_LOCATION_X = Config.getFloat('location', 'x')
_LOCATION_Y = Config.getFloat('location', 'y')
_LOCATION_Z = Config.getFloat('location', 'z')
_RANGE_SQUARED = Config.getFloat('location', 'distance')**2
_LOGGER.info("Configured for %.1f LY around %s", Config.getFloat('location', 'distance'), Config.getString('location', 'name'))

# Provide regular expressions to remove extraneous text specifiers
_MATCH_GOV = re.compile(r'\$government_(.*);', re.IGNORECASE)
_MATCH_SEC = re.compile(r'\$system_security_(.*);', re.IGNORECASE)
_MATCH_SEC2 = re.compile(r'\$GAlAXY_MAP_INFO_state_(.*);', re.IGNORECASE)
_MATCH_ECO = re.compile(r'\$economy_(.*);', re.IGNORECASE)

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
    """Consumes the FSDJump event (or equivalent subset of Location event)
        provided by Journal, extracting the factions and influence levels.
    """
    # Extract the StarPos to confirm we're interested
    (starPosX, starPosY, starPosZ) = event["StarPos"]
    starDist2 = pow(_LOCATION_X-starPosX,2)+pow(_LOCATION_Y-starPosY,2)+pow(_LOCATION_Z-starPosZ,2)
    if starDist2 > _RANGE_SQUARED:
        return
    # Extract the star name which is always provided
    starName = event["StarSystem"]
    # Determine if the timestamp is considered relevant
    timestamp = event["timestamp"]
    eventDate = timestamp[0:10]
    eventTime = timestamp[11:19]
    todayDate = dt.utcnow().strftime("%Y-%m-%d")
    if _TODAY_ONLY and eventDate != todayDate:
        _LOGGER.debug("Event for %s discarded as not today: %s", starName, eventDate)
        return
    # Interested, so we gather information we want to publish
    # Nothing else below here guaranteed to be available
    systemFaction = event.get("SystemFaction", "")
    systemAllegiance = event.get("SystemAllegiance", "")
    systemSecurity = event.get("SystemSecurity", "")
    systemGovernment = event.get("SystemGovernment", "")
    systemEconomy = event.get("SystemEconomy", "")
    distance = sqrt(starDist2)
    systemPopulation = event.get("Population", "")
    
    # Grab the list of factions, if available
    factionList = event.get("Factions", [])
    # Sort by descending influence (just in case)
    factionList = sorted(factionList, key=lambda faction: float(faction["Influence"]), reverse=True)

    #print "%s %s (%.1fly) %s" % (timestamp, starName, distance, systemFaction)
    #for faction in factionList:
    #    print " %s at %.1f%% in state %s" % (faction["Name"],faction["Influence"]*100,faction["FactionState"])

    # Only want to update if we have factions to report on...
    if len(factionList) == 0:
        _LOGGER.debug("Event for %s discarded since no factions present.", starName)
    else: # len(factionList) > 0
        _LOGGER.debug("Processing update for %s (%.1fly) from %s", starName, distance, timestamp)
        # Create the update
        update = CreateUpdate(timestamp, starName, systemFaction, factionList)
        update["EventDate"] = eventDate
        update["EventTime"] = eventTime
        # Add the other useful information
        update["Distance"] = distance
        update["Population"] = systemPopulation
        if len(systemAllegiance) > 0:
            update["SystemAllegiance"] = systemAllegiance
        if len(systemSecurity) > 0 and _MATCH_SEC.match(systemSecurity) is not None:
            update["SystemSecurity"] = _MATCH_SEC.match(systemSecurity).group(1)
        if len(systemSecurity) > 0 and _MATCH_SEC2.match(systemSecurity) is not None:
            update["SystemSecurity"] = _MATCH_SEC2.match(systemSecurity).group(1)
        if len(systemGovernment) > 0 and _MATCH_GOV.match(systemGovernment) is not None:
            update["SystemGovernment"] = _MATCH_GOV.match(systemGovernment).group(1)
        if len(systemEconomy) > 0 and _MATCH_ECO.match(systemEconomy) is not None:
            update["SystemEconomy"] = _MATCH_ECO.match(systemEconomy).group(1)
        # Send the update, if Cache says we need to
        if CheckCache(eventDate, starName, factionList):
            if SendUpdate(update):
                _LOGGER.info("Processed (sent) update for %s (%.1fly)", starName, distance)
                # Update the Cache Entry (after send so we have definitely send)
                CacheUpdate(eventDate, starName, factionList)
            else:
                _LOGGER.warning("Failed to send update for %s (%.1fly)", starName, distance)
        else:
            _LOGGER.debug("Processed (not sent) update for %s (%.1fly)", starName, distance)

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
        # Support for Pending/Recovering States
        #  since sheet is expecting either all information or none for
        #  each faction we always need to specify these, even if not present
        states = []
        if "PendingStates" in faction:
            for pendingState in faction["PendingStates"]:
                states.append(pendingState["State"])
        data[prefix+"PendingState"] = ",".join(states)
        states = []
        if "RecoveringStates" in faction:
            for recoveringState in faction["RecoveringStates"]:
                states.append(recoveringState["State"])
        data[prefix+"RecoveringState"] = ",".join(states)
        factionNo = factionNo + 1
    return data

def SendUpdate(dictionary):
    """Posts the specified dictionary to the Google Sheet.

    To be successful we need to provide an appropriate API_KEY value, and we also
    want to retry any infrastructure errors (i.e. unable to complete the POST) but
    abandon the entire process if the "application" does not report success (i.e.
    on an invalid token, badly formed request, etc.).
    """
    dictionary['API_KEY'] = __SHEET_API_KEY
    data = urlencode(dictionary)
    retries = __SHEET_RETRIES
    success = 0
    response = None
    while success != 200 and retries > 0:
        try:
            request = urlopen(__SHEET_URL, data, __SHEET_TIMEOUT)
            success = request.getcode()
            response = request.read(__SHEET_RESPONSE_BUFFER)
            request.close()
        except Exception, e:
            _LOGGER.info("(Retry %d) Exception while attempting to POST data: %s", retries, str(e))
            retries -= 1
            if retries > 0:
                time.sleep(__SHEET_RETRY_WAIT)
    # Check the response for validity, where "result"="success"
    if success == 200 and response is not None:
        result = json.loads(response) # Throws Exception if JSON not returned
        if (result["result"] != "success"):
            raise Exception("Bad response from Sheet: %s" % result)
        _LOGGER.debug("Success Response: %s" % result)
    return (success == 200)
