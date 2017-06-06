import json
import sys
from config import Config
from influence import ConsumeFSDJump

def main():
    """Main method that reads file for update."""
    logger = Config.getLogger("file")
    fileName = sys.argv[1]
    logger.info("Reading file: %s", fileName)
    try:
        with open(fileName, "r") as file:
            for line in file:
                __content = json.loads(line)
                # Only interested in FSDJump event currently
                if __content["event"] == "FSDJump":
                    ConsumeFSDJump(__content)
    except:
        logger.critical('Unexpected exception while processing.', exc_info=True)

# Enable command line execution
if __name__ == '__main__':
    main()
