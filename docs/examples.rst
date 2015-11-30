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
maximum value of an input sequence until it is reset. For example if such a 
component were to be fed an oscillating input with steadily increasing
amplitude we would expect the following result:

.. image:: max_hold_demo.png

This example will show you how you can use ChipTools to generate stimulus, 
check responses, manage test reports and generate bit files for this component.


Project Creation
----------------

Before ChipTools can use the files in this project we must first either create
a ChipTools XML project file or write a Python script that imports ChipTools
and then adds the source files directly. The Max Hold example directory holds
the following files: 

    * **Project Files:**

        * max_hold.xml
        * max_hold_project.py
    * **Unit Tests:**

        * max_hold_tests.py
    * **Source Files:**

        * max_hold.vhd
        * pkg_max_hold.vhd
        * tb_max_hold.vhd 
    * **Constraints:**

        * max_hold.ucf

The **max_hold.xml** file provides an example ChipTools XML file for the 
project and the **max_hold_project.py** file provides an example Python script.

Python Script
~~~~~~~~~~~~~

To use ChipTools directly in a script the Project class must first be imported:

.. code-block:: python

    from chiptools.core.project import Project

A new Project can now be created:

.. code-block:: python

    # Create a new Project
    project = Project()

Project objects hold all the information about the source files for an FPGA
project as well as configuration data such as which FPGA part is being
targeted. To configure the project we can use the **add_config** or
**add_config_dict** methods:

.. code-block:: python

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

Source files can be added to a Project through the **add_file** or **add_files**
methods:

.. code-block:: python

    # Source files for the max_hold component are added to the project. The Project
    # 'add_file' method accepts a file path and library name, if no library is
    # specified it will default to 'work'.
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

Constraints and unit tests can also be added to the Project using similar 
methods:

.. code-block:: python

    # The design requires constraints before it can be synthesised. Add the
    # constraints using the 'add_constraints' Project method.
    project.add_constraints('max_hold.ucf')

    # Some unit tests have been written for the max_hold component and stored in
    # max_hold_tests.py. The Project class provides an 'add_unittest' method for
    # adding unit tests to the project, it expects a path to the unit test file.
    project.add_unittest('max_hold_tests.py')

The complete Python script **max_hold_project.py** creates and configures a
Project before running the unit test suite and then finally synthesising the 
design.

ChipTools XML Project
~~~~~~~~~~~~~~~~~~~~~

The pre-written project file **max_hold.xml** defines the source file paths
and project configuration for the Max Hold component:

.. code-block:: xml

    <project>
        <config simulation_directory='simulation'/>
        <config synthesis_directory='synthesis'/>
        <config simulator='modelsim'/>
        <config synthesiser='ise'/>
        <config part='xc6slx9-csg324-2'/>

        <unittest path='max_hold_tests.py'/>
        <constraints path='max_hold.ucf'/>
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

This project file defines the same configuration as the **max_hold_project.py**
script; to use it open a terminal in the Max Hold example directory and invoke
ChipTools:

.. code-block:: bash

    $ chiptools

The project can then be loaded using the ChipTools command line interface:

.. code-block:: bash

    (cmd) load_project max_hold.xml

Various operations can be performed on the Project once loaded, type 'help' for
a full listing. To make sure the source files have no syntax errors we can issue
the 'compile' command to compile each source file using the selected simulator:

.. code-block:: bash

    (Cmd) compile
    [INFO] ...adding library: lib_max_hold
    [INFO] ...compiling max_hold.vhd (FileType.VHDL) into library lib_max_hold
    [INFO] ...compiling pkg_max_hold.vhd (FileType.VHDL) into library lib_max_hold
    [INFO] ...adding library: lib_tb_max_hold
    [INFO] ...compiling tb_max_hold.vhd (FileType.VHDL) into library lib_tb_max_hold
    [INFO] ...saving cache file
    [INFO] ...done
    [INFO] 3 file(s) processed in 3.753499984741211s
    (Cmd)

Testing
-------

To test the Max Hold component an accompanying VHDL testbench, 
*tb_max_hold.vhd*, is used to feed the component data from a stimulus input
text file and record the output values in an output text file. By using 
stimulus input files and response output files we gain the freedom to use a
language of our choice to generate stimulus and check outputs.

Testbench Stimulus File Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The testbench expects a file called **input.txt** to be present in the
simulation folder and each line of the file should have the following format:

    * Binary 8bit opcode (either 00000000 for reset or 00000001 for write)
    * (*optional*) Binary Nbit data to write (only when write opcode is used)

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
the testbench that is to be simulated:

.. code-block:: python

    class MaxHoldsTestBase(ChipToolsTest):
        # Specify the duration your test should run for in seconds.
        # If the test should run until the testbench aborts itself use 0.
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
    * Invoke simulator using the set-up attributes.
    * Execute test case (function with a 'test' prefix).
    * Execute simulatorTearDown function if defined.

The **simulationSetup** function should be overloaded to run any 'preparation'
code your testbench may require before it is executed. For testing the Max Hold
component we can use this function to write the input file to the testbench 
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

The above example test is saved in **basic_unit_test.py** in the Max Hold 
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

