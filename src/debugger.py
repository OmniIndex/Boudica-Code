"""
Debugger Integration - Support for GDB (C++), pdb (Python), Node Inspector (JS), jdb (Java)
"""

import sys
import os
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DebuggerSession:
    """Manages an interactive debugger session"""
    
    def __init__(self, language: str, executable_path: str, source_files: List[str], project_dir: Path = None):
        """
        Initialize debugger session
        
        Args:
            language: 'cpp', 'python', 'javascript', 'java'
            executable_path: Path to executable or script to debug
            source_files: List of source file paths for breakpoint context
            project_dir: Project root directory for relative path resolution
        """
        self.language = language
        self.executable_path = executable_path
        self.source_files = source_files
        self.project_dir = project_dir or Path.cwd()
        self.breakpoints: Dict[str, List[int]] = {}  # filepath -> [line_numbers]
        self.process = None
        self.output_buffer = []
        self.crash_output = None
        
    def add_breakpoint(self, filepath: str, line_number: int) -> bool:
        """Add breakpoint at file:line (filepath can be relative to project_dir)"""
        # Try to resolve relative path
        check_path = Path(filepath)
        if not check_path.is_absolute():
            check_path = self.project_dir / filepath
        
        # Debug: show what we're checking
        print(f"DEBUG: Checking breakpoint path: {check_path}")
        
        if not check_path.exists():
            print(f"DEBUG: Path does not exist")
            return False
        
        if filepath not in self.breakpoints:
            self.breakpoints[filepath] = []
        if line_number not in self.breakpoints[filepath]:
            self.breakpoints[filepath].append(line_number)
        return True
    
    def remove_breakpoint(self, filepath: str, line_number: int) -> bool:
        """Remove breakpoint at file:line"""
        if filepath in self.breakpoints and line_number in self.breakpoints[filepath]:
            self.breakpoints[filepath].remove(line_number)
            return True
        return False
    
    def list_breakpoints(self) -> Dict[str, List[int]]:
        """Return all breakpoints"""
        return self.breakpoints
    
    def run(self) -> Tuple[bool, str]:
        """
        Run program in debugger until crash or completion
        
        Returns:
            (success, output) tuple
        """
        if self.language == 'cpp':
            return self._run_gdb()
        elif self.language == 'python':
            return self._run_pdb()
        elif self.language == 'javascript':
            return self._run_node_inspector()
        elif self.language == 'java':
            return self._run_jdb()
        else:
            return False, f"Unsupported language: {self.language}"
    
    def _run_gdb(self) -> Tuple[bool, str]:
        """Run C++ program with GDB"""
        gdb_commands = []
        
        # Set breakpoints
        for filepath, lines in self.breakpoints.items():
            for line in lines:
                gdb_commands.append(f"break {filepath}:{line}")
        
        # Run to first breakpoint or crash
        gdb_commands.append("run")
        
        # Print backtrace on crash
        gdb_commands.append("bt")
        
        # Print local variables
        gdb_commands.append("info locals")
        
        # Quit
        gdb_commands.append("quit")
        
        gdb_cmd = f"echo '{chr(10).join(gdb_commands)}' | gdb {self.executable_path}"
        
        try:
            result = subprocess.run(
                gdb_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            self.crash_output = output
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "GDB timed out (30s)"
        except Exception as e:
            return False, f"GDB error: {str(e)}"
    
    def _run_pdb(self) -> Tuple[bool, str]:
        """Run Python script with pdb"""
        pdb_commands = []
        
        # Set breakpoints
        for filepath, lines in self.breakpoints.items():
            for line in lines:
                pdb_commands.append(f"b {filepath}:{line}")
        
        # Run
        pdb_commands.append("c")
        
        # Print variables on crash
        pdb_commands.append("l")
        pdb_commands.append("p locals()")
        
        # Quit
        pdb_commands.append("q")
        
        cmd_input = '\n'.join(pdb_commands)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pdb", self.executable_path],
                input=cmd_input,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            self.crash_output = output
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Python debugger timed out (30s)"
        except Exception as e:
            return False, f"Python debugger error: {str(e)}"
    
    def _run_node_inspector(self) -> Tuple[bool, str]:
        """Run Node.js with inspector"""
        try:
            # Run with inspector, capture crash output
            result = subprocess.run(
                [sys.executable, "-m", "node", "--inspect-brk", self.executable_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            self.crash_output = output
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Node.js inspector timed out (30s)"
        except Exception as e:
            return False, f"Node.js error: {str(e)}"
    
    def _run_jdb(self) -> Tuple[bool, str]:
        """Run Java program with jdb"""
        jdb_commands = []
        
        # Extract class name from executable path
        class_name = Path(self.executable_path).stem
        
        # Set breakpoints
        for filepath, lines in self.breakpoints.items():
            for line in lines:
                # Convert filepath to class name (simplified)
                jdb_commands.append(f"stop at {class_name}:{line}")
        
        # Run
        jdb_commands.append("run")
        
        # Print stack
        jdb_commands.append("where")
        
        # Print local variables
        jdb_commands.append("locals")
        
        # Quit
        jdb_commands.append("quit")
        
        cmd_input = '\n'.join(jdb_commands)
        
        try:
            result = subprocess.run(
                ["jdb", class_name],
                input=cmd_input,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            self.crash_output = output
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Java debugger timed out (30s)"
        except Exception as e:
            return False, f"Java debugger error: {str(e)}"
    
    def extract_crash_info(self) -> Dict:
        """Extract crash information from debug output"""
        if not self.crash_output:
            return {}
        
        info = {
            'crashed': False,
            'error_type': None,
            'error_message': None,
            'stacktrace': [],
            'variables': {}
        }
        
        # Detect crash signals
        crash_patterns = [
            r'Segmentation fault',
            r'SIGSEGV',
            r'Bus error',
            r'SIGABRT',
            r'Aborted',
            r'Fatal error',
            r'Exception',
            r'Traceback',
            r'Error',
        ]
        
        for pattern in crash_patterns:
            if re.search(pattern, self.crash_output, re.IGNORECASE):
                info['crashed'] = True
                info['error_type'] = pattern
                break
        
        # Extract stacktrace (GDB format: #0, #1, etc)
        stacktrace_lines = re.findall(r'#\d+\s+0x[0-9a-f]+\s+in\s+(.+)', self.crash_output)
        info['stacktrace'] = stacktrace_lines
        
        # Extract error message
        error_match = re.search(r'(Error|Exception|Fatal):\s*(.+?)(?:\n|$)', self.crash_output)
        if error_match:
            info['error_message'] = error_match.group(2)
        
        return info


def create_debugger_session(language: str, project_dir: Path) -> Optional[DebuggerSession]:
    """
    Create debugger session for a project
    
    Args:
        language: Programming language
        project_dir: Project directory
    
    Returns:
        DebuggerSession or None if can't create
    """
    source_files = []
    executable_path = None
    
    if language == 'cpp':
        # Find C++ source files
        source_files = list(project_dir.glob('src/**/*.cpp')) + list(project_dir.glob('src/**/*.h'))
        # Look for executable in build directory
        build_dir = project_dir / 'build'
        print(f"DEBUG: Looking for C++ executable in {build_dir}")
        print(f"DEBUG: Build dir exists: {build_dir.exists()}")
        
        if build_dir.exists():
            # Find executable: files with no extension (Linux) or .exe (Windows)
            # Exclude build artifacts: .o, .a, .cmake, Makefile, etc
            exclude_extensions = {'.o', '.a', '.so', '.dll', '.cmake', '.txt'}
            exclude_names = {'Makefile', 'CMakeFiles', '.gitignore', 'cmake_install.cmake'}
            
            print(f"DEBUG: Searching recursively in {build_dir}")
            
            candidates = []
            for item in build_dir.rglob('*'):  # Recursive search
                if item.is_file():
                    name = item.name
                    suffix = item.suffix
                    
                    # Skip excluded names and extensions
                    if name in exclude_names or name.startswith('cmake_install'):
                        continue
                    if suffix in exclude_extensions:
                        continue
                    
                    # Check if this looks like an executable
                    # On Linux: no extension, is executable
                    # On Windows: .exe extension
                    if suffix == '' or suffix == '.exe':
                        # Try to stat it - executables often have execute permission
                        try:
                            stat_info = item.stat()
                            # Check execute bit for Unix (executable if mode & 0o111)
                            is_executable = (stat_info.st_mode & 0o111) != 0 or suffix == '.exe'
                            if is_executable or suffix == '.exe':
                                print(f"DEBUG: Candidate found: {item.relative_to(build_dir)}")
                                candidates.append((name, str(item)))
                        except:
                            pass
            
            print(f"DEBUG: Candidates: {candidates}")
            
            # Sort by name: prefer exact project name match, then shortest path (closest to root), then alphabetically
            project_name = project_dir.name
            candidates.sort(key=lambda x: (x[0] != project_name, len(x[1]), x[0]))
            
            if candidates:
                executable_path = candidates[0][1]
                print(f"DEBUG: Selected executable: {executable_path}")

    
    elif language == 'python':
        # Find main Python file
        source_files = list(project_dir.glob('**/*.py'))
        main_file = project_dir / 'main.py'
        if main_file.exists():
            executable_path = str(main_file)
        elif source_files:
            executable_path = str(source_files[0])
    
    elif language == 'javascript':
        # Find main.js or index.js
        source_files = list(project_dir.glob('**/*.js'))
        main_file = project_dir / 'main.js' or project_dir / 'index.js'
        if main_file.exists():
            executable_path = str(main_file)
        elif source_files:
            executable_path = str(source_files[0])
    
    elif language == 'java':
        # Find Java source files
        source_files = list(project_dir.glob('src/**/*.java'))
        # Find .class files
        class_files = list(project_dir.glob('**/*.class'))
        if class_files:
            executable_path = str(class_files[0])
    
    if not executable_path:
        print(f"DEBUG: No executable found for {language} project")
        return None
    
    print(f"DEBUG: Creating debugger session with executable: {executable_path}")
    return DebuggerSession(language, executable_path, [str(f) for f in source_files], project_dir)

