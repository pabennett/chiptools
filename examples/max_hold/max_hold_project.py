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
    'part': 'xc7a100tcsg324-1',
}
# The Project class provides an add_config or add_config_dict method. We use
# the add_config_dict method here to load the config dictionary, you can set
# individual configuration items using add_config.
project.add_config_dict(**config)

# Some unit tests have been written for the max_hold component and stored in
# max_hold_tests.py. The Project class provides an 'add_unittest' method for
# adding unit tests to the project, it expects a path to the unit test file.
project.add_unittest('max_hold_tests.py')
project.add_unittest('basic_unit_test.py')

# The constraints are added to the project using the add_constraints method.
# The optional 'flow' argument is used to explicitly identify which synthesis
# flow the constraints are intended for (the default is to infer supported
# flows from the file extension).
project.add_constraints('max_hold.xdc', flow='vivado')
project.add_constraints('max_hold.ucf', flow='ise')

# Synthesis generics can be assigned via the add_generic command, in this
# example we set the data_Width generic to 3:
project.add_generic('data_width', 3)

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

interactive = False

if interactive:
    # ChipTools provides a command line interface to allow you to perform
    # actions on the project such as synthesis and simulation interactively.
    # It can be launched by importing the CommandLine from chiptools.core.cli
    # and executing the cmdloop() method - the project is passed to the
    # CommandLine constructor. Launch the ChipTools command line with the
    # project we just configured:
    from chiptools.core.cli import CommandLine
    CommandLine(project).cmdloop()
else:
    # actions can be performed on the project directly using the simulate,
    # synthesise or run_tests methods:
    # Simulate the project interactively by presenting the simulator GUI:
    #project.simulate(
    #    library='lib_tb_max_hold',
    #    entity='tb_max_hold',
    #    gui=True,
    #    tool_name='modelsim'
    #)
    ## Run the automated unit tests on the project:
    #project.run_tests(tool_name='isim')
    ## Synthesise the project:
    project.synthesise(
        library='lib_max_hold',
        entity='max_hold',
        tool_name='vivado'
    )