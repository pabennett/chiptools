import logging
import os
import shlex

from chiptools.wrappers.simulator import Simulator
from chiptools.common.filetypes import FileType
from chiptools.common import utils

log = logging.getLogger(__name__)


class Ghdl(Simulator):

    name = 'ghdl'
    executables = ['ghdl']

    def __init__(self, project, user_paths):
        super(Ghdl, self).__init__(project, self.executables, user_paths)
        self.ghdl = os.path.join(self.path, 'ghdl')

    def simulate(
        self,
        library,
        entity,
        gui=False,
        generics={},
        includes={},
        args=[],
        duration=None
    ):
        # Elaborate
        args = [
            '-e',
            '--work=' + library,
            entity,
        ]
        Ghdl._call(
            self.ghdl, args, cwd=self.project.get_simulation_directory()
        )
        # Run command
        args = [
            '-r',
            '--work=' + library,
        ]
        # Map any generics
        for name, binding in generics.items():
            args += ['-g{0}={1}'.format(name, binding)]
        if duration is not None:
            if duration > 0:
                args += [
                    '--stop-time=' + utils.seconds_to_timestring(duration)
                ]
        # Run the simulation
        args += [entity]
        ret, stdout, stderr = Ghdl._call(
            self.ghdl,
            args,
            cwd=self.project.get_simulation_directory(),
            quiet=False
        )

        return ret, stdout, stderr

    def compile(self, file_object, cwd=None):
        args = self.project.get_tool_arguments(self.name, 'compile')
        if len(args) == 0:
            args = file_object.get_tool_arguments(self.name, 'compile')
        args = shlex.split(['', args][args is not None])
        args += [
            '-a',
            '--work=' + file_object.library,
            file_object.path
        ]
        if file_object.fileType == FileType.VHDL:
            Ghdl._call(
                self.ghdl,
                args,
                cwd=self.project.get_simulation_directory()
            )
        else:
            log.warning(
                'Simulator ignoring file with unsupported extension: ' +
                file_object.path
            )

    def library_exists(self, libname, workdir):
        """
        Return True if the given libname exists in the workdir.
        GHDL doesn't create a folder for each library so we have to check for
        compiled units directly.
        """
        files = os.listdir(workdir)
        for path in files:
            if path.startswith(libname) and path.endswith('.cf'):
                return True
        return False

    def set_working_library(self, library, cwd=None):
        pass

    def set_library_path(self, library, path, cwd=None):
        pass

    def add_library(self, library):
        pass
