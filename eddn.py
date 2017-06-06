import zlib
import zmq
import json
import time
from config import Config
from influence import ConsumeFSDJump

# Configuration determination, currently on import since it's required
__relayEDDN = Config.getString('eddn', 'relay')
__timeoutEDDN = Config.getInteger('eddn', 'timeout', 60000)

# Only interested in the Journal Schema ($schemaRef)
_SCHEMA_REF = "http://schemas.elite-markets.net/eddn/journal/1"

def main():
    """Main method that connects to EDDN."""
    logger = Config.getLogger("eddn")
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, "")

    while True:
        try:
            subscriber.connect(__relayEDDN)
            logger.info('Connected to EDDN at %s', __relayEDDN)
            
            poller = zmq.Poller()
            poller.register(subscriber, zmq.POLLIN)
 
            while True:
                socks = dict(poller.poll(__timeoutEDDN))
                if socks:
                    if socks.get(subscriber) == zmq.POLLIN:
                        __message   = subscriber.recv(zmq.NOBLOCK)
                        __message   = zlib.decompress(__message)
                        __json      = json.loads(__message)
                        if __json["$schemaRef"] == _SCHEMA_REF:
                            __content = __json["message"]
                            # Only interested in FSDJump event currently
                            if __content["event"] == "FSDJump":
                                ConsumeFSDJump(__content)
                else:
                    logger.warning('Disconnect from EDDN (After timeout)')
                    subscriber.disconnect(__relayEDDN)
                    break
                
        except zmq.ZMQError, e:
            logger.warning('Disconnect from EDDN (After receiving ZMQError)', exc_info=True)
            subscriber.disconnect(__relayEDDN)
            time.sleep(10)
        except Exception:
            logger.critical('Unhandled exception occurred while processing EDDN messages.', exc_info=True)
            break # exit the main loop

# Enable command line execution
if __name__ == '__main__':
    main()
