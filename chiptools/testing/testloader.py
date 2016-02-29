import unittest
import logging
import traceback
import os
import sys
from chiptools.common import utils
from chiptools.core.project import Project

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

    # Simulation duration in seconds for simulators that support user defined
    # durations.
    duration = 0
    # Map of module generic/parameter name and value for simulators that
    # support this feature.
    generics = {}
    # Name of the entity to simulate
    entity = ''
    # Library of the entity to simulate
    library = ''
    # Simulation return data (stdout, stderr and return code)
    sim_stdout = ''
    sim_stderr = ''
    sim_ret_val = 0
    # Project reference (only required if external tools such as nosetests will
    # be used to execute the unit tests).
    project = None 
    environment_type = None
    loaded_path = None

    @staticmethod
    def get_environment(project, tool_name=None):
        """
        Return the simulation environment items from the supplied project
        instance.
        """
        # Get the simulation root directory
        simulation_root = project.get_simulation_directory()
        # Get the simulator instance to allow compilation/simulation
        simulator = project._get_tool(
            tool_name,
            tool_type='simulation'
        )
        # Get the simulation library map so that external dependencies
        # can be resolved.
        simulation_libraries = (
            project.options.get_simulator_library_dependencies(
                simulator.name
            )
        )
        return (simulator, simulation_root, simulation_libraries)

    @classmethod
    def setUpClass(cls):
        log.debug('setUpClass of {0} called...'.format(cls))
        # Check to see if the environment that this class is initialised for
        # matches the project path (if specified). If the environment was
        # initialised by the ChipTools internal loaded then skip these steps.
        if cls.environment_type != 'chiptools':
            if cls.loaded_path != cls.project:
                project = Project()
                project.load_project(cls.project)
                # Using external test runner (such as Nosetests) to execute this
                # test. The test environment therefore needs to be loaded from
                # the Project instance:
                simulator, root, libs = cls.get_environment(project)
                cls.loaded_path = cls.project
                cls.simulator = simulator
                cls.simulation_root = root
                cls.simulation_libraries = libs
                cls.environment_type = 'external'
                # Compile the design if required (simulators with caching will
                # perform this step once).
                cls.simulator.compile_project(
                    includes=cls.simulation_libraries
                )
                log.debug(
                    '...finished initialising environment for {0}'.format(cls)
                )

    def load_environment(self, project, tool_name=None):
        """
        Initialise the TestCase simulation environment using the supplied 
        Project reference so that the individual tests implemented in this
        TestCase are able to compile and simulate the design.
        """
        if self.environment_type == 'chiptools':
            log.debug(
                'Environment for {0} is already initialised.'.format(self)
            )
            return
        simulator, root, libs = ChipToolsTest.get_environment(
            project, 
            tool_name
        )
        self.__class__.loaded_path = None
        self.__class__.simulator = simulator
        self.__class__.simulation_root = root
        self.__class__.simulation_libraries = libs
        self.__class__.environment_type = 'chiptools'
        log.debug('Finished load_environment call on {0}'.format(self))

    def simulate(self):
        if self.environment_type is None:
            raise EnvironmentError(
                'The simulation environment for this TestCase is not ' +
                'initialised so the test cases cannot be executed. ' +
                'Ensure that a chiptools.core.project instance is stored ' +
                'in the "project" attribute of this TestCase'
            )
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

