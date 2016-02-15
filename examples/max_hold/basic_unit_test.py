import os
import random
import logging

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Import the ChipTools base test class, our test classes should be derived from
# the ChipToolsTest class (which is derived from unittest.TestCase)
from chiptools.testing.testloader import ChipToolsTest

# The logging system is already configured by ChipTools, any messages you print
# here will be formatted and displayed using the ChipTools logger config.
log = logging.getLogger(__name__)


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

    def setUp(self):
        """Place any code that is required to prepare simulator inputs in this
        method."""
        # Set the paths for the input and output files using the
        # 'simulation_root' attribute as the working directory
        self.input_path = os.path.join(self.simulation_root, 'input.txt')
        self.output_path = os.path.join(self.simulation_root, 'output.txt')

    def tearDown(self):
        """Insert any cleanup code to remove generated files in this method."""
        #os.remove(self.input_path)
        #os.remove(self.output_path)
        pass

    def run_random_data_test(self, n):

        # Generate a list of n random integers
        self.values = [random.randint(0, 2**32-1) for i in range(n)]

        # Write the values to the testbench input file
        with open(self.input_path, 'w') as f:
            for value in self.values:
                f.write(
                    '{0} {1}\n'.format(
                        '0',  # Reset status (0) 
                        bin(value)[2:].zfill(32),  # write 32bit data
                    )
                )

        # Run the simulation
        return_code, stdout, stderr = self.simulate()
        self.assertEqual(return_code, 0)

        # Read the simulation output
        output_values = []
        with open(self.output_path, 'r') as f:
            data = f.readlines()
        for valueIdx, value in enumerate(data):
            # testbench response
            output_values.append(int(value, 2))  # Binary to integer

        # Use Python to work out the expected result from the original imput
        max_hold = [
            max(self.values[:i+1]) for i in range(len(self.values))
        ]

        # Compare the expected result to what the Testbench returned:
        self.assertListEqual(output_values, max_hold)

    def test_10_random_integers(self):
        """Check the Max hold component using 10 random integers."""
        self.run_random_data_test(10)

    def test_100_random_integers(self):
        """Check the Max hold component using 100 random integers."""
        self.run_random_data_test(100)
