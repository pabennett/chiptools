########
Examples
########

The following examples are provided in the ChipTools repository to show you
how to use the various features of the framework.

Max Hold
========

The **Max Hold** example is located in **examples/max_hold**.

Introduction
------------

The **Max Hold** example implements a basic component in VHDL to output the 
maximum value of an input sequence until it is reset. For example, if such a 
component were to be fed an oscillating input with steadily increasing
amplitude we would expect the following result:

.. image:: max_hold_demo.png

This example will show you how you can use ChipTools to generate stimulus, 
check responses, manage test reports and generate bit files for the 
**Max Hold** component.

Source Files
------------

The following source files belong to the Max Hold example:

    * **VHDL Files:**

        * *max_hold.vhd* - The Max Hold component.
        * *pkg_max_hold.vhd* - Supporting package for the Max Hold component.
        * *tb_max_hold.vhd* - Testbench for the Max Hold component.

    * **Simulation Files:**

        * *max_hold_tests.py* - A collection of unit tests for the Max Hold component.
        * *basic_unit_test.py* - A simple unit test for the Max Hold component.
        * *simulation* - A subfolder where simulations will be executed.

    * **Synthesis Files:**

        * *max_hold.ucf* - A constraints file for the Max Hold component when using the ISE synthesis flow.
        * *max_hold.xdc* - A constraints file for the Max Hold component when using the Vivado synthesis flow.
        * *synthesis* - A subfolder where synthesis will be executed.

Creating the Project
---------------------

This section will walk through the steps required to load and use the source
files with ChipTools. The complete example is available in 
**max_hold_project.py** in the Max Hold project directory.

Initial Setup
~~~~~~~~~~~~~

Firstly, import the ChipTools Project wrapper and create a project instance:

.. code-block:: python

    from chiptools.core.project import Project

    # Create a new Project
    project = Project()

The project wrapper provides a set of functions for loading source files and
configuring a project.

Project Configuration
~~~~~~~~~~~~~~~~~~~~~

Configure the project to use the simulation and synthesis directories, the
default simulation and synthesis tools and the FPGA part:

.. code-block:: python

    # Configure project, you may wish to edit some of these settings depending
    # on which simulation/synthesis tools are installed on your system.
    project.add_config('simulation_directory', 'simulation')
    project.add_config('synthesis_directory', 'synthesis')
    project.add_config('simulator', 'modelsim')
    project.add_config('synthesiser', 'ise')
    project.add_config('part', 'xc6slx9-csg324-2')

Apply Values to Generic Ports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Designs can be parameterised via the use of a generic port on the top level
component. You can assign values to top level port generics by using the 
**add_generic** method:

.. code-block:: python

    # Synthesis generics can be assigned via the add_generic command, in this
    # example we set the data_Width generic to 3:
    project.add_generic('data_width', 3)

Add Files
~~~~~~~~~

Add the Max Hold source files to the project and assign them to a library:

.. code-block:: python

    # Source files for the max_hold component are added to the project. The Project
    # **add_file** method accepts a file path and library name, if no library is
    # specified it will default to 'work'. Other file attributes are available but
    # not covered in this example.
    project.add_file('max_hold.vhd', library='lib_max_hold')
    project.add_file('pkg_max_hold.vhd', library='lib_max_hold')

The testbench is also added to the project. The optional argument *synthesise*
is set to 'False' when adding the testbench as we do not want to include it 
in the files sent to synthesis:

.. code-block:: python

    # When adding the testbench file we supply a 'synthesise' attribute and set it
    # to 'False', this tells the synthesis tool not to try to synthesise this file.
    # If not specified, 'synthesise' will default to 'True'
    project.add_file(
        'tb_max_hold.vhd',
        library='lib_tb_max_hold',
        synthesise=False
    )

There are two unit test files provided for the Max Hold project, these can be
added to the project using the **add_unittest** method:

.. code-block:: python

    # Some unit tests have been written for the max_hold component and stored in
    # max_hold_tests.py. The Project class provides an 'add_unittest' method for
    # adding unit tests to the project, it expects a path to the unit test file.
    project.add_unittest('max_hold_tests.py')
    project.add_unittest('basic_unit_test.py')

Finally, the constraints files can be added to the project using the 
**add_constraints** method, which takes a filepath argument and an optional
**flow** name argument which allows you to explicitly name which synthesis flow
the constraints are intended for:

.. code-block:: python

    # The constraints are added to the project using the add_constraints method.
    # The optional 'flow' argument is used to explicitly identify which synthesis
    # flow the constraints are intended for (the default is to infer supported
    # flows from the file extension).
    project.add_constraints('max_hold.xdc', flow='vivado')
    project.add_constraints('max_hold.ucf', flow='ise')

The project is now fully configured and can be synthesised, simulated or the
unit test suite can be executed to check that the requirements are met:

.. code-block:: python

    # Simulate the project interactively by presenting the simulator GUI:
    project.simulate(
        library='lib_tb_max_hold',
        entity='tb_max_hold',
        gui=True,
        tool_name='modelsim'
    )
    # Run the automated unit tests on the project:
    project.run_tests(tool_name='isim')
    # Synthesise the project:
    project.synthesise(
        library='lib_max_hold',
        entity='max_hold',
        tool_name='vivado'
    )

Alternatively the ChipTools command line can be launched on the project to
enable the user to run project operations interactively:

.. code-block:: python

    # Launch the ChipTools command line with the project we just configured:
    from chiptools.core.cli import CommandLine
    CommandLine(project).cmdloop()


Project (XML) File
~~~~~~~~~~~~~~~~~~

The Project configuration can also be captured as an XML file. 
The example project file **max_hold.xml** provides the same configuration as 
**max_hold_project.py**:

.. code-block:: xml

    <project>
        <config simulation_directory='simulation'/>
        <config synthesis_directory='synthesis'/>
        <config simulator='vivado'/>
        <config synthesiser='vivado'/>
        <config part='xc7a100tcsg324-1'/>
        <unittest path='max_hold_tests.py'/>
        <unittest path='basic_unit_test.py'/>
        <constraints path='max_hold.ucf' flow='ise'/>
        <constraints path='max_hold.xdc' flow='vivado'/>
        <generic data_width='3'/>
        <library name='lib_max_hold'>
            <file path='max_hold.vhd'/>
            <file path='pkg_max_hold.vhd'/>
        </library>
        <library name='lib_tb_max_hold'>
            <file 
                path='tb_max_hold.vhd'
                synthesise='false'
            />
        </library>
    </project>

The project XML file can either be loaded in the ChipTools command line
interface using the **load_project** command, or by using the
**XmlProjectParser** class in a custom script:

.. code-block:: python

    from chiptools.parsers.xml_project import XmlProjectParser
    new_project = Project()
    XmlProjectParser.load_project('max_hold.xml', new_project)
    # new_project is now configured and ready to use.

Via the command line interface:

.. code-block:: bash

    $ chiptools
    (cmd) load_project max_hold.xml

Testing
-------

To test the Max Hold component an accompanying VHDL testbench, 
*tb_max_hold.vhd*, is used to feed the component data from a stimulus input
text file and record the output values in an output text file. By using 
stimulus input files and response output files we gain the freedom to use a
language of our choice to generate stimulus and check results.

Testbench Stimulus File Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The testbench expects a file called **input.txt** to be present in the
simulation folder and expects the file to conform to the following format:

.. code-block:: xml

    [8bit opcode] [Nbit data (if opcode = 00000001)]
    [8bit opcode] [Nbit data (if opcode = 00000001)]
    [8bit opcode] [Nbit data (if opcode = 00000001)]
    ...

Where:

    * Binary 8bit opcode is either 00000000 for reset or 00000001 for write.
    * Binary Nbit data is the data to write to the component, the number of bits is determined by the data_width generic.

We will use Python to create stimulus files in this format for the testbench.

Unit Tests
~~~~~~~~~~

We can use the Python Unittest framework to define tests for the Max Hold
component by first importing the **ChipToolsTest** class from 
**chiptools.testing.testloader**

.. code-block:: python
    
    from chiptools.testing.testloader import ChipToolsTest

The **ChipToolsTest** class provides a wrapper around Python's Unittest
**TestCase** class that will manage simulation execution behind the scenes
while our test cases are executed.

First off, create a ChipToolsTest class and define some basic information about
the testbench:

.. code-block:: python

    class MaxHoldsTestBase(ChipToolsTest):
        # Specify the duration your test should run for in seconds.
        # If the test should run "forever" use 0.
        duration = 0
        # Testbench generics are defined in this dictionary.
        # In this example we set the 'width' generic to 32, it can be overridden
        # by your tests to check different configurations.
        generics = {'data_width': 32}
        # Specify the entity that this Test should target
        entity = 'tb_max_hold'
        # Specify the library that this Test should target
        library = 'lib_tb_max_hold'

These attributes provide the basic information required by ChipTools to execute
the testbench.

Tests are executed in the following way when using the ChipToolsTest class:

    * Execute simulationSetup function if defined.
    * Invoke and run simulator in console mode.
    * Execute test case (functions with a 'test' prefix).
    * Execute simulatorTearDown function if defined.

The **simulationSetup** function should be overloaded to run any **preparation**
code your testbench may require before it is executed. For testing the Max Hold
component we can use this function to write the input file for the testbench 
using different stimulus waveforms that we have created in Python.

.. code-block:: python


    def simulationSetUp(self):
        """The ChipTools test framework will call the simulationSetup method
        prior to executing the simulator. Place any code that is required to
        prepare simulator inputs in this method."""

        # Generate a list of 10 random integers
        self.values = [random.randint(0, 2**32-1) for i in range(10)]

        # Get the path to the testbench input file.
        simulator_input_path = os.path.join(self.simulation_root, 'input.txt')

        # Write the values to the testbench input file
        with open(simulator_input_path, 'w') as f:
            for value in self.values:
                f.write(
                    '{0} {1}\n'.format(
                        '00000001',  # write instruction
                        bin(value)[2:].zfill(32),
                    )
                )

Our tests will be implemented in methods with a **test** prefix. As the test
methods are executed after the simulator has finished, our tests will involve
reading the simulator output file and comparing it to what our internal model
expects given the same input waveform:

.. code-block:: python

    def test_10_random_numbers(self):
        """Check that the Max Hold component correctly locates the maximum
        value in 10 random numbers."""

        # Get the path to the testbench input file.
        simulator_output_path = os.path.join(self.simulation_root, 'output.txt')

        output_values = []
        with open(simulator_output_path, 'r') as f:
            data = f.readlines()
        for valueIdx, value in enumerate(data):
            # testbench response
            output_values.append(int(value, 2))  # Binary to integer

        # Use Python to work out the expected result
        max_hold = [
            max(self.values[:i+1]) for i in range(len(self.values))
        ]

        # Compare the expected result to what the Testbench returned:
        self.assertListEqual(output_values, max_hold)

The above example is saved as **basic_unit_test.py** in the Max Hold 
example folder. We can run this test by invoking ChipTools in the example
folder, loading the **max_hold.xml** project and then adding and running the
testsuite:


.. code-block:: bash

    $ chiptools
    (cmd) load_project max_hold.xml
    (cmd) run_tests
    [INFO] ...skipping: max_hold.vhd
    [INFO] ...skipping: pkg_max_hold.vhd
    [INFO] ...skipping: tb_max_hold.vhd
    [INFO] ...skipped 3 unmodified file(s). Use "clean" to erase the file cache
    [INFO] ...saving cache file
    [INFO] ...done
    [INFO] 3 file(s) processed in 53.999900817871094ms
    [INFO] chiptools_tests_basic_unit_test.MaxHoldsTestBase.test_10_random_numbers
    [INFO] Added test_10_random_numbers (chiptools_tests_basic_unit_test.MaxHoldsTestBase) to testsuite
    [INFO] Running testsuite...
    [INFO] Reading C:/modelsim_dlx_10.3d/tcl/vsim/pref.tcl
    [INFO]
    [INFO] # 10.3d
    [INFO]
    [INFO] # vsim -L unimacro -L xilinxcorelib -L unisim -L secureip -L simprim -Gdata_width=32 -c -do "set NumericStdNoWarnings 1
    [INFO] # run -all;quit" lib_tb_max_hold.tb_max_hold
    [INFO] # Start time: 17:16:58 on Nov 30,2015
    [INFO] # //  ModelSim DE 10.3d Oct  7 2014
    [INFO] # //
    [INFO] # //  Copyright 1991-2014 Mentor Graphics Corporation
    [INFO] # //  All Rights Reserved.
    [INFO] # //
    [INFO] # //  THIS WORK CONTAINS TRADE SECRET AND PROPRIETARY INFORMATION
    [INFO] # //  WHICH IS THE PROPERTY OF MENTOR GRAPHICS CORPORATION OR ITS
    [INFO] # //  LICENSORS AND IS SUBJECT TO LICENSE TERMS.
    [INFO] # //
    [INFO] # Loading std.standard
    [INFO] # Loading std.textio(body)
    [INFO] # Loading ieee.std_logic_1164(body)
    [INFO] # Loading ieee.numeric_std(body)
    [INFO] # Loading ieee.std_logic_textio(body)
    [INFO] # Loading ieee.math_real(body)
    [INFO] # Loading lib_max_hold.pkg_max_hold
    [INFO] # Loading std.env(body)
    [INFO] # Loading lib_tb_max_hold.tb_max_hold(beh)
    [INFO] # Loading lib_max_hold.max_hold(rtl)
    [INFO] # set NumericStdNoWarnings 1
    [INFO] # run -all
    [INFO] # End time: 17:16:59 on Nov 30,2015, Elapsed time: 0:00:01
    [INFO] # Errors: 0, Warnings: 0
    ok test_10_random_numbers (chiptools_tests_basic_unit_test.MaxHoldsTestBase)
    Time Elapsed: 0:00:02.097000

Note: When the max_hold.xml project is loaded, additional unit tests from the
**max_hold_tests.py** unit test script will be added. You can selectively run
tests by using the **show_tests**, **add_tests** and **remove_tests** commands
to build a test sequence before executing the **run_tests** commamd.


Advanced Unit Tests
~~~~~~~~~~~~~~~~~~~~

The previous example showed how a simple unit test can be created to test the 
Max Hold component with random stimulus. This approach can be extended to 
produce a large set of tests to thoroughly test the component and provide
detailed information about how it is performing. The **max_hold_tests.py**
file in the Max Hold example folder implements the following tests:

   * max_hold_constant_data_0
   * max_hold_constant_data_1
   * max_hold_constant_data_100
   * max_hold_impulse_test
   * max_hold_ramp_down_test
   * max_hold_ramp_up_test
   * max_hold_random_single_sequence
   * max_hold_random_tests_100bit
   * max_hold_random_tests_128bit
   * max_hold_random_tests_1bit
   * max_hold_random_tests_32bit
   * max_hold_random_tests_8bit
   * max_hold_sinusoid_single_sequence
   * max_hold_sinusoid_test
   * max_hold_square_test

When the tests are run, the Unit Test will also create an output image in the
simulation folder to show a graph of the input data with the model data and
the Max Hold component output data. For example, the max_hold_sinusoid_single_sequence
test produces the following output:

.. image:: max_hold_sinusoid_single_sequence.png

Plots such as these can be easily created with Matplotlib and provide a powerful
diagnostic tool when debugging components.

