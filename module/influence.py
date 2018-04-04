from math import pow, sqrt
from datetime import datetime as dt
from config import Config
from sheet import PostUpdate
import re

# Logger instance used by the functions in this module
_LOGGER = Config.getLogger("influence")

# Determine if only looking for events today
_TODAY_ONLY = Config.getBoolean('events', 'today_only', True)
# Determine whether we are rounding the distance or location
_ROUND_DISTANCE = Config.getInteger('events', 'distancedp', -1)
_ROUND_LOCATION = Config.getInteger('events', 'locationdp', -1)
# Allow specific factions to be ignored
_IGNORE_FACTION_SET = set()
_IGNORE_FACTIONS = Config.getString('events', 'ignore_factions')
if _IGNORE_FACTIONS is not None and len(_IGNORE_FACTIONS.strip()) > 0:
    _IGNORE_FACTION_SET.update([faction.strip() for faction in _IGNORE_FACTIONS.split(",")])

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

    # Grab the list of factions, if available
    factionList = event.get("Factions", [])
    # Sort by descending influence (just in case)
    factionList = sorted(factionList, key=lambda faction: float(faction["Influence"]), reverse=True)

    # Compute the distance as square root
    distance = sqrt(starDist2)
    if _ROUND_DISTANCE >= 0:
        distance = round(distance, _ROUND_DISTANCE)
    if _ROUND_LOCATION >= 0:
        starPosX = round(starPosX, _ROUND_LOCATION)
        starPosY = round(starPosY, _ROUND_LOCATION)
        starPosZ = round(starPosZ, _ROUND_LOCATION)

    # Only want to update if we have factions to report on...
    if len(factionList) == 0:
        _LOGGER.debug("Event for %s (%.1fly) discarded since no factions present.", starName, distance)
    elif set([x["Name"] for x in factionList]).issubset(_IGNORE_FACTION_SET):
        _LOGGER.debug("Event for %s (%.1fly) discarded since no interesting factions present.", starName, distance)
    else: # len(factionList) > 0
        _LOGGER.debug("Processing update for %s (%.1fly) from %s", starName, distance, timestamp)
        # Create the update
        update = CreateUpdate(timestamp, starName, systemFaction, factionList)
        update["EventDate"] = eventDate
        update["EventTime"] = eventTime
        # Add the other useful information
        update["Distance"] = distance
        update["LocationX"] = starPosX
        update["LocationY"] = starPosY
        update["LocationZ"] = starPosZ
        update["Population"] = event.get("Population", "")
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
        # Send the update
        PostUpdate(update, factionList)

def CreateUpdate(timestamp, starName, systemFaction, factionList):
    """Formats the information for the upload to the Google Sheet."""
    data = { "Timestamp": timestamp, "StarSystem": starName, "SystemFaction": systemFaction }
    data["SystemAllegiance"] = ""
    data["SystemSecurity"] = ""
    data["SystemGovernment"] = ""
    data["SystemEconomy"] = ""
    factionNo = 1
    for faction in factionList:
        # Not interested in these factions
        if faction["Name"] in _IGNORE_FACTION_SET:
            continue
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
        if "PendingStates" in faction and faction["PendingStates"] is not None:
            for pendingState in faction["PendingStates"]:
                states.append(pendingState["State"])
        data[prefix+"PendingState"] = ",".join(states)
        states = []
        if "RecoveringStates" in faction and faction["RecoveringStates"] is not None:
            for recoveringState in faction["RecoveringStates"]:
                states.append(recoveringState["State"])
        data[prefix+"RecoveringState"] = ",".join(states)
        factionNo = factionNo + 1
    return data
