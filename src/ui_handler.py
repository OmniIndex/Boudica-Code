"""
UI Handler - User interface and interactive prompts for CLI
"""

from typing import Optional, List, Dict
import difflib
from pathlib import Path
import sys
import os

# Enable line editing with Backspace and Delete keys
# This must be imported before any input() calls
def _enable_readline():
    """Enable readline for proper line editing"""
    try:
        # Try to import readline (Unix/Linux/macOS)
        import readline
        # Configure readline for better editing
        readline.parse_and_bind('tab: complete')
        return True
    except ImportError:
        try:
            # Try Windows version
            import pyreadline as readline
            return True
        except ImportError:
            # Fallback for systems without readline
            return False

# Call this at module import time
_enable_readline()

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory


class UIHandler:
    """Handles all user interface interactions"""
    
    def __init__(self):
        self.width = 80
        
        # Single-line prompt session - Enter submits, full line editing support
        self.prompt_session = PromptSession(
            history=InMemoryHistory(),
            multiline=False
        )
    
    def show_welcome(self):
        """Display welcome message"""
        print("\n" + "=" * self.width)
        print(" " * 20 + "🛡️  BOUDICA CODE 🛡️")
        print(" " * 10 + "AI-Powered Code Generation & Project Management")
        print("=" * self.width + "\n")
    
    def show_goodbye(self):
        """Display goodbye message"""
        print("\n" + "=" * self.width)
        print(" " * 25 + "Goodbye from Boudica Code!")
        print("=" * self.width + "\n")
    
    def show_main_menu(self) -> str:
        """Display main menu and get user choice"""
        print("\nMain Menu:")
        print("  [N]ew       - Create a new project")
        print("  [O]pen      - Open existing project")
        print("  [L]ist      - List all projects")
        print("  [E]xit      - Exit Boudica Code")
        print()
        
        while True:
            choice = self.prompt_session.prompt("Choice (n/o/l/e): ").strip().lower()
            
            if choice in ['n', 'new']:
                return 'new'
            elif choice in ['o', 'open']:
                return 'open'
            elif choice in ['l', 'list']:
                return 'list'
            elif choice in ['e', 'exit']:
                return 'exit'
            else:
                self.error("Invalid choice")
    
    def show_project_help(self):
        """Show project command help"""
        print("\nProject Commands:")
        print()
        print("  File Management:")
        print("    ls, list, files     - Browse all project files")
        print("    view <path>         - View file contents")
        print("    delete, rm <path>   - Delete a file")
        print()
        print("  Code Generation:")
        print("    create <path>: <desc> - Generate and create new file")
        print("    edit <path>: <desc>   - Edit existing file with AI")
        print()
        print("  Project:")
        print("    status              - Show project status")
        print("    build               - Build/compile project")
        print("    workflows           - Generate GitHub Actions CI/CD workflows")
        print("    debug, run          - Run with debugger (set breakpoints, analyze crashes)")
        print("    help                - Show this help")
        print("    exit                - Return to main menu")
        print()
        print("Line Editing (available in all prompts):")
        print("  Backspace           - Delete character before cursor")
        print("  Delete              - Delete character at cursor")
        print("  Ctrl+A              - Move to start of line")
        print("  Ctrl+E              - Move to end of line")
        print("  Ctrl+U              - Delete from cursor to start of line")
        print("  Ctrl+K              - Delete from cursor to end of line")
        print("  ↑ / ↓               - Navigate command history")
        print()
        print("Examples:")
        print("  > ls                    (view all files)")
        print("  > view src/main.cpp     (view file contents)")
        print("  > create src/utils.ts: Helper functions for API calls")
        print("  > edit src/server.ts: Add authentication middleware")
        print("  > delete src/old_file.py")
        print("  > workflows             (generate CI/CD workflows)")
        print("  > debug                 (run with debugger, set breakpoints)")
        print()
    
    def prompt_text(self, prompt: str, default: str = None) -> Optional[str]:
        """Prompt user for text input. Press Enter to accept the suggested example or default."""
        import re
        
        # Extract suggested example from prompt if it contains "(e.g., ...)"
        example_match = re.search(r'\(e\.g\.,\s*([^)]+)\)', prompt)
        if example_match and not default:
            default = example_match.group(1).strip()
        
        if default:
            prompt_str = f"{prompt} [{default}]: "
        else:
            prompt_str = f"{prompt}: "
        
        try:
            response = self.prompt_session.prompt(prompt_str).strip()
            
            if response:
                return response
            elif default:
                # User pressed Enter - using the suggested default
                return default
            else:
                # User pressed Enter with no input and no default - return None to skip
                return None
        except EOFError:
            # User pressed Ctrl+D
            if default:
                return default
            else:
                return None
    
    def prompt_stack_selection(self) -> Optional[str]:
        """Prompt user to select technology stack"""
        print("\nSelect Technology Stack:")
        print("  [1] Python (Backend)")
        print("  [2] Node.js (Backend)")
        print("  [3] TypeScript (Backend)")
        print("  [4] Java (Backend)")
        print("  [5] C++ (Backend)")
        print("  [6] Bash Scripts")
        print("  [7] Windows Batch Scripts")
        print("  [8] Full-Stack (Node.js + React)")
        print("  [9] Full-Stack (Python + React)")
        print("  [10] Full-Stack (Java + React)")
        print("  [11] Custom Mix")
        print()
        
        stacks = {
            '1': 'python',
            '2': 'nodejs',
            '3': 'typescript',
            '4': 'java',
            '5': 'cpp',
            '6': 'bash',
            '7': 'batch',
            '8': 'fullstack-node',
            '9': 'fullstack-python',
            '10': 'fullstack-java',
            '11': 'custom'
        }
        
        while True:
            choice = self.prompt_session.prompt("Choice (1-11): ").strip()
            
            if choice in stacks:
                return stacks[choice]
            else:
                self.error("Invalid choice")
    
    def prompt_session_selection(self, sessions: List[Dict]) -> Optional[str]:
        """Prompt user to select from existing sessions"""
        if not sessions:
            self.error("No sessions available")
            return None
        
        print("\nAvailable Projects:")
        for i, session in enumerate(sessions, 1):
            print(f"  [{i}] {session['name']} ({session['stack']})")
        print(f"  [0] Cancel")
        print()
        
        while True:
            try:
                choice = int(self.prompt_session.prompt("Choice: ").strip())
                
                if choice == 0:
                    return None
                elif 1 <= choice <= len(sessions):
                    return sessions[choice - 1]['name']
                else:
                    self.error("Invalid choice")
            except ValueError:
                self.error("Enter a number")
    
    def prompt_project_command(self, project_name: str) -> Optional[str]:
        """Prompt user for project command with full line editing support via prompt-toolkit"""
        prompt = f"{project_name}> "
        
        try:
            # Use prompt_session for superior line editing support
            # Includes: Backspace, Delete, Ctrl+A, Ctrl+E, Ctrl+U, Ctrl+K, history, etc.
            text = self.prompt_session.prompt(prompt).strip()
            return text if text else None
        except EOFError:
            # User pressed Ctrl+D
            return None
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            return None

            return "exit"
        except EOFError:
            # Ctrl+D pressed
            return None
    
    def confirm(self, message: str) -> bool:
        """Ask for yes/no confirmation"""
        while True:
            response = self.prompt_session.prompt(f"{message} (y/n): ").strip().lower()
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                self.error("Enter 'y' or 'n'")
    
    def show_code_preview(self, code: str, filepath: str):
        """Show code preview to user"""
        lines = code.split('\n')
        
        print(f"\n{'=' * self.width}")
        print(f"File: {filepath}")
        print(f"{'=' * self.width}")
        
        # Show first 30 lines
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:3d} | {line}")
        
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} more lines)")
        
        print(f"{'=' * self.width}\n")
    
    def show_diff(self, old_code: str, new_code: str, filepath: str):
        """Show side-by-side or unified diff with validation"""
        print(f"\n{'=' * self.width}")
        print(f"Changes to: {filepath}")
        print(f"{'=' * self.width}\n")
        
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')
        
        # Validate: check if a large amount of code is being deleted
        deleted_lines = len([l for l in old_lines if l.strip()])
        added_lines = len([l for l in new_lines if l.strip()])
        
        if added_lines < (deleted_lines * 0.7):  # Lost more than 30% of code
            print("\033[93m⚠️  WARNING: This diff removes a large amount of code!\033[0m")
            print(f"   Original: {deleted_lines} lines → Modified: {added_lines} lines")
            print("   This may indicate Boudica returned an incomplete response.\n")
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f'{filepath} (current)',
            tofile=f'{filepath} (proposed)',
            lineterm=''
        )
        
        # Show first 50 lines of diff
        for i, line in enumerate(diff):
            if i >= 50:
                remaining = sum(1 for _ in diff)
                if remaining:
                    print(f"\n... ({remaining} more lines)")
                break
            
            if line.startswith('-'):
                print(f"\033[91m{line}\033[0m")  # Red
            elif line.startswith('+'):
                print(f"\033[92m{line}\033[0m")  # Green
            elif line.startswith('@'):
                print(f"\033[94m{line}\033[0m")  # Blue
            else:
                print(line)
        
        print(f"\n{'=' * self.width}\n")
    
    def show_build_errors(self, errors: List[str]):
        """Display build errors"""
        print("\n" + "!" * self.width)
        print("BUILD ERRORS:")
        print("!" * self.width + "\n")
        
        for i, error in enumerate(errors[:10], 1):
            print(f"{i}. {error}")
        
        if len(errors) > 10:
            print(f"\n... and {len(errors) - 10} more errors")
        
        print()
    
    def show_debug_output(self, output: str, language: str):
        """Display debugger output"""
        print("\n" + "=" * self.width)
        print(f"DEBUG OUTPUT ({language.upper()}):")
        print("=" * self.width + "\n")
        
        # Show first 60 lines of output
        lines = output.split('\n')
        for i, line in enumerate(lines[:60]):
            if line.strip():
                print(line)
        
        if len(lines) > 60:
            print(f"\n... ({len(lines) - 60} more lines)")
        
        print("\n" + "=" * self.width + "\n")
    
    def show_ai_response(self, response: str):
        """Display AI response"""
        print("\n" + "-" * self.width)
        print("BOUDICA RESPONSE:")
        print("-" * self.width + "\n")
        
        print(response)
        print()
    
    def show_project_status(self, status: Dict):
        """Display project status"""
        print("\n" + "=" * self.width)
        print("PROJECT STATUS")
        print("=" * self.width)
        
        print(f"\nName:       {status.get('name')}")
        print(f"Type:       {status.get('type')}")
        print(f"Stack:      {status.get('stack')}")
        print(f"Languages:  {', '.join(status.get('languages', []))}")
        print(f"Files:      {status.get('files')}")
        print(f"Path:       {status.get('path')}")
        print()
    
    def show_sessions_list(self, sessions: List[Dict]):
        """Display list of sessions"""
        print("\n" + "=" * self.width)
        print("ALL PROJECTS")
        print("=" * self.width + "\n")
        
        for session in sessions:
            created = session.get('created_at', 'Unknown')[:10]
            print(f"  {session['name']:<25} {session['stack']:<15} (Created: {created})")
        
        print(f"\nTotal: {len(sessions)} project(s)\n")
    
    def info(self, message: str):
        """Display info message"""
        print(f"\n💬 {message}")
    
    def success(self, message: str):
        """Display success message"""
        print(f"\n✅ {message}")
    
    def error(self, message: str):
        """Display error message"""
        print(f"\n❌ Error: {message}")
    
    def warning(self, message: str):
        """Display warning message"""
        print(f"\n⚠️  Warning: {message}")
