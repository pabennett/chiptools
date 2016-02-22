import unittest
import logging
import traceback
import os
import sys
if sys.version_info < (3, 0, 0):
    import imp
else:
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

    def postImport(
        self,
        simulation_libraries,
        simulation_path,
        simulation_tool
    ):
        """
        Store project environment information so that it is available to
        testcases when they are run.
        """
        self.simulation_libraries = simulation_libraries
        self.simulation_root = simulation_path
        self.simulator = simulation_tool

    def simulate(self):

        # Simulate the testbench
        if len(self.generics.keys()) == 0:
            log.warning(
                'No generics are supplied by this test case, if the ' +
                'testbench uses generics' +
                ' they will assume their default values.'
            )

        if self.simulator is None or not self.simulator.installed:
            name = None if self.simulator is None else self.simulator.name
            raise EnvironmentError(
                "Test aborted, {0} is not available.".format(
                    name
                )
            )

        ret_val, stdout, stderr = self.simulator.simulate(
            library=self.library,
            entity=self.entity,
            includes=self.simulation_libraries,
            duration=self.duration,
            generics=self.generics,
            gui=False
        )
        return (ret_val, stdout, stderr)


def load_tests(
    path,
    simulation_path,
):
    """Import the test shim python module given by path and return a
    collection of Unittest classes for each of the tests found in the shim"""
    if not os.path.exists(path):
        log.error('File not found, aborting test package load: ' + str(path))
        return

    log.debug('Loading test package: ' + path + '...')

    try:
        test_loader = unittest.TestLoader()
        # Load modules with support for Python 2 or 3
        if sys.version_info < (3, 0, 0):
            module = imp.load_source(
                'chiptools_tests_' + os.path.basename(path).split('.')[0],
                path
            )
            suite = test_loader.loadTestsFromModule(module)
        else:
            module_loader = importlib.machinery.SourceFileLoader(
                'chiptools_tests_' + os.path.basename(path).split('.')[0],
                path
            )
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
