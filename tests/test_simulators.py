import unittest
import os
import re
import logging
import sys
import shutil
import hashlib

testroot = os.path.dirname(__file__) or '.'
sys.path.insert(0, os.path.abspath(os.path.join(testroot, os.path.pardir)))

from chiptools.core import cli

# Blackhole log messages from chiptools
logging.config.dictConfig({'version': 1})


class BaseTests:
    class SimulatorInterfaceChecks(unittest.TestCase):

        project_path = None
        simulator_name = ''

        def setUp(self):
            if self.project_path is None:
                return
            self.assertTrue(
                os.path.exists(self.project_path),
                msg='Could not find the project file: {0}'.format(
                    self.project_path
                )
            )
            self.cli = cli.CommandLine()
            self.cli.do_load_project(self.project_path)

            # Override the project simulator config
            self.cli.project.add_config(
                'simulator',
                self.simulator_name,
                force=True
            )

            # Check that the required dependencies are available before running
            # the tests. If the user does not have the required simulator
            # installed we cannot run these unit tests.
            simulator = self.cli.project.get_available_simulators().get(
                self.cli.project.get_simulation_tool_name(),
                None
            )
            if simulator is None or not simulator.installed:
                raise unittest.SkipTest(
                    'Cannot run this test as {0} is not available.'.format(
                        simulator.name
                    )
                )

        def tearDown(self):
            root = self.cli.project.get_simulation_directory()
            for f in os.listdir(root):
                path = os.path.join(root, f)
                if not os.path.isdir(path):
                    if os.path.basename(path) != '.gitignore':
                        os.remove(path)
                else:
                    shutil.rmtree(path)

        def add_unit_selection(self, command=''):
            self.cli.do_add_tests(command)

        def remove_unit_selection(self, command=''):
            self.cli.do_remove_tests(command)

        def run_unit_selection(self, command=''):
            self.cli.do_show_synthesis_fileset('')
            self.cli.do_run_tests(command)

        def check_unit_framework(self):
            self.cli.do_show_tests('')
            self.add_unit_selection('1-50')
            slen = len(self.cli.test_set)
            if slen > 0:
                self.remove_unit_selection('1')
                self.assertEqual(len(self.cli.test_set), slen-1)
                self.add_unit_selection('1')
                self.assertEqual(len(self.cli.test_set), slen)
            if len(self.cli.project.get_tests()) > 0:
                self.run_unit_selection()
                self.check_report(
                    path=os.path.join(
                        self.cli.project.get_simulation_directory(),
                        'report.html'
                    )
                )

        def check_report(self, path='report.html'):
            self.assertTrue(
                os.path.exists(path),
                msg='Could not find report: {0}'.format(path)
            )
            with open(path, 'r') as f:
                data = f.read()
            self.assertTrue(
                len(data) > 0,
                msg='The test report is empty.'
            )
            failures = re.search(
                'Failure (\\d+)',
                data
            )
            errors = re.search(
                'Error (\\d+)',
                data
            )
            passes = re.search(
                'Pass (\\d+)',
                data
            )
            self.assertIsNotNone(passes)
            if failures is not None:
                failures = int(failures.group(1))
                self.assertEqual(failures, 0)
            if errors is not None:
                errors = int(errors.group(1))
                self.assertEqual(errors, 0)

###############################################################################
# Test the simulator wrappers using the Max Hold (VHDL) example
###############################################################################


class TestExampleProjectsMaxHoldModelsim(BaseTests.SimulatorInterfaceChecks):

    simulator_name = 'modelsim'
    base = os.path.dirname(__file__)
    root = os.path.join(base, '..', 'examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold.xml')
    cache_path = os.path.join(root, '.max_hold_compilation.cache')

    def test_compile(self):
        self.cli.do_compile('')

    def test_cached_compile(self):
        # Clean uninitialised workspace
        self.cli.do_clean('')
        # Compile the project
        self.cli.do_compile('')
        # Clear the compilation cache
        self.cli.do_clean('')
        # Compile the project
        self.cli.do_compile('')
        # Check cache exists
        self.assertTrue(os.path.exists(self.cache_path))
        # Get the cache checksum
        md5 = hashlib.md5(open(self.cache_path, 'rb').read()).hexdigest()
        # Now recompile the project to check the caching
        self.cli.do_compile('')
        # Check that the cache has not changed
        md5new = hashlib.md5(open(self.cache_path, 'rb').read()).hexdigest()
        self.assertEqual(md5, md5new)

    def test_unit_test_framework(self):
        self.check_unit_framework()


class TestExampleProjectsMaxHoldVhdlIsim(TestExampleProjectsMaxHoldModelsim):
    simulator_name = 'isim'


class TestExampleProjectsMaxHoldVhdlGhdl(TestExampleProjectsMaxHoldModelsim):
    simulator_name = 'ghdl'

###############################################################################
# Test the simulator wrappers using the Max Hold (SystemVerilog) example
###############################################################################


class TestExampleProjectsMaxHoldSvIcarus(TestExampleProjectsMaxHoldModelsim):
    simulator_name = 'iverilog'
    base = os.path.dirname(__file__)
    root = os.path.join(base, '..', 'examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold_sv.xml')


class TestExampleProjectsMaxHoldSvVivado(TestExampleProjectsMaxHoldModelsim):
    simulator_name = 'vivado'
    base = os.path.dirname(__file__)
    root = os.path.join(base, '..', 'examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold_sv.xml')


class TestExampleProjectsMaxHoldSvModelsim(TestExampleProjectsMaxHoldModelsim):
    simulator_name = 'modelsim'
    base = os.path.dirname(__file__)
    root = os.path.join(base, '..', 'examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold_sv.xml')

if __name__ == '__main__':
    unittest.main()
