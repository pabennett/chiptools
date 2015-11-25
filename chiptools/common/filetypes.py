import os
import re
from enum import Enum
import logging

log = logging.getLogger(__name__)


class FileType(Enum):
    VHDL = 1  # VHDL
    Verilog = 2  # Verilog
    SystemVerilog = 3  # Verilog (SV)
    NGCNetlist = 4  # Netlist
    TCL = 5  # TCL
    UCF = 6  # Universal constraints format
    SDC = 7  # Synopsis design constraints

# Mapping of file extensions to FileType objects
fileExtensionsLookup = {
    '.vhd': FileType.VHDL,
    '.vhdl': FileType.VHDL,
    '.v': FileType.Verilog,
    '.sv': FileType.SystemVerilog,
    '.ngc': FileType.NGCNetlist,
    '.tcl': FileType.TCL,
    '.sdc': FileType.SDC,
}


class ProjectAttributes:
    # XML nodes identify opening tags that can be used in the file
    XML_NODE_PROJECT = 'project'
    XML_NODE_LIBRARY = 'library'
    XML_NODE_FILE = 'file'
    XML_NODE_CONFIG = 'config'
    XML_NODE_COMMENT = '#comment'
    XML_NODE_TEXT = '#text'
    XML_NODE_CONSTRAINTS = 'constraints'
    XML_NODE_GENERIC = 'generic'
    # XML attributes identify parameters that can be applied to XML nodes.
    XML_ATTRIBUTE_NAME = 'name'
    XML_ATTRIBUTE_PATH = 'path'
    XML_ATTRIBUTE_UNITTEST = 'unittest'
    XML_ATTRIBUTE_PREPROCESSOR = 'preprocessor'
    XML_ATTRIBUTE_SYNTHESIS = 'synthesise'
    # These XML attributes are required configuration attributes that control
    # which tools and directories are used by the framework. They must be
    # present in the project file.
    ATTRIBUTE_SIM_DIR = 'simulation_directory'
    ATTRIBUTE_SYNTH_DIR = 'synthesis_directory'
    ATTRIBUTE_SIM_TOOL = 'simulator'
    ATTRIBUTE_SYNTH_TOOL = 'synthesiser'
    ATTRIBUTE_SYNTH_PART = 'part'
    ATTRIBUTE_REPORTER = 'reporter'
    # Additional tool-specific arguments can be attached to a config object in
    # the XML file to allow fine tweaking of the simulation or synthesis flows.
    ATTRIBUTE_MODELSIM_SIMULATE = 'args_modelsim_simulate'
    ATTRIBUTE_MODELSIM_COMPILE = 'args_modelsim_compile'
    ATTRIBUTE_ISE_MAP = 'args_ise_map'
    ATTRIBUTE_ISE_PAR = 'args_ise_par'
    ATTRIBUTE_ISE_XST = 'args_ise_xst'
    ATTRIBUTE_ISE_PROMGEN = 'args_ise_promgen'
    ATTRIBUTE_ISE_NGDBUILD = 'args_ise_ndgbuild'
    ATTRIBUTE_ISE_BITGEN = 'args_ise_bitgen'
    ATTRIBUTE_ISE_XFLOW = 'args_ise_xflow'

    # Additional tool arguments can be attached to File objects by supplying
    # attributes using the naming convention:
    #   args_toolname_flowstagenname
    # These attributes will be stored with the file so that the additional
    # arguments can be used by the relevent tool and flow stage if it is
    # invoked on the file.
    XML_ADDITIONAL_TOOL_ARGS_RE = re.compile(
        'args_([A-Z,a-z]+)_([A-Z,a-z]+)'
    )


class File(object):
    """
    The File object contains properties of a design source file that has been
    loaded from the project XML file.
    """

    def __init__(self, library, **kwargs):
        # The library to which this file belongs
        self.library = library
        # MD5 sum for change detection
        self.md5 = ''
        # A processed testsuite that can be run on this file, this is set by
        # the test manager when running tests.
        self.testsuite = None
        # The path to this source file
        self.path = kwargs[ProjectAttributes.XML_ATTRIBUTE_PATH]
        # A flag to indicate whether or not this file should be included for
        # synthesis. It not specified it will default to True.
        self.synthesise = kwargs.get(
            ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS,
            True
        )
        self.synthesise = True if self.synthesise is None else self.synthesise
        # Path to a Python unittest shim that can be used to run tests on this
        # file.
        self.testsuite_path = kwargs.get(
            ProjectAttributes.XML_ATTRIBUTE_UNITTEST,
            None
        )
        # The preprocessor is a path to a Python module containing a
        # preprocessor object that can edit the associated source file before
        # it is passed to synthesis.
        self.preprocessor = kwargs.get(
            ProjectAttributes.XML_ATTRIBUTE_PREPROCESSOR,
            None
        )
        # Automatically discover the filetype from the extension
        fileName, fileExtension = os.path.splitext(self.path)
        fileExtension = fileExtension.strip(' ')  # Remove trailing whitespace
        self.fileType = fileExtensionsLookup.get(fileExtension, FileType.VHDL)
        # Search through the keyword arguments for any attributes that match
        # the XML_ADDITIONAL_TOOL_ARGS_RE search pattern and store these as
        # additional tool arguments
        self.optionalToolArgs = {}
        for k, v in kwargs.items():
            match = ProjectAttributes.XML_ADDITIONAL_TOOL_ARGS_RE.match(k)
            if match:
                try:
                    toolName = match.group(1)
                    flowName = match.group(2)
                except IndexError:
                    # The attribute matched but did not return enough match
                    # groups.
                    log.warning(
                        'Ignoring attribute {0} on file {1}'.format(
                            k,
                            self.path
                        )
                    )
                    continue
                if toolName not in self.optionalToolArgs:
                    self.optionalToolArgs[toolName] = {}
                self.optionalToolArgs[toolName][flowName] = v
                log.debug(
                    'Added attribute {0} with value {2} to file {1}'.format(
                        k,
                        self.path,
                        v
                    )
                )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def get_tool_arguments(self, toolName, flowName):
        """
        Return the optional tool arguments attached to this file for the given
        toolname and flowname. If the tool or flow are not present in the
        optional arguments then return an empty string.
        """
        return self.optionalToolArgs.get(toolName, {}).get(flowName, '')


class Constraints(object):
    """The constraints object provides a container for constraints files"""
    def __init__(self, **kwargs):
        self.path = kwargs[ProjectAttributes.XML_ATTRIBUTE_PATH]
        self.fileType = FileType.TCL
        fileName, fileExtension = os.path.splitext(self.path)
        fileExtension = fileExtension.strip(' ')
        if fileExtension in fileExtensionsLookup.keys():
            self.fileType = fileExtensionsLookup[fileExtension]
