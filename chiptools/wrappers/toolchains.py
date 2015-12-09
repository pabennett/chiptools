"""
ToolchainBase provides a base class for all tool wrappers and provides the
ability to automatically detect the presence of the toolchain on the user's
system by searching the PATH variable. For system configurations where the
toolchain is not available on the user PATH, or there are multiple versions
of a toolchain, the .chiptoolsconfig configuration file in the user home
directory can be updated to point directly to the toolchain installation
directories.
"""

import os
import sys
import logging

from chiptools.common.utils import execute

log = logging.getLogger(__name__)


class ToolchainBase:

    executables = []

    def __init__(self, project, executables, user_paths):
        self.installed = False
        self.project = project
        if self.name in user_paths:
            path = user_paths[self.name]
            if os.path.exists(path):
                self.path = path
                self.installed = True
                return
            else:
                log.error(
                    (
                        'Invalid path {0} for the {1} toolchain ' +
                        'in the system configuration file. Auto-discovery ' +
                        'for this tool will be used instead.'
                    ).format(
                        path,
                        self.name.capitalize()
                    )
                )
        else:
            log.debug(
                'No user defined path for {0}, using auto-discovery'.format(
                    self.name
                )
            )

        # No explicit path was provided, attempt to auto-discover
        # the location of this particular tool.
        # Search the user's PATH for the required binaries to determine if
        # the tool is available.
        self.path = ToolchainBase.get_path(executables)
        self.installed = os.path.isdir(self.path)

    @staticmethod
    def environ_paths():
        """
        Return a list of the paths found in the PATH environment variable.
        """
        path = os.environ['PATH']
        paths = path.split(os.pathsep)
        paths = [p.lstrip(' ').rstrip(' ') for p in paths]
        return paths

    @staticmethod
    def find_executable(executable, paths):
        """
        Form a list of paths from the input path list pointing to the given
        executable. Only paths that point to the executable in the file system
        will be returned.
        """
        name, ext = os.path.splitext(executable)
        if sys.platform == 'win32' and len(ext) == 0:
            executable += '.exe'
        files = list(
            filter(
                lambda x: os.path.isfile(x),
                [os.path.join(p, executable) for p in paths]
            )
        )
        return files

    @staticmethod
    def find_toolchain(executables, paths):
        """
        Return the first path from the paths list that contains all supplied
        executable names.
        """
        allRoots = [
            [
                os.path.dirname(
                    path
                ) for path in ToolchainBase.find_executable(
                    exe,
                    paths
                )
            ] for exe in executables
        ]
        # Iterate across each root path in the first root list and return the
        # root path if it is present in all other root lists.
        for root in allRoots[0]:
            if all(root in roots for roots in allRoots):
                return root
        return None

    @staticmethod
    def get_path(executables):
        """
        Return the first path in the PATH environment path list that contains
        all of the executable names required by this toolchain.
        """
        if len(executables) == 0:
            return ''
        paths = ToolchainBase.environ_paths()
        root = ToolchainBase.find_toolchain(executables, paths)
        if root is None:
            return ''
        if os.path.isdir(root):
            return root
        return ''

    @staticmethod
    def _call(executable, args=[], cwd=None, quiet=True):
        log.debug('executing {0} in dir {1} with args {2}'.format(
            executable,
            cwd,
            args
        ))
        command = [executable]
        command += args
        ret, stdout, stderr = execute(command, path=cwd, quiet=quiet)
        return (ret, stdout, stderr)

    @staticmethod
    def _call_str_args(executable, args='', cwd=None, quiet=True):
        log.debug('executing {0} in dir {1} with args {2}'.format(
            executable,
            cwd,
            args
        ))
        command = executable
        command += (' ' + args)
        ret, stdout, stderr = execute(command, path=cwd, quiet=quiet)
        return (ret, stdout, stderr)
