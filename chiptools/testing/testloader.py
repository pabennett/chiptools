import unittest
import logging
import traceback
import os
import sys
from chiptools.common import utils
from chiptools.core.project import Project

log = logging.getLogger(__name__)


class ChipToolsTest(unittest.TestCase):
    """
    The *ChipToolsTest* class is derived from unittest.TestCase and provides a
    base class for your unit tests to allow them to make full use of ChipTools.

    When creating a unit test class you should override the *duration*,
    *generics*, *library* and *entity* attributes to define the test
    configuration for the simulator. Individual tests can redefine these
    attributes at run-time to provide a powerful testing mechanism for covering
    different configurations.

    A brief example of a basic unit test case is given below:

    >>> from chiptools.testing.testloader import ChipToolsTest
    >>> class MyBasicTestCase(ChipToolsTest):
    ...     duration = 0  # Run forever
    ...     generics = {'data_width' : 3}  # Set data-width to 3
    ...     library = 'lib_tb_max_hold'  # Testbench library
    ...     entity = 'tb_max_hold'  # Entity to simulate
    ...     # Defining a path to a project allows us to run this test case
    ...     # with Nosetests etc. as well as through ChipTools.
    ...     project = os.path.join('max_hold.xml')
    ...     # The setUp method is called at the beginning of each test:
    ...     def setUp(self):
    ...         # Do individual test set-up here
    ...         pass
    ...     # Methods starting with 'test_' are considered test cases:
    ...     def test_max_hold(self):
    ...         # Run the simulator
    ...         return_code, stdout, stderr = self.simulate()
    ...         self.assertEqual(return_code, 0)  # Check error code
    ...         # More advanced checks could search stdout/stderr for
    ...         # assertions, or read output files and compare the
    ...         # response to a Python model.
    ...         pass            
    ...     # The tearDown method is called at the end of each test:
    ...     def tearDown(self):
    ...         # Clean up after your tests here
    ...         pass

    For a complete example refer to the Max Hold example in the examples
    folder.
    """

    duration = 0
    """
    The duration attribute defines the time in seconds that the simulation
    should run for if the chosen simulator supports this as an argument during
    execution.  If a time of 0 is specified the simulation will run until it is
    terminated automatically by the testbench.  e.g. To fix simulation time at
    10ms set duration to 10e-3
    """

    generics = {}
    """
    The *generics* attribute is a dictionary of parameter/generic names and
    associated values.  These key, value pairs will be passed to the simulator
    to override top-level generics or parameters to customise the test
    environment:

    >>> generics = {
    ...     'data_width' : 3,
    ...     'invert_bits': True,
    ...     'test_string': 'hello',
    ...     'threshold': 0.33,
    >>> }

    The *generics* attribute can also be used to dynamically specify parameters
    for individual tests to check different configurations in your testbench:

    >>> def test_32_bit_bus(self):
    ...     self.generics['data_width'] = 32
    ...     self.simulate()
    >>> def test_16_bit_bus(self):
    ...     self.generics['data_width'] = 16
    ...     self.simulate()
    """

    entity = None
    """
    The *entity* attribute defines the name of the top level component to be
    simulated when running this test. The entity should name a valid design
    unit that has been compiled as part of the project.
    """

    library = None
    """
    The *library* attribute defines the name of the library in which the top
    level component to be simulated exists.
    """

    project = None
    """
    The *project* attribute is optional, but if used it should supply an
    absolute path to a valid ChipTools Project XML file that defines the
    libraries and source files that make up the design that this test case
    belongs to.  This attribute is required when the test case is executed
    directly by an external test runner instead of ChipTools, as it will be
    used to prepare the simulation environment for the external test runner.

    The following provides a convenient way of setting the project path so that
    your test can be run from any directory:

    >>> from chiptools.testing.testloader import ChipToolsTest
    >>> class MyUnitTest(ChipToolsTest) 
    ...     base = os.path.dirname(__file__)
    ...     # Now use os.path.join to build a relative path to the project.
    ...     project = os.path.join(base, '..', 'my_project.xml')
    """

    _environment_type = None

    _loaded_path = None

    @staticmethod
    def get_environment(project, tool_name=None):
        """
        Return the simulation environment items from the supplied project
        instance as a tuple of (simulator, simulation_root, libraries).
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
    
    @property
    def simulation_root(self):
        """
        The *simulation_root* property is an absolute path to the directory
        where the simulator is invoked when simulating the testbench. Any
        inputs required by the testbench, such as stimulus files, should be
        placed in this directory by your TestCase. Similarly, any outputs
        produced by the testbench will be placed in this directory.

        For example, to build paths to a testbench input and output file you
        could do the following:

        >>> def setUp(self):
        ...     self.tb_in = os.path.join(self.simulation_root, 'input.txt')
        ...     self.tb_out = os.path.join(self.simulation_root, 'output.txt')
        """
        return self._simulation_root

    @classmethod
    def setUpClass(cls):
        """
        The *setUpClass* method prepares the ChipTools simulation environment
        if it has not already been loaded. 
        
        If this test case is loaded via the ChipTools Project API it will be
        initialised via a call to the *load_environment* method, which pulls
        the simulation environment information from the parent Project
        instance.

        If this test case is loaded via an external tool such as Nosetests the
        setUpClass method will attempt to load the project file pointed to by
        the project path stored in the *project* attribute. When you create
        your test case you can specify this attribute in your test class to
        allow an external runner like Nosetests to call your test cases.

        If the environment was not already initialised by ChipTools and a valid
        project file path is not stored in the *project* attribute, this method
        will raise an EnvironmentError and cause your test to fail.

        This method overloads the unittest.TestCase.setUpClass classmethod,
        which is called once when a TestCase class is instanced.
        """
        log.debug('setUpClass of {0} called...'.format(cls))
        # Check to see if the environment that this class is initialised for
        # matches the project path (if specified). If the environment was
        # initialised by the ChipTools internal loaded then skip these steps.
        if cls._environment_type != 'chiptools':
            if cls._loaded_path != cls.project:
                project = Project()
                project.load_project(cls.project)
                # Using external test runner (such as Nosetests) to execute this
                # test. The test environment therefore needs to be loaded from
                # the Project instance:
                simulator, root, libs = cls.get_environment(project)
                cls._loaded_path = cls.project
                cls._simulator = simulator
                cls._simulation_root = root
                cls._simulation_libraries = libs
                cls._environment_type = 'external'
                # Compile the design if required (simulators with caching will
                # perform this step once).
                cls._simulator.compile_project(
                    includes=cls._simulation_libraries
                )
                log.debug(
                    '...finished initialising environment for {0}'.format(cls)
                )
        if cls._environment_type is None:
            raise EnvironmentError(
                'The simulation environment for this TestCase is not ' +
                'initialised so the test cases cannot be executed. ' +
                'If you are running this test directly ensure that ' +
                'the TestCase class has a "project" attribute which ' +
                'holds a path to a valid ChipTools project file.'
            )
    def load_environment(self, project, tool_name=None):
        """
        Initialise the TestCase simulation environment using the supplied 
        Project reference so that the individual tests implemented in this
        TestCase are able to compile and simulate the design.
        """
        if self._environment_type == 'chiptools':
            log.debug(
                'Environment for {0} is already initialised.'.format(self)
            )
            return
        simulator, root, libs = ChipToolsTest.get_environment(
            project, 
            tool_name
        )
        self.__class__._loaded_path = None
        self.__class__._simulator = simulator
        self.__class__._simulation_root = root
        self.__class__._simulation_libraries = libs
        self.__class__._environment_type = 'chiptools'
        log.debug('Finished load_environment call on {0}'.format(self))

    def simulate(self):
        """
        Launch the simulation tool in console mode to execute the testbench.

        The simulation tool used and the arguments passed during simulation are
        defined by the test environment configured by the test case and the
        *Project* settings. When the simulation is complete this method will
        return a tuple of (*return_code*, *stdout*, *stderr*) which can be used
        to determine if the test was a success or failure. For example your
        testbench may use assertions to print messages during simulation, your
        Python TestCase could use regex to match success of failure criteria in
        the stdout string:

        >>> def test_stdout(self):
        ...     return_code, stdout, stderr = self.simulate()
        ...     # Use an assertion to check for a negative result on a search
        ...     # for 'Error:' in the simulator stdout string.
        ...     self.assertIsNone(re.search('.*Error:.*', stdout))
        """
        # Simulate the testbench
        if len(self.generics.keys()) == 0:
            log.warning(
                'No generics are supplied by this test case, if the ' +
                'testbench uses generics' +
                ' they will assume their default values.'
            )

        if self._simulator is None or not self._simulator.installed:
            name = None if self._simulator is None else self._simulator.name
            raise EnvironmentError(
                "Test aborted, {0} is not available.".format(
                    name
                )
            )

        ret_val, stdout, stderr = self._simulator.simulate(
            library=self.library,
            entity=self.entity,
            includes=self._simulation_libraries,
            duration=self.duration,
            generics=self.generics,
            gui=False
        )
        return (ret_val, stdout, stderr)

