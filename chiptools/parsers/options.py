"""
Options parser package for the build/verification framework application.

The Options class contained within provides convenient access to system
configuration settings with error checking and file-modification checking.

The path to the system configuration file is hard-coded into options_path.
"""

import configparser as config
import os
import logging
import traceback
import hashlib
from collections import OrderedDict
from os.path import expanduser

log = logging.getLogger(__name__)

# Get the user home directory
home = expanduser('~')
# The chiptools config file resides in the user home directory
options_path = os.path.join(home, '.chiptoolsconfig')


class Options:
    """
    An Options instance provides convenient access to an INI based
    configuration file.

    When an Options instance is created it will load the '.chiptoolsconfig'
    file located in the root of the application and parse the settings
    contained within.

    If no configuration file is preset a placeholder will be generated using
    the CONFIG_DEFAULTS as a base.
    """

    CONFIG_DEFAULTS = OrderedDict([
        ('simulation dependencies', OrderedDict([
        ])),
        ('simulation executables', OrderedDict([

        ])),
        ('synthesis executables', OrderedDict([

        ])),
    ])

    def __init__(self):
        """
        Initialise an Options instance.

        An exception is raised if the system configuration file is missing or
        contains invalid data.
        """
        self.synthesisers = {}
        self.simulators = {}
        self.simulatorLibraryDependencies = {}
        super(Options, self).__init__()
        self.options_md5 = None
        log.debug('Initialising options parser')
        self._options = config.RawConfigParser()
        self.startup()

    def startup(self):
        """
        Load the system configuration file and store the settings in local
        attributes.

        The system configuration file MD5 sum is stored so that file changes
        can be detected at runtime.

        This method will return an exception if the system configuration file
        is missing or contains invalid data.
        """
        try:
            log.debug('Loading options file...')
            self._loadOptionsFile()
            self.synthesisers = Options.readOptionsPaths(
                self._options,
                'synthesis executables',
                transform=lambda x: os.path.expandvars(x),
            )
            self.simulators = Options.readOptionsPaths(
                self._options,
                'simulation executables',
                transform=lambda x: os.path.expandvars(x),
            )
            self.simulatorLibraryDependencies = Options.readOptionsPaths(
                self._options,
                'simulation dependencies'
            )
            log.debug('...done loading options file')
        except (config.ParsingError):
            log.error(
                'The Options file is badly formatted, ' +
                'parsing failed with the ' +
                'following error:'
            )
            log.error(traceback.format_exc())

    def _loadOptionsFile(self):
        """
        Open the system configuration file and store the configuration data in
        this Options instance.

        Store the system configuration MD5 sum to detect file changes during
        runtime.
        """
        if not os.path.exists(options_path):
            log.debug(
                'The options file could not be found, a default options ' +
                'file will be created...'
            )
            for section in self.CONFIG_DEFAULTS.keys():
                self._options.add_section(section)
                for k, v in self.CONFIG_DEFAULTS[section].items():
                    self._options.set(section, k, v)
            with open(options_path, 'w') as cf:
                self._options.write(cf)
            log.debug('... finished creating default options file')
        with open(options_path, 'rb') as f:
            self.options_md5 = hashlib.md5(f.read()).hexdigest()
        self._options.read(options_path)

    @staticmethod
    def readOptionsPaths(options, section, transform=lambda x: x):
        result = {}
        try:
            for key, value in options.items(section):
                result[key] = transform(value)
        except config.NoSectionError:
            pass
        return result

    def refresh(self):
        try:
            with open(options_path, 'rb') as f:
                current_md5 = hashlib.md5(f.read()).hexdigest()
            if self.options_md5 != current_md5:
                self.startup()
        except FileNotFoundError:
            pass

    def getOptionsPath(self):
        """
        Return the path to the system configuration file
        """
        return os.path.abspath(os.path.normpath(options_path))

    def getSynthesisTools(self):
        """
        Return a dictionary of synthesis tool name / path pairs.

        If the configuration file was modified since the last access it will be
        reloaded and the new entries returned.
        """
        self.refresh()
        return self.synthesisers

    def getSimulationTools(self):
        """
        Return a dictionary of simulation tool name / path pairs.

        If the configuration file was modified since the last access it will be
        reloaded and the new entries returned.
        """
        self.refresh()
        return self.simulators

    def get_user_tool_paths(self):
        """
        Return a dictionary of all user specified tool paths.
        """
        ret = self.synthesisers.copy()
        ret.update(self.simulators)
        return ret

    def get_synthesis_tool_path(self, toolName):
        """
        Return the executable path for the given simulator name 'toolName'.

        If no path is found for 'toolName' NoneType will be returned.

        If the configuration file was modified since the last access it will be
        reloaded and the new entries returned.
        """
        self.refresh()
        if toolName in self.synthesisers:
            return self.synthesisers[toolName]
        log.error('Unknown synthesis tool: ' + toolName)
        return None

    def get_simulator_library_dependencies(self):
        """
        Return the simulator library dependencies.

        If the configuration file was modified since the last access it will be
        reloaded and the new entries returned.
        """
        self.refresh()
        return self.simulatorLibraryDependencies
