# INSTALLATION

## On a Linux or Mac system:

1. Open up a terminal window
2. Run `git clone https://github.com/dark-echo/gurgle.git`
3. Copy this google sheet: https://goo.gl/E3Z7mz (or create a google sheet as described below)
4. In sheet, go to Tools > Script Editor
5. Copy Code.gs and paste it into Script Editor. (if code not already in there)
6. Run > setup
7. Publish > Deploy as web app 
   - enter Project Version name and click 'Save New Version' 
   - set security level and enable service (most likely execute as 'me' 
     and access 'anyone, even anonymously) 
8. Copy gurgle.ini to gurgle.local.ini
9. Copy the 'Current web app URL' and put this in the "url" in gurgle.local.ini.
10.  Insert column names on your destination sheet matching the parameter
    names of the data you are passing in (exactly matching case)
11. Make up a key (string), and run `md5 -s 'yourapikey'` or 
    `echo -n 'yourapikey' | md5sum`
12. Put the original key into gurgle.local.ini as apikey
13.  Put the hex string from md5/md5sum into 'api_key' in 
     Script Editor > Project Properties > Script Properties
     (you'll need to add new item)
14. In gurgle.local.ini, edit location name, x, y, z and distance (radius).
    (you can get this info from EDDB)
15. Install python zmq library (for python 2, not 3).
    Depending on your system, any of these might be correct:
    - `yum install python-zmq`
    - `apt-get install python-zmq`
    - `easy_install zmq`
    - `pip install -r requirements.txt`
16. Run `python eddn.py` or `python2 eddn.py` and see what happens.

## On Windows
So far we've just run this on Linux and MacOSX, but there's no reason it
shouldn't work on Windows. Get the latest python2.x and try to do the same
things...  Or install cygwin with md5 and python2 and you can probably
follow the Linux/Mac instructions.

## Google Sheet Requirements

1. A tab called "Influence", or an alternate name configured in the Script Editor.
2. The included `Code.gs` provides for placing provided values into columns based on the column header. Simply add the required columns to the tab defined in step 1.
3. The following columns are supported:
   - `Timestamp` - defined by EDDN message, defining when the event was created by the client in UTC.
   - `EventDate` - date extracted from Timestamp
   - `EventTime` - time extracted from Timestamp
   - `StarSystem` - name of the system for which the data is provided
   - `LocationX` / `LocationY` / `LocationZ` - system coordinates
   - `Distance` - distance calculated for the system based on coordinates provided and configured location in gurgle.ini
   - `SystemSecurity` / `SystemAllegiance` / `SystemGovernment` / `SystemEconomy`
   - `Population` - population, if available in the feed, else blank
   - `SystemFaction` - faction which controls the system
   - For each faction in the system there will be the following, where $ is replaced by 1 to 10.
     - `Faction$Name`
     - `Faction$Influence`
     - `Faction$State` / `Faction$PendingState` / `Faction$RecoveringState`
     - `Faction$Allegiance` / `Faction$Government`
