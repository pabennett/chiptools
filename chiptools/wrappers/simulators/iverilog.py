import logging
import os
import shlex
import time

from chiptools.wrappers.simulator import Simulator
from chiptools.common.filetypes import FileType
from chiptools.common import utils

log = logging.getLogger(__name__)


class Iverilog(Simulator):

    name = 'iverilog'
    executables = ['iverilog', 'vvp']

    def __init__(self, project, user_paths):
        super(Iverilog, self).__init__(project, self.executables, user_paths)
        self.iverilog = os.path.join(self.path, 'iverilog')
        self.vvp = os.path.join(self.path, 'vvp')
        self.filetypes = [
            FileType.Verilog,
            FileType.SystemVerilog
        ]
        self.files = []
    def compile_project(self, includes={}):
        """
        This method stages files for compilation as we cannot perform
        compilation until additional runtime information such as generic
        assignments and the desired top-level entity are known. Incremental
        compilation is not supported by Icarus so the cache and library
        tracking are not used at all.
        """
        self.files = []
        for file_object in self.project.get_files():
            if os.path.isfile(file_object.path):
                if file_object.fileType in self.filetypes:
                    self.files.append(file_object)
                else:
                    log.warning(
                        'Icarus ignoring file with unsupported ' +
                        'extension: ' +
                        file_object.path
                    )
            else:
                raise FileNotFoundError(
                    'File could not be found: ' +
                    '{0}, operation aborted.'.format(
                        file_object.path
                    )
                )
        log.info(
            (
                'Deferring compilation of {0} file(s) until simulation '
                'is called.'
            ).format(
                len(self.files)
            )
        )

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
        Compile and simulate the design.
        """
        start_time = time.time()
        args = []
        # Specify the output name
        args += [
            '-o',
            'icarus_sim'
        ]
        # Get the files
        for file_object in self.files:
            args.append(file_object.path)
            # TODO: Add additional custom compile args for each file.
        # Define the top level
        args += [
            '-s',
            entity
        ]
        # Define top level parameters
        # TODO: Icarus does not seem to support parameter/generic overrides
        # in the latest version so `define overrides need to be used instead.
        if len(generics.keys()) > 0:
            log.warning(
                'Icarus parameter overrides via the -P flag are not ' +
                'supported. Parameter overrides will be translated into ' +
                '`define overrides via the -D command line switch.'
            )
        for k, v in generics.items():
            args += [
                '-D',
                '{0}={1}'.format(k, v) 
            ]
        # Add custom library paths (the library name is ignored)
        for k, v in includes.items():
            args += [
                '-y' + v
            ]
        # Call the Iverilog compilation stage
        Iverilog._call(
            self.iverilog,
            args,
            cwd=self.project.get_simulation_directory()
        )
        log.info("...done")
        log.info(
            str(len(self.files)) +
            ' file(s) processed in ' +
            utils.time_delta_string(start_time, time.time())
        )
        ######################################################################
        # Invoke simulation
        # $ vvp [flags] foo.vvp [extended args]
        # Extended Args:
        #   -none/-vcd-none/-vcd-off/-fst-none
        #   -fst
        #   -lxt/lxt2
        #   -sdf-warn
        #   -sdf-info
        #   -sdf-verbose
        extended_args = [
            '-none', '-vcd-none', '-vcd-off', '-fst-none',
            '-fst', '-lxt', '-lxt2', '-sdf-warn', '-sdf-info',
            '-sdf-verbose'
        ]
        ######################################################################
        # Get user specified args
        args = self.project.get_tool_arguments(self.name, 'simulate')
        flags = list(filter(lambda x: x not in extended_args, args))
        extended = list(filter(lambda x: x in extended_args, args))
        args = flags
        # Target application
        args += ['icarus_sim']
        # Extended Args
        args += extended
        # Run the simulation
        ret, stdout, stderr = Iverilog._call(
            self.vvp,
            args,
            cwd=self.project.get_simulation_directory(),
            quiet=False
        )
        return ret, stdout, stderr

