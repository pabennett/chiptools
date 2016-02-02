import logging
import subprocess

log = logging.getLogger(__name__)

from chiptools.parsers.vhdl import ParsedVhdlFile, Component, Entity
from chiptools.common import utils


class CallGraph:
    def __init__(self, files, root=None):
        self.parsed_files = [CallGraph.get_parsed_file(f) for f in files]

    @staticmethod
    def get_callchain(graph, modified_nodes):
        """Return a topologically sorted list of the nodes dependent on the
        given node."""
        try:
            sorted_nodes = utils.topological_sort(graph)
        except Exception as e:
            # The graph contains cycles
            log.error(e)
            return None
        callchain = []
        callchain += modified_nodes
        for n in sorted_nodes:
            if n not in graph:
                # This node has no incoming edges and so has no dependencies
                continue
            if any(caller in graph[n] for caller in callchain):
                if n not in callchain:
                    callchain.append(n)
        return callchain

    @staticmethod
    def get_parsed_file(sourcefile):
        return ParsedVhdlFile(sourcefile)

    @staticmethod
    def get_definition_map(files):
        """Return a dictionary mapping design unit instances to a set of files
        that provide an implementation for the design unit.
        """
        definition_map = {}
        for file_object in files:
            for definition in file_object.definitions:
                if definition in definition_map:
                    definition_map[definition].add(file_object)
                else:
                    definition_map[definition] = set([file_object])
        return definition_map

    @staticmethod
    def get_reference_map(files):
        """Return a dictionary mapping design unit instances to a set of files
        that reference them.
        """
        reference_map = {}
        for file_object in files:
            for reference in file_object.references:
                if reference in reference_map:
                    reference_map[reference].append(file_object)
                else:
                    reference_map[reference] = [file_object]
        return reference_map

    @staticmethod
    def get_design_hierarchy(definition_map, reference_map):
        graph = {}
        for dependency in reference_map.keys():
            # List of files that implement this dependency, note that if there
            # are more than one files implementing this dependency we are in
            # danger of creating a link to the wrong child, we need to
            # determine exactly which child is referred to by this parent file.
            children = definition_map.get(dependency, [])
            # List of files that require this dependency
            parents = reference_map[dependency]
            # Generate a graph of the design hierarchy.
            for parent in parents:
                # If the parent is contained in the childen then it implements
                # its own dependency and an edge should not be added.
                if parent in children:
                    continue
                # Initialise parent edge set
                if parent not in graph:
                    graph[parent] = set()
                if (
                    len(children) == 0 and
                    not isinstance(dependency, Component)
                ):
                    # If no files implement this dependency then it is
                    # unresolved, it could be the case that this dependency is
                    # a primitive. It will be added to the graph as a stub.
                    graph[parent].add(dependency)
                else:
                    # Create an edge from the parent node to the child nodes.
                    graph[parent].update(children)
        return graph

    @staticmethod
    def write_graph_png(graph, show_unresolved=False, highlight_nodes=[]):
        with open('out.dot', 'w') as f:
            f.write('digraph project {\n')
            f.write('node [fontname = "helvetica", fontsize = "10"];\n')
            for node in graph.keys():
                if isinstance(node, ParsedVhdlFile):
                    if node in highlight_nodes:
                        colour = '{0} {1} {2}'.format(
                            0.6,
                            (
                                (1.0 / len(highlight_nodes)) *
                                highlight_nodes.index(node)
                            ),
                            1.0
                        )
                        f.write(
                            node.name +
                            ' [shape=box,style=filled,color="' + colour + '"];\n'
                        )
                    else:
                        f.write(
                            node.name +
                            ' [shape=box,style=filled,color="1. 1. 1."];\n'
                        )
                for child in graph[node]:
                    if isinstance(child, ParsedVhdlFile):
                        f.write(
                            '{0} -> {1};\n'.format(
                                node.name,
                                child.name
                            )
                        )
                    elif show_unresolved and (
                        isinstance(child, Entity) or isinstance(child, Component)
                    ):
                        f.write(
                            node.name +
                            ' -> ' +
                            str(child) +
                            '[style=dotted]' +
                            ';\n'
                        )
            f.write('}')
        subprocess.call(
            ['dot', f.name, '-Tpng', '-o', 'output.png']
        )
