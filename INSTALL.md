# INSTALLATION

## On a Linux or Mac system:

1. Open up a terminal window
2. Run `git clone https://github.com/dark-echo/gurgle.git`
3. Create a google sheet with a tab named "Influences"
   (or copy canonical sheet)
4. In sheet, go to Tools > Script Editor
5. Copy Code.gs and paste it into Script Editor.
6. Run > setup
7. Publish > Deploy as web app 
   - enter Project Version name and click 'Save New Version' 
   - set security level and enable service (most likely execute as 'me' 
     and access 'anyone, even anonymously) 
8. Copy the 'Current web app URL' and put this in the "url" in gurgle.ini.
9.  Insert column names on your destination sheet matching the parameter
    names of the data you are passing in (exactly matching case)
10. Make up a key (string), and run `md5 -s 'yourapikey'` or 
    `echo -n 'yourapikey' | md5sum`
11. Put the original key into gurgle.ini as apikey
12.  Put the hex string from md5/md5sum into 'api_key' in 
     Script Editor > Project Properties > Script Properties
     (you'll need to add new item)
13. In gurgle.ini, edit location name, x, y, z and distance (radius).
    (you can get this info from EDDB)
14. Run `python eddn.py` or `python2 eddn.py` and see what happens.
