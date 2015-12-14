##############
Project Format
##############

ChipTools supports an XML project format that is intended to allow the 
designer to express an FPGA project configuration in a tool-agnostic manner.
This means that the same project file should work for different synthesis or
simulation tools when used with ChipTools. Certain *tool specific* data is
unavoidable in FPGA designs, so the project format allows argument-passing to
specific tools or inclusion of tool-specific data such as constraints or
netlists without affecting other tools that may be supported.

The *XmlProjectParser* class implements the XML parser for ChipTools project
files. It can be used either through the ChipTools command line interface via
the load project command, or via a Python script by importing it directly.

Command line interface:

.. code-block:: bash

    $ chiptools
    (cmd) load_project my_project.xml

Python import:

.. code-block:: python

    from chiptools.core.project import Project
    from chiptools.parsers.xml_project import XmlProjectParser

    my_project = Project()
    XmlProjectParser.load_project('my_project.xml', my_project)

.. currentmodule:: chiptools.parsers.xml_project
.. autoclass:: XmlProjectParser