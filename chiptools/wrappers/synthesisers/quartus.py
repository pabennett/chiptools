import os
import logging
import datetime
import shlex
import traceback

from chiptools.common import exceptions
from chiptools.common.filetypes import FileType
from chiptools.wrappers import synthesiser

log = logging.getLogger(__name__)


class Quartus(synthesiser.Synthesiser):
    """
    A Quartus Synthesiser instance can be used to synthesise the files in the
    given Project using the quartus_sh utility provided in a base Altera
    Quartus installation. The Quartus synthesis flow follows the following
    steps:
    * Create synthesis directories
    * Create a project TCL file listing FPGA part, source files and any
    constraints * Invoke quartus_sh
    * Archive the outputs

    In addition to running the quartus_sh synthesis flow, the Quartus
    Synthesiser instance also uses a Reporter instance to filter the synthesis
    log messages for important information relating to the build.

    When complete, the output files from synthesis will be stored in an
    archive bearing the name of the entity that was synthesised and a unique
    timestamp.

    """
    name = 'quartus'
    executables = ['quartus_sh']

    def __init__(self, project, user_paths):
        """
        Initialise a Quartus Synthesiser instance
        """
        super(Quartus, self).__init__(project, self.executables, user_paths)
        self.quartus_sh = os.path.join(self.path, 'quartus_sh')

    @synthesiser.throws_synthesis_exception
    def synthesise(self, library, entity, fpga_part=None):
        """
        Synthesise the target entity in the given library for the currently
        loaded project.
        The following steps are performed during synthesis:

        * Create synthesis directories
        * Create a project TCL file listing FPGA part, source files and any
        constraints * Invoke quartus_sh
        * Generate reports
        * Archive the outputs
        """
        super(Quartus, self).synthesise(library, entity, fpga_part)
        # make a temporary working directory for the synth tool
        import tempfile
        startTime = datetime.datetime.now()
        with tempfile.TemporaryDirectory(
            dir=self.project.get_synthesis_directory()
        ) as workingDirectory:
            log.info(
                'Created temporary synthesis directory: ' + workingDirectory
            )
            synthName = entity + '_synth_' + startTime.strftime(
                '%d%m%y_%H%M%S'
            )
            archiveName = synthName + '.tar'
            synthesisDirectory = os.path.join(workingDirectory, synthName)
            os.makedirs(synthesisDirectory)
            projectFilePath = os.path.join(synthesisDirectory, entity + '.tcl')
            if fpga_part is None:
                fpga_part = self.project.get_fpga_part()
            self.makeProject(
                projectFilePath,
                self.project.get_synthesis_fileset(),
                self.project.get_constraints(),
                fpga_part,
                self.project.get_generics(),
                synthesisDirectory,
                entity,
            )
            try:
                # Run the flow
                self.exec_quartus_sh(
                    os.path.basename(projectFilePath),
                    synthesisDirectory
                )
            except:
                # Archive the outputs
                log.error(
                    'Synthesis error, storing output in error directory...'
                )
                self.storeOutputs(workingDirectory, 'ERROR_' + archiveName)
                raise
            log.info(
                'Build successful, checking reports for unacceptable ' +
                'messages...'
            )
            #  Check the report
            reporter_fn = self.project.get_reporter()
            try:
                if reporter_fn is not None:
                    reporter_fn(synthesisDirectory)
            except:
                log.error(
                    'The post-synthesis reporter script caused an error:\n' +
                    traceback.format_exc()
                )
            # Archive the outputs
            log.info('Synthesis completed, saving output to archive...')
            self.storeOutputs(workingDirectory, archiveName)
            log.info('...done')

    @synthesiser.throws_synthesis_exception
    def makeProject(
        self,
        projectFilePath,
        files,
        constraints,
        part,
        generics,
        workingDirectory,
        entity
    ):
        """
        Generate a TCL file that is compatible with the quartus_sh API to
        allow the source files in the supplied *files* list to be built using
        the quartus_sh utility.
        The following items are inserted into the resulting TCL file:

        * Relevant TCL imports (::quartus::project, ::quartus::flow)
        * Entity
        * FPGA Part
        * Source Files
        * Synthesis Generics (for the top level entity)
        * Constraints (as a TCL script appended to the project TCL file)
        * TCL commands to execute synthesis flow

        The TCL file to be written will be stored at the given
        *projectFilePath* filepath.
        """
        log.info('Creating project file for Quartus...')
        # Import the quartus TCL project module
        projectFileString = 'package require ::quartus::project' + '\n'
        projectFileString += 'package require ::quartus::flow' + '\n'
        projectFileString += 'load_package report' + '\n'
        # Create the project
        projectFileString += self.tcl_project_new(entity)
        # Set the top level
        projectFileString += self.tcl_set_top_level_entity(entity)
        # Set the part
        projectFileString += self.tcl_set_part(part)
        # Add all the source files to the project
        for libName, fileList in files.items():
            for fileObject in fileList:
                projectFileString += self.tcl_add_file(fileObject)

        # Add the project generics
        for k, v in generics.items():
            projectFileString += self.tcl_set_generic(k, v)

        # Add user constraints and other source files
        sdcString = ''
        for fileObject in constraints:
            if fileObject.flow == 'quartus' or fileObject.flow is None:
                if fileObject.fileType == FileType.TCL:
                    with open(fileObject.path, 'r') as constraintsFile:
                        projectFileString += constraintsFile.read()
                        projectFileString += '\n'
                        log.info(
                            'Added supplementary TCL script: ' +
                            fileObject.path
                        )
                elif fileObject.fileType == FileType.SDC:
                    with open(fileObject.path, 'r') as constraintsFile:
                        sdcString += constraintsFile.read()
                        sdcString += '\n'
                        log.info(
                            'Added timing constraints script: ' +
                            fileObject.path
                        )
        if len(sdcString) > 0:
            sdcPath = os.path.join(workingDirectory, entity + '.sdc')
            with open(sdcPath, 'w') as f:
                log.info('Writing: ' + str(sdcPath))
                f.write(sdcString)

        # Commit the assignment
        projectFileString += 'export_assignments' + '\n'
        # Execute the flow
        projectFileString += 'execute_flow -compile' + '\n'
        # Close the project
        projectFileString += self.tcl_project_close()

        # Write out the synthesis project file
        log.debug('Writing: ' + projectFilePath)
        with open(projectFilePath, 'w') as f:
            f.write(projectFileString)
        log.info("...done")

    def tcl_set_part(self, part):
        """
        Return the Quartus API TCL command string:
        set_global_assignment -name DEVICE *<part>*
        """
        return 'set_global_assignment -name DEVICE ' + part + '\n'

    def tcl_set_top_level_entity(self, entity):
        """
        Return the Quartus API TCL command string:
        set_global_assignment -name TOP_LEVEL_ENTITY *<entity>*
        """
        return 'set_global_assignment -name TOP_LEVEL_ENTITY ' + entity + '\n'

    def tcl_set_generic(self, name, value):
        """
        Return the Quartus API TCL command string:
        set_parameter -name *<name>* *<value>*
        """
        return 'set_parameter -name ' + str(name) + ' ' + str(value) + '\n'

    @synthesiser.throws_synthesis_exception
    def tcl_add_file(self, fileObject):
        """
        Return the Quartus API TCL command string:
        set_global_assignment [VHDL_FILE/VERILOG_FILE] *<fileObject.path>*
        -library *<fileObject.library>*
        """
        # We could leave it to the synthesis tool to report missing files, but
        # handling them here means we can abort the process early and notify
        # the user.
        string = ''
        string += 'set_global_assignment -name '
        if os.path.isfile(fileObject.path):
            if fileObject.fileType == FileType.VHDL:
                string += 'VHDL_FILE '
            elif fileObject.fileType == FileType.Verilog:
                string += 'VERILOG_FILE '
            elif fileObject.fileType == FileType.SystemVerilog:
                string += 'VERILOG_FILE '
            else:
                raise exceptions.SynthesisException(
                    'Unknown file type for synthesis tool: ' +
                    fileObject.fileType
                )
            # Quartus will not allow backslashes, force forward slashes here.
            filePath = fileObject.path.replace('\\', '/')
            string += filePath + ' '
            string += '-library ' + fileObject.library + '\n'
            return string
        else:
            raise FileNotFoundError(fileObject.path)

    def tcl_project_close(self):
        """
        Return the Quartus API TCL command string:
        project_close [-dont_export_assignments]
        """
        return 'project_close' + '\n'

    def tcl_project_new(self, entity):
        """
        Return the Quartus API TCL command string:
        project_new [-family <family>] [-overwrite] [-part <part>] [-revision
        <revision_name>] <project_name>
        """
        return (
            'project_new -overwrite -revision ' +
            entity + ' ' + entity + 'proj' + '\n'
        )

    @synthesiser.throws_synthesis_exception
    def exec_quartus_sh(
        self,
        projectFilePath,
        workingDirectory,
    ):
        """

        Invoke quartus_sh using the TCL file pointed to by *projectFilePath*
        using the given *workingDirectory* as a working directory.

        quartus_sh uses the following command line arguments:

        ::

            quartus_sh
            -f=<argument file>
            -h
            -s
            -t=<script file>
            -v
            --64bit
            --archive
            --determine_smart_action
            --dse
            --dtw
            --flow
            --help[=<option|topic>]
            --lower_priority
            --prepare
            --qboard
            --qhelp
            --qinstall
            --qslave
            --relcon
            --restore
            --script=<script file>
            --set
            --shell
            --simlib_comp
            --tcl_eval=<tcl command>
            --version
        """
        # Get additional tool arguments for this flow stage
        args = self.project.get_tool_arguments(self.name, 'quartus_sh')
        args = shlex.split(['', args][args is not None])
        args += ['-t' + projectFilePath]

        Quartus._call(
            self.quartus_sh,
            args,
            cwd=workingDirectory,
            quiet=False
        )
