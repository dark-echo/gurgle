import zlib
import zmq
import json
import sys
import time
from influence import ConsumeFSDJump

# Configuration determination, currently on import since it's required
import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('gurgle.ini')

__relayEDDN = config.get('eddn', 'relay')
__timeoutEDDN = config.getint('eddn', 'timeout')

# Only interested in the Journal Schema ($schemaRef)
_SCHEMA_REF = "http://schemas.elite-markets.net/eddn/journal/1"

def main():
    """Main method that connects to EDDN."""
    context     = zmq.Context()
    subscriber  = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, "")

    while True:
        try:
            subscriber.connect(__relayEDDN)
            print 'Connected to EDDN at', __relayEDDN
            sys.stdout.flush()
            
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
                                sys.stdout.flush()
                else:
                    print 'Disconnect from EDDN (After timeout)'
                    sys.stdout.flush()
                    
                    subscriber.disconnect(__relayEDDN)
                    break
                
        except zmq.ZMQError, e:
            print 'Disconnect from EDDN (After receiving ZMQError)'
            print 'ZMQSocketException: ' + str(e)
            sys.stdout.flush()
            
            subscriber.disconnect(__relayEDDN)
            time.sleep(10)

# Enable command line execution
if __name__ == '__main__':
    main()
