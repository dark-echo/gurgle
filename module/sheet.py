from urllib2 import urlopen
from urllib import urlencode
from config import Config
from cache import IsNotInCache, CacheUpdate
import json
import time

# Logger instance used by the functions in this module
_LOGGER = Config.getLogger("sheet")

# Configuration for the Google Sheet interaction
__SHEET_URL = Config.getString('sheet', 'url')
__SHEET_API_KEY = Config.getCrypt('sheet', 'apikey')
__SHEET_RETRIES = Config.getInteger('sheet', 'retries', 3)
__SHEET_RETRY_WAIT = Config.getInteger('sheet', 'retry_wait', 3)
__SHEET_TIMEOUT = Config.getInteger('sheet', 'timeout', 10)
__SHEET_RESPONSE_BUFFER = Config.getInteger('sheet', 'buffer', 512)


def PostUpdate(update, factionList):
    """Responsible for sending the specified update to the Google Sheet."""
    starName = update["StarSystem"]
    eventDate = update["EventDate"]
    distance = update["Distance"]
    # Send the update, if Cache says we need to
    if IsNotInCache(eventDate, starName, factionList):
        if SendUpdate(update):
            _LOGGER.info("Processed (sent) update for %s (%.1fly)", starName, distance)
            # Update the Cache Entry (after send so we have definitely sent)
            CacheUpdate(eventDate, starName, factionList)
        else:
            _LOGGER.warning("Failed to send update for %s (%.1fly)", starName, distance)
    else:
        _LOGGER.debug("Processed (not sent) update for %s (%.1fly)", starName, distance)

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
