import unittest
import os
import re
import logging
import sys
import tarfile

testroot = os.path.dirname(__file__) or '.'
sys.path.insert(0, os.path.abspath(os.path.join(testroot, os.path.pardir)))
verbose = True

from chiptools.core import cli

# Blackhole log messages from chiptools
if not verbose:
    logging.config.dictConfig({'version': 1})


class TestSynthesiserInterface(unittest.TestCase):

    project_path = None
    synthesiser_name = ''
    library = 'lib_max_hold'
    entity = 'max_hold'

    def preTestCheck(self):
        """
        Check that the required dependencies are available before running the
        tests. If the user does not have the required synthesiser installed we
        cannot run these unit tests.
        """
        synthesiser = self.cli.project.get_available_synthesisers().get(
            self.cli.project.get_synthesis_tool_name(),
            None
        )
        if synthesiser is None or not synthesiser.installed:
            raise unittest.SkipTest(
                'Cannot run this test as no synthesiser is available.'
            )

    def setUp(self):
        if self.project_path is None:
            return
        self.assertTrue(os.path.exists(self.project_path))
        self.cli = cli.CommandLine()
        self.cli.do_load_project(self.project_path)
        # Clean up any existing test data
        self.tearDown()
        # Override the project synthesiser config
        self.cli.project.add_config(
            'synthesiser',
            self.synthesiser_name,
            force=True
        )

    def tearDown(self):
        root = self.cli.project.get_synthesis_directory()
        for f in os.listdir(root):
            if f.endswith('.tar'):
                os.remove(os.path.join(root, f))

    def checkTestReport(self, path='report.html'):
        self.assertTrue(os.path.exists(path))
        with open(path, 'r') as f:
            data = f.read()
        self.assertTrue(len(data) > 0)
        failures = re.search(
            'Failure (\\d+)',
            data
        )
        passes = re.search(
            'Pass (\\d+)',
            data
        )
        self.assertIsNotNone(passes)
        # Absence of 'Failures' in test report means nothing failed
        if failures is not None:
            failures = int(failures.group(1))
            self.assertEqual(failures, 0)

    def checkTarFile(self, includeFileList=[], excludeFileList=[]):
        '''
        Open the synthesis tar file and check that the items in
        includeFileList appear in the tarFile and check that the items in
        excludeFileList are not present in the tarFile. This method also
        checks that there is only one tar file present
        '''
        root = self.cli.project.get_synthesis_directory()
        # Expect to find a single tar file in the synthesis directory:
        tarFiles = list(filter(lambda x: x.endswith('.tar'), os.listdir(root)))
        self.assertEqual(len(tarFiles), 1)
        # Open the tar file
        with tarfile.TarFile(
            os.path.join(root, tarFiles[0]),
            'r'
        ) as tarFileHandle:
            # Get the files in the archive
            fileList = tarFileHandle.getnames()
            subroot = fileList[0]
            fileList = [os.path.normpath(p) for p in fileList]
            # Check that the items in includeFileList appear in the fileList
            for filename in includeFileList:
                self.assertTrue(
                    os.path.normpath(
                        os.path.join(subroot, filename)
                    ) in fileList
                )
            # Check that the items in excludeFileList do not appear in fileList
            for filename in excludeFileList:
                self.assertFalse(
                    os.path.normpath(
                        os.path.join(subroot, filename)
                    ) in fileList
                )


class TestMaxHoldSynthesisIse(TestSynthesiserInterface):

    synthesiser_name = 'ise'
    root = os.path.join('examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold.xml')
    part = 'xc6slx9-csg324-2'

    def test_synthesise(self):
        self.preTestCheck()
        self.cli.do_synthesise(
            (
                self.library + '.' +
                self.entity + ' ' +
                self.synthesiser_name + ' ' +
                self.part
            )
        )
        # Check for output products
        expected_outputs = [
            self.entity + '.bit',
        ]
        exclude_outputs = [
            'xflow.log'
        ]
        self.checkTarFile(expected_outputs, exclude_outputs)


class TestMaxHoldSynthesisVivado(TestSynthesiserInterface):

    synthesiser_name = 'vivado'
    root = os.path.join('examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold.xml')
    part = 'xc7a100tcsg324-1'

    def test_synthesise(self):
        self.preTestCheck()
        self.cli.do_synthesise(
            (
                self.library + '.' +
                self.entity + ' ' +
                self.synthesiser_name + ' ' +
                self.part
            )
        )
        # Check for output products
        expected_outputs = [
            self.entity + '.bit',
        ]
        exclude_outputs = []
        self.checkTarFile(expected_outputs, exclude_outputs)


class TestMaxHoldSynthesisQuartus(TestSynthesiserInterface):

    synthesiser_name = 'quartus'
    root = os.path.join('examples', 'max_hold')
    project_path = os.path.join(root, 'max_hold.xml')
    part = 'EP3C40F484C6'

    def test_synthesise(self):
        self.preTestCheck()
        # Configure the project to create a JIC file:
        self.cli.project.add_config(
            'args_quartus_cpf_jic',
            '-c -d EPCS128 -s ' + self.part
        )
        # Run synthesis
        self.cli.do_synthesise(
            (
                self.library + '.' +
                self.entity + ' ' +
                self.synthesiser_name + ' ' +
                self.part
            )
        )
        # Check for output products
        expected_outputs = [
            self.entity + '.sof',
            self.entity + '.jic',
        ]
        exclude_outputs = []
        self.checkTarFile(expected_outputs, exclude_outputs)



if __name__ == '__main__':
    unittest.main()
