"""
The tests in this module check that the Project class and XmlProjectParser can
correctly load and process user-defined project files. These tests do not
perform simulation or synthesis on the project data so they will work even if
vendor tools are not available in the environment.
"""

import unittest
import os
import logging
import sys
import re

testroot = os.path.dirname(__file__) or '.'
sys.path.insert(0, os.path.abspath(os.path.join(testroot, os.path.pardir)))

from chiptools.core.project import Project
from chiptools.core.cli import CommandLine

# Blackhole log messages from chiptools
logging.config.dictConfig({'version': 1})


class TestProjectInterface(unittest.TestCase):

    vhdl_file_data = """library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
entity %(entity)s is
    port (
        CLOCK   : in std_logic;
        RESET   : in std_logic;
        COUNT   : out std_logic_vector(31 downto 0)
    );
end entity;
architecture RTL of %(entity)s is
    signal local_count : unsigned(COUNT'range) := (others => '0');
begin
    DUMMY_PROCESS : process(CLOCK)
    begin
        if rising_edge(CLOCK) then
            if RESET = '1' then
                local_count <= (others => '0');
            else
                local_count <= local_count + 1;
            end if;
        end if;
    end process;
    COUNT <= std_logic_vector(local_count);
end RTL;
"""
    project_wrapper = """
<project>
    <project path='%(path)s'/>
</project>
"""
    project_data = """
<project>
    <config
        simulation_directory='%(simulation_directory)s'
        synthesis_directory='%(synthesis_directory)s'
        simulator='%(simulation_tool_name)s'
        synthesiser='%(synthesis_tool_name)s'
        part='%(project_part)s'
        reporter='%(reporter_path)s'
    />
    %(generics)s
    %(constraints)s
    %(libraries)s
</project>
"""

    invalid_project_data = """
<project>
    <not valid!>;
</project>
    """

    reporter_data = """
def report(x):
    pass
"""
    preprocessor_data = """
import time
def process(data, path):
    data = ['-- Preprocessed at ' + time.strftime('%H:%M:%S')] + data
    return data
"""
    base = os.path.dirname(__file__)
    root = os.path.join(base, '..', 'tests', 'testprojects', 'project_checks')
    child_project_path = os.path.join(root, 'dummy.xml')
    project_path = os.path.join(root, 'master.xml')
    invalid_project_path = os.path.join(root, 'invalid.xml')
    reporter_path = os.path.join(root, 'reporter.py')
    preprocessor_path = os.path.join(root, 'preprocessor.py')
    synthesis_directory = 'synthesis'
    simulation_directory = 'simulation'
    project_part = 'best_fpga_ever'
    simulation_tool_name = 'modelsim'
    synthesis_tool_name = 'ise'

    project_structure = {
        'lib1': [
            'file1.vhd',
            'top.vhd',
            'support.vhd',
        ],
        'lib2': [
            'file2.vhd',
        ],
        'lib3': [
            'file3.vhd',
        ],
    }

    project_constraints = [
        'constraints.ucf',
        'constraints.tcl',
        'constraints.sdc',
    ]

    project_generics = {
        'BUS_WIDTH': '32',
        'DDR_ENABLED': 'True',
        'MODEL_CODE': 'model_a',
    }

    def setUp(self):
        # Guarantee a clean working copy
        self.tearDown()
        # Check that the working area is clean
        self.assertFalse(os.path.exists(self.project_path))
        self.assertFalse(os.path.exists(self.reporter_path))
        # Prepare working area
        libraries = ''
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            libraries += '\t<library name=\'{0}\'>\n'.format(libname)
            if not os.path.exists(os.path.join(self.root, libname)):
                os.makedirs(os.path.join(self.root, libname))
            for path in files:
                libraries += (
                    '\t\t<file path=\'{0}\' preprocessor=\'{1}\'/>\n'.format(
                        os.path.join(libname, path),
                        os.path.basename(self.preprocessor_path),
                    )
                )
                with open(os.path.join(self.root, libname, path), 'w') as f:
                    f.write(
                        self.vhdl_file_data % dict(
                            entity=os.path.basename(path).split('.')[0]
                        )
                    )
            libraries += '\t</library>\n'.format(libname)
        constraints = ''
        for path in self.project_constraints:
            constraints += '<constraints path=\'{0}\'/>\n'.format(path)
        generics = ''
        for k, v in self.project_generics.items():
            generics += '<generic {0}=\'{1}\'/>\n'.format(k, v)

        with open(self.reporter_path, 'w') as f:
            f.write(self.reporter_data)

        with open(self.preprocessor_path, 'w') as f:
            f.write(self.preprocessor_data)

        with open(self.invalid_project_path, 'w') as f:
            f.write(self.invalid_project_data)

        with open(self.project_path, 'w') as f:
            f.write(
                self.project_wrapper % dict(
                    path=os.path.abspath(self.child_project_path)
                )
            )

        with open(self.child_project_path, 'w') as f:
            f.write(
                self.project_data % dict(
                    synthesis_directory=self.synthesis_directory,
                    simulation_directory=self.simulation_directory,
                    project_part=self.project_part,
                    libraries=libraries,
                    constraints=constraints,
                    generics=generics,
                    simulation_tool_name=self.simulation_tool_name,
                    synthesis_tool_name=self.synthesis_tool_name,
                    reporter_path=os.path.basename(self.reporter_path),
                )
            )

    def tearDown(self):
        if os.path.exists(self.child_project_path):
            os.remove(self.child_project_path)
        if os.path.exists(self.project_path):
            os.remove(self.project_path)
        if os.path.exists(self.reporter_path):
            os.remove(self.reporter_path)
        for libname in self.project_structure.keys():
            if os.path.exists(os.path.join(self.root, libname)):
                files = self.project_structure[libname]
                for path in files:
                    os.remove(os.path.join(self.root, libname, path))
                os.rmdir(os.path.join(self.root, libname))
        # If you're running these tests on a network drive you may encounter
        # failures due to delay in the files being removed and generating
        # PermissionErrors on followup tests.
        self.assertFalse(os.path.exists(self.project_path))
        self.assertFalse(os.path.exists(self.reporter_path))

    def run_and_check_preprocessors(self, project):
        project.run_preprocessors()
        regex = re.compile('-- Preprocessed at (\d+){2}:(\d+){2}:(\d+){2}')
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            for path in files:
                path = os.path.join(self.root, libname, path)
                with open(path, 'r') as f:
                    data = f.readlines()
                    match = regex.match(data[0])
                    self.assertIsNotNone(
                        match,
                        msg='File {0} was not correctly preprocessed.'.format(
                            path
                        )
                    )


class TestXmlProjectLoading(TestProjectInterface):
    def test_synthesis_directory(self):
        project = Project()
        project.load_project(self.project_path)
        abs_path = os.path.join(
            os.path.abspath(self.root),
            self.synthesis_directory
        )
        self.assertEqual(project.get_synthesis_directory(), abs_path)

    def test_simulation_directory(self):
        project = Project()
        project.load_project(self.project_path)
        abs_path = os.path.join(
            os.path.abspath(self.root),
            self.simulation_directory
        )
        self.assertEqual(project.get_simulation_directory(), abs_path)

    def test_project_load(self):
        project = Project()
        project.load_project(self.project_path)

    def test_project_part(self):
        project = Project()
        project.load_project(self.project_path)
        # Check project part
        self.assertEqual(
            self.project_part,
            project.get_fpga_part()
        )

    def test_simulation_Tool_name(self):
        project = Project()
        project.load_project(self.project_path)
        # Check simulation tool name
        self.assertEqual(
            self.simulation_tool_name,
            project.get_simulation_tool_name()
        )

    def test_synthesis_tool_name(self):
        project = Project()
        project.load_project(self.project_path)
        # Check synthesis tool name
        self.assertEqual(
            self.synthesis_tool_name,
            project.get_synthesis_tool_name()
        )

    def test_file_set(self):
        project = Project()
        project.load_project(self.project_path)
        # Check the file set loaded from the project
        expected_files = []
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            for path in files:
                expected_files.append(os.path.basename(path))

        self.assertEqual(
            sorted(expected_files),
            sorted([os.path.basename(f.path) for f in project.get_files()]),
        )

    def test_project_constraints(self):
        project = Project()
        project.load_project(self.project_path)
        # Check the project constraints
        self.assertEqual(
            self.project_constraints,
            [os.path.basename(c.path) for c in project.get_constraints()],
        )

    def test_generics(self):
        project = Project()
        project.load_project(self.project_path)
        # Check the synthesis generics
        self.assertDictEqual(
            self.project_generics,
            project.get_generics(),
        )

    def test_reporter(self):
        project = Project()
        project.load_project(self.project_path)
        # Check the synthesis reporter
        self.assertTrue(
            callable(project.get_reporter())
        )

    def test_preprocessor(self):
        project = Project()
        project.load_project(self.project_path)
        files = project.get_files()
        preprocessors = list(
            filter(
                lambda x: os.path.exists(x.preprocessor), files
            )
        )
        self.assertTrue(len(preprocessors) > 0)
        self.run_and_check_preprocessors(project)


class TestManualProjectInterface(TestProjectInterface):

    def test_file_set(self):
        project = Project()

        expected_files = []
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            for path in files:
                expected_files.append(os.path.basename(path))
                project.add_file(path, libname)

        self.assertEqual(
            sorted(expected_files),
            sorted([os.path.basename(f.path) for f in project.get_files()]),
        )

    def test_add_all(self):
        project = Project()
        expected_files = []
        expected_libs = []
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            expected_libs.append(libname)
            project.add_files(
                root=os.path.join(self.root, libname),
                library=libname,
                pattern='*.vhd'
            )
            for path in files:
                expected_files.append(os.path.basename(path))

        self.assertEqual(
            sorted(expected_files),
            sorted([os.path.basename(f.path) for f in project.get_files()]),
        )

        self.assertEqual(
            sorted(expected_libs),
            sorted(list(project.get_libraries()),)
        )

    def test_reporter(self):
        project = Project()
        project.add_config('reporter', self.reporter_path)
        # Check the synthesis reporter
        self.assertTrue(
            callable(project.get_reporter())
        )

    def test_preprocessor(self):
        project = Project()
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            project.add_files(
                root=os.path.join(self.root, libname),
                library=libname,
                pattern='*.vhd',
                preprocessor=self.preprocessor_path
            )

        self.run_and_check_preprocessors(project)

    def test_constraints(self):
        project = Project()
        for constraints in self.project_constraints:
            project.add_constraints(constraints, flow='dummy_flow')
        constraints = project.get_constraints()
        self.assertEqual(
            len(constraints),
            len(self.project_constraints),
            msg='Incorrect number of constraints added to project.'
        )
        self.assertTrue(
            len(constraints) > 0,
            msg='Not correctly tested as no constraints are present.'
        )
        for idx in range(len(constraints)):
            self.assertEqual(
                constraints[idx].path,
                os.path.abspath(self.project_constraints[idx]),
                msg='Constraints path was incorrectly processed.'
            )


class TestUninitialisedProjectCLI(TestProjectInterface):
    """
    These tests check that the CommandLine handles all user command errors
    gracefully when there is no project loaded.
    """
    def test_compile(self):
        cli = CommandLine()
        cli.do_compile('')

    def test_synthesise(self):
        cli = CommandLine()
        cli.do_synthesise('')

    def test_simulate(self):
        cli = CommandLine()
        cli.do_simulate('')

    def test_show_config(self):
        cli = CommandLine()
        cli.do_show_config('')

    def test_add_tests(self):
        cli = CommandLine()
        cli.do_add_tests('')

    def test_remove_tests(self):
        cli = CommandLine()
        cli.do_remove_tests('')

    def test_run_tests(self):
        cli = CommandLine()
        cli.do_run_tests('')

    def test_clean(self):
        cli = CommandLine()
        cli.do_clean('')

    def test_run_preprocessors(self):
        cli = CommandLine()
        cli.do_run_preprocessors('')

    def test_show_synthesis_fileset(self):
        cli = CommandLine()
        cli.do_show_synthesis_fileset('')

    def test_plugins(self):
        cli = CommandLine()
        cli.do_plugins('')

class TestCLI(TestProjectInterface):
    def test_missing_project(self):
        """Test the load_project command with an invalid path."""
        cli = CommandLine()
        cli.do_load_project('invalid/project/path')

    def test_invalid_project(self):
        """Test the load_project command with an invalid project."""
        cli = CommandLine()
        cli.do_load_project(self.invalid_project_path)

    def test_synthesis_fileset(self):
        cli = CommandLine()
        cli.do_load_project(self.project_path)
        cli.do_show_synthesis_fileset('')

class TestMissingReporter(TestProjectInterface):
    reporter_data = """
def report_spelled_wrong(x):
    pass
"""

    def test_reporter(self):
        """If the user incorrectly defines a reporter it should fail gracefully
        and return None."""
        project = Project()
        project.add_config('reporter', self.reporter_path)
        self.assertIsNone(
            project.get_reporter()
        )


class TestReporterSyntaxError(TestProjectInterface):
    reporter_data = """
dfe reporter()){
    oops;
}
"""

    def test_reporter(self):
        """If the user incorrectly defines a reporter it should fail gracefully
        and return None."""
        project = Project()
        project.add_config('reporter', self.reporter_path)
        self.assertIsNone(
            project.get_reporter()
        )

class TestPreprocesorSyntaxError(TestProjectInterface):
    preprocessor_data = """
dfe preprocessor(a, b, c):
    oops;
"""

    def test_preprocessor(self):
        """Invalid preprocessors should not be executed on files."""
        project = Project()
        project.load_project(self.project_path)
        files = project.get_files()
        preprocessors = list(
            filter(
                lambda x: os.path.exists(x.preprocessor), files
            )
        )
        self.assertTrue(len(preprocessors) > 0)
        project.run_preprocessors()
        regex = re.compile('library ieee;')
        for libname in self.project_structure.keys():
            files = self.project_structure[libname]
            for path in files:
                path = os.path.join(self.root, libname, path)
                with open(path, 'r') as f:
                    data = f.readlines()
                    match = regex.match(data[0])
                    self.assertIsNotNone(
                        match,
                        msg='File {0} was not correctly preserved.'.format(
                            path
                        )
                    )

if __name__ == '__main__':
    unittest.main()
