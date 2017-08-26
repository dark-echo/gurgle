from datetime import datetime as dt

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

def IsNotInCache(date, name, value):
    """Returns True if the specified value does NOT match the cache, else False.

    Note that this cache implementation only ensures that values for the current
    date are stored and is not a general cache mechanism.
    """
    # We only ever cache the values for 'today', assuming either the caller
    #  will reject other dates or requires all updates to flow
    todayDate = dt.utcnow().strftime("%Y-%m-%d")
    # If we're provided an item that isn't for today, simply return True
    if date != todayDate:
        return True
    # If the cache doesn't have an entry for today, clear it and add empty
    if date not in _CACHE_BY_DATE:
        _CACHE_BY_DATE.clear()
        _CACHE_BY_DATE[date] = {}
        return True
    # Does the cache already have this key?
    entries = _CACHE_BY_DATE[date]
    if name not in entries:
        return True
    # Need to check if the cache entry matches what we want to send
    if entries[name] != value:
        return True
    # Cache matches specified value
    return False

def CacheUpdate(date, name, value):
    """Ensures the cache is updated with the lastest value."""
    if date in _CACHE_BY_DATE:
        entries = _CACHE_BY_DATE[date]
        entries[name] = value
