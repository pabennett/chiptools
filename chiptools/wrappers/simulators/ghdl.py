import logging
import os
import shlex

from chiptools.wrappers.simulator import Simulator
from chiptools.common.filetypes import FileType

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
        """
        Invoke the simulator and target the given *entity* in the given
        *library*.
        If the optional argument *gui* is set to False the simulator will
        execute as a console application otherwise it will run as a GUI. This
        function is blocking and will only continue when the simulator
        terminates.
        The optional argument *generics* provides a dictionary of *generic
        name*/*generic value*key, value pairs that are passed to the simulator
        as a command line argument. This allowsyou to set generics present on
        the entity being simulated.
        The optional argument *do* can be used to supply a string argument to
        be interpreted by the simulator as a script to execute after loading.
        """


        # Elaborate
        args = [
            '-e',
            '--work=' + library,
            entity,
        ]
        Ghdl._call(self.ghdl, args, cwd=self.project.get_simulation_directory())

        # Run
        args = [
            '-r',
            '--work=' + library,
        ]
        # Map any generics
        for name, binding in generics.items():
            args += ['-g{0}={1}'.format(name, binding)]
        if duration is not None:
            if duration > 0:
                args += ['--stop-time=' + utils.seconds_to_timestring(self.duration)]

        args += [entity]
        ret, stdout, stderr = Ghdl._call(
            self.ghdl,
            args,
            cwd=self.project.get_simulation_directory(),
            quiet=False
        )

        # Add any custom arguments from the project file
        arguments = self.project.get_tool_arguments(self.name, 'simulate')
        arguments = shlex.split(['', arguments][arguments is not None])
        arguments += args




        return ret, stdout, stderr

    def compile(self, file_object, cwd=None):
        """
        Compile the supplied *file_object* into the current working library.
        """
        # Before compiling this file, check to see if it has any additional
        # arguments that need passing to modelsim. First check the global
        # project config, and then check the local file config.
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