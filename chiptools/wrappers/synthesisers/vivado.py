import os
import logging
import datetime
import sys
import traceback
import tempfile

from chiptools.common.filetypes import FileType
from chiptools.wrappers import synthesiser

log = logging.getLogger(__name__)


class Vivado(synthesiser.Synthesiser):
    name = 'vivado'

    if sys.platform == 'win32':
        vivado_name = 'vivado.bat'
    else:
        vivado_name = 'vivado'
    executables = [vivado_name]

    def __init__(self, project, user_paths):
        """
        Initialise a Quartus Synthesiser instance
        """
        super(Vivado, self).__init__(project, self.executables, user_paths)
        self.vivado = os.path.join(self.path, self.vivado_name)
        self.project_path = None

    @synthesiser.throws_synthesis_exception
    def synthesise(self, library, entity):
        super(Vivado, self).synthesise(library, entity)
        # Make a temporary working directory for the synth tool
        start_time = datetime.datetime.now()
        with tempfile.TemporaryDirectory(
            dir=self.project.get_synthesis_directory()
        ) as working_directory:
            log.info(
                'Created temporary synthesis directory: ' + working_directory
            )
            # Get project configuration
            part = self.project.get_fpga_part()
            generics = self.project.get_generics()
            synthesis_name = entity + '_synth_' + start_time.strftime(
                '%d%m%y_%H%M%S'
            )
            archive_name = synthesis_name + '.tar'
            synthesis_dir = os.path.join(working_directory, synthesis_name)
            os.makedirs(synthesis_dir)
            self.project_path = os.path.join(synthesis_dir, entity + '.tcl')
            if os.path.exists(self.project_path):
                os.remove(self.project_path)

            ###################################################################
            # Generate a Vivado TCL script from the source tree:
            # This process is based on the example script provided in ug975
            # Vivado quick reference guide.
            ###################################################################
            # Step 1: Add source files (HDL, UCF, NGC, XCI)
            self.add_sources()
            self.add_constraints()
            # Step 2: Run synthesis, report utilisation and timing estimates,
            # write checkpoint.
            self.synth_design(
                synthesis_name,
                part,
                entity,
                generics,
                *self.project.get_tool_arguments(self.name, 'synthesis')
            )
            self.report_timing(synthesis_name + '_post_synth_timing.rpt')
            self.write_checkpoint(synthesis_name + '_post_synth.dcp')
            self.report_utilization(synthesis_name + '_post_synth_util.rpt')
            # Step 3: Run placement and logic optimisation, report utilisation
            # and timing estimates:
            self.write_tcl('opt_design')
            self.write_tcl('power_opt_design')
            self.write_tcl('place_design')
            self.write_tcl('phys_opt_design -retime')
            self.write_checkpoint(synthesis_name + '_post_place.dcp')
            self.report_clock_utilization(synthesis_name + '_clock_util.rpt')
            self.report_utilization(synthesis_name + '_post_place_util.rpt')
            self.report_timing(synthesis_name + '_post_place_timing.rpt')
            # Step 4: Run router, report actual utilisation and timing, write
            # checkpoint, run DRCs.
            self.write_tcl('route_design')
            self.write_checkpoint(synthesis_name + '_post_route.dcp')
            self.report_timing_summary(
                synthesis_name + '_post_route_timing.rpt'
            )
            self.report_utilization(synthesis_name + '_post_route_util.rpt')
            self.write_tcl(
                'report_power -file {0}'.format(
                    synthesis_name + '_post_route_power.rpt'
                )
            )
            self.report_drc(synthesis_name + '_post_route_drc.rpt')
            # Step 5: Write bitstream
            self.write_bitstream(synthesis_name + '.bit')
            self.write_tcl('quit')
            # Run the Vivado flow
            try:
                Vivado._call(
                    self.vivado,
                    [
                        '-nojournal',
                        '-mode', 'tcl',
                        '-source', self.project_path,
                    ],
                    cwd=synthesis_dir,
                    quiet=False,
                )
            except:
                # Archive the outputs
                log.error(
                    'Synthesis error, storing output in error directory...'
                )
                self.storeOutputs(working_directory, 'ERROR_' + archive_name)
                raise
            log.info(
                'Build successful, checking reports for unacceptable ' +
                'messages...'
            )
            try:
                #  Check the report
                reporter_fn = self.project.get_reporter()
                if reporter_fn is not None:
                    reporter_fn(synthesis_dir)
            except:
                log.error(
                    'The post-synthesis reporter script caused an error:\n' +
                    traceback.format_exc()
                )
            # Archive the outputs
            log.info('Synthesis completed, saving output to archive...')
            self.storeOutputs(working_directory, archive_name)
            log.info('...done')

    def report_clock_utilization(self, path):
        self.write_tcl('report_clock_utilization -file {0}'.format(path))

    def report_timing(self, path):
        self.write_tcl(
            'report_timing -sort_by group -max_paths 5 ' +
            '-path_type summary -file {0}'.format(path)
        )

    def report_timing_summary(self, path):
        self.write_tcl('report_timing_summary -file {0}'.format(path))

    def write_checkpoint(self, path):
        self.write_tcl('write_checkpoint -force {0}'.format(path))

    def report_utilization(self, path):
        self.write_tcl('report_utilization -file {0}'.format(path))

    def write_bitstream(self, path):
        self.write_tcl('write_bitstream -file {0}'.format(path))

    def report_drc(self, path):
        self.write_tcl('report_drc -file {0}'.format(path))

    def synth_design(self, name, part, entity, generics, *args):
        self.write_tcl(
            (
                'synth_design -name %(name)s -part %(part)s -top %(top)s ' +
                '%(generics)s' +
                '%(additional_args)s'
            ) % dict(
                name=name,
                part=part,
                entity=entity,
                top=entity,
                generics=''.join(
                    '-generic {0}={1} '.format(
                        k,
                        v
                    ) for k, v in generics.items()
                ),
                additional_args=''.join(a + ' ' for a in args)
            )
        )

    def add_sources(self):
        file_set = self.project.get_synthesis_fileset()
        for libName, fileList in file_set.items():
            for file_object in fileList:
                path = file_object.path.replace('\\', '/')
                # We could leave it to the synthesis tool to report missing
                # files, but handling them here means we can abort the process
                # early and notify the user.
                if os.path.isfile(file_object.path):
                    if file_object.fileType == FileType.VHDL:
                        self.write_tcl(
                            'read_vhdl -library {0} {1}'.format(
                                file_object.library, path
                            )
                        )
                    elif file_object.fileType == FileType.Verilog:
                        self.write_tcl(
                            'read_verilog -library {0} {1}'.format(
                                file_object.library, path
                            )
                        )
                    elif file_object.fileType == FileType.SystemVerilog:
                        self.write_tcl(
                            'read_verilog -library {0} {1}'.format(
                                file_object.library, path
                            )
                        )
                    elif file_object.fileType == FileType.NGCNetlist:
                        self.write_tcl(
                            'read_edif {0}'.format(path)
                        )
                    elif file_object.filetype == FileType.VivadoIp:
                        self.write_tcl(
                            'read_ip {0}'.format(path)
                        )
                    else:
                        log.warning(
                            'Ignoring file of unknown type: {0}'.format(path)
                        )
                else:
                    raise FileNotFoundError(path)

    def add_constraints(self):
        constraints = self.project.get_constraints()
        files_processed = []
        for file_object in constraints:
            path = file_object.path.replace('\\', '/')
            if path not in files_processed:
                if file_object.flow == 'vivado' or file_object.flow is None:
                    if file_object.fileType == FileType.VivadoXDC:
                        self.write_tcl('read_xdc {0}'.format(path))
                        log.info('Added constraints file: ' + path)
                    else:
                        log.warning(
                            'Ignoring constraints file of unknown type: ' +
                            path
                        )
            files_processed.append(path)

    def write_tcl(self, command):
        """
        Append the given TCL command to the project TCL script. The command
        will be wrapped in a try: catch block so that Vivado can exit
        gracefully in the event of an error.
        """
        with open(self.project_path, 'a') as f:
            string = (
                'if { [catch {%(command)s} result] } {\n' +
                '   puts stderr \"Command failed: $result\"\n' +
                '   exit 1\n' +
                '}\n'
            ) % dict(command=command)
            f.write(string)
