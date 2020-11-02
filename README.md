# STARS: Stony Brook Assembler and Run-time Simulator
This program is a MIPS Assembly simulator made for the purpose of education. Inspired by Missouri State University's [MARS simulator](https://courses.missouristate.edu/KenVollmar/MARS/).

## Dependencies
* PySide2
* NumPy

To download the dependecies run `pip install -r requirements.txt`.

## How to run:
* `sbumips.py [-a] [-h] [-d] [-g] [-n #] [-i] [-w] [-pa arg1, arg2, ...] filename`

## Positional arguments:
* `filename`       Input MIPS Assembly file.

## Optional arguments:
* `-a`, `--assemble`    Assemble program without running it
* `-h`, `--help`     Shows help message and exits
* `-d`, `--debug`    Enables debugging mode
* `-g`, `--garbage`  Enables garbage data
* `-n`, `--max_instructions`  Sets max number of instructions
* `-i`, `--disp_instr_count`  Displays the total instruction count
* `-w`, `--warnings`  Enables warnings
* `-pa`  Program arguments for the MIPS program
    
## Example:
* `stars.py tests/test2.asm -d`     Runs test2.asm with debugger on
* `stars.py tests/test2.asm -g`     Runs test2.asm with garbage data on
* `stars.py tests/test2.asm -d -g`     Runs test2.asm with debugger and garbage data on
* `stars.py tests/test2.asm -pa A 30`     Runs test2.asm with program arguments "A" and "30"
