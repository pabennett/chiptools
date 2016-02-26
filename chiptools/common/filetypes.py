import os
import re
import sys
import logging
from chiptools.common import utils
import xml

log = logging.getLogger(__name__)

filetypes = [
    'Unknown',
    'VHDL',             # VHDL
    'Verilog',          # Verilog
    'SystemVerilog',    # Verilog (SV)
    'NGCNetlist',       # Netlist
    'TCL',              # TCL
    'UCF',              # Universal constraints format
    'SDC',              # Synopsis design constraints
    'Python',
    'VivadoIp',
    'VivadoXDC',
]

try:
    from enum import Enum
    FileType = Enum('FileType', ' '.join(f for f in filetypes))
except ImportError:
    # Enum module not supported, roll our own.
    def enum(*sequence, **names):
        enums = dict(zip(sequence, range(len(sequence))), **names)
        return type('Enum', (), enums)
    FileType = enum(*filetypes)

# Mapping of file extensions to FileType objects
fileExtensionsLookup = {
    # Common VHDL source extensions
    '.vhd': FileType.VHDL,
    '.vhdl': FileType.VHDL,
    # Common Verilog source extentions
    '.v': FileType.Verilog,
    '.vl': FileType.Verilog,
    '.sv': FileType.SystemVerilog,
    # Netlist Extensions
    '.ngc': FileType.NGCNetlist,
    # Constraint/Script Extensions
    '.tcl': FileType.TCL,
    '.sdc': FileType.SDC,
    # Python
    '.py': FileType.Python,
    # Vivado/ISE Extentions
    '.xci': FileType.VivadoIp,
    '.xco': FileType.VivadoIp,
    '.xdc': FileType.VivadoXDC,
    '.ucf': FileType.UCF,
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
    XML_NODE_UNITTEST = 'unittest'
    # XML attributes identify parameters that can be applied to XML nodes.
    ATTRIBUTE_NAME = 'name'
    ATTRIBUTE_PATH = 'path'
    ATTRIBUTE_FLOW = 'flow'
    ATTRIBUTE_PREPROCESSOR = 'preprocessor'
    ATTRIBUTE_SYNTHESIS = 'synthesise'
    # These XML attributes are required configuration attributes that control
    # which tools and directories are used by the framework. They must be
    # present in the project file.
    ATTRIBUTE_SIM_DIR = 'simulation_directory'
    ATTRIBUTE_SYNTH_DIR = 'synthesis_directory'
    ATTRIBUTE_SIM_TOOL = 'simulator'
    ATTRIBUTE_SYNTH_TOOL = 'synthesiser'
    ATTRIBUTE_SYNTH_PART = 'part'
    ATTRIBUTE_REPORTER = 'reporter'

    # Additional tool arguments can be attached to File objects by supplying
    # attributes using the naming convention:
    #   args_toolname_flowstagenname
    # These attributes will be stored with the file so that the additional
    # arguments can be used by the relevent tool and flow stage if it is
    # invoked on the file.
    XML_ADDITIONAL_TOOL_ARGS_RE = re.compile(
        'args_([A-Z,a-z]+)_([A-Z,a-z]+)'
    )
    @staticmethod
    def cast_attributes_to_dict(attributes):
        """
        Ensure that attributes is a dictionary. Casts None to an empty dict
        and casts an xml.dom.minidom.NamedNodeMap to a dict.
        """
        if attributes is None:
            return {}
        elif isinstance(attributes, xml.dom.minidom.NamedNodeMap):
            attributes = dict(attributes.items())
        return attributes

    @staticmethod
    def process_attributes(attributes, root):
        """Return the attributes as a dictionary if any attributes exist.
        Attributes will be pre-processed according to the NODE_PROCESSOR
        function dictionary. The returned dictionary will contain AT LEAST
        the keys present in NODE_PROCESSOR, additional optional keys may
        also be present.

        Attributes can be a dictionary or an XML NamedNodeMap.
        """
        attributes = ProjectAttributes.cast_attributes_to_dict(attributes)
        for attribute, function in NODE_PROCESSOR.items():
            # If the attribute exists process it using the processor function
            # otherwise insert a default value
            if attribute in attributes:
                attributes[attribute] = function(
                    attributes[attribute],
                    root
                )
            else:
                # Ensure the attribute is initialised to its default
                attributes[attribute] = FILE_DEFAULTS[attribute]
        return attributes

    @staticmethod
    def get_processed_attribute(attribute, root, name):
        """
        Process the given attribute according to the functions in the
        NODE_PROCESSOR dictionary using the name as a key and the root as the
        project root.
        """
        if name in NODE_PROCESSOR:
            return NODE_PROCESSOR[name](attribute, root)
        return FILE_DEFAULTS.get(name, None)

# Process each of the file attributes using the following functions
NODE_PROCESSOR = {
    ProjectAttributes.ATTRIBUTE_PATH: utils.relative_path_to_abs,
    ProjectAttributes.ATTRIBUTE_SIM_DIR: utils.relative_path_to_abs,
    ProjectAttributes.ATTRIBUTE_SYNTH_DIR: utils.relative_path_to_abs,
    ProjectAttributes.ATTRIBUTE_PREPROCESSOR: utils.relative_path_to_abs,
    ProjectAttributes.ATTRIBUTE_REPORTER: utils.relative_path_to_abs,
    ProjectAttributes.ATTRIBUTE_SYNTHESIS:
        lambda x, root: x.lower() != 'false',
    ProjectAttributes.ATTRIBUTE_SIM_TOOL: lambda x, root: x,
    ProjectAttributes.ATTRIBUTE_SYNTH_TOOL: lambda x, root: x,
    ProjectAttributes.ATTRIBUTE_SYNTH_PART: lambda x, root: x,
}

# Default node attributes for file objects
FILE_DEFAULTS = {
    ProjectAttributes.ATTRIBUTE_PATH: None,
    ProjectAttributes.ATTRIBUTE_PREPROCESSOR: None,
    ProjectAttributes.ATTRIBUTE_REPORTER: None,
    ProjectAttributes.ATTRIBUTE_SYNTHESIS: None,
    ProjectAttributes.ATTRIBUTE_SIM_DIR: None,
    ProjectAttributes.ATTRIBUTE_SYNTH_DIR: None,
    ProjectAttributes.ATTRIBUTE_SIM_TOOL: None,
    ProjectAttributes.ATTRIBUTE_SYNTH_TOOL: None,
    ProjectAttributes.ATTRIBUTE_SYNTH_PART: None,
}

class UnitTestFile(object):
    """The UnitTestFile object provides a container for Python test shims."""
    def __init__(self, **kwargs):
        self.path = kwargs[ProjectAttributes.ATTRIBUTE_PATH]
        self.fileType = FileType.Python
        self.testsuite = None


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
        # The path to this source file
        self.path = kwargs[ProjectAttributes.ATTRIBUTE_PATH]
        # A flag to indicate whether or not this file should be included for
        # synthesis. It not specified it will default to True.
        self.synthesise = kwargs.get(
            ProjectAttributes.ATTRIBUTE_SYNTHESIS,
            True
        )
        self.synthesise = True if self.synthesise is None else self.synthesise
        # The preprocessor is a path to a Python module containing a
        # preprocessor object that can edit the associated source file before
        # it is passed to synthesis.
        self.preprocessor = kwargs.get(
            ProjectAttributes.ATTRIBUTE_PREPROCESSOR,
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
        self.path = kwargs[ProjectAttributes.ATTRIBUTE_PATH]
        self.fileType = FileType.Unknown
        self.flow = kwargs.get(ProjectAttributes.ATTRIBUTE_FLOW, None)
        fileName, fileExtension = os.path.splitext(self.path)
        fileExtension = fileExtension.strip(' ')
        if fileExtension in fileExtensionsLookup.keys():
            self.fileType = fileExtensionsLookup[fileExtension]
