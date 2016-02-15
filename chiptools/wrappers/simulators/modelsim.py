import logging
import os
import shlex

from chiptools.wrappers.simulator import Simulator
from chiptools.common.filetypes import FileType
from chiptools.common import utils

log = logging.getLogger(__name__)


class Modelsim(Simulator):
    """
    ModelsimSimulator provides a wrapper around ModelSim to allow simulations
    to be performed using the data contained in the supplied Project and
    Options instances.
    The ModelsimSimulator wrapper can be used to create libraries, compile
    files and invoke ModelSim in either interactive (GUI) mode or as a console
    application to support automated unit testing of the design.
    """

    name = 'modelsim'
    executables = ['vcom', 'vlib', 'vlog', 'vmap', 'vsim']

    def __init__(self, project, user_paths):
        super(Modelsim, self).__init__(project, self.executables, user_paths)
        self.vmap = os.path.join(self.path, 'vmap')
        self.vcom = os.path.join(self.path, 'vcom')
        self.vlog = os.path.join(self.path, 'vlog')
        self.vlib = os.path.join(self.path, 'vlib')
        self.vsim = os.path.join(self.path, 'vsim')

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
        # Add any custom arguments from the project file
        arguments = self.project.get_tool_arguments(self.name, 'simulate')
        arguments = shlex.split(['', arguments][arguments is not None])
        arguments += args
        # Add any includes
        for libname, path in includes.items():
            arguments += ['-L', libname]
        # Add project libraries
        for libname in self.project.get_libraries():
            arguments += ['-L', libname]
        # Map any generics
        for name, binding in generics.items():
            arguments += ['-G{0}={1}'.format(name, binding)]
        # Enable or disable the GUI
        arguments += [['-c'], ['-i']][gui]
        # Apply any DO commands
        if duration is not None:
            if duration <= 0:
                duration = '-all'
            else:
                duration = utils.seconds_to_timestring(duration)
            do = 'set NumericStdNoWarnings 1\n' + 'run ' + duration + ';quit'
            arguments += ['-do', '{0}'.format(do)]
        # Finish processing arguments and invoke vsim
        # arguments += ['-L ' + library for library in includes.keys()]
        arguments += ['{0}.{1}'.format(library, entity)]
        ret, stdout, stderr = Modelsim._call(
            self.vsim,
            arguments,
            cwd=self.project.get_simulation_directory(),
            quiet=False
        )
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
        args += [file_object.path]
        if file_object.fileType == FileType.VHDL:
            Modelsim._call(
                self.vcom,
                args,
                cwd=self.project.get_simulation_directory()
            )
        elif file_object.fileType == FileType.Verilog:
            Modelsim._call(
                self.vlog,
                args,
                cwd=self.project.get_simulation_directory()
            )
        elif file_object.fileType == FileType.SystemVerilog:
            Modelsim._call(
                self.vlog,
                args,
                cwd=self.project.get_simulation_directory()
            )
        else:
            log.warning(
                'Simulator ignoring file with unsupported extension: ' +
                file_object.path
            )

    def set_working_library(self, library, cwd=None):
        Modelsim._call(
            self.vmap,
            ['work', library],
            cwd=self.project.get_simulation_directory()
        )

    def set_library_path(self, library, path, cwd=None):
        Modelsim._call(
            self.vmap,
            [library, path],
            cwd=self.project.get_simulation_directory()
        )

    def add_library(self, library):
        Modelsim._call(
            self.vlib,
            [library],
            cwd=self.project.get_simulation_directory()
        )
        Modelsim._call(
            self.vmap,
            [library, library],
            cwd=self.project.get_simulation_directory()
        )
