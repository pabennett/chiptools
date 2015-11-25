import logging.config
import chiptools.common.colourer as colourer

colourer.colour_terminal()  # Init colorama

handler_name = 'chiptools.common.colourer.ColouredStreamHandler'

LOG_CONFIG = {
    'handlers': {
        'console': {
            'stream': 'ext://sys.stdout',
            'class': handler_name,
            'level': 'INFO',
            'formatter': 'simple'
        },
    },
    'disable_existing_loggers': False,
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG'
    },
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s - %(module)s - %(levelname)s] %(message)s'
        },
        'simple': {
            'format': '[%(levelname)s] %(message)s'
        }
    },
    'version': 1
}

logging.config.dictConfig(LOG_CONFIG)
