import datetime
from langchain_core.tools import tool

@tool
def get_current_time() -> str:
    """
    获取当前的系统日期和时间。
    当大模型需要了解当前的年份、月份、具体时间或进行时间差计算时，应当调用此工具。

    Returns:
        str: 格式化后的当前时间字符串，例如 "2026-07-30 20:54:12 Thursday"
    """
    now = datetime.datetime.now()
    # 格式化输出：年-月-日 时:分:秒 星期几
    return now.strftime("%Y-%m-%d %H:%M:%S %A")
