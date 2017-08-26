import json
import sys
from module.config import Config
from module.influence import ConsumeFSDJump

def main():
    """Main method that reads file for update."""
    logger = Config.getLogger("file")
    fileName = sys.argv[1]
    logger.info("Reading file: %s", fileName)
    try:
        with open(fileName, "r") as file:
            for line in file:
                content = json.loads(line)
                # Only interested in FSDJump or Location events
                if content["event"] in ["FSDJump", "Location"]:
                    ConsumeFSDJump(content)
    except:
        logger.critical('Unexpected exception while processing.', exc_info=True)

# Enable command line execution
if __name__ == '__main__':
    main()
