# PROG

**PROG — Terminal Programming Environment**

PROG is a terminal-based programming environment designed for Linux. It provides an interactive code editor, automatic programming language detection, and code execution in a single application.

## Features

- Automatic detection of installed programming languages.
- Interactive terminal code editor.
- Syntax-independent text editing.
- Code execution and compilation.
- Keyboard shortcuts for navigation and editing.
- Graphical file opening and saving.
- Support for multiple programming languages.

## Requirements

- Linux
- Python 3
- Zenity (for graphical file dialogs)
- Compilers and interpreters for the languages you want to use.

## Installation

Clone or download this repository.

Create the application directory:

```bash
mkdir -p ~/prog
```

Copy `prog.py` into `~/prog/`.

Create the launcher:

```bash
mkdir -p ~/.local/bin
nano ~/.local/bin/prog
```

Add:

```bash
#!/bin/bash
exec python3 "$HOME/prog/prog.py"
```

Make it executable:

```bash
chmod +x ~/.local/bin/prog
```

Run the application:

```bash
python3 ~/prog/prog.py
```

## Platform

Developed for Linux, with Linux Mint as the primary environment.

## Project

PROG is an independent programming environment project.
