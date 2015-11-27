import unittest
import logging
import traceback
import os
import importlib.machinery

from chiptools.common import utils

log = logging.getLogger(__name__)


class ChipToolsTest(unittest.TestCase):

    """The ChipToolsTest class inherits unittest.TestCase and should be used
    as a base class for any unit tests that are included in your Project.
    The ChipToolsTest class implements a setUp method to execute your chosen
    simulator prior to each of the tests defined in your unit tests. After
    the simulator has executed, the return code, stdout stream and stderr
    stream are captured and stored in following attributes:
        * self.sim_ret_val (simulator return code)
        * self.sim_stdout (simulator stdout as string)
        * self.sim_stderr (simulator stderr as string)
        * self.simulation_root (path to the simulator working directory)

    Additional attibutes belonging to the ChipToolsTest class that you should
    override are:
        * self.duration (a float number of seconds to run the simulation for,
            if 0 the simulator will run until the testbench terminates)
        * self.generics (a dictionary of name:value where *name* is the name
            of a testbench port generic and *value* is the value to be
            assigned to the port generic) (*this is an optional attribute*)
        * self.entity (the name of the entity that this testcase targets)
        * self.library (the library in which the entity targeted by this
            testcase resides)

    Refer to the *examples* directory for demonstrations on how to create unit
    tests.
    """

    duration = 0
    generics = {}
    entity = ''
    library = ''
    sim_stdout = ''
    sim_stderr = ''
    sim_ret_val = 0

    def postImport(self, tool_wrapper, simulation_libraries, simulation_path):
        """
        Store project environment information so that it is available to
        testcases when they are run.
        """
        self.tool_wrapper = tool_wrapper
        self.simulation_libraries = simulation_libraries
        self.simulation_root = simulation_path

    def simulationSetUp(self):
        """The ChipTools test framework will call the simulationSetup method
        prior to executing the simulator. Place any code that is required to
        prepare simulator inputs in this method."""
        pass

    def simulationTearDown(self):
        """The ChipTools test framework will call the simulationTearDown method
        after completing the tests. Insert any cleanup code to remove generated
        files in this method."""
        pass

    def setUp(self):
        # Run user setup first
        self.simulationSetUp()

        # Simulate the testbench
        # TODO: Not all simulators may support this TCL format, move this to
        # the tool-specific wrappers.
        if self.duration <= 0:
            duration = '-all'
        else:
            duration = utils.seconds_to_timestring(self.duration)

        if len(self.generics.keys()) == 0:
            log.warning(
                'No generics are supplied by this test case, if the ' +
                'testbench uses generics' +
                ' they will assume their default values.'
            )
        simulator = self.tool_wrapper.get_tool(
            tool_type='simulation'
        )

        ret_val, stdout, stderr = simulator.simulate(
            library=self.library,
            entity=self.entity,
            includes=self.simulation_libraries,
            do=(
                'set NumericStdNoWarnings 1\n' + 'run ' +
                duration + ';quit'
            ),
            generics=self.generics,
            gui=False
        )
        self.sim_ret_val = ret_val
        self.sim_stdout = stdout
        self.sim_stderr = stderr

    def tearDown(self):
        # Run user teardown
        self.simulationTearDown()


def load_tests(
    path,
    tool_wrapper,
    simulation_path,
    simulation_libraries={}
):
    """Import the test shim python module given by path and return a
    collection of Unittest classes for each of the tests found in the shim"""
    if not os.path.exists(path):
        log.error('File not found, aborting test package load: ' + str(path))
        return

    log.debug('Loading test package: ' + path + '...')

    try:
        module_loader = importlib.machinery.SourceFileLoader(
            'chiptools_tests_' + os.path.basename(path).split('.')[0],
            path
        )
        test_loader = unittest.TestLoader()
        suite = test_loader.loadTestsFromModule(
            module_loader.load_module()
        )
    except:
        log.error(
            'The module could not be imported due to the ' +
            ' following error:'
        )
        log.error(traceback.format_exc())
        return None

    return suite
