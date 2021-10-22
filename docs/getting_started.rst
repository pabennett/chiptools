###############
Getting Started
###############

Installing ChipTools
====================

Dependencies
------------

ChipTools has the following requirements:
    * `Python 3.6+ <https://www.python.org/downloads/>`_
    * `Colorama <https://pypi.org/project/colorama/>`_ *(Optional)* to support coloured terminal text on Windows platforms.


Installation
------------

ChipTools should work on any platform that can run Python 3 and your preferred
FPGA simulation and synthesis tools.

Clone the ChipTools repository to your system (or download the `latest tag <https://github.com/pabennett/chiptools/tags>` or master tarball from github):

.. code-block:: bash

    $ git clone --recursive https://github.com/pabennett/chiptools.git

Install using the setup.py script provided in the root directory:

.. code-block:: bash

    $ cd chiptools
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

The .chiptoolsconfig file uses *INI* format and contains the following:

    * **[simulation executables]** Paths to simulation tools
    * **[synthesis executables]** Paths to synthesis tools
    * **[<toolname> simulation libraries]** Paths to precompiled libraries for the given *<toolname>*

An example .chiptoolsconfig is given below:

.. code-block:: ini

    [simulation executables]
    modelsim        = C:\modelsim_dlx_10.3d\win32pe

    [synthesis executables]
    ise             = C:\Xilinx\14.7\ISE_DS\ISE\bin\nt\
    quartus         = C:\altera\13.1\quartus\bin\

    [modelsim simulation libraries]
    unisim          = C:\modelsim_dlx_10.3d\unisim
    xilinxcorelib   = C:\Xilinx\modelsim_10_3de_simlibs\xilinxcorelib
    unimacro        = C:\Xilinx\modelsim_10_3de_simlibs\unimacro
    secureip        = C:\Xilinx\modelsim_10_3de_simlibs\secureip

Tool names under the simulation or synthesis executables categories will only
be used if a tool wrapper plugin is available. A list of available
plugins can be obtained by launching ChipTools and issuing the **plugins**
command.

Loading a design
=================

Project data can be loaded into ChipTools in two ways: using a project file or
by importing ChipTools in a Python script and using the **Project** class
directly:

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

