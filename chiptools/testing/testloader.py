import unittest
import logging
import traceback
import sys
import os
import datetime
from collections import OrderedDict
import inspect
import imp

from chiptools.common import utils

log = logging.getLogger(__name__)


def test_factory(
    tool_wrapper,
    simulation_path,
    simulation_libraries,
    shim,
    shimSetUp,
    shimRunCheck,
    shimTearDown
):
    """Return a Unittest class from the shim"""

    simulator = tool_wrapper.get_tool(
        tool_type='simulation'
    )

    def wrappedSetUp(self):
        shimSetUp(simulationRoot=simulation_path)

    def wrappedTearDown(self):
        shimTearDown(simulationRoot=simulation_path)

    def wrappedTest(self):
        # Simulate the testbench
        if shim.duration <= 0:
            duration = '-all'
        else:
            duration = utils.seconds_to_timestring(shim.duration)

        if len(shim.generics.keys()) == 0:
            log.warning(
                'No generics are supplied by this test case, if the ' +
                'testbench uses generics' +
                ' they will assume their default values.'
            )

        retVal, stdout, stderr = simulator.simulate(
            library=shim.library,
            entity=shim.entity,
            includes=simulation_libraries,
            do=(
                'set NumericStdNoWarnings 1\n' + 'run ' +
                duration + ';quit'
            ),
            generics=shim.generics,
            gui=False
        )
        # Make a copy of the stdout in the simulation path for reference
        filename = (
            shim.entity +
            '_' +
            shim.library +
            '_' +
            shimRunCheck.__name__ +
            '_' +
            datetime.datetime.now().strftime('%d%m%y_%H%M%S') +
            '.stdout'
        )
        with open(os.path.join(simulation_path, filename), 'w') as f:
            f.write(stdout)
        # When the simulator has completed the test shim runChecks
        # method can be called
        testResult, testMessage = shimRunCheck(
            simulationRoot=simulation_path,
            stdout=stdout,
            stderr=stderr
        )
        if not testResult:
            self.fail(testMessage)

    wrappedTest.__doc__ = shimRunCheck.__doc__
    wrappedSetUp.__doc__ = shimSetUp.__doc__
    wrappedTearDown.__doc__ = shimTearDown.__doc__

    classDict = {
        'setUp': wrappedSetUp,
        'tearDown': wrappedTearDown,
        'runTest': wrappedTest,
        'id': lambda x: shimRunCheck.__name__,
        '__doc__': shim.library + '.' + shim.entity,
        '__module__': shim.__module__,
        # TODO: Overriding __class__ like this can be dangerous, but in this
        # case it is probably OK. Is there a better way of doing this?
        '__class__': shim.__class__,
    }

    return type(shim.name, (unittest.TestCase,), classDict)


test_package_module_name = 'chiptools_unit_test_temporary_module'


def load_tests(path, tool_wrapper, simulation_path, simulation_libraries={}):
    """Import the test shim python module given by path and return a
    collection of Unittest classes for each of the tests found in the shim"""

    if test_package_module_name in sys.modules:
        # Clear the reference to the testPackageModule module
        del sys.modules[test_package_module_name]

    if not os.path.exists(path):
        log.error('File not found, aborting test package load: ' + str(path))
        return

    log.debug('Loading test package: ' + path + '...')

    try:
        imp.load_source(test_package_module_name, path)
        import chiptools_unit_test_temporary_module
    except:
        log.error(
            'The module could not be imported due to the ' +
            ' following error:'
        )
        log.error(traceback.format_exc())
        return None

    # The framework inspects all classes contained in the test package and if
    # they subclass unittest.TestCase it will load any tests found into the
    # test suite for that file
    tests = OrderedDict()
    for name, obj in inspect.getmembers(chiptools_unit_test_temporary_module):
        if inspect.isclass(obj):
            if issubclass(obj, unittest.TestCase):
                try:
                    testPackage = obj()
                except Exception:
                    log.error(
                        'An error was encountered when instancing the ' +
                        'unittest: ' + path +
                        ' This test will not be unpacked or included ' +
                        'in the testsuite.'
                    )
                    log.error('Refer to the traceback for more information.')
                    log.error(traceback.format_exc())
                    return None
                if not hasattr(testPackage, 'tests'):
                    log.error(
                        'No test attribute is present in this unittest' +
                        ', skipping.'
                    )
                    continue
                tests[name] = OrderedDict()
                # Generate unit tests from the tests found in the testPackage
                for testName in sorted(testPackage.tests.keys()):
                    testObject = testPackage.tests[testName]
                    if type(testObject) is not tuple:
                        log.error(
                            testName +
                            ' does not supply a tuple of functions: ' +
                            '(setup, check, teardown) ' +
                            'and will be disabled.'
                        )
                        continue
                    setUp, runCheck, tearDown = testObject
                    if not callable(setUp):
                        log.error(
                            testName +
                            ' setupFunction not a callable function, ' +
                            'this test will be disabled.'
                        )
                        continue
                    if not callable(runCheck):
                        log.error(
                            testName +
                            ' runCheckFunction not a callable function, ' +
                            'this test will be disabled.'
                        )
                        continue
                    if not callable(tearDown):
                        log.error(
                            testName +
                            ' tearDownFunction not a callable function, ' +
                            'this test will be disabled.'
                        )
                        continue

                    try:
                        testClass = test_factory(
                            tool_wrapper,
                            simulation_path,
                            simulation_libraries,
                            testPackage,
                            setUp,
                            runCheck,
                            tearDown
                        )
                        testInstance = testClass()
                        tests[name][testName] = testInstance
                    except Exception:
                        log.error(
                            'The test factory encountered an error while ' +
                            'unpacking ' + testName
                        )
                        log.error(
                            'This test will not be included in the test ' +
                            'suite for ' + path
                        )
                        log.error(
                            'Refer to the traceback for more information.'
                        )
                        log.error(traceback.format_exc())

                log.info(
                    'Unpacked {0} test(s) from testPackage {1}'.format(
                        str(len(tests[name].keys())),
                        obj.__name__,
                    )
                )
            else:
                log.warning(
                    'Ignoring ' + str(name) + '(' + str(obj) + ') in ' +
                    str(path) + ' as it does not subclass unittest.TestCase.'
                )
    return tests
