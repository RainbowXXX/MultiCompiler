import os
import re
import json
import argparse
import subprocess
import sys

from loguru import logger

logger.add("MultiCompiler.log", rotation="500 MB", backtrace=True, diagnose=True)


# replace all the patterns in the dict keys to dict vals
def replace_multiple_patterns(text, replacements):
    pattern = re.compile("|".join(re.escape(key) for key in replacements.keys()))

    def replace_match(match):
        return replacements[match.group(0)]

    return pattern.sub(replace_match, text)


def run_command_with_timeout(command, run_in_shell, timeout):
    if timeout == -1:
        timeout = None

    if not run_in_shell:
        command = command.split(' ')

    try:
        result = subprocess.run(command, shell=run_in_shell, timeout=timeout, capture_output=True, text=True)

        print(result.stdout, file=sys.stdout) if result.stdout != '' else None
        print(result.stderr, file=sys.stderr) if result.stderr != '' else None
        return result.returncode
    except subprocess.TimeoutExpired:
        # 超时异常
        logger.error(f"Command '{command}' timed out after {timeout} seconds")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-language compilers for OnlineJudge")
    parser.add_argument('-t', '--type', type=str, required=True, help="The type of the source file")
    parser.add_argument('-c', '--config', type=str, default='./config.json', help="Position of config file")
    parser.add_argument('params', type=str, nargs='*', help='Compilation parameters')

    # parse command args and transfer to dict[str, object]
    args = parser.parse_args()
    args_dict = vars(args)

    # load config file
    config_file_path = args_dict['config']
    with open(config_file_path) as config_file:
        config = json.load(config_file)['configs']

    lang_config = None
    lang_type = args_dict['type']
    # the specified file type is not supported
    if lang_type not in config:
        logger.error(f"The type {lang_type} is not supported in the config file")
        exit(1)
    else:
        lang_config = config[lang_type]

    # get compilation parameters
    params_dict = {}
    params_set = set()
    params = args_dict['params']
    for param in params:
        eq_split = param.split('=')
        if len(eq_split) != 2:
            logger.error(f"The parameter {param} is invalid")
            exit(1)

        params_set.add(eq_split[0])
        params_dict['${'+eq_split[0]+'}'] = eq_split[1]

    lang_command_args = lang_config['command_args']
    for required_param in lang_command_args['required']:
        if required_param not in params_set:
            logger.error(f"The required parameter {required_param} is not given in command line or the config file");
            exit(1)

    lang_optional_command_args = lang_command_args['optional']
    for optional_param_key in lang_optional_command_args:
        optional_param_val = lang_optional_command_args[optional_param_key]
        if optional_param_key not in params_set:
            params_dict['${'+optional_param_key+'}'] = optional_param_val

    compile_command: str = lang_config['compile_command']
    compile_command = replace_multiple_patterns(compile_command, params_dict)

    logger.debug(f"Compiling command: {compile_command}")

    result = run_command_with_timeout(compile_command, params_dict['${run_in_shell}'], params_dict['${timeout}'])
    exit(result)
