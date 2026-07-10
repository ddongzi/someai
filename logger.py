
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
def get_file_logger(logger_name: str, filename: str, log_dir: str = 'logs', level=logging.INFO, backup_count: int = 1) -> logging.Logger:
    """
    创建并返回一个仅输出到文件的日志对象（自动按天切分，不打印到控制台）。
    
    参数:
    logger_name: 日志对象的名称（全局唯一，如 'sse_logger'、'chat_logger'）
    log_dir: 日志文件存放的目录路径
    filename: 日志文件名（如 'sse_stream.log'）
    level: 日志级别，默认为 logging.INFO
    backup_count: 历史日志保留天数，默认为 1 天
    """
    # 1. 获取或创建 run_logger 实例
    run_logger = logging.getLogger(logger_name)
    run_logger.setLevel(level)
    
    # ⭐ 核心：关闭日志向父级传播，彻底阻止其打印到控制台
    run_logger.propagate = False

    # 2. 健壮性检查：如果该 run_logger 已经配置过 handler，直接返回，避免重复添加导致重复打印
    if run_logger.handlers:
        return run_logger

    # 3. 自动创建不存在的日志目录
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, filename)

    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=0, 
        backupCount=backup_count, 
        encoding="utf-8"
    )
        # 2. 【核心】如果日志文件已经存在，说明是上次运行留下的，立即强制切分
    if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 0:
        file_handler.doRollover()
    # 5. 设置统一的日志格式

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s')
    file_handler.setFormatter(formatter)
    
    # 6. 将 handler 绑定到 run_logger
    run_logger.addHandler(file_handler)

    # 终端也能输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    run_logger.addHandler(console_handler)
    
    return run_logger


run_logger = get_file_logger(
    logger_name='run',
    log_dir='./logs',
    filename='run.log'
)
sse_logger = get_file_logger(
    logger_name='sse',
    log_dir='./logs',
    filename='sse.log'
)