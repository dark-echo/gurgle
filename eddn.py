import zlib
import zmq
import json
import time
from config import Config
from influence import ConsumeFSDJump

# Configuration specified for the EDDN connection
__EDDN_RELAY = Config.getString('eddn', 'relay')
__EDDN_TIMEOUT = Config.getInteger('eddn', 'timeout', 60000)
__EDDN_RECONNECT = Config.getInteger('eddn', 'reconnect', 10)

# Only interested in the Journal Schema ($schemaRef)
_SCHEMA_REFS = [ "http://schemas.elite-markets.net/eddn/journal/1", "http://eddn.edcd.io/eddn/journal/1" ]

def processMessage(message, logger):
    """Processes the specified message, if possible."""
    try:
        jsonmsg = json.loads(message)
        if jsonmsg["$schemaRef"] in _SCHEMA_REFS:
            content = jsonmsg["message"]
            # Only interested in FSDJump event currently
            if content["event"] == "FSDJump":
                ConsumeFSDJump(content)
    except Exception:
        logger.exception('Received message caused unexpected exception, Message: %s' % message)

def main():
    """Main method that connects to EDDN and processes messages."""
    logger = Config.getLogger("eddn")
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, "")

    while True:
        try:
            subscriber.connect(__EDDN_RELAY)
            logger.info('Connected to EDDN at %s', __EDDN_RELAY)

            poller = zmq.Poller()
            poller.register(subscriber, zmq.POLLIN)

            while True:
                socks = dict(poller.poll(__EDDN_TIMEOUT))
                if socks:
                    if socks.get(subscriber) == zmq.POLLIN:
                        message = subscriber.recv(zmq.NOBLOCK)
                        message = zlib.decompress(message)
                        processMessage(message, logger)
                else:
                    logger.warning('Disconnect from EDDN (After timeout)')
                    subscriber.disconnect(__EDDN_RELAY)
                    break

        except zmq.ZMQError, e:
            logger.warning('Disconnect from EDDN (After receiving ZMQError)', exc_info=True)
            subscriber.disconnect(__EDDN_RELAY)
            logger.debug('Reconnecting to EDDN in %d seconds.' % __EDDN_RECONNECT)
            time.sleep(__EDDN_RECONNECT)
        except Exception:
            logger.critical('Unhandled exception occurred while processing EDDN messages.', exc_info=True)
            break # exit the main loop

# Enable command line execution
if __name__ == '__main__':
    main()
