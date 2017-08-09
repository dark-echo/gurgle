"""Provides for basic configuration of the system parameters and logging infrastructure."""
import ConfigParser
import json
import logging
import logging.config
import md5
from os import makedirs
from os.path import isdir, isfile

# Defines the file names checked for configuration information
_CONFIG_FILES = ['gurgle-local.ini', 'gurgle.local.ini', 'gurgle.ini']
# Defines the section and field used to hold logging framework configuration
_LOG_SECTION = 'logging'
_LOG_CONFIG = 'config'
_LOG_DIRECTORY = 'directory'
# Defines a default formatter for the logging framework, if not configured
_LOG_FORMAT = "%(asctime)-19.19s %(levelname)-5.5s [%(name)s] %(message)s"

class Configuration(object):
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        # Check configuration files in preference order
        for filename in _CONFIG_FILES:
            if isfile(filename):
                self.config.read(filename)
                break # first config file found is used

    def initialiseLogging(self):
        # If a directory is specified, we might need to create it
        if self.config.has_option(_LOG_SECTION, _LOG_DIRECTORY):
            logDirectory = self.config.get(_LOG_SECTION, _LOG_DIRECTORY)
            if not isdir(logDirectory):
                makedirs(logDirectory)
        # Use any logging configuration specified
        if self.config.has_option(_LOG_SECTION, _LOG_CONFIG):
            logConfig = self.config.get(_LOG_SECTION, _LOG_CONFIG)
            logDict = json.loads(logConfig)
            logging.config.dictConfig(logDict)
        else:
            logging.basicConfig(format=_LOG_FORMAT)

    def getLogger(self, name):
        return logging.getLogger(name)

    def getString(self, section, name):
        return self.config.get(section, name)

    def getInteger(self, section, name, default):
        if self.config.has_option(section, name):
            return self.config.getint(section, name)
        return default

    def getFloat(self, section, name):
        return self.config.getfloat(section, name)

    def getBoolean(self, section, name, default=False):
        return self.config.getboolean(section, name) if self.config.has_option(section, name) else default

    def getCrypt(self, section, name):
        return md5.new(self.config.get(section, name)).hexdigest()

# Initialise on the first import of the module
Config = Configuration()
Config.initialiseLogging()
