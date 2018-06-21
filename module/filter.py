from math import pow
from datetime import datetime as dt
from config import Config

# Logger instance used by the functions in this module
_LOGGER = Config.getLogger("filter")

# Determine if only looking for events today
_TODAY_ONLY = Config.getBoolean('events', 'today_only', True)
# Allow specific named systems to be included in the updates
_INCLUDE_SYSTEM_SET = set()
_INCLUDE_SYSTEMS = Config.getString('events', 'include_systems')
if _INCLUDE_SYSTEMS is not None and len(_INCLUDE_SYSTEMS.strip()) > 0:
    _INCLUDE_SYSTEM_SET.update([system.strip() for system in _INCLUDE_SYSTEMS.split(",")])
if len(_INCLUDE_SYSTEM_SET) > 0:
    _LOGGER.info("Configured for systems: %s", ", ".join(_INCLUDE_SYSTEM_SET))

# Interested in activity around specific locations
def InitialiseLocations():
    """Returns a list of dictionaries that define the volumes within which events
        should be reported.
    """
    locations = []
    section = "location"
    sectionNumber = 0
    while Config.hasSection(section):
        locationX = Config.getFloat(section, 'x')
        locationY = Config.getFloat(section, 'y')
        locationZ = Config.getFloat(section, 'z')
        locationD = Config.getFloat(section, 'distance')
        locations.append({'x': locationX, 'y': locationY, 'z': locationZ, 'd2': locationD**2})
        _LOGGER.info("Configured for %.1f LY around %s", locationD, Config.getString(section, 'name'))
        sectionNumber+=1
        section = "location.%d" % sectionNumber
    return locations
_LOCATIONS = InitialiseLocations()

def IsInteresting(event):
    """Returns True if the FSDJump event (or equivalent subset of Location event)
        provided by Journal is interesting according to the filter configuration.
    """
    isInterestingSystem = IsInterestingSystem(event)
    if isInterestingSystem:
        # Determine if the timestamp is considered relevant
        # (NOTE: assumption we receive UTC)
        timestamp = event["timestamp"]
        eventDate = timestamp[0:10]
        todayDate = dt.utcnow().strftime("%Y-%m-%d")
        if _TODAY_ONLY and eventDate != todayDate:
            starName = event["StarSystem"]
            _LOGGER.debug("Event for %s discarded as not today: %s", starName, eventDate)
            return False
    return isInterestingSystem

def IsInterestingSystem(event):
    """Returns True if the FSDJump event (or equivalent subset of Location event)
        provided by Journal references a system we are interested in, else False.
    """
    # Extract the star name which is always provided
    starName = event["StarSystem"]
    # Determine if the system must always be included in updates
    if starName in _INCLUDE_SYSTEM_SET:
        return True
    # Extract the StarPos to confirm we're interested
    (starPosX, starPosY, starPosZ) = event["StarPos"]
    for location in _LOCATIONS:
        x = location['x']
        y = location['y']
        z = location['z']
        d2 = location['d2']
        starDist2 = pow(x-starPosX,2)+pow(y-starPosY,2)+pow(z-starPosZ,2)
        if starDist2 <= d2:
            return True
    # Not included in any particular location selection, so not interested
    return False

