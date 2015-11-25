###############
Getting Started
###############

Installing ChipTools
====================

Dependencies
------------

ChipTools has the following requirements:
    * `Python 3.4 <https://www.python.org/downloads/>`_ 
    * `Colorama <https://pypi.python.org/pypi/colorama>`_ *(Optional)* to support coloured terminal text on Windows platforms.


Installation
------------

ChipTools should work on any platform that can run Python 3 and your preferred
FPGA simulation and synthesis tools.

Clone the ChipTools repository to your system (or `download it here <https://github.com/pabennett/chiptools/archive/master.zip>`_):

.. code-block:: bash

    $ git clone https://github.com/pabennett/chiptools.git

Install using the setup.py script provided in the root directory:

.. code-block:: bash

    $ python setup.py install

After installation, the ChipTools command line interface can be started with:

.. code-block:: bash

    $ chiptools


Configuring ChipTools
=====================

.chiptoolsconfig
----------------

ChipTools will automatically detect supported simulation and synthesis tools installed on your system by searching the PATH environment variable.
If you prefer to explicitly point ChipTools to a specific program you can edit
the *.chiptoolsconfig* file which is automatically created by ChipTools in your
HOME directory.

The .chiptoolsconfig file uses *INI* format and contains three sections:

    * **[simulation executables]** Paths to simulation tools
    * **[synthesis executables]** Paths to synthesis tools
    * **[simulation dependencies]** Paths to precompiled libraries to be passed to the chosen simulator when simulating a design.

An example .chiptoolsconfig is given below:

.. code-block:: ini

    [simulation executables]
    modelsim        = C:\modelsim_dlx_10.3d\win32pe

    [synthesis executables]
    ise             = C:\Xilinx\14.7\ISE_DS\ISE\bin\nt\
    quartus         = C:\altera\13.1\quartus\bin\

    [simulation dependencies]
    unisim          = C:\modelsim_dlx_10.3d\unisim
    xilinxcorelib   = C:\Xilinx\modelsim_10_3de_simlibs\xilinxcorelib
    unimacro        = C:\Xilinx\modelsim_10_3de_simlibs\unimacro
    secureip        = C:\Xilinx\modelsim_10_3de_simlibs\secureip


Loading a design
=================

You can use ChipTools in two ways: with a project file or directly as a Python script. Both approaches will be discussed.

As a Python Script
------------------

ChipTools can be imported and used in custom Python scripts, for example the
code block below uses ChipTools to create a simple project and synthesise it
using the Altera Quartus synthesis flow.

.. code-block:: python

    from chiptools.core.project import Project

    # Configure project
    project.add_config('simulation_directory': 'path/to/simulation_directory')
    project.add_config('synthesis_directory': 'path/to/synthesis_directory')
    project.add_config('simulator': 'modelsim')
    project.add_config('synthesiser': 'quartus')
    project.add_config('part': 'EP3C40F484C6')
    # Add constraints
    project.add_constraints('path/to/synthesis_constraints.sdc')
    # Add source files
    project.add_file('path/to/my_top.vhd', library='top')    
    # Synthesise the project (library and entity)
    project.synthesise('top', 'my_top')


Project File
------------

ChipTools supports a simple XML file format that can be used to define source
files and configuration for your project:

.. code-block:: xml

    <!-- Paths in a project file are relative to the project file location -->
    <project>
        <!-- Project Config -->
        <config synthesis_directory='path/to/simulation_directory'/>
        <config simulation_directory='path/to/synthesis_directory'/>
        <config simulator='modelsim'/>
        <config synthesiser='ise'/>
        <config part='xc6slx100t-3-fgg676'/>
        <constraints path='path/to/synthesis_constraints.ucf'/>
        <library name=top>
            <file path=’path/to/my_top.vhd’/>
        </library>
    </project>

The XML file can be loaded into the ChipTools command line interface and operated on interactively.

.. code-block:: bash

    $ chiptools
    (cmd) load_project my_project.xml
    (cmd) synthesise top.my_top

