##################
Introduction
##################

What is ChipTools?
==================

ChipTools is a build and verification framework for FPGA designs.

What can it do?
===============

ChipTools aims to simplify the process of building and testing FPGA designs by
providing a consistent interface to vendor applications and automating simulation and synthesis flows.

Key features
------------

    * Seamlessly switch between vendor applications without having to modify build scripts or restructure project files.
    * Quickly design and deploy testbenches with Python based stimulus generation and checking.
    * Hook directly into the Python Unittest framework to allow automated execution and reporting of your unit test suite.
    * Automatically check and archive build outputs.
    * Preprocess and update files during a build to enable features such as automatically updating version registers.
    * Build and test projects using one procedure to reduce the learning curve for new starters and reduce the burden on code reviewers.
    * Free and open source under the `Apache 2.0 License <https://www.apache.org/licenses/LICENSE-2.0>`_.

Supported Tools
===============

The following tools are currently supported, or support will be added in the 
near future. 

Simulation Tools
----------------

* Modelsim (tested with 10.3)
* ISIM (tested with 14.7)
* GHDL (tested with 0.31)

Synthesis Tools
---------------

* Xilinx ISE (tested with 14.7)
* Quartus (tested with 13.1)
* Vivado (tested with 2015.4)
* Lattice (*in progress*)
