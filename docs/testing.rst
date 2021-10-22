#######
Testing
#######

The Python Unittest module provides access to a powerful unit testing
framework that can be extended to test FPGA firmware designs. ChipTools
provides the **ChipToolsTest** class which extends **unittest.TestCase** to
allow the automated execution and checking of FPGA firmware simulations. Any
tests that you define should inherit the ChipToolsTest class, which can be
found in **chiptools.testing.testloader**.
ChipTools is re-using the existing Python Unittest framework which means that
the rich ecosystem of testing tools provided by the Python community can now be
used on your FPGA designs.

Before attempting to create your own FPGA unit tests in ChipTools you
should first acquaint yourself with the `Python Unittest framework
<https://docs.python.org/3.9/library/unittest.html>`_ to understand how
the test flow and assertions work.

Test Flow
=========

The Unittest TestCase defines a set of pre-defined functions that are called
during different points in the test, this allows the designer to prepare the
test environment and inputs, execute the tests and then clean up temporary
files and close unused processes. The full detail of the pre-defined setUp/tearDown
functions can be found in the `Python Unittest docs
<https://docs.python.org/3.9/library/unittest.html>`_, a typical test flow is
given below:

    #. setUpModule
    #. setUpClass
    #. setUp
    #. *<user_test_1>*
    #. tearDown
    #. setUp
    #. *<user_test_2>*
    #. tearDown
    #. tearDownClass
    #. tearDownModule

Using ChipToolsTest
===================
    
Assertion Based Tests
---------------------

You may already have some testbenches for a design that use a self-checking
approach that prints messages to the simulator transcript. Incorporating tests
like these into the unit test framework is a simple exercise as ChipTools
provides access to the simulator stdout and stderr streams as well as the
simulator return code:

.. code-block:: python

    import re
    from chiptools.testing.testloader import ChipToolsTest


    class TestSimulatorStdout(ChipToolsTest):
        duration = 0  # Run forever
        library = 'my_test_lib'  # Testbench library
        entity = 'my_testbench'  # Entity to simulate

        def test_simulator_stdout(self):
            # Run the simulation
            return_code, stdout, stderr = self.simulate()

            # Check return code
            self.assertEquals(return_code, 0)

            # Check stdout for 'Error:' using regex
            errors = re.search('.*Error:.*', stdout)
            self.assertIsNone(errors)

This is one of the simplest tests you can define although it is also fairly
limited. ChipTools allows you to make this approach slightly more flexible by
providing a way to override generics/parameters before the test is run:

.. code-block:: python

    import re
    from chiptools.testing.testloader import ChipToolsTest


    class TestSimulatorStdout(ChipToolsTest):
        duration = 0  # Run forever
        library = 'my_test_lib'  # Testbench library
        entity = 'my_testbench'  # Entity to simulate
        generics = {'width' : 3) # Default generic width to 3

        def check_simulator_stdout(self):
            # Run the simulation
            return_code, stdout, stderr = self.simulate()

            # Check return code
            self.assertEquals(return_code, 0)

            # Check stdout for 'Error:' using regex
            errors = re.search('.*Error:.*', stdout)
            self.assertIsNone(errors)

        def test_width_5(self):
            self.generics['width'] = 5
            self.check_simulator_stdout()

        def test_width_12(self):
            self.generics['width'] = 12
            self.check_simulator_stdout()

By using simple test cases like these you are able to re-use your existing
self-checking testbenches and define new test cases for them by modifying
parameters/generics or stimulus files through ChipTools.

Model Based Tests
-----------------

One of the big benefits of using Python is that you have access to a wide
range of open source libraries that can assist with test development; for
example you could use Python to model the expected behavior of a system such
as a signal processing pipeline or cryptographic core. You can incorporate
such models into the ChipTools test framework and use them to generate
sets of stimulus which can be fed into your testbench, and you can then check
the simulation response against the model response to determine whether or not
the implementation is correct:


.. code-block:: python

    import numpy as np
    from chiptools.testing.testloader import ChipToolsTest

    class TestFastFourierTransform(ChipToolsTest):

        duration = 0  # Run forever
        library = 'my_test_lib'  # Testbench library
        entity = 'my_testbench'  # Entity to simulate
        N = 1024  # Our fixed FFT size
        generics = {'n' : N)

        def test_noise(self):
            values = np.random.randint(0, 2**16-1, self.N)
            self.run_fft_simulation(values)

        def test_sinusoid(self):
            f = 10
            values = np.sin(2*np.pi*f*np.linspace(0, 1, self.N))
            self.run_fft_simulation(values)

        def run_fft_simulation(self, values):
            out_path = os.path.join(self.simulation_root, 'fft_out.txt')
            in_path = os.path.join(self.simulation_root, 'fft_in.txt')

            # Create the stimulus file
            with open(in_path, 'w') as f:
                for value in values:
                    f.write('{0}\n'.format(value))

            # Run the simulation
            return_code, stdout, stderr = self.simulate()

            # Check return code
            self.assertEquals(return_code, 0)

            # Open the simulator response file that our testbench created.
            with open(out_path, 'r') as f:
                actual = [float(x) for x in f.readlines()]

            # Run the FFT model to generate the expected response
            expected = np.fft.fft(values)

            # (compare our actual and expected values)
            self.compare_fft_response(actual, expected) 

The example above demonstrates how you might check a common signal processing
application using a Fast Fourier Transform. By using this approach a large
suite of stimulus can be created to thoroughly check the functionality of the
design.

External Test Runners
---------------------

Perhaps you would like to set up a continous integration system such as
`Jenkins <https://www.jenkins.io//>`_ to execute your tests on a nightly basis.
ChipTools makes this easy to do by allowing your unit tests to be run using
external test runners like Nosetests or Pytest. To enable a unit test to be run
using an external test runner simply add a *project* attribute to the test
class which provides a path to a valid ChipTools XML project file defining the
files and libraries required by the simulation environment:


.. code-block:: python

    import numpy as np
    import os
    from chiptools.testing.testloader import ChipToolsTest

    class TestFastFourierTransform(ChipToolsTest):

        duration = 0
        library = 'my_test_lib'
        entity = 'my_testbench'
        base = os.path.dirname(__file__)
        project = os.path.join(base, 'my_project.xml')

Test cases that do not provide a *project* attribute will not be able to be
run using an external runner.

ChipToolsTest Class Detail
==========================

.. currentmodule:: chiptools.testing.testloader
.. autoclass:: ChipToolsTest
    :members:
    :undoc-members:
