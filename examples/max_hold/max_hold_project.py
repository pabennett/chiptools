"""
This script provides an example of how to use the ChipTools scripted flow.
"""
try:
    # Import the Project class from chiptools.core.project
    from chiptools.core.project import Project
except ImportError:
    import sys
    print("ChipTools is not installed on your system.")
    sys.exit(1)

# Create a new Project
project = Project()

# Configure project, you may wish to edit some of these settings depending
# on which simulation/synthesis tools are installed on your system.
config = {
    'simulation_directory': 'simulation',
    'synthesis_directory': 'synthesis',
    'simulator': 'modelsim',
    'synthesiser': 'ise',
    'part': 'xc6slx9-csg324-2',
}
# The Project class provides an add_config or add_config_dict method. We use
# the add_config_dict method here to load the config dictionary, you can set
# individual configuration items using add_config.
project.add_config_dict(**config)

# Some unit tests have been written for the max_hold component and stored in
# max_hold_tests.py. The Project class provides an 'add_unittest' method for
# adding unit tests to the project, it expects a path to the unit test file.
project.add_unittest('max_hold_tests.py')

# Source files for the max_hold component are added to the project. The Project
# 'add_file' method accepts a file path and library name, if no library is
# specified it will default to 'work'. Other file attributes are available but
# not covered in this example.
project.add_file('max_hold.vhd', library='lib_max_hold')
project.add_file('pkg_max_hold.vhd', library='lib_max_hold')

# When adding the testbench file we supply a 'synthesise' attribute and set it
# to 'False', this tells the synthesis tool not to try to synthesise this file.
# If not specified, 'synthesise' will default to 'True'
project.add_file(
    'tb_max_hold.vhd',
    library='lib_tb_max_hold',
    synthesise=False
)

# Run all of the test suites held in the project by using the 'run_tests'
# method.
project.run_tests()

# The max_hold component has a generic input 'data_width' to allow it to be
# parameterized.
# For this example, lets set the 'data_width' to 3.
project.add_generic('data_width', 3)

# The design requires constraints before it can be synthesised. Add the
# constraints using the 'add_constraints' Project method.
project.add_constraints('max_hold.ucf')

# Synthesise the project
project.synthesise('lib_max_hold', 'max_hold')
