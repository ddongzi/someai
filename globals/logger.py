from utils import get_file_logger

import os
from enum import Enum
from dotenv import load_dotenv
load_dotenv()


run_logger = get_file_logger(
    logger_name='run',
    log_dir='./logs',
    filename='run.log',
    so=True
)
