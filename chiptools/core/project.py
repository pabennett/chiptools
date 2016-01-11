import logging
import glob
import os
import traceback
import re
import unittest

from chiptools.common import exceptions
from chiptools.common import utils
from chiptools.common.filetypes import File
from chiptools.common.filetypes import Constraints
from chiptools.common.filetypes import ProjectAttributes
from chiptools.common.filetypes import UnitTestFile
from chiptools.core.preprocessor import Preprocessor
from chiptools.core import reporter
from chiptools.core.cache import FileCache
from chiptools.parsers import options
from chiptools.testing import testloader
from chiptools.testing.custom_runners import HTMLTestRunner
from chiptools.wrappers.wrapper import ToolWrapper

log = logging.getLogger(__name__)


class Project:
    def __init__(self):
        super(Project, self).__init__()
        self.initialise()

    def initialise(self):
        self.options = options.Options()
        self.tool_wrapper = ToolWrapper(
            self,
            self.options.get_user_tool_paths()
        )

        self.config = {}
        self.cache = FileCache('.chiptools')
        self.root = os.getcwd()
        self.generics = {}
        self.constraints = []
        self.file_list = []
        self.project_data = {}
        self.tests = []

    def set_cache_path(self, cache_path):
        # Update the FileCache to point at the new path
        self.cache = FileCache(cache_path)
        self.root = os.path.dirname(cache_path)

    def add_file(self, path, library='work', **attribs):
        """Add the given file to the project."""
        path = utils.relativePathToAbs(path, self.root)
        # Ensure library names are lower case
        library = library.lower()
        # Default synthesis to true
        file_object = File(
            path=path,
            library=library,
            **attribs
        )
        if library not in self.project_data:
            self.project_data[library] = []
        if file_object not in self.project_data[library]:
            # Both a dictionary and list of files are maintained so that
            # compilation order can be preserved
            self.project_data[library].append(file_object)
            self.file_list.append(file_object)

    def add_files(self, root, library='work', pattern='*.*'):
        """Add all files in the given directory to the project. The optional
        pattern can be used to filter which paths are added.
        """
        if not os.path.exists(root):
            log.error('Project (add_all): invalid path: {0}'.format(root))
        for filepath in glob.glob(os.path.join(root, pattern)):
            self.add_file(filepath, library)

    def add_constraints(self, path, **attribs):
        """Add the given constraints file to the project."""
        path = utils.relativePathToAbs(path, self.root)
        self.constraints.append(Constraints(path=path, **attribs))

    def add_unittest(self, path, **attribs):
        """Add the given TestSuite file to the project."""
        path = utils.relativePathToAbs(path, self.root)
        unit = UnitTestFile(path=path, **attribs)
        # Perform TestSuite loading on the supplied path
        if os.path.exists(path):
            # Convert the testsuite path into an unpacked testsuite
            # for each file object that has a link to a test suite.
            unpacked_testsuite = testloader.load_tests(
                path,
                self.get_simulation_directory(),
            )
            # Modify the file object, replacing the testsuite path
            # string with the testsuite object that we just
            # unpacked.
            unit.testsuite = unpacked_testsuite
        self.tests.append(unit)

    def add_config(self, name, value, force=False):
        """
        Add a configuration key, value mapping for the project.
        """
        if self.config.get(name, None) is not None and not force:
            log.warning(
                'Ignoring duplicate configuration attribute ' +
                'found in project file, ' +
                str(name) +
                ' set to ' +
                str(value) + ' ' +
                'but already defined as ' +
                str(self.config[name])
            )
        else:
            log.debug(
                'Set project configuration \'' +
                str(name) +
                '\' to \'' +
                str(value) +
                '\''
            )
            self.config[name] = value

    def add_config_dict(self, **kwargs):
        """
        Add a configuration dictionary of key, value mappings for the project.
        """
        for name, value in kwargs.items():
            self.add_config(name, value)

    def add_generic(self, name, value):
        """Add a generic key, value mapping for the project."""
        self.generics[name] = value

    def get_fpga_part(self):
        """
        Return the FPGA part to be used for synthesis.
        """
        return self.config.get(ProjectAttributes.ATTRIBUTE_SYNTH_PART, None)

    def get_simulation_tool_name(self):
        """
        Return the name of the simulation tool to use for simulation.
        """
        return self.config.get(ProjectAttributes.ATTRIBUTE_SIM_TOOL, None)

    def get_synthesis_tool_name(self):
        """
        Return the name of the synthesis tool to use for synthesis.
        """
        return self.config.get(ProjectAttributes.ATTRIBUTE_SYNTH_TOOL, None)

    def get_synthesis_directory(self):
        """
        Return the path to the synthesis directory where all synthesis outputs
        will be stored.
        """
        path = self.config.get(ProjectAttributes.ATTRIBUTE_SYNTH_DIR, None)
        if path is not None:
            return os.path.normpath(path)
        else:
            return None

    def get_simulation_directory(self):
        """
        Return the path to the simulation directory where all simulation
        outputs will be stored.
        """
        path = self.config.get(ProjectAttributes.ATTRIBUTE_SIM_DIR, None)
        if path is not None:
            return os.path.normpath(path)
        else:
            return None

    def get_reporter(self):
        """
        Return function pointer to a reporter function that is executed after a
        synthesis run.
        """
        return reporter.get_reporter(
            self.config.get(ProjectAttributes.ATTRIBUTE_REPORTER, None)
        )

    def get_tool_arguments(self, tool_name, flow_name):
        """
        Return the optional tool arguments attached to this file for the given
        toolname and flowname. If the tool or flow are not present in the
        optional arguments then return an empty string. Multiple spaces in the
        tool argument string are merged into a single space.
        """
        return re.sub(
            ' +',
            ' ',
            self.config.get(
                'args_{0}_{1}'.format(tool_name, flow_name), ''
            )
        )

    def get_libraries(self):
        """
        Return a dictionary of *libname*, *[file_list]* where *libname* is a
        string indicating a library name and *[file_list]* is a list of
        *File* objects that have been added to the library.
        """
        return self.project_data

    def get_generics(self):
        """
        Return a dictionary of (generic : setting) where *generic* is the
        string name of a HDL port generic and *setting* is the value to assign
        to the port generic. The port value can be a string, integer or
        boolean type.
        """
        return self.generics

    def get_constraints(self):
        """
        Return a list of *Constraint* objects that have been added to the
        project.
        """
        return self.constraints

    def get_files(self):
        """
        Return a list of *File* objects that have been added to the *Project*.
        The order in which the files appear in the list matches the order in
        which they were added to the project.
        """
        return self.file_list

    def get_synthesis_fileset(self):
        """
        Return a dictionary of {lib : [file_a, file_b]} where *lib* is a string
        indicating the name of the library and *[file_a, file_b]* is a list of
        *File* objects that has been filtered to contain only files that have
        their *.synthesise* attribute set.
        """
        result = {}
        if self.project_data is not None:
            for libName, library in self.project_data.items():
                if libName not in result:
                    result[libName] = []
                # Only include files that are registered for synthesis
                result[libName] += (list(
                    filter(lambda x: x.synthesise, library))
                )
        return result

    def get_available_simulators(self):
        """
        Get a dictionary of the Simulators available on this system.
        Return a dictionary of tool_name : tool_instance where *tool_name* is
        a string name and *tool_instance* is a Simulator instance.
        """
        return self.tool_wrapper.simulators

    def get_available_synthesisers(self):
        """
        Get a dictionary of the Synthesisers available on this system.
        Return a dictionary of tool_name : tool_instance where *tool_name* is
        a string name and *tool_instance* is a Synthesiser instance.
        """
        return self.tool_wrapper.synthesisers

    def get_simulator_library_dependencies(self, tool_name):
        """
        Return a dictionary of library_name : path where both are strings and
        the *library_name* defines a simulation library dependency name and
        *path* provides the path to the dependency. Simulation libraries for
        the given simulation tool name are returned.
        """
        return self.options.get_simulator_library_dependencies(tool_name)

    def get_system_config_path(self):
        """
        Return a path string indicating the location of the .chiptoolsconfig
        configuration file.
        """
        return self.options.getOptionsPath()

    def run_preprocessors(self):
        """
        Execute any *Preprocessors* attached to *Files* currently loaded into
        the *Project*. A preprocessor can be used to modify the contents of the
        file prior to simulation or synthesis.
        """
        files = self.file_list
        if files is None:
            return
        for file_object in files:
            # Preprocess the file if it has a preprocessor
            if file_object.preprocessor:
                try:
                    if Preprocessor.process(
                        file_object.path,
                        file_object.preprocessor
                    ):
                        log.info(
                            'Executed preprocessor {0} on file {1}'.format(
                                os.path.basename(file_object.preprocessor),
                                file_object.path
                            )
                        )
                except:
                    log.error(traceback.format_exc())

    def compile(self, tool_name=None):
        """
        Compile the libraries and files loaded into the *Project*.
        The Simulation tool that is used is determined by the
        *tool_name* input if supplied, otherwise the *Project* configuration
        : 'simulator' tool name will be used instead.
        """
        simulation_tool = self._get_tool(tool_name, tool_type='simulation')
        simulation_tool.compile_project(
            includes=self.options.get_simulator_library_dependencies(
                simulation_tool.name
            )
        )

    def _get_tool(self, tool_name=None, tool_type='simulation'):
        tool = self.tool_wrapper.get_tool(
            tool_type=tool_type,
            tool_name=tool_name
        )
        if tool is None:
            raise EnvironmentError(
                "Operation aborted, no {0} tool is available".format(tool_type)
            )
        if not tool.installed:
            raise EnvironmentError(
                "Operation aborted, {0} is not available.".format(
                    tool.name
                )
            )
        return tool

    def simulate(self, library, entity, tool_name=None, **kwargs):
        """
        Simulate the *Project* using the given *library* and *entity* as a top
        level. The Simulation tool that is used is determined by the
        *tool_name* input if supplied, otherwise the *Project* configuration
        : 'simulator' tool name will be used instead.
        """

        simulation_tool = self._get_tool(tool_name, tool_type='simulation')
        includes = self.options.get_simulator_library_dependencies(
            simulation_tool.name
        )
        # Do a compilation of the design to ensure the libraries are up to date
        try:
            simulation_tool.compile_project(
                includes=includes
            )
        except:
            log.error(traceback.format_exc())
            log.error("Compilation aborted due to previous error")
            return False

        includes.update(kwargs.get('includes', {}))
        kwargs.update(
            {
                'includes': includes,
            }
        )

        log.info('Simulating entity ' + entity + ' in library ' + library)
        simulation_tool.simulate(library, entity, **kwargs)

    def synthesise(self, library, entity, tool_name=None, fpga_part=None):
        """
        Synthesise the *Project* using the given *library* and *entity* as a
        top level. The synthesis tool that is used is determined by the
        *tool_name* input if supplied, otherwise the *Project* configuration
        : 'synthesiser' tool name will be used instead.
        """
        # Run the preprocessors prior to build.
        self.run_preprocessors()

        try:
            synthesis_tool = self._get_tool(tool_name, tool_type='synthesis')
            log.info(
                'Synthesising entity ' + entity + ' in library ' + library
            )
            try:
                synthesis_tool.synthesise(library, entity, fpga_part)
            except exceptions.SynthesisException:
                log.error(
                    'Synthesis failed, refer to log for more information.'
                )
                return
        except:
            log.error(traceback.format_exc())

    def get_tests(self):
        """
        Return a list of files implementing TestSuite objects.
        """
        files_with_tests = list(
            filter(lambda x: x.testsuite, self.tests)
        )
        return files_with_tests

    def run_tests(self, ids=None, tool_name=None):
        """
        Run the Project unit tests. The *ids* input is an iterable containing
        integer IDs referencing test cases from the test suite. If *ids* is
        None all tests in the test suite will be executed, otherwise the
        *ids* will be used to select which tests in the test suite are run.

        The Simulation tool that is used is determined by the
        *tool_name* input if supplied, otherwise the *Project* configuration
        : 'simulator' tool name will be used instead.
        """
        simulation_tool = self._get_tool(tool_name, tool_type='simulation')
        # First compile the project
        try:
            simulation_tool.compile_project(
                includes=self.options.get_simulator_library_dependencies(
                    simulation_tool.name
                )
            )
        except:
            log.error(traceback.format_exc())
            log.error("Compilation aborted due to previous error")
            return

        suite = unittest.TestSuite()
        tests = []

        for file_object in self.get_tests():
            file_name = os.path.basename(file_object.path)
            for test_group in file_object.testsuite:
                for testId, test in enumerate(utils.iterate_tests(test_group)):
                    # Patch in the simulation runtime data
                    test.postImport(
                        self.options.get_simulator_library_dependencies(
                            simulation_tool.name
                        ),
                        self.get_simulation_directory(),
                        simulation_tool,
                    )
                    # Add the test to the library
                    tests.append((file_name, test))

        if len(tests) == 0:
            log.warning('No tests available.')
            return

        # Run all tests by default if no IDs are specified
        if ids is None:
            ids = list(range(len(tests)))
        elif len(ids) == 0:
            ids = list(range(len(tests)))

        for id in ids:
            if id < len(tests):
                fileName, test = tests[id]
                log.info(
                    str(test.id())
                )
                suite.addTest(test)
                log.info('Added ' + str(test) + ' to testsuite')

        log.info('Running testsuite...')
        try:
            # TODO: Allow HTML or Console selection
            if True:
                with open(
                    os.path.join(
                        self.get_simulation_directory(), 'report.html'
                    ), 'w'
                ) as report:
                    HTMLTestRunner.HTMLTestRunner(
                        verbosity=2,
                        stream=report
                    ).run(suite)
            else:
                unittest.TextTestRunner(verbosity=2).run(suite)
        except Exception:
            log.error('An error was encountered when running the TestSuite')
            log.error(traceback.format_exc())
        log.info('...done')
