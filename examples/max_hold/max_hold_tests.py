"""
This Python file implements Unit Tests for the 'max_hold' component, a basic
component that always outputs the maximum value from the input sequence until
it is reset. These tests serve as an example on how to write Python Unit Tests
for a testbench that expects a stimulus file input and generates a response
file output - we use Python to generate the stimulus inputs and then model
the expected output which is then compared to the response file. This approach
can be used for more complex systems and is particularly useful for signal
processing pipelines.

In addition to checking the simulation outputs, this unit test also generates
Matplotlib plots of the stimulus input and expected/actual outputs if
Matplotlib is available on your system.
"""

import os
import random
import logging
import re
import math

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
try:
    import seaborn
except ImportError:
    # We dont care if seaborn isn't installed - it just makes plots prettier.
    pass

# Import the ChipTools base test class, our test classes should be derived from
# the ChipToolsTest class (which is derived from unittest.TestCase)
from chiptools.testing.testloader import ChipToolsTest

# The logging system is already configured by ChipTools, any messages you print
# here will be formatted and displayed using the ChipTools logger config.
log = logging.getLogger(__name__)

# Opcodes used by the Max Hold testbench file reader
reset_opcode = 0
write_opcode = 1


def get_random_data(data_width, sequence_lengths):
    return [
        [
            random.randint(0, 2**data_width-1) for i in range(l)
        ] for l in sequence_lengths
    ]


class MaxHoldTests(ChipToolsTest):
    """
    The MaxHoldsTests class is a place for us to store common properties of
    the tests we would like to run on the Max Hold component. In here we define
    the name of the entity and architecture, functions to read and write files
    and a checker function that compares the output file with a Python model
    that has been given the same stimulus. Our tests will extend this class.
    As your tests grow more complex could move common functions such as these
    into a 'test library' which can be imported by your unit tests.
    """
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

    def run_simulation(self, values, data_width):
        """Prepare the simulation environment and run the simulation."""
        # Override the 'data_width' generic with the test setting
        self.generics['data_width'] = data_width
        # Write the stimulus file to be used by the testbench
        self.write_stimulus(self.input_path, values, data_width)
        # Run the simulation
        return_code, stdout, stderr = self.simulate()
        self.assertEqual(return_code, 0)

    def tearDown(self):
        """Insert any cleanup code to remove generated files in this method."""
        os.remove(self.input_path)
        os.remove(self.output_path)

    def write_stimulus(self, path, values, data_width):
        """
        Write the values array to a stimulus file. The values array is a 2D
        list containing lists of integers. After each integer list the
        component will be reset and the maximum output recorded, this allows us
        to test the reset functionality of the component too.
        """
        with open(path, 'w') as f:
            for sequence in values:
                # Reset the component at the beginning of a new sequence.
                f.write('{0}\n'.format(bin(reset_opcode)[2:].zfill(4)))
                # Write each value in the sequence to the stimulus file
                for value in sequence:
                    f.write(
                        '{0} {1}\n'.format(
                            bin(write_opcode)[2:].zfill(4),
                            bin(value)[2:].zfill(data_width),
                        )
                    )

    def read_output(self, path):
        output_values = []
        with open(path, 'r') as f:
            data = f.readlines()
        for valueIdx, value in enumerate(data):
            # testbench response
            output_values.append(int(value, 2))  # Binary to integer
        return output_values

    def sequence_max(self, sequence):
        tracking_max = []
        for subsequence in sequence:
            seq_max = 0
            for value in subsequence:
                seq_max = max(value, seq_max)
                tracking_max.append(seq_max)
        return tracking_max

    def check_output(self, path, input_values, testname):
        """
        Read the reported maximum values from the response file and compare
        them with what the Python model expects given the same input. We use
        Python unittest assertion methods here to check our expectations and
        flag any failures.
        """
        # Replace empty subsequences in value sequence with a zero, prefix
        # all subsequences with a zero value to represent the reset state.
        input_values = [
            [0] + seq if len(seq) > 0 else [0] for seq in input_values
        ]
        # Get the actual values from the testbench output file
        actual = self.read_output(path)
        # Get the expected maximum values from the value sequence
        expected = self.sequence_max(input_values)
        log.info("Got {0} actual values".format(len(actual)))
        log.info("Got {0} expected values".format(len(expected)))
        log.info("Plotting data...")
        # Save the actual and expected values as a plot for reference
        if plt is not None:
            self.save_figure(actual, expected, input_values, testname)
        # Compare our actual values with our expected values
        log.info("Comparing data values...")
        self.assertEqual(len(actual), len(expected))
        for valIdx, val in enumerate(actual):
            # Per element comparison checking, you could use assertListEqual
            # but it can be slow for large lists
            # (https://bugs.python.org/issue19217)
            self.assertEqual(val, expected[valIdx])
        log.info("...done")

    def save_figure(
        self, actual, expected, input_values, testname, fontsize=10
    ):
        """
        Save a plot of the actual and expected values recorded during the test.
        Figures are a useful reference to see why a test might be failing.
        """
        fig = plt.figure(0, figsize=(10, 7.5))
        # Plot the actual maximum and expected maximum values together
        plt.title(
            'Actual and Expected Results for \'{0}\''.format(testname),
            fontsize=fontsize
        )
        plt.xlabel('Value Index', fontsize=fontsize)
        plt.ylabel('Value', fontsize=fontsize)
        yvals = [v for sl in input_values for v in sl]
        plt.plot(
            range(len(actual)),
            actual,
            'r:',
            label='Actual values',
            alpha=0.8
        )
        plt.plot(
            range(len(yvals)),
            expected,
            'g--',
            label='Expected values',
            alpha=0.8
        )
        plt.plot(range(len(yvals)), yvals, 'b-', label='Input', alpha=0.5)
        plt.legend(loc='best', shadow=True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.simulation_root, testname + '.png'))
        plt.close(fig)

    def generic_random_data_test(self, data_width, testname):
        # 10 sequences of random length (between 0 and 400 integers)
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        # Generate the values for the test
        values = get_random_data(data_width, sequence_lengths)
        self.generic_data_test(data_width, values, testname)

    def generic_constant_data_test(self, data_width, data, testname):
        # 10 sequences of random length (between 0 and 400 integers)
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        # Generate the values for the test
        values = [[data for i in range(l)] for l in sequence_lengths]
        self.generic_data_test(data_width, values, testname)

    def generic_data_test(self, data_width, values, testname):
        self.run_simulation(values, data_width)
        # Use the output checker to validate the output
        self.check_output(self.output_path, values, testname)
        # You can also access the simulator stdout (transcript) and search it
        # for patterns, this is useful if your testbench has built in assertion
        # checking.
        self.assertIsNone(re.search('.*Error:.*', self.sim_stdout))

    def test_max_hold_random_32bit(self):
        """Test the max hold function with 32bit random data."""
        self.generic_random_data_test(32, 'test_max_hold_random_32bit')

    def test_max_hold_random_100bit(self):
        """Test the max hold function with 100bit random data."""
        self.generic_random_data_test(100, 'test_max_hold_random_100bit')

    def test_max_hold_random_128bit(self):
        """Test the max hold function with 128bit random data."""
        self.generic_random_data_test(128, 'test_max_hold_random_128bit')

    def test_max_hold_random_1bit(self):
        """Test the max hold function with 1bit random data."""
        self.generic_random_data_test(1, 'test_max_hold_random_1bit')

    def test_max_hold_random_8bit(self):
        """Test the max hold function with 8bit random data."""
        self.generic_random_data_test(8, 'test_max_hold_random_8bit')

    def test_max_hold_constant_data_1(self):
        """Test the max hold function with constant 1 data."""
        self.generic_constant_data_test(32, 1, 'test_max_hold_constant_data_1')

    def test_max_hold_constant_data_100(self):
        """Test the max hold function with constant 100 data."""
        self.generic_constant_data_test(
            32, 100, 'test_max_hold_constant_data_100'
        )

    def test_max_hold_constant_data_0(self):
        """Test the max hold function with constant 0 data."""
        self.generic_constant_data_test(32, 0, 'test_max_hold_constant_data_0')

    def test_max_hold_ramp_up(self):
        """Test the max hold function with positive gradient ramps."""
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        values = [
            [i for i in range(l)] for l in sequence_lengths
        ]
        self.generic_data_test(32, values, 'test_max_hold_ramp_up')

    def test_max_hold_ramp_down(self):
        """Test the max hold function with negative gradient ramps."""
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        values = [
            [l-i for i in range(l)] for l in sequence_lengths
        ]
        self.generic_data_test(32, values, 'test_max_hold_ramp_down')

    def test_max_hold_impulse(self):
        """Test the max hold function with impulses."""
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        values = [
            [[0, l][i == 0] for i in range(l)] for l in sequence_lengths
        ]
        self.generic_data_test(32, values, 'test_max_hold_impulse')

    def test_max_hold_sinusoid(self):
        """Test the max hold function with sinusoids."""
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        values = [
            [
                int(
                    i/l * (2**10-1) * (math.sin(8*math.pi*(i/l)) + 1)
                ) for i in range(l)
            ] for l in sequence_lengths
        ]
        self.generic_data_test(32, values, 'test_max_hold_sinusoid')

    def test_max_hold_square(self):
        """Test the max hold function with square waves."""
        sequence_lengths = [random.randint(0, 400) for i in range(10)]
        values = [
            [
                int((2**8-1) * (i % 2)) for i in range(l)
            ] for l in sequence_lengths
        ]
        self.generic_data_test(32, values, 'test_max_hold_square')

    def test_max_hold_sinusoid_single_sequence(self):
        """Test the max hold function with a single sinusoid sequence."""
        sequence_lengths = [200]
        values = [
            [
                int(
                    i/l * (2**10-1) * (math.sin(8*math.pi*(i/l)) + 1)
                ) for i in range(l)
            ] for l in sequence_lengths
        ]
        self.generic_data_test(
            32, values, 'test_max_hold_sinusoid_single_sequence'
        )

    def test_max_hold_random_single_sequence(self):
        """Test the max hold function with a single random sequence."""
        sequence_lengths = [200]
        data_width = 32
        values = get_random_data(data_width, sequence_lengths)
        self.generic_data_test(
            data_width, values, 'test_max_hold_random_single_sequence'
        )
