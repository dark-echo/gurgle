import json
import sys
from influence import ConsumeFSDJump

def main():
    """Main method that reads file for update."""
    fileName = sys.argv[1]
    print "Checking file: %s" % fileName
    with open(fileName, "r") as file:
        for line in file:
            __content = json.loads(line)
            # Only interested in FSDJump event currently
            if __content["event"] == "FSDJump":
                ConsumeFSDJump(__content)
                sys.stdout.flush()

# Enable command line execution
if __name__ == '__main__':
    main()
