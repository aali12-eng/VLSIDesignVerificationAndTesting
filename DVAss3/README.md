# VLSI Design Verification and Test - Assignment 3

This assignment processes a gate-level Verilog netlist and generates stuck-at
fault lists before and after fault equivalence collapsing.

## Run

Install Python 3, then run from this directory:

```bash
python3 main.py
```

The input file is `c432_new.v`. The script writes:

- `c432_BF.txt` - faults before collapsing
- `c432_AF.txt` - faults after collapsing
- `faults_after_equivalence.txt` - remaining faults grouped by gate

To use a different netlist, update `input_file_name` near the top of
`main.py`. The input file must be in the same directory as the script.
