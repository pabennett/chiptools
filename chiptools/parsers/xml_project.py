import logging
import traceback
import xml
import os
import time

from xml.dom import minidom

from chiptools.common import utils
from chiptools.common import exceptions
from chiptools.common.filetypes import ProjectAttributes


log = logging.getLogger(__name__)


PROJECT_DICT_CONSTRAINTS_KEY = 'constraints_files'
PROJECT_DICT_SOURCE_FILES_KEY = 'source_hdl_files'
PROJECT_DICT_ORDERED_FILE_SET = 'ordered_file_set'
PROJECT_DICT_GENERICS = 'generics'


class XmlProjectParser:
    """
    The XmlProjectParser class implements an XML parser for the project file
    XML format.
    """

    # Process each of the file attributes using the following functions
    XML_NODE_PROCESSOR = {
        ProjectAttributes.XML_ATTRIBUTE_PATH: utils.format_paths,
        ProjectAttributes.ATTRIBUTE_SIM_DIR: utils.format_paths,
        ProjectAttributes.ATTRIBUTE_SYNTH_DIR: utils.format_paths,
        ProjectAttributes.XML_ATTRIBUTE_PREPROCESSOR: utils.format_paths,
        ProjectAttributes.ATTRIBUTE_REPORTER: utils.format_paths,
        ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS:
            lambda x, root: x.lower() != 'false',
        ProjectAttributes.ATTRIBUTE_SIM_TOOL: lambda x, root: x,
        ProjectAttributes.ATTRIBUTE_SYNTH_TOOL: lambda x, root: x,
        ProjectAttributes.ATTRIBUTE_SYNTH_PART: lambda x, root: x,
    }
    FILE_DEFAULTS = {
        ProjectAttributes.XML_ATTRIBUTE_PATH: None,
        ProjectAttributes.XML_ATTRIBUTE_PREPROCESSOR: None,
        ProjectAttributes.ATTRIBUTE_REPORTER: None,
        ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS: None,
        ProjectAttributes.ATTRIBUTE_SIM_DIR: None,
        ProjectAttributes.ATTRIBUTE_SYNTH_DIR: None,
        ProjectAttributes.ATTRIBUTE_SIM_TOOL: None,
        ProjectAttributes.ATTRIBUTE_SYNTH_TOOL: None,
        ProjectAttributes.ATTRIBUTE_SYNTH_PART: None,
    }

    @staticmethod
    def load_project(path, project_object):
        """
        Load the project XML file provided by the *path*.
        """
        log.info('Loading project: ' + str(path))
        project_object.initialise()
        base_name = os.path.basename(path).split('.')[0]
        cache_path = os.path.join(
            os.path.dirname(path),
            '.' + base_name
        )
        project_object.set_cache_path(cache_path)
        # Parse the project file
        XmlProjectParser.parse_project(path, project_object)

    @staticmethod
    def parse_project(
        filepath,
        project_object,
        synthesise=None
    ):
        """Parse the XML project and update the project_dictionary or return
        a new dictionary if one is not supplied.
        """
        log.info('Parsing: ' + str(filepath) + ' synthesis=' + str(synthesise))
        start_time = time.time()
        project_root = os.path.dirname(os.path.realpath(filepath))
        try:
            xml_obj = minidom.parse(filepath)
            for project_node in xml_obj.getElementsByTagName(
                ProjectAttributes.XML_NODE_PROJECT
            ):
                # Project attributes (if any)
                # If this whole node should not be synthesised, ignore any
                # child flags otherwise get the child synthesis flag and use
                # that.
                if synthesise is None:
                    project_attribs = XmlProjectParser._get_node_attributes(
                        project_node,
                        project_root
                    )
                    synthesis_enabled = project_attribs.get(
                        ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS,
                        None
                    )
                else:
                    synthesis_enabled = synthesise

                for child in project_node.childNodes:
                    if child.nodeName == ProjectAttributes.XML_NODE_PROJECT:
                        attribs = XmlProjectParser._get_node_attributes(
                            child,
                            project_root
                        )
                        # If this whole node should not be synthesised, ignore
                        # any child flags otherwise get the child synthesis
                        # flag and use that.
                        if synthesis_enabled is None:
                            fileAttributes = (
                                XmlProjectParser._get_node_attributes(
                                    child,
                                    project_root
                                )
                            )
                            try:
                                synthesise = fileAttributes[
                                    ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS
                                ]
                            except KeyError:
                                synthesise = None
                        else:
                            synthesise = synthesis_enabled

                        if ProjectAttributes.XML_ATTRIBUTE_PATH in attribs:
                            log.debug(
                                'Found sub-project: ' +
                                str(
                                    attribs[
                                        ProjectAttributes.XML_ATTRIBUTE_PATH
                                    ]
                                )
                            )
                            # Recursively call this parser with the new project
                            # path
                            XmlProjectParser.parse_project(
                                str(
                                    attribs[
                                        ProjectAttributes.XML_ATTRIBUTE_PATH
                                    ]
                                ),
                                project_object,
                                synthesise
                            )
                    elif child.nodeName == ProjectAttributes.XML_NODE_CONFIG:
                        XmlProjectParser._add_config(
                            child,
                            project_root,
                            project_object
                        )
                    elif child.nodeName == ProjectAttributes.XML_NODE_LIBRARY:
                        XmlProjectParser._add_library(
                            child,
                            project_root,
                            project_object,
                            synthesis_enabled
                        )
                    elif child.nodeName == (
                        ProjectAttributes.XML_NODE_CONSTRAINTS
                    ):
                        XmlProjectParser._add_constraints(
                            child,
                            project_root,
                            project_object,
                        )
                    elif child.nodeName == (
                        ProjectAttributes.XML_NODE_UNITTEST
                    ):
                        XmlProjectParser._add_unittest(
                            child,
                            project_root,
                            project_object,
                        )
                    elif child.nodeName == ProjectAttributes.XML_NODE_GENERIC:
                        # Build a dictionary of generics using the attribute
                        # name and value
                        attribs = child.attributes
                        if attribs is None:
                            continue
                        attribs = dict(attribs.items())
                        for attrName, attrVal in attribs.items():
                            project_object.add_generic(
                                attrName,
                                attrVal
                            )
                    elif child.nodeName == ProjectAttributes.XML_NODE_FILE:
                        # Files should not be left unassociated with a library
                        # unless you wish to add all files to the work library.
                        # The default behavior will be to add parentless files
                        # to the work library, but a configuration option could
                        # make this post an error instead.
                        log.warning(
                            'Found file with no parent library, ' +
                            'defaulting to work library'
                        )
                        # If this whole node should not be synthesised, ignore
                        # any child flags otherwise get the child synthesis
                        # flag and use that.
                        if synthesis_enabled is None:
                            fileAttributes = (
                                XmlProjectParser._get_node_attributes(
                                    child,
                                    project_root
                                )
                            )
                            try:
                                synthesise = fileAttributes[
                                    ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS
                                ]
                            except KeyError:
                                synthesise = None
                        else:
                            synthesise = synthesis_enabled

                        XmlProjectParser._add_file(
                            child,
                            'work',
                            project_root,
                            project_object,
                            synthesise=synthesise
                        )
                    elif child.nodeName == ProjectAttributes.XML_NODE_TEXT:
                        pass
                    elif child.nodeName == ProjectAttributes.XML_NODE_COMMENT:
                        pass
        except xml.parsers.expat.ExpatError:
            log.error(
                'Error found in XML file, check the formatting. ' +
                'Refer to the traceback below for the line number and file.'
            )
            log.error(traceback.format_exc())
            raise exceptions.ProjectFileException()
        log.debug(filepath + ' parsed in ' + utils.time_delta_string(
            start_time,
            time.time())
        )

    @staticmethod
    def _get_node_attributes(node, root):
        """Return the node attributes as a dictionary if any attributes exist.
        Attributes will be pre-processed according to the XML_NODE_PROCESSOR
        function dictionary. The returned dictionary will contain AT LEAST
        the keys present in XML_NODE_PROCESSOR, additional optional keys may
        also be present
        """
        attribs = node.attributes
        if attribs is None:
            return {}
        else:
            attribs = dict(attribs.items())

        for attribute, function in XmlProjectParser.XML_NODE_PROCESSOR.items():
            # If the attribute exists process it using the processor function
            # otherwise insert a default value
            if attribute in attribs:
                attribs[attribute] = function(
                    attribs[attribute],
                    root
                )
            else:
                # Ensure the attribute is initialised to its default
                attribs[attribute] = XmlProjectParser.FILE_DEFAULTS[attribute]
        return attribs

    @staticmethod
    def _add_config(child, root, project_object):
        """Process and add all child attributes to the given
        configuration dict. Return a reference to the modified dict.
        """
        attribs = XmlProjectParser._get_node_attributes(child, root)
        config = {}
        for k, v in attribs.items():
            if v is not None:
                config[k] = v
        project_object.add_config_dict(**config)

    @staticmethod
    def _add_file(
        file_node,
        library_name,
        root,
        project_object,
        synthesise
    ):
        """Add the given file to the given library and ensure that any
        relative file paths are correctly converted into absolute paths using
        the project_root as a reference"""
        attribs = XmlProjectParser._get_node_attributes(
            file_node,
            root
        )
        if attribs is not None:
            # Override the file synthesis flag if the library is marked for
            # exclusion from synthesis
            if synthesise is not None:
                attribs[ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS] = synthesise
            path = attribs['path']
            del attribs['path']
            project_object.add_file(
                path=path,
                library=library_name,
                **attribs
            )
        else:
            log.debug('Ignoring empty file tag')

    @staticmethod
    def _add_library(
        child,
        root,
        project_object,
        synthesise,
    ):
        """Process the given library node and add it to the
        project_dictionary. Any files containedwithin the library will be
        added to the project_dictionary under that library"""
        attribs = XmlProjectParser._get_node_attributes(child, root)
        if ProjectAttributes.XML_ATTRIBUTE_NAME not in attribs:
            log.warning('Ignoring library with no name specified')
            return
        library_name = attribs[ProjectAttributes.XML_ATTRIBUTE_NAME]
        if synthesise is None:
            synthesise = attribs[ProjectAttributes.XML_ATTRIBUTE_SYNTHESIS]
        # Add all files in this library node to the project
        for file in filter(
            lambda x: x.nodeName == ProjectAttributes.XML_NODE_FILE,
            child.childNodes
        ):
            XmlProjectParser._add_file(
                file,
                library_name,
                root,
                project_object,
                synthesise,
            )

    @staticmethod
    def _add_constraints(child, root, project_object):
        attribs = XmlProjectParser._get_node_attributes(child, root)
        path = attribs['path']
        del attribs['path']
        project_object.add_constraints(
            path,
            **attribs
        )

    @staticmethod
    def _add_unittest(child, root, project_object):
        attribs = XmlProjectParser._get_node_attributes(child, root)
        path = attribs['path']
        del attribs['path']
        project_object.add_unittest(
            path,
            **attribs
        )
