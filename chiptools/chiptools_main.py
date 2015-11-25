import logging


def main():
    """
    Launch the Framework application command line interface.
    """
    main = CommandLine()
    main.cmdloop()
    logging.shutdown()

if __name__ == '__main__':
    from core.cli import CommandLine
    main()
else:
    from chiptools.core.cli import CommandLine
