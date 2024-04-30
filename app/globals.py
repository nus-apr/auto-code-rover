"""
Values of global configuration variables.
"""

# Overall output directory for results
output_dir: str = ""

# upper bound of the number of conversation rounds for the agent
conv_round_limit: int = 15

# whether to perform sbfl
enable_sbfl: bool = False

# whether to perform layered search
enable_layered: bool = True

# whether to perform our own validation
enable_validation: bool = False

# whether to do angelic debugging
enable_angelic: bool = False

# whether to do perfect angelic debugging
enable_perfect_angelic: bool = False


# A special mode to only save SBFL result and exit
only_save_sbfl_result: bool = False

# timeout for test cmd execution, currently set to 5 min
test_exec_timeout: int = 300
