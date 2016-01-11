import cmd
import logging
import traceback
import os
import sys
import shutil
import textwrap

from chiptools.parsers.xml_project import XmlProjectParser
from chiptools.core.project import Project
from chiptools.common import exceptions
from chiptools.common import utils
from chiptools.common import colourer as term
from chiptools.core import _version

log = logging.getLogger(__name__)


def wraps_do_commands(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        log.debug('USER COMMAND: (' + fn.__name__ + ') ' + args[1])
        try:
            return fn(*args, **kwargs)
        except:
            log.error('Command failed due to error:')
            log.error(traceback.format_exc())
    return wrapper

SEP = ' ' * 4

INTRO_TEMPL = (
    '\n' +
    '-'*79+'\n' +
    term.colourise('ChipTools ', fn='bold') +
    '(version: ' + term.colourise('%(version)s', fg='teal') + ')' + '\n\n' +
    'Type ' + term.colourise('\'help\'', fg='yellow') + ' to get started.\n' +
    '%(projects)s' + '\n' +
    '-'*79+'\n'
)


class CommandLine(cmd.Cmd):
    def __init__(self, project=None):
        super(CommandLine, self).__init__()
        prj = ''
        if project is None:
            try:
                self.project = Project()
                projects = self.locateProjects()
                if len(projects) > 0:
                    prj = (
                        'Type ' + term.colourise(
                            '\'load_project <path>\'', fg='yellow'
                        ) +
                        ' to load a project.\n'
                    )
                    prj += (
                        'The current directory contains ' +
                        'the following projects:\n'
                    )
                    prj += term.colourise(
                        '\n'.join('\t{0}: {1}'.format(
                            idx+1,
                            path
                        ) for idx, path in enumerate(projects)),
                        fg='yellow'
                    )
                self.intro = INTRO_TEMPL % dict(
                    version=_version.__version__,
                    projects=prj,
                )
            except exceptions.ProjectFileException:
                log.error(
                    'The project file contains errors, ' +
                    'fix them and then type \'reload\''
                )
            except:
                log.error(
                    'The software has to terminate due to the following error:'
                )
                log.error(traceback.format_exc())
                sys.exit(1)
        else:
            self.project = project
            prj = (
                'Project contains ' + term.colourise(
                    str(len(self.project.get_files())),
                    fg='yellow'
                ) + ' file(s) and ' + term.colourise(
                    str(len(self.project.get_tests())),
                    fg='yellow'
                ) + ' test(s).'
            )
            self.intro = INTRO_TEMPL % dict(
                version=_version.__version__,
                projects=prj,
            )

        self.test_set = set()

    def locateProjects(self):
        """
        Return a list of projects found in the current path.
        """
        projects = []
        logging.getLogger("chiptools").setLevel(
            logging.CRITICAL
        )
        for filePath in os.listdir(os.getcwd()):
            if filePath.endswith('.xml'):
                try:
                    tempProject = Project()
                    # Load the XML file
                    XmlProjectParser.load_project(filePath, tempProject)
                    # If the project contains files we can add it to our list
                    files = tempProject.get_files()
                    files = files if files is not None else []
                    if len(files) != 0:
                        projects.append(filePath)
                except:
                    pass
        logging.getLogger("chiptools").setLevel(logging.DEBUG)
        return projects

    @wraps_do_commands
    def do_load_project(self, path):
        """Load the given project XML file: load_project <path_to_project>"""
        path = os.path.abspath(path)
        if os.path.exists(path) and os.path.isfile(path):
            try:
                log.info(
                    'Loading {0} in current working directory: {1}'.format(
                        path,
                        os.getcwd()
                    )
                )
                XmlProjectParser.load_project(path, self.project)
            except:
                log.error('The project could not be loaded due to an error:')
                log.error(traceback.format_exc())
        else:
            log.error('File not found: {0}'.format(path))

    @wraps_do_commands
    def do_exit(self, command):
        return True

    @wraps_do_commands
    def do_compile(self, command):
        self.project.compile()

    @wraps_do_commands
    def do_show_synthesis_fileset(self, command):
        """Print out the synthesis file set"""
        items = self.project.get_synthesis_fileset().items()
        if len(items) == 0:
            log.info('There are no synthesisable files loaded.')
            return
        for libName, fileList in items:
            log.info('Library: ' + libName)
            for file in fileList:
                log.info('\t\t' + file.path)

    @wraps_do_commands
    def do_synthesise(self, command):
        """Synthesise the design using the chosen synthesis tool and report any
        errors Example: (Cmd) simulate my_library.my_entity"""
        command_elems = command.split(' ')
        fpga_part = None
        if len(command_elems) == 3:
            target, tool_name, fpga_part = command_elems
        elif len(command_elems) == 2:
            target, tool_name = command_elems
        else:
            target = command_elems[0]
            tool_name = None

        try:
            library, entity = target.split('.')
        except ValueError:
            log.error('Command \"' + command + '\" not understood.')
            log.error(
                "Please specify a library and entity.\n" +
                "Example: (Cmd) synthesise my_library.my_entity [tool_name]"
            )
            return

        self.project.synthesise(
            library,
            entity,
            tool_name=tool_name,
            fpga_part=fpga_part
        )

    @wraps_do_commands
    def do_run_preprocessors(self, command):
        """For each project file in the design run any associated
        preprocessors. You can use this command to test that a preprocessor is
        running on your file correctly. Preprocessors are called automatically
        when you run synthesis"""
        log.info('Running preprocessors...')
        self.project.run_preprocessors()
        log.info('...done')

    @wraps_do_commands
    def do_simulate(self, command):
        """Compile the given entity in the given library using the chosen
        simulator and invoke the simulator GUI.
        Example: (Cmd) simulate my_library.my_entity"""
        command_elems = command.split(' ')
        if len(command_elems) == 2:
            target, tool_name = command_elems
        else:
            target = command_elems[0]
            tool_name = None

        try:
            library, entity = target.split('.')
        except ValueError:
            log.error('Command \"' + command + '\" not understood.')
            log.error(
                "Please specify a library and entity.\n" +
                "Example: (Cmd) simulate my_library.my_entity [tool_name]"
            )
            return
        self.project.simulate(library, entity, gui=True, tool_name=tool_name)

    @wraps_do_commands
    def do_clean(self, command):
        """Clear the file cache"""
        # Delete libraries from the simulation area
        simpath = self.project.get_simulation_directory()
        if simpath is None:
            log.error('No simulation path is set, aborting operation.')
            return
        log.info('Cleaning simulation folder: ' + simpath)
        for tool_name in self.project.cache.get_tool_names():
            for libname in self.project.cache.get_libraries(tool_name):
                path = os.path.join(simpath, libname)
                if os.path.exists(path):
                    log.info('Removing ' + path)
                    shutil.rmtree(path)
        log.info('...done')
        self.project.cache.initialise_cache()

    @wraps_do_commands
    def do_pwd(self, command):
        print(
            term.colourise('Working directory: ', fg='yellow') +
            term.colourise('{0}', fg='green').format(os.getcwd())
        )

    @wraps_do_commands
    def do_plugins(self, command):
        simulators = self.project.get_available_simulators()
        synthesisers = self.project.get_available_synthesisers()
        for i, plugin_registry in enumerate([simulators, synthesisers]):
            print(term.yellow(['Simulator Plugins:', 'Synthesis Plugins:'][i]))
            for name, inst in plugin_registry.items():
                plugin_path = sys.modules[inst.__module__].__file__
                plugin_file = os.path.basename(plugin_path)
                print(
                    SEP * 1 + term.darkgray(plugin_file) + '\n' +
                    SEP * 2 + '{:<15}: {:<35}'.format(
                        'Plugin Path',
                        term.green(plugin_path)
                    ) + '\n' +
                    SEP * 2 + '{:<15}: {:<35}'.format(
                        'Name',
                        term.green(str(name))
                    ) + '\n' +
                    SEP * 2 + '{:<15}: {:<35}'.format(
                        'Tool Path',
                        [
                            term.red('(not found) ' + str(inst.path)),
                            term.green(str(inst.path))
                        ][inst.installed]
                    )
                )

    @wraps_do_commands
    def do_show_config(self, command):
        """Print out the project settings"""
        available_simulator_string = ''
        for name, inst in self.project.get_available_simulators().items():
            available_simulator_string += (
                SEP * 2 + '{:<15}: ' +
                [
                    '(not found) ' + term.red('{:<35}'),
                    term.green('{:<35}')
                ][inst.installed] +
                '\n'
            ).format(name, inst.path)

        available_synthesiser_string = ''
        for name, inst in self.project.get_available_synthesisers().items():
            available_synthesiser_string += (
                SEP * 2 + '{:<15}: ' +
                [
                    '(not found) ' + term.red('{:<35}'),
                    term.green('{:<35}')
                ][inst.installed] +
                '\n'
            ).format(name, inst.path)
        simulation_libraries_string = ''
        for name in self.project.get_available_simulators().keys():
            libraries = self.project.get_simulator_library_dependencies(name)
            if len(libraries.keys()) > 0:
                simulation_libraries_string += (
                    term.darkgray(
                        SEP + name.capitalize() + ' ' +
                        'Simulation libraries:\n'
                    )
                )
            for libname, path in libraries.items():
                simulation_libraries_string += (
                    (
                        SEP * 2 + '{:<15}: ' + term.green('{:<35}') + '\n'
                    ).format(libname, path)
                )
        msg = (
            '\n' +
            term.yellow(term.bold('System Configuration: ')) +
            term.green('%(options)s') + '\n' +
            term.darkgray(SEP + 'Working directory:\n') +
            SEP * 2 + term.green('%(working_directory)s') + '\n' +
            term.darkgray(SEP + 'Available simulators:\n') +
            available_simulator_string +
            term.darkgray(SEP + 'Available synthesisers:\n') +
            available_synthesiser_string +
            simulation_libraries_string +
            '\n' +
            term.yellow(term.bold('Project Configuration: ')) +
            term.green('%(project)s') + '\n' +
            term.darkgray(SEP + 'Simulation directory set to:\n') +
            SEP * 2 + term.green('%(simulation_directory)s') + '\n' +
            term.darkgray(SEP + 'Using the simulation tool:\n') +
            SEP * 2 + term.green('%(simulation_tool_name)s') + '\n' +
            term.darkgray(SEP + 'Synthesis directory set to:\n') +
            SEP * 2 + term.green('%(synthesis_directory)s') + '\n' +
            term.darkgray(SEP + 'Using the synthesis tool:\n') +
            SEP * 2 + term.green('%(synthesis_tool_name)s') + '\n' +
            term.darkgray(SEP + 'Targeting FPGA part:\n') +
            SEP * 2 + term.green('%(fpga_part)s') + '\n' +
            term.darkgray(SEP + 'Using synthesis generic binding:\n') +
            SEP * 2 + term.green('%(synthesis_generics)s') + '\n'
        )

        print(msg % dict(
            working_directory=os.getcwd(),
            options=self.project.get_system_config_path(),
            simulation_directory=self.project.get_simulation_directory(),
            simulation_tool_name=self.project.get_simulation_tool_name(),
            synthesis_directory=self.project.get_synthesis_directory(),
            synthesis_tool_name=self.project.get_synthesis_tool_name(),
            fpga_part=self.project.get_fpga_part(),
            modelsim_vsim_args=self.project.get_tool_arguments(
                'modelsim',
                'simulate'
            ),
            project='',
            synthesis_generics=''.join(
                str(k) + ':' + str(v) + ', ' for k, v in
                self.project.get_generics().items()
            ))
        )

    @wraps_do_commands
    def do_show_tests(self, command):
        """
        Show the tests available in the current project.
        """
        tests = self.project.get_tests()

        if len(tests) == 0:
            log.info('There are no tests available.')
            return

        testUniqueId = 0
        for file_object in tests:
            file_name = os.path.basename(file_object.path)
            print(term.yellow(file_name))
            for test_group in file_object.testsuite:
                for testId, test in enumerate(utils.iterate_tests(test_group)):
                    if testId == 0:
                        print(
                            SEP + term.green(str(test.__class__.__name__))
                        )
                    doc = test.shortDescription()
                    if doc is None:
                        doc = term.darkred('No description')
                    if testUniqueId in self.test_set:
                        msg = SEP * 2 + '[' + term.blue('ID ' + str(
                            testUniqueId) + ' ' + test.id().split('.')[-1]
                        ) + ']'
                    else:
                        msg = SEP * 2 + term.lightgray('ID ' + str(
                            testUniqueId) + ' ' + test.id().split('.')[-1]
                        )
                    print(msg)
                    print(term.darkgray(textwrap.fill(
                        doc,
                        width=80,
                        initial_indent=SEP * 2,
                        subsequent_indent=SEP * 2,
                    )))
                    testUniqueId += 1

    def show_test_selection(self):
        """
        Show the currently selected tests in the current project.
        Add or remove tests using the
        add_tests and remove_tests commands respectively.
        """
        ids_list = list(self.test_set)
        tests = []
        for file_object in self.project.get_tests():
            file_name = os.path.basename(file_object.path)
            print(term.yellow(file_name))
            for test_group in file_object.testsuite:
                for testId, test in enumerate(utils.iterate_tests(test_group)):
                    if testId == 0:
                        groupName = str(test.__class__.__name__)
                    testName = test.id().split('.')[-1]
                    tests.append((file_name, groupName, testName, test))

        # Filter out any invalid indices
        ids_list = list(filter(lambda x: x < len(tests), ids_list))
        for idx, (fileName, groupName, testName, test) in enumerate(
            [tests[idx] for idx in ids_list]
        ):
            print(
                '{:<5}'.format(str(ids_list[idx]) + ':') +
                '[' + term.yellow(fileName) + ']' +
                '[' + term.green(groupName) + ']' +
                '[' + term.blue(testName) + ']'
            )

    @wraps_do_commands
    def do_add_tests(self, command):
        """
        Add the given tests to the test suite. Tests should be supplied as
        comma separated numbers or numeric ranges, for example:

        add_tests 1-3, 5, 6, 7

        Would add tests 1, 2, 3, 5, 6, 7 to the test suite.

        You can check which tests are available by issuing the show_tests
        command or remove tests that have been added to the suite by issuing
        the remove_tests command.
        """
        try:
            ids = utils.parseRange(command)
        except ValueError:
            log.error('Invalid test range specified: ' + command)
            return
        for testId in ids:
            self.test_set.add(testId)
        self.show_test_selection()

    @wraps_do_commands
    def do_remove_tests(self, command):
        """
        Remove the given tests from the test suite. Tests should be supplied
        as comma separated numbers or numeric ranges, for example:

        remove_tests 1-3, 5, 6, 7

        Would remove tests 1, 2, 3, 5, 6, 7 from the test suite.

        You can check which tests are available by issuing the show_tests
        command or add tests by issuing the add_tests command.
        """
        try:
            ids = utils.parseRange(command)
        except ValueError:
            log.error('Invalid test range specified: ' + command)
            return
        for testId in ids:
            try:
                self.test_set.remove(testId)
            except KeyError:
                pass
        self.show_test_selection()

    @wraps_do_commands
    def do_run_tests(self, command):
        """
        Run the tests that were selected via the add_tests command and report
        the results.
        """
        if len(command) > 0:
            tool_name = command
        else:
            tool_name = None
        self.show_test_selection()
        self.project.run_tests(self.test_set, tool_name=tool_name)
