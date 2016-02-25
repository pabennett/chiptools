import os
import logging
import datetime
import shutil
import traceback
import re
import shlex

from chiptools.common.filetypes import FileType
from chiptools.common import exceptions
from chiptools.common.exceptions import FileNotFoundError
from chiptools.wrappers import synthesiser

log = logging.getLogger(__name__)

# Options file to be used by XFLOW
XST_MIXED_OPT = '''
FLOWTYPE = FPGA_SYNTHESIS;
Program xst
-ifn <design>_xst.scr;       # input XST script file
-ofn <design>_xst.log;       # output XST log file
-intstyle xflow;             # Message Reporting Style: ise, xflow, or silent
ParamFile: <design>_xst.scr
"run";
"-ifn <synthdesign>";        # Input/Project File Name
"-ifmt mixed";               # Input Format
"-ofn <design>";             # Output File Name
"-ofmt ngc";                 # Output File Format
"-top <design>";             # Top Design Name
"-generics %(generics)s";
"-p <partname>";             # Target Device
End ParamFile
End Program xst
'''


class Ise(synthesiser.Synthesiser):
    """
    A ISE Synthesiser instance can be used to synthesise the files in the
    given Project using the XFLOW utility or individual Xst, Map, Par,
    Ngdbuild, Bitgen and Promgen tools provided in a base Xilinx ISE
    installation. The ISE synthesis flow can be set to either *'manual'* flow
    where the individual ISE binaries are called in sequence or *'xflow'*
    where the XFLOW utility is called (effectively the same thing).
    To use the ISE class it must be instanced with a Project and Options
    object passed as arguments, the *'synthesise'* method may then be called
    to initiate the synthesis flow.
    In addition to running the synthesis flow, the ISE Synthesiser instance
    also uses a Reporter instance to filter the synthesis log messages for
    important information relating to the build.

    When complete, the output files from synthesis will be stored in an
    archive bearing the name of the entity that was synthesised and a unique
    timestamp.

    """
    name = 'ise'

    executables = [
        'xwebtalk',
        'promgen',
        'xst',
        'map',
        'par',
        'ngdbuild',
        'bitgen',
        'xflow'
    ]

    def __init__(self, project, user_paths, mode='manual'):
        """
        Create a new ISE Synthesiser instance using the supplied Project and
        Options objects with the optionsal string parameter *mode* set to
        either 'manual' or 'xflow' to determine which ISE tool flow to use
        during synthesis.
        """
        super(Ise, self).__init__(project, self.executables, user_paths)
        self.mode = mode
        self.xwebtalk = os.path.join(self.path, 'xwebtalk')
        self.promgen = os.path.join(self.path, 'promgen')
        self.xst = os.path.join(self.path, 'xst')
        self.map = os.path.join(self.path, 'map')
        self.par = os.path.join(self.path, 'par')
        self.ngdbuild = os.path.join(self.path, 'ngdbuild')
        self.bitgen = os.path.join(self.path, 'bitgen')
        self.xflow = os.path.join(self.path, 'xflow')

    @synthesiser.throws_synthesis_exception
    def makeProject(self, projectFilePath, fileFormat='mixed'):
        """
        Generate a Xilinx ISE project file listing source files with their
        filetypes and libraries.
        ISE requires a project file to be written using the following format:

        .. code-block: xml

            <hdl_language> <compilation_library> <source_file>

        Where *hdl_language* specifies whether the designated HDL source file
        is written in VHDL or Verilog, *compilation_library* specifies the
        library where the HDL is compiled and *source_file* specifies the path
        to the source file.
        This method generates an appropriate file from the project data that
        has been loaded into the ISE Synthesiser instance.
        """
        log.info('Creating project file for ISE...')
        projectFileString = ''
        fileSet = self.project.get_synthesis_fileset()
        for libName, fileList in fileSet.items():
            for fileObject in fileList:
                # We could leave it to the synthesis tool to report missing
                # files, but handling them here means we can abort the process
                # early and notify the user.
                if os.path.isfile(fileObject.path):
                    if fileObject.fileType == FileType.VHDL:
                        if fileFormat == 'mixed':
                            projectFileString += 'vhdl '
                    elif fileObject.fileType == FileType.Verilog:
                        if fileFormat == 'mixed':
                            projectFileString += 'verilog '
                    elif fileObject.fileType == FileType.SystemVerilog:
                        if fileFormat == 'mixed':
                            projectFileString += 'verilog '
                    elif fileObject.fileType == FileType.NGCNetlist:
                        base = os.path.dirname(projectFilePath)
                        newPath = os.path.join(
                            base,
                            os.path.basename(fileObject.path)
                        )
                        if os.path.exists(newPath):
                            log.warning(
                                'File already exists: ' + str(newPath) +
                                ' and will be overwritten by: ' +
                                str(fileObject.path)
                            )
                        # Copy the NGC into the local directory
                        shutil.copyfile(fileObject.path, newPath)
                        continue
                    else:
                        raise exceptions.SynthesisException(
                            'Unknown file type for synthesis tool: ' +
                            fileObject.fileType
                        )
                    projectFileString += fileObject.library + ' '
                    projectFileString += fileObject.path + '\n'
                else:
                    raise FileNotFoundError(fileObject.path)

        # Write out the synthesis project file
        log.debug('Writing: ' + projectFilePath)
        with open(projectFilePath, 'w') as f:
            f.write(projectFileString)
        log.info("...done")

    @synthesiser.throws_synthesis_exception
    def synthesise(self, library, entity, fpga_part=None):
        """
        Synthesise the target entity in the given library for the currently
        loaded project.
        The following steps are performed during synthesis:
        * Create synthesis directories
        * Generate an ISE project file
        * Generate an ISE UCF constraints file
        * Invoke XFLOW or the flow tools individually with appropriate command
          line arguments * Generate reports
        * Archive the outputs of the synthesis flow
        """
        super(Ise, self).synthesise(library, entity, fpga_part)
        # make a temporary working directory for the synth tool
        import tempfile

        startTime = datetime.datetime.now()

        log.info(
            'Turning Xilinx WebTalk off as it may prevent the removal of ' +
            'temporary directories'
        )
        try:
            self.ise_webtalk_off()
        except:
            log.debug(traceback.format_exc())
            log.warning(
                'Could not disable WebTalk, ' +
                'you may encounter PermissionErrors ' +
                'during temporary directory removal'
            )
        with tempfile.TemporaryDirectory(
            dir=self.project.get_synthesis_directory()
        ) as workingDirectory:
            log.info(
                'Created temporary synthesis directory: ' + workingDirectory
            )
            synthName = (
                entity +
                '_synth_' +
                startTime.strftime('%d%m%y_%H%M%S')
            )
            archiveName = synthName + '.tar'
            synthesisDirectory = os.path.join(workingDirectory, synthName)
            os.makedirs(synthesisDirectory)
            if fpga_part is None:
                fpga_part = self.project.get_fpga_part()
            generics = self.project.get_generics().items()
            generics = (
                '{' +
                ' '.join(k + '=' + str(v) for k, v in generics) +
                '}'
            )
            projectFilePath = os.path.join(synthesisDirectory, entity + '.prj')
            exportDirectory = os.path.join(synthesisDirectory, 'output')
            reportDirectory = os.path.join(synthesisDirectory, 'reports')
            # Add user constraints and other source files
            self.addConstraints(entity, synthesisDirectory)
            self.makeProject(projectFilePath)
            if self.mode == 'xflow':
                try:
                    # Run the flow
                    self.ise_xflow(
                        projectFilePath,
                        fpga_part,
                        entity,
                        generics,
                        synthesisDirectory,
                        reportDirectory,
                        exportDirectory
                    )
                    self.generate_programming_files(entity, synthesisDirectory)
                except:
                    # Archive the outputs
                    log.error(
                        'Synthesis error, storing output in error directory...'
                    )
                    self.storeOutputs(workingDirectory, 'ERROR_' + archiveName)
                    raise
            elif self.mode == 'manual':
                try:
                    # Run the flow
                    self.ise_manual_flow(
                        projectFilePath,
                        fpga_part,
                        entity,
                        generics,
                        synthesisDirectory,
                        reportDirectory,
                        exportDirectory
                    )
                    self.generate_programming_files(entity, synthesisDirectory)
                except:
                    # Archive the outputs
                    log.error(
                        'Synthesis error, storing output in error directory...'
                    )
                    self.storeOutputs(workingDirectory, 'ERROR_' + archiveName)
                    raise
            else:
                raise exceptions.SynthesisException(
                    'Invalid flow type: ' + self.mode
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
    def generate_programming_files(self, entity, working_directory):
        """
        Generate programming files using the output bitfile from the synthesis
        run. An MCS file is always generated, but additional files can be
        generated by adding 'args_ise_promgen_<format>' configuration items
        with the tool arguments to apply when calling promgen for that output
        format.
        """
        # Get all ISE tool arguments for the PROMGEN stage:
        arg_keys = self.project.get_all_tool_argument_keys(self.name)

        def filter_args_fn(x):
            return x.startswith('args_{0}_promgen'.format(self.name))

        arg_keys = list(filter(filter_args_fn, arg_keys))
        for key in arg_keys:
            mode = key.split('_')[-1]
            if len(mode) > 0 and mode != 'promgen':
                log.info(
                    'Generating PROM file using user defined '
                    'arguments from configuration item: {0}'.format(key)
                )
                # Run promgen using the mode recovered from the config key
                self.ise_make_prom_file(
                    entity + '.bit',
                    entity + '.' + mode,
                    working_directory,
                    mode=mode
                )

        # Always ensure that an MCS file is created.
        if 'args_{0}_promgen_mcs'.format(self.name) not in arg_keys:
            self.ise_make_prom_file(
                entity + '.bit',
                entity + '.mcs',
                working_directory,
                mode='mcs'
            )

    @synthesiser.throws_synthesis_exception
    def ise_webtalk_off(self):
        """
        Call the *xwebtalk* binary with the *-user off* switch to disable
        WebTalk
        """
        Ise._call(
            self.xwebtalk,
            ['-user', 'off'],
            cwd=self.project.get_synthesis_directory(),
            quiet=False,
        )

    @synthesiser.throws_synthesis_exception
    def ise_promgen(self, fin, fout, working_directory, args=None):
        """
        Call the *promgen* binary, which accepts the following arguments:

        Usage: promgen [-b] [-spi] [-p mcs|exo|tek|hex|bin|ieee1532|ufp] [-o
        <outfile> {<outfile>}] [-s <size> {<size>}] [-x <xilinx_prom>
        {<xilinx_prom>}] [-c [<hexbyte>]] [-l] [-w] [-bpi_dc serial|parallel]
        [-intstyle ise|xflow|silent] [-t <templatefile[.pft]>] [-z
        [<version:0,3>]] [-i <version:0,3>] [-data_width 8|16|32]
        [-config_mode selectmap8|selectmap16|selectmap32] {-ver <version:0,3>
        <file> {<file>}} {-u <hexaddr> <file> {<file>}} {-d <hexaddr> <file>
        {<file>}} {-n <file> {<file>}} {-bd <file> [start <hexaddr>] [tag
        <tagname> {<tagname>}]} {-bm <file>} {-data_file up|down <hexaddr>
        <file> {<file>}} [-r <promfile>]

        * *fin* is passed to the *<file>* input parameter
        * *fout* is passed to the *-o* input parameter
        * *workingDirectory* is the working directory where the tool is invoked
        """
        # Get additional tool arguments for this flow stage if this method was
        # not called with existing arguments.
        if args is None:
            args = self.project.get_tool_arguments(self.name, 'promgen')
        # Allow the user to override PROM loading of bitfiles
        if not any([k in args for k in ['-r', '-u', '-d', '-ver']]):
            # Default to upward loading from address 0
            args += ['-u', '0', fin]
        else:
            # User provided custom PROM loading argument which we will honour
            pass
        # Check that the user has supplied a mode
        if not any([k in args for k in ['-p', 'mcs']]):
            # Default to MCS if the user did not specify a mode
            args += ['-p', 'mcs']
        # Always overwrite existing files
        if '-w' not in args:
            args += ['-w']
        # Allow the user to override the output file name
        if '-o' not in args:
            args += ['-o', fout]
        Ise._call(self.promgen, args, cwd=working_directory, quiet=False)

    @synthesiser.throws_synthesis_exception
    def ise_make_prom_file(self, fin, fout, working_directory, mode='mcs'):
        """
        Generate a programming file using the promgen tool, the user can
        supply arguments to this flow stage with args_ise_promgen_<mode>.
        """
        # Get additional tool arguments for this flow stage
        args = self.project.get_tool_arguments(
            self.name, 'promgen_{0}'.format(mode)
        )
        args = shlex.split(['', args][args is not None])
        if not any([k in args for k in ['-p', mode]]):
            args += ['-p', mode]
        self.ise_promgen(fin, fout, working_directory, args)

    @synthesiser.throws_synthesis_exception
    def ise_xst(self, part, entity, generics, working_directory):
        """
        Generate an XST settings file and call the *XST* binary
        """
        # Get additional tool arguments for this flow stage
        xstargs = self.project.get_tool_arguments(self.name, 'xst')
        # Format the args as XST expects
        xstargs = re.sub(' -', '\n-', xstargs)
        # Write XST file
        xst_scr = (
            'run\n' +
            '-ifn %(entity)s.prj\n' +
            '-ofn %(entity)s.ngc\n' +
            '-ofmt NGC\n' +
            '-p %(part)s\n' +
            '-top %(entity)s\n' +
            '-generics %(synthesis_generics)s\n' +
            xstargs + '\n'
        )
        with open(os.path.join(working_directory, entity + '.xst'), 'w') as f:
            f.write(
                xst_scr % dict(
                    entity=entity,
                    part=part,
                    synthesis_generics=generics,
                )
            )

        args = ['-ifn', entity + '.xst']
        args += ['-ofn', entity + '.log']
        Ise._call(
            self.xst,
            args,
            cwd=working_directory,
            quiet=False
        )

    @synthesiser.throws_synthesis_exception
    def ise_map(self, part, entity, working_directory):
        """
        Call the *MAP* binary, which accepts the following arguments:

        map [-h] [-p partname] (infile[.ngd]) [-o (outfile[.ncd])]
        http://www.xilinx.com/support/documentation/sw_manuals/xilinx14_1/devref.pdf

        * *part* is passed to the *-p* input parameter
        * *entity* is used to generate output file names
        * *workingDirectory* is the working directory where the tool is invoked
        """
        # Get additional tool arguments for this flow stage
        args = self.project.get_tool_arguments(self.name, 'map')
        args = shlex.split(['', args][args is not None])
        # Part name
        args += ['-p', part]
        # Output file
        args += ['-o', entity + '_map.ncd']
        args += [entity + '.ngd']
        # PCF Output name
        args += [entity + '.pcf']

        Ise._call(
            self.map,
            args,
            cwd=working_directory,
            quiet=False
        )

    @synthesiser.throws_synthesis_exception
    def ise_par(self, entity, working_directory):
        """
        Call the *PAR* binary, which accepts the following arguments:

        par [-ol std|high] [-pl std|high] [-rl std|high] [-xe n|c] [-mt
        on|off|1| 2|3|4] [-t <costtable:1,100>] [-p] [-k]
        [-r] [-w] [-smartguide <guidefile[.ncd]>] [-x] [-nopad] [-power
        on|off|xe] [-act ivityfile <activityfile[.vcd|.saif]>]
        [-ntd] [-intstyle ise|xflow|silent|pa] [-ise <projectrepositoryfile>]
        [-filter < filter_file[.filter]>] <infile[.ncd]>

        <outfile> [<constraintsfile[.pcf]>]

        * *entity* is used to generate output file names
        * *workingDirectory* is the working directory where the tool is invoked
        """
        # Get additional tool arguments for this flow stage
        args = self.project.get_tool_arguments(self.name, 'par')
        args = shlex.split(['', args][args is not None])
        # Infile
        args += [entity + '_map.ncd']
        # Output file
        args += [entity + '.ncd']
        # Physical Constraints File (auto generated)
        args += [entity + '.pcf']

        Ise._call(
            self.par,
            args,
            cwd=working_directory,
            quiet=False
        )

    @synthesiser.throws_synthesis_exception
    def ise_ngdbuild(self, part, entity, working_directory):
        """
        Call the *NGDBUILD* binary, which accepts the following arguments:

        Usage: ngdbuild [-p <partname>] {-sd <source_dir>} {-l <library>} [-ur
        <rules_file[.urf]>] [-dd <output_dir>] [-r] [-a] [-u] [-nt
        timestamp|on|off] [-uc <ucf_file[.ucf]>] [-aul] [-aut] [-bm
        <bmm_file[.bmm]>] [-i] [-intstyle ise|xflow|silent] [-quiet]
        [-verbose] [-insert_keep_hierarchy] [-filter <filter_file[.filter]>]
        <design_name> [<ngd_file[.ngd]>]

        * *entity* is used to generate input and output file names
        * *-sd* is set to *workingDirectory*
        * *-p* is set to *part*
        * *workingDirectory* is the working directory where the tool is invoked
        """
        # Get additional tool arguments for this flow stage
        args = self.project.get_tool_arguments(self.name, 'ngdbuild')
        args = shlex.split(['', args][args is not None])
        # Constraints
        args += ['-uc', entity + '.ucf']
        # Search directory
        args += ['-sd', working_directory]
        # Part name
        args += ['-p', part]
        # Input design file
        args += [entity + '.ngc']
        # Output NGD file
        args += [entity + '.ngd']

        Ise._call(
            self.ngdbuild,
            args,
            cwd=working_directory,
            quiet=False
        )

    @synthesiser.throws_synthesis_exception
    def ise_bitgen(self, part, entity, working_directory):
        """
        Call the *BITGEN* binary, which accepts the following arguments:

        Usage: bitgen [-d] [-j] [-b] [-w] [-l] [-m] [-t] [-n] [-u] [-a] [-r
        <bitFile>] [-intstyle ise|xflow|silent|pa] [-ise
        <projectrepositoryfile>] {-bd <BRAM_data_file> [tag <tagname>]} {-g
        <setting_value>} [-filter <filter_file[.filter]>] <infile[.ncd]>
        [<outfile>] [<pcffile[.pcf]>]

        * *entity* is used to generate input and output file names
        * *workingDirectory* is the working directory where the tool is invoked
        """
        # Get additional tool arguments for this flow stage
        args = self.project.get_tool_arguments(self.name, 'bitgen')
        args = shlex.split(['', args][args is not None])
        # Input file
        args += [entity + '.ncd']
        # Output file
        args += [entity + '.bit']

        Ise._call(
            self.bitgen,
            args,
            cwd=working_directory,
            quiet=False
        )

    @synthesiser.throws_synthesis_exception
    def ise_xflow(
        self,
        projectFilePath,
        part,
        entity,
        generics,
        workingDirectory,
        reportDirectory,
        exportDirectory
    ):
        """

        Call the *XFLOW* binary, which accepts the following arguments:

        xflow [-p partname] [flow type] [options file[.opt]] [xflow options]
        design_name

        XFLOW Flow Types:
            Create a bitstream for FPGA device configuration using a routed
            design.
            -config option_file

            Create a file that can be used for formal verification of an FPGA
            design.
            -ecn option_file

            Incorporate logic from the design into physical macrocell locations
            in a CPLD
            -fit option_file

            Generate a file that can be used for functional simulation of an
            FPGA or CPLD design
            -fsim option_file

            Implement the design and output a routed NCD file
            -implement option_file[fast_runtime.opt, balanced.opt,
            high_effort.opt]

            Create a file that can be used to perform static timing analysis
            of an FPGA design
            -sta option_file

            Synthesise the design for implementation in an FPGA, for fitting
            in a CPLD or for
            compiling for functional simulation.
            -syth option_file[xst_vhdl.opt/xst_verilog.opt/xst_mixed.opt]

            Generate a file that can be used for timing simulation of an FPGA
            or CPLD design.
            -tsim option_file
        """
        # Additional arguments are not supported for XFLOW, the XST flow should
        # be used if more control of the stages is required.
        if len(self.project.get_tool_arguments(self.name, 'xflow')) > 0:
            log.warning(
                'The ISE wrapper does not allow additional arguments' +
                ' to be passed to XFLOW. Use the XST flow if fine control' +
                ' of the synthesis stages is required.'
            )
        # Write the auto-generated options file
        with open(os.path.join(workingDirectory, 'xst_custom.opt'), 'w') as f:
            f.write(XST_MIXED_OPT % dict(generics=generics))
        # Call the flow
        args = ['-p', part]
        args += ['-synth', 'xst_custom.opt']
        args += ['-implement', 'balanced.opt']
        args += ['-config', 'bitgen.opt']
        args += ['-wd', workingDirectory]
        args += ['-ed', exportDirectory]
        args += ['-rd', reportDirectory]
        args += [projectFilePath]

        Ise._call(
            self.xflow,
            args,
            cwd=workingDirectory,
            quiet=False
        )

    @synthesiser.throws_synthesis_exception
    def ise_manual_flow(
        self,
        projectFilePath,
        part,
        entity,
        generics,
        workingDirectory,
        reportDirectory,
        exportDirectory
    ):
        """
        Execute the manual ISE tool flow in the following order:
        #. XST
        #. NGDBUILD
        #. MAP
        #. PAR
        #. BITGEN

        Refer to the individual documentation for these tools for more
        information.
        """
        # XST > NGDBUILD > MAP > PAR > BitGen > PromGen
        self.ise_xst(part, entity, generics, workingDirectory)
        self.ise_ngdbuild(part, entity, workingDirectory)
        self.ise_map(part, entity, workingDirectory)
        self.ise_par(entity, workingDirectory)
        self.ise_bitgen(part, entity, workingDirectory)

    @synthesiser.throws_synthesis_exception
    def addConstraints(self, entity, synthesisDirectory):
        """
        Load the user constraints file path from the Project instance and
        generate a UCF file in the supplied *synthesisDirectory* directory
        where the synthesis tools are invoked.
        """
        # Add user constraints and other source files
        constraintsFiles = self.project.get_constraints()
        constraintsData = ''
        filesProcessed = []
        for fileObject in constraintsFiles:
            # Avoid duplicates
            if fileObject.path not in filesProcessed:
                if fileObject.flow == 'ise' or fileObject.flow is None:
                    if fileObject.fileType == FileType.UCF:
                        # Copy the UCF data into the string var
                        with open(fileObject.path, 'r') as constraintsFile:
                            constraintsData += constraintsFile.read()
                            log.info(
                                'Added constraints file: ' + fileObject.path
                            )
                filesProcessed.append(fileObject.path)
        # Write the string var to a single file if we have data
        if len(constraintsData) != 0:
            newPath = os.path.join(synthesisDirectory, entity + '.ucf')
            with open(newPath, 'w') as outFile:
                outFile.write(constraintsData)
            log.info('Wrote: ' + newPath)
