from tools.ast import ast_search
from tools.environment import get_environment_variable
from tools.filer import read_file, create_file,inspect_project,write_to_file,delete_files,inspect_file_summary
from tools.pyright_check import static_check
from tools.pyright_client import find_symbol_definition, find_symbol_references
from tools.search_replace_tool import apply_search_replace
from tools.setup_spec_environment import setup_spec_environment
from tools.time import get_current_time
from tools.web_search import web_search
all_tools = [
    ast_search,
    get_environment_variable,
    read_file,
    create_file,
    inspect_project,
    write_to_file,
    delete_files,
    inspect_file_summary,
    static_check,
    find_symbol_definition,
    find_symbol_references,
    apply_search_replace,
    setup_spec_environment,
    get_current_time,
    web_search
]