import logging
import traceback
import os
import importlib.machinery
import inspect

from chiptools.wrappers.simulator import Simulator
from chiptools.wrappers.synthesiser import Synthesiser
from chiptools.wrappers.toolchains import ToolchainBase

log = logging.getLogger(__name__)


def plugin_discovery(
    plugin_directory,
    plugin_subclass,
    class_filter=['Simulator', 'Synthesiser']
):
    result = {}
    for path in os.listdir(plugin_directory):
        if path.endswith('.py'):
            loader = importlib.machinery.SourceFileLoader(
                'chiptools_wrappers_' + os.path.basename(path).split('.')[0],
                os.path.join(plugin_directory, path),
            )
            try:
                module = loader.load_module()
            except:
                log.error(
                    'Plugin module ' +
                    '{0} contains errors and will be disabled:'.format(
                        os.path.basename(path)
                    )
                )
                log.error(traceback.format_exc())
                continue
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    if (
                        issubclass(obj, ToolchainBase) and
                        obj.__name__ not in class_filter
                    ):
                        if issubclass(obj, plugin_subclass):
                            result[
                                obj.__name__.lower()
                            ] = obj
    return result

synthesis_tool_class_registry = plugin_discovery(
    os.path.join(os.path.dirname(__file__), 'synthesisers'),
    Synthesiser,
)
simulation_tool_class_registry = plugin_discovery(
    os.path.join(os.path.dirname(__file__), 'simulators'),
    Simulator,
)


def get_all_tools(project, user_paths, tool_type='synthesis'):
    """Return all tools of the given type, this could be used for reporting
    available tools."""
    if tool_type == 'synthesis':
        registry = synthesis_tool_class_registry
    elif tool_type == 'simulation':
        registry = simulation_tool_class_registry
    else:
        log.error(
            'Invalid tool type specified: {0}'.format(tool_type) +
            ' Use one of [simulation, synthesis]'
        )
        return None

    tools = {}
    for toolname, inst_fn in registry.items():
        try:
            inst = inst_fn(project, user_paths)
            if not inst.installed:
                log.warning(
                    toolname.capitalize() +
                    ' could not be found.' +
                    ' Update .chiptoolsconfig or your PATH variable'
                )
            tools[toolname] = inst
        except:
            # Error instancing this tool.
            log.error(
                'Encountered an error when loading tool wrapper: ' +
                toolname
            )
            log.error(traceback.format_exc())
    return tools


class ToolWrapper:
    """
    ToolWrapper holds instances of all available toolchains and provides a
    method of retrieving the tool currently specified in the loaded project
    file.
    """
    def __init__(self, project, user_paths={}):
        self.project = project
        self.synthesisers = get_all_tools(
            self.project,
            user_paths,
            tool_type='synthesis'
        )
        self.simulators = get_all_tools(
            self.project,
            user_paths,
            tool_type='simulation'
        )

    def get_tool(self, tool_type='synthesis', tool_name=None):
        if tool_type == 'synthesis':
            if tool_name is None:
                tool_name = self.project.get_synthesis_tool_name()
            tool = self.synthesisers.get(tool_name, None)
        elif tool_type == 'simulation':
            if tool_name is None:
                tool_name = self.project.get_simulation_tool_name()
            tool = self.simulators.get(tool_name, None)
        else:
            log.error(
                'Invalid tool type specified: {0}'.format(tool_type) +
                ' Use one of [simulation, synthesis]'
            )
            tool = None
        if tool is None:
            log.error(
                'No wrapper exists for the tool: ' + str(tool_name)
            )
        return tool
