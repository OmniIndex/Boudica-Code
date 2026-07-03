#!/usr/bin/env python3
"""
Boudica Code - Interactive AI-Powered Code Generation & Management CLI

Main entry point for the conversational CLI agent.
Handles session management, project orchestration, and user interaction.
"""

import sys
import os
import subprocess
import re
import shutil
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from session_manager import SessionManager
from project_manager import ProjectManager
from boudica_integration import BoudicaCodegen
from ui_handler import UIHandler
from git_integration import GitIntegration


def extract_filepath_from_command(command: str, project_manager: ProjectManager) -> Optional[str]:
    """Extract filepath from natural language command like 'modify the file src/main.cpp add color'"""
    
    # Look for common patterns: "file src/main.cpp", "src/main.cpp", "./path/file.ext"
    # Match: file/path with extension OR quoted paths
    patterns = [
        r'\bfile\s+([./\w\-]+\.\w+)',  # "file src/main.cpp"
        r'([./]?[\w\-/]+\.[\w]+)',      # Direct path like "src/main.cpp"
        r'"([^"]+\.[\w]+)"',             # Quoted path
        r"'([^']+\.[\w]+)'",            # Single quoted path
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            filepath = match.group(1)
            # Verify file exists in project
            try:
                project_dir = project_manager.project_dir
                if (project_dir / filepath).exists():
                    return filepath
            except:
                pass
    
    return None


def maybe_auto_commit_and_push(project_manager: ProjectManager, ui: UIHandler, action: str):
    """Apply optional auto-commit and auto-push according to git settings."""
    git = GitIntegration()

    if not git.check_git_installed() or not git.is_git_repo(project_manager.project_dir):
        return

    auto_commit = bool(git.get_setting('auto_commit', False))
    auto_push = bool(git.get_setting('auto_push', False))

    if not auto_commit:
        return

    if git.get_status(project_manager.project_dir) == "":
        return

    if not git.add_all(project_manager.project_dir):
        ui.error(f"Auto-commit skipped: {git.last_error}")
        return

    commit_message = f"Auto-commit: {action}"
    if git.commit(project_manager.project_dir, commit_message):
        ui.info(f"Git: committed changes ({commit_message})")
    else:
        ui.error(f"Auto-commit failed: {git.last_error}")
        return

    if auto_push:
        pushed, msg = git.safe_push(project_manager.project_dir)
        if pushed:
            ui.success(f"Git: {msg}")
        else:
            # Soft failure: remote/upstream may not exist for local-only projects.
            ui.info(f"Git push skipped: {msg}")


def handle_git_settings(ui: UIHandler, command: str):
    """Configure git automation settings (auto-commit and auto-push)."""
    git = GitIntegration()

    if not git.check_git_installed():
        ui.error("Git is not installed")
        return

    auto_commit = bool(git.get_setting('auto_commit', False))
    auto_push = bool(git.get_setting('auto_push', False))

    # Optional direct command mode:
    #   git settings auto-commit on|off
    #   git settings auto-push on|off
    parts = command.strip().lower().split()
    if len(parts) >= 4 and parts[0] == 'git' and parts[1] == 'settings':
        setting = parts[2]
        value_token = parts[3]
        desired = value_token in ('on', 'true', '1', 'yes')

        if setting == 'auto-commit':
            if git.set_setting('auto_commit', desired):
                ui.success(f"Git setting updated: auto_commit={desired}")
            else:
                ui.error(git.last_error or "Failed to update auto_commit")
            return
        if setting == 'auto-push':
            if desired and not auto_commit:
                ui.error("Enable auto-commit first before enabling auto-push")
                return
            if git.set_setting('auto_push', desired):
                ui.success(f"Git setting updated: auto_push={desired}")
            else:
                ui.error(git.last_error or "Failed to update auto_push")
            return

    ui.info(f"Current git automation settings: auto_commit={auto_commit}, auto_push={auto_push}")

    commit_choice = ui.confirm("Enable auto-commit after file changes?")
    auto_commit = bool(commit_choice)

    if auto_commit:
        push_choice = ui.confirm("Enable auto-push after auto-commit? (requires remote/upstream)")
        auto_push = bool(push_choice)
    else:
        auto_push = False

    ok_commit = git.set_setting('auto_commit', auto_commit)
    ok_push = git.set_setting('auto_push', auto_push)

    if ok_commit and ok_push:
        ui.success(f"Saved git automation settings: auto_commit={auto_commit}, auto_push={auto_push}")
    else:
        ui.error(git.last_error or "Failed to save git automation settings")


def main():
    """Main CLI entry point"""
    
    try:
        # Initialize managers
        session_db = Path.home() / "boudica_code" / "sessions.db"
        session_db.parent.mkdir(parents=True, exist_ok=True)
        
        session_manager = SessionManager(str(session_db))
        ui = UIHandler()
        boudica = BoudicaCodegen()
        
        # Check git installation and configuration
        git = GitIntegration()
        
        if not git.check_git_installed():
            ui.error("Git is not installed")
            ui.info("Please install Git to use BoudicaCode")
            ui.info("Visit: https://git-scm.com/downloads")
            sys.exit(1)
        
        # Check git configuration
        is_configured, error_msg = git.check_git_config()
        if not is_configured:
            ui.info("Git needs to be configured with your identity")
            user = ui.prompt_text("Git username: ")
            email = ui.prompt_text("Git email: ")
            
            if git.configure_git(user, email):
                ui.success(f"Git configured: {user} <{email}>")
            else:
                ui.error(f"Failed to configure git: {git.last_error}")
                sys.exit(1)
        
        # Main CLI loop
        ui.show_welcome()
        
        while True:
            choice = ui.show_main_menu()
            
            if choice == "new":
                handle_new_project(session_manager, ui, boudica)
            elif choice == "open":
                handle_open_project(session_manager, ui, boudica)
            elif choice == "list":
                handle_list_sessions(session_manager, ui)
            elif choice == "remove":
                handle_remove_project(session_manager, ui)
            elif choice == "exit":
                ui.show_goodbye()
                sys.exit(0)
            else:
                ui.error(f"Unknown choice: {choice}")
    
    except KeyboardInterrupt:
        ui.info("\nExiting Boudica Code...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_new_project(session_manager: SessionManager, ui: UIHandler, boudica: BoudicaCodegen):
    """Create a new project"""
    
    project_name = ui.prompt_text("Project name (alphanumeric + underscore)")
    if not project_name:
        return
    
    # Check if project already exists
    if session_manager.session_exists(project_name):
        ui.error(f"Project '{project_name}' already exists")
        if not ui.confirm("Overwrite?"):
            return
        # Delete old session to allow recreation
        session_manager.delete_session(project_name)
    
    # Prompt for stack selection
    stack = ui.prompt_stack_selection()
    if not stack:
        return
    
    # Create session
    session = session_manager.create_session(project_name, stack)
    if not session:
        ui.error("Failed to create project session")
        return
    
    project_dir = Path(session['project_path'])
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Scaffold project structure based on stack
    project_manager = ProjectManager(project_dir, stack)
    project_manager.scaffold_project()
    ui.info("✅ Project scaffolded with initial structure")
    
    ui.success(f"Created project: {project_name}")
    ui.info(f"Location: {project_dir}")
    
    # Enter interactive project session
    interactive_session(session_manager, ui, boudica, session)


def handle_open_project(session_manager: SessionManager, ui: UIHandler, boudica: BoudicaCodegen):
    """Open an existing project"""
    
    sessions = session_manager.list_sessions()
    if not sessions:
        ui.error("No projects found")
        return
    
    # Show list and select
    project_name = ui.prompt_session_selection(sessions)
    if not project_name:
        return
    
    session = session_manager.get_session(project_name)
    if not session:
        ui.error(f"Project '{project_name}' not found")
        return
    
    interactive_session(session_manager, ui, boudica, session)


def handle_list_sessions(session_manager: SessionManager, ui: UIHandler):
    """List all sessions"""
    
    sessions = session_manager.list_sessions()
    if not sessions:
        ui.info("No projects found")
        return
    
    ui.show_sessions_list(sessions)


def handle_remove_project(session_manager: SessionManager, ui: UIHandler):
    """Remove a project from the session list, optionally deleting local files."""
    sessions = session_manager.list_sessions()
    if not sessions:
        ui.info("No projects found")
        return

    project_name = ui.prompt_session_selection(sessions)
    if not project_name:
        return

    session = session_manager.get_session(project_name)
    if not session:
        ui.error(f"Project '{project_name}' not found")
        return

    project_path = Path(session['project_path'])
    ui.info(f"Selected project: {project_name}")
    ui.info(f"Path: {project_path}")

    if not ui.confirm("Remove this project from the project list?"):
        ui.info("Cancelled.")
        return

    delete_files = False
    if project_path.exists():
        delete_files = ui.confirm("Also delete this project's files from disk?")

    removed = session_manager.delete_session(project_name)
    if not removed:
        ui.error(f"Failed to remove project '{project_name}' from the list")
        return

    if delete_files:
        confirm_text = ui.prompt_text("Type DELETE to permanently remove project files")
        if confirm_text == "DELETE":
            try:
                shutil.rmtree(project_path)
                ui.success(f"Removed project '{project_name}' and deleted project files")
            except Exception as e:
                ui.error(f"Removed from list, but failed to delete files: {e}")
        else:
            ui.info("Removed from list; files were kept because confirmation text did not match")
    else:
        ui.success(f"Removed project '{project_name}' from the project list")


def interactive_session(session_manager: SessionManager, ui: UIHandler, 
                       boudica: BoudicaCodegen, session: dict):
    """Interactive project session loop"""
    
    project_name = session['name']
    project_dir = Path(session['project_path'])
    project_manager = ProjectManager(project_dir, session['stack'])
    
    # Track currently viewed file for context-aware edits
    current_file = None
    
    ui.success(f"\nEntered project: {project_name}")
    ui.info(f"Stack: {session['stack']}")
    
    while True:
        try:
            command = ui.prompt_project_command(project_name)
            if not command:
                continue
            
            if command.lower() in ["exit", "quit"]:
                if ui.confirm("Are you sure you want to exit this project?"):
                    ui.info("Exiting project session...")
                    break
                else:
                    ui.info("Staying in project...")
                    continue
            elif command.lower() in ["status"]:
                handle_status(project_manager, ui)
            elif command.lower() in ["ls", "list", "files", "browse"]:
                current_file = handle_list_files(project_manager, ui)
            elif command.lower().startswith("view"):
                current_file = handle_view_file(project_manager, ui, command)
            elif command.lower().startswith("delete") or command.lower().startswith("rm"):
                handle_delete_file(project_manager, ui, session_manager, session, command)
                current_file = None  # Clear file context after delete
            elif command.lower().startswith("restore"):
                handle_restore_file(project_manager, ui, session_manager, session, command)
                current_file = None
            elif command.lower().startswith("git settings"):
                handle_git_settings(ui, command)
            elif command.lower().startswith("create"):
                handle_create_file(session_manager, ui, boudica, session, project_manager, command)
            elif command.lower().startswith("edit"):
                handle_edit_file(session_manager, ui, boudica, session, project_manager, command)
                current_file = None  # Clear file context after edit
            elif command.lower().startswith("build"):
                handle_build(project_manager, ui, session_manager, session)
            elif command.lower().startswith("workflows"):
                handle_workflows(project_manager, ui)
            elif command.lower().startswith("debug") or command.lower().startswith("run"):
                handle_debug(project_manager, ui, session_manager, session, boudica)
            elif command.lower() == "help":
                ui.show_project_help()
            else:
                # Check if this looks like a natural language edit request for current file
                edit_keywords = ['change', 'modify', 'update', 'add', 'remove', 'fix', 'replace', 'implement', 'refactor', 'improve']
                is_edit_request = any(keyword in command.lower() for keyword in edit_keywords)
                
                if is_edit_request:
                    # Try to extract filepath from command (e.g., "modify the file src/main.cpp add color")
                    extracted_file = extract_filepath_from_command(command, project_manager)
                    
                    if extracted_file:
                        # Found file in command - use it directly
                        handle_edit_file_by_name(session_manager, ui, boudica, session, project_manager, 
                                                extracted_file, command)
                        current_file = None
                    elif current_file:
                        # No file specified but we have context from previous command
                        handle_edit_file_by_name(session_manager, ui, boudica, session, project_manager, 
                                                current_file, command)
                        current_file = None
                    else:
                        # No file found and no context - ask user
                        ui.error("Which file would you like to edit? (e.g., 'modify src/main.cpp add color')")
                        continue
                else:
                    # Check if this looks like a creation request (for a new file)
                    create_keywords = ['application', 'program', 'function', 'method', 'class', 'service', 
                                      'write', 'create', 'generate', 'build', 'design', 'implement', 'make',
                                      'code', 'script', 'file', 'module', 'component']
                    is_create_request = any(keyword in command.lower() for keyword in create_keywords)
                    
                    if is_create_request and not current_file:
                        # Route to create file handler
                        handle_create_file(session_manager, ui, boudica, session, project_manager, command)
                    else:
                        # General planning discussion
                        handle_planning_discussion(session_manager, ui, boudica, session, project_manager, command)
        
        except KeyboardInterrupt:
            ui.info("\nReturning to main menu...")
            break
        except Exception as e:
            ui.error(f"Error: {e}")



def open_file_in_editor(filepath: str, ui: UIHandler) -> bool:
    """Open file in user's default editor. Returns True if successful."""
    try:
        # Get the editor from environment or default to vi
        editor = os.environ.get('EDITOR', 'vi')
        
        # On Windows, try to use notepad if EDITOR not set
        if sys.platform == 'win32' and 'EDITOR' not in os.environ:
            editor = 'notepad'
        
        # Open file in editor
        subprocess.call([editor, filepath])
        return True
    except FileNotFoundError:
        ui.error(f"Editor '{editor}' not found. Edit the file manually: {filepath}")
        return False
    except Exception as e:
        ui.error(f"Could not open editor: {e}")
        return False


def handle_list_files(project_manager: ProjectManager, ui: UIHandler):
    """List all files in the project. Returns the viewed file path if user selects one."""
    files = project_manager.get_all_files()
    
    if not files:
        ui.info("No files in project yet.")
        return None
    
    ui.info("\nProject Files:")
    ui.info("=" * 60)
    
    for i, filepath in enumerate(files, 1):
        try:
            file_size = (project_manager.project_dir / filepath).stat().st_size
            size_str = f"{file_size} bytes" if file_size < 1024 else f"{file_size / 1024:.1f} KB"
            print(f"  [{i:2d}] {filepath:<40} ({size_str})")
        except:
            print(f"  [{i:2d}] {filepath:<40}")
    
    ui.info("=" * 60)
    
    # Ask if user wants to view or edit a file
    choice = ui.prompt_text("\nSelect file by number to view (or press Enter to skip)")
    if choice and choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            filepath = files[idx]
            code = project_manager.read_file(filepath)
            if code:
                ui.show_code_preview(code, filepath)
                if ui.confirm("Open this file in your editor?"):
                    full_path = project_manager.project_dir / filepath
                    open_file_in_editor(str(full_path), ui)
                return filepath  # Return the viewed file path for context
    
    return None  # No file was viewed


def handle_view_file(project_manager: ProjectManager, ui: UIHandler, command: str):
    """View a specific file. Returns the filepath if successful."""
    # Extract filename from "view <filename>" or "view src/main.cpp"
    filepath = command.replace("view", "").strip()
    
    if not filepath:
        filepath = ui.prompt_text("Which file do you want to view?")
        if not filepath:
            return None
    
    code = project_manager.read_file(filepath)
    if not code:
        ui.error(f"File not found: {filepath}")
        return None
    
    ui.show_code_preview(code, filepath)
    return filepath  # Return the viewed file path for context


def handle_delete_file(project_manager: ProjectManager, ui: UIHandler,
                      session_manager: SessionManager, session: dict, command: str):
    """Delete a file from the project"""
    # Extract filename from "delete <filename>" or "rm <filename>"
    filepath = command.replace("delete", "").replace("rm", "").strip()
    
    if not filepath:
        filepath = ui.prompt_text("Which file do you want to delete?")
        if not filepath:
            return
    
    # Check if file exists
    full_path = project_manager.project_dir / filepath
    if not full_path.exists():
        ui.error(f"File not found: {filepath}")
        return
    
    # Show what we're about to delete
    ui.info(f"File to delete: {filepath}")
    ui.info(f"Full path: {full_path}")
    
    if not ui.confirm("Are you sure you want to DELETE this file?"):
        ui.info("Cancelled.")
        return
    
    try:
        full_path.unlink()  # Delete the file
        ui.success(f"Deleted: {filepath}")
        session_manager.add_history(session['name'], f"delete {filepath}")
        maybe_auto_commit_and_push(project_manager, ui, f"delete {filepath}")
    except Exception as e:
        ui.error(f"Failed to delete file: {e}")


def handle_restore_file(project_manager: ProjectManager, ui: UIHandler,
                       session_manager: SessionManager, session: dict, command: str):
    """Restore a previously created backup"""
    restore_arg = command.replace("restore", "", 1).strip()
    filter_name = Path(restore_arg).name if restore_arg else None

    backups = project_manager.get_backups(filter_name)
    if not backups:
        ui.info("No backups found.")
        return

    ui.info("\nAvailable backups:")
    ui.info("=" * 80)
    for i, backup in enumerate(backups, 1):
        size_str = f"{backup['size']} B" if backup['size'] < 1024 else f"{backup['size'] / 1024:.1f} KB"
        print(f"  [{i:2d}] {backup['name']:<45} {size_str:>8}  {backup['mtime']}")
    ui.info("=" * 80)

    selection = ui.prompt_text("Select backup number to restore")
    if not selection or not selection.isdigit():
        ui.info("Cancelled.")
        return

    index = int(selection) - 1
    if index < 0 or index >= len(backups):
        ui.error("Invalid backup number")
        return

    selected_backup = backups[index]

    target_filepath = restore_arg if restore_arg else project_manager.guess_restore_target(selected_backup['name'])
    if target_filepath:
        ui.info(f"Suggested restore target: {target_filepath}")
        if not ui.confirm("Use this target path?"):
            target_filepath = ui.prompt_text("Enter target file path to restore into")
    else:
        target_filepath = ui.prompt_text("Enter target file path to restore into")

    if not target_filepath:
        ui.info("Cancelled.")
        return

    ui.info(f"Backup: {selected_backup['name']}")
    ui.info(f"Target: {target_filepath}")

    if not ui.confirm("Restore this backup?"):
        ui.info("Cancelled.")
        return

    success, result = project_manager.restore_backup(selected_backup['path'], target_filepath)
    if success:
        ui.success(f"Restored backup to: {result}")
        session_manager.add_history(session['name'], f"restore {selected_backup['name']} -> {target_filepath}")
        maybe_auto_commit_and_push(project_manager, ui, f"restore {target_filepath}")
    else:
        ui.error(f"Failed to restore backup: {result}")


def handle_status(project_manager: ProjectManager, ui: UIHandler):
    """Show project status"""
    status = project_manager.get_status()
    ui.show_project_status(status)


def handle_create_file(session_manager: SessionManager, ui: UIHandler, 
                       boudica: BoudicaCodegen, session: dict,
                       project_manager: ProjectManager, command: str):
    """Handle file creation request using NLP parsing"""
    
    # Remove "create" prefix if present (may have been routed here via NLP detection)
    request = command
    if request.lower().startswith("create"):
        request = request[6:].strip()  # Remove "create " prefix
    
    ui.info("Understanding your request...")
    
    # Use NLP to parse file path and description
    filepath, description = boudica.parse_create_request(request, session, project_manager)
    
    if not filepath:
        # Suggest appropriate file extension based on stack
        stack = session.get('stack', 'python').lower()
        if 'python' in stack:
            suggestion = "src/main.py"
        elif 'node' in stack or 'javascript' in stack:
            suggestion = "src/main.js"
        elif 'typescript' in stack:
            suggestion = "src/main.ts"
        elif 'java' in stack:
            suggestion = "src/Main.java"
        elif 'bash' in stack:
            suggestion = "src/script.sh"
        elif 'batch' in stack:
            suggestion = "src/script.bat"
        else:
            suggestion = "src/main.cpp"
        
        filepath = ui.prompt_text(f"What file should I create? (e.g., {suggestion})")
        if not filepath:
            return
    
    if not description:
        ui.info("Describe what this file should do (Enter for multiple lines, Escape+Enter to finish):")
        # Use multi-line prompt session for complex descriptions
        description = ui.prompt_session.prompt("description> ").strip()
        if not description:
            return
    
    ui.info(f"Generating: {filepath}")
    ui.info("Please wait... calling Boudica for code generation...")
    
    # Generate code
    code = boudica.generate_code(description, session, project_manager)
    if not code:
        ui.error(f"Failed to generate code: {boudica.last_error}")
        return
    
    # Show code to user
    ui.show_code_preview(code, filepath)
    
    if ui.confirm("Create this file?"):
        project_manager.create_file(filepath, code)
        # Update CMakeLists.txt if this is a C++ file
        project_manager.update_cmake_for_file(filepath)
        session_manager.add_history(session['name'], f"create {filepath}")
        ui.success(f"Created: {filepath}")
        maybe_auto_commit_and_push(project_manager, ui, f"create {filepath}")
        
        # Ask user if they want to edit the file
        full_path = project_manager.project_dir / filepath
        if ui.confirm("Open this file in your editor?"):
            open_file_in_editor(str(full_path), ui)



def handle_edit_file(session_manager: SessionManager, ui: UIHandler,
                     boudica: BoudicaCodegen, session: dict,
                     project_manager: ProjectManager, command: str):
    """Handle file edit request using NLP parsing"""
    
    # Remove "edit" prefix and clean up
    request = command.replace("edit", "").strip()
    
    ui.info("Understanding your request...")
    
    # Use NLP to parse file path and change description
    filepath, change_desc = boudica.parse_edit_request(request, session, project_manager)
    
    if not filepath:
        filepath = ui.prompt_text("Which file do you want to edit?")
        if not filepath:
            return
    
    # Read current file
    current_code = project_manager.read_file(filepath)
    if not current_code:
        ui.error(f"File not found: {filepath}")
        return
    
    if not change_desc:
        ui.info("What changes do you want to make? (Enter for multiple lines, Escape+Enter to finish):")
        # Use multi-line prompt session for complex descriptions
        change_desc = ui.prompt_session.prompt("changes> ").strip()
    if not change_desc:
            return
    
    ui.info(f"Editing: {filepath}")
    ui.info(f"Request: {change_desc}")
    
    # Check if request is already detailed (contains code snippets or is long)
    # Skip clarification if so - it's detailed enough
    is_detailed = (len(change_desc) > 50 or 
                   '<<' in change_desc or '>>' in change_desc or 
                   '::' in change_desc or '"' in change_desc)
    
    if is_detailed:
        ui.info("Request is detailed - proceeding with editing...")
        clarified_desc = change_desc
    else:
        ui.info("Please wait... clarifying request with NLP...")
        # Clarify request using Boudica's NLP to improve specificity
        clarified_desc = boudica.clarify_request(change_desc, session)
        if clarified_desc != change_desc:
            ui.info(f"Clarified: {clarified_desc}")
    
    # Validate that request doesn't contain embedded code snippets
    is_valid, error_msg = boudica.validate_edit_request(clarified_desc)
    if not is_valid:
        ui.error(error_msg)
        return
    
    ui.info("Calling Boudica for code modifications...")
    
    # Ask Boudica to modify code with clarified request
    new_code = boudica.edit_code(current_code, clarified_desc, filepath, session, project_manager)
    if not new_code:
        ui.error(f"Failed to generate edit: {boudica.last_error}")
        return
    
    # Show diff
    ui.show_diff(current_code, new_code, filepath)
    
    if ui.confirm("Apply changes?"):
        success, backup_path = project_manager.backup_and_edit(filepath, new_code)
        if success:
            session_manager.add_history(session['name'], f"edit {filepath}")
            ui.success(f"Updated: {filepath}")
            ui.info(f"Backup saved: {backup_path}")
            maybe_auto_commit_and_push(project_manager, ui, f"edit {filepath}")
            
            # Ask user if they want to edit the file further
            full_path = project_manager.project_dir / filepath
            if ui.confirm("Open this file in your editor?"):
                open_file_in_editor(str(full_path), ui)
        else:
            ui.error(f"Failed to apply changes: {backup_path}")


def handle_edit_file_by_name(session_manager: SessionManager, ui: UIHandler,
                            boudica: BoudicaCodegen, session: dict,
                            project_manager: ProjectManager,
                            filepath: str, change_request: str):
    """Handle file edit when filepath is already known (context-aware editing)"""
    
    # Read current file
    current_code = project_manager.read_file(filepath)
    if not current_code:
        ui.error(f"File not found: {filepath}")
        return
    
    ui.info(f"Editing: {filepath}")
    ui.info(f"Request: {change_request}")
    
    # Check if request is already detailed (contains code snippets or is long)
    # Skip clarification if so - it's detailed enough
    is_detailed = (len(change_request) > 50 or 
                   '<<' in change_request or '>>' in change_request or 
                   '::' in change_request or '"' in change_request)
    
    if is_detailed:
        ui.info("Request is detailed - proceeding with editing...")
        clarified_request = change_request
    else:
        ui.info("Please wait... clarifying request with NLP...")
        # Clarify request using Boudica's NLP to improve specificity
        clarified_request = boudica.clarify_request(change_request, session)
        if clarified_request != change_request:
            ui.info(f"Clarified: {clarified_request}")
    
    # Validate that request doesn't contain embedded code snippets
    is_valid, error_msg = boudica.validate_edit_request(clarified_request)
    if not is_valid:
        ui.error(error_msg)
        return
    
    ui.info("Calling Boudica for code modifications...")
    
    # Ask Boudica to modify code with clarified request
    new_code = boudica.edit_code(current_code, clarified_request, filepath, session, project_manager)
    if not new_code:
        ui.error(f"Failed to generate edit: {boudica.last_error}")
        return
    
    # Show diff
    ui.show_diff(current_code, new_code, filepath)
    
    if ui.confirm("Apply changes?"):
        success, backup_path = project_manager.backup_and_edit(filepath, new_code)
        if success:
            session_manager.add_history(session['name'], f"edit {filepath}")
            ui.success(f"Updated: {filepath}")
            ui.info(f"Backup saved: {backup_path}")
            maybe_auto_commit_and_push(project_manager, ui, f"edit {filepath}")
            
            # Ask user if they want to edit the file further
            full_path = project_manager.project_dir / filepath
            if ui.confirm("Open this file in your editor?"):
                open_file_in_editor(str(full_path), ui)
        else:
            ui.error(f"Failed to apply changes: {backup_path}")



def handle_build(project_manager: ProjectManager, ui: UIHandler,
                session_manager: SessionManager, session: dict):
    """Handle build/compile request"""
    
    ui.info("Building project...")
    ui.info("Please wait... this may take a few moments...")
    result = project_manager.build()
    
    if result['success']:
        ui.success("Build successful!")
        session_manager.add_history(session['name'], "build succeeded")
    else:
        ui.error("Build failed!")
        ui.show_build_errors(result['errors'])
        
        if ui.confirm("Attempt automatic fix?"):
            ui.info("Analyzing build errors...")
            
            # Import here to avoid circular imports
            from boudica_integration import BoudicaCodegen
            boudica = BoudicaCodegen()
            
            # Get full error output
            error_summary = '\n'.join(result['errors'][:5])  # First 5 errors for context
            
            # Check for linker errors first (they require library installation)
            linker_error_msg = boudica._handle_linker_error(error_summary, session, project_manager)
            
            if linker_error_msg:
                # This is a linker error - show installation instructions
                ui.info("")
                ui.show_ai_response(linker_error_msg)
                ui.info("")
                
                # Rebuild after user installs library
                if ui.confirm("Rebuild after installing the library?"):
                    ui.info("Rebuilding...")
                    result = project_manager.build()
                    if result['success']:
                        ui.success("Build successful!")
                        session_manager.add_history(session['name'], "build succeeded after installing library")
                    else:
                        ui.error("Build still failing. Check installation and try again.")
            else:
                # Try to fix code-level errors
                # Extract first file from error (usually in format: /path/to/file.cpp:line: error)
                error_line = result['errors'][0] if result['errors'] else ""
                file_match = re.match(r'([^:]+):', error_line)
                
                if file_match:
                    error_file = file_match.group(1)
                    
                    # Check if file exists
                    if Path(error_file).exists():
                        try:
                            current_code = Path(error_file).read_text()
                            
                            # Try to fix using Boudica
                            fixed_code = boudica.fix_build_error(
                                error_summary,
                                error_file,
                                current_code,
                                session,
                                project_manager
                            )
                            
                            if fixed_code:
                                # Show diff
                                ui.show_diff(current_code, fixed_code, error_file)
                                
                                if ui.confirm("Apply fix?"):
                                    # Apply the fix
                                    project_manager.backup_and_edit(error_file, fixed_code)
                                    ui.success("Fix applied. Rebuilding...")
                                    maybe_auto_commit_and_push(project_manager, ui, f"build fix {error_file}")
                                    
                                    # Retry build
                                    result = project_manager.build()
                                    if result['success']:
                                        ui.success("Build successful after fix!")
                                        session_manager.add_history(session['name'], "build fixed and succeeded")
                                    else:
                                        ui.error("Build still failing after fix")
                            else:
                                ui.error(f"Could not generate fix: {boudica.last_error if hasattr(boudica, 'last_error') else 'Unknown error'}")
                        except Exception as e:
                            ui.error(f"Error attempting fix: {str(e)}")
                    else:
                        ui.error(f"Could not find file: {error_file}")
                else:
                    ui.error("Could not extract file path from error message")


def handle_workflows(project_manager: ProjectManager, ui: UIHandler):
    """Handle GitHub Actions workflow generation"""
    
    ui.info("Generating GitHub Actions workflows...")
    
    try:
        if project_manager.generate_workflows():
            ui.success("✅ GitHub Actions workflows generated successfully!")
            ui.info("Created workflows in .github/workflows/:")
            ui.info("  • build.yml  - Builds on push to main/develop")
            ui.info("  • test.yml   - Runs tests on pull requests")
            ui.info("  • deploy.yml - Template for manual deployments")
            ui.info("\nNext steps:")
            ui.info("  1. Push to GitHub: git push -u origin main")
            ui.info("  2. Workflows will run automatically on push")
            ui.info("  3. Edit deploy.yml to configure your deployment steps")
        else:
            ui.error("Failed to generate workflows")
    except Exception as e:
        ui.error(f"Error generating workflows: {str(e)}")


def handle_debug(project_manager: ProjectManager, ui: UIHandler,
                session_manager: SessionManager, session: dict,
                boudica: BoudicaCodegen):
    """Handle debug/run with debugger request"""
    
    from debugger import create_debugger_session
    
    ui.info("Setting up debugger...")
    
    # Create debugger session for the project language
    language = session.get('stack', 'cpp').lower()
    if language not in ['cpp', 'c++', 'python', 'javascript', 'java']:
        ui.error(f"Debugger not yet supported for {language}")
        return
    
    # Normalize language name
    lang_map = {'c++': 'cpp'}
    language = lang_map.get(language, language)
    
    debugger = create_debugger_session(language, project_manager.project_dir)
    if not debugger:
        ui.error(f"Could not find executable for {language} project")
        return
    
    ui.info(f"Project: {project_manager.project_dir}")
    ui.info(f"Executable: {debugger.executable_path}")
    ui.info(f"Source files: {len(debugger.source_files)}")
    
    # Interactive breakpoint setup
    while True:
        ui.info("\nDebugger options:")
        ui.info("  1. Set breakpoint")
        ui.info("  2. List breakpoints")
        ui.info("  3. Run (start debugging)")
        ui.info("  4. Back to main menu")
        
        choice = ui.prompt_text("Choice (1-4): ")
        
        if choice == '1':
            filepath = ui.prompt_text("Enter file path (relative to project): ")
            line_str = ui.prompt_text("Enter line number: ")
            try:
                line = int(line_str)
                if debugger.add_breakpoint(filepath, line):
                    ui.success(f"Breakpoint set at {filepath}:{line}")
                else:
                    ui.error(f"File not found: {filepath}")
            except ValueError:
                ui.error("Invalid line number")
        
        elif choice == '2':
            bps = debugger.list_breakpoints()
            if bps:
                ui.info("Current breakpoints:")
                for filepath, lines in bps.items():
                    ui.info(f"  {filepath}: {', '.join(map(str, lines))}")
            else:
                ui.info("No breakpoints set (will run until crash)")
        
        elif choice == '3':
            ui.info("Running with debugger...")
            success, output = debugger.run()
            
            ui.show_debug_output(output, language)
            
            crash_info = debugger.extract_crash_info()
            if crash_info['crashed']:
                ui.error(f"Program crashed: {crash_info['error_type']}")
                
                if ui.confirm("Analyze crash with AI?"):
                    # Read source file for context
                    source_files = debugger.source_files
                    source_code = ""
                    if source_files:
                        try:
                            source_code = Path(source_files[0]).read_text()[:2000]
                        except:
                            pass
                    
                    ui.info("Analyzing crash...")
                    analysis = boudica.analyze_crash(output, source_code, language, session)
                    if analysis:
                        ui.show_ai_response(analysis)
                        
                        if ui.confirm("Apply AI suggestions?"):
                            ui.info("Use 'edit' command to apply suggested fixes")
                    else:
                        ui.error(f"Could not analyze: {boudica.last_error}")
            else:
                ui.success("Program ran successfully!")
            
            break
        
        elif choice == '4':
            break
        
        else:
            ui.error("Invalid choice")


def handle_planning_discussion(session_manager: SessionManager, ui: UIHandler,
                               boudica: BoudicaCodegen, session: dict,
                               project_manager: ProjectManager, prompt: str):
    """Handle general planning/discussion with AI"""
    
    ui.info("Consulting with Boudica...")
    ui.info("Please wait... processing your request...")
    
    response = boudica.chat_planning(prompt, session, project_manager)
    if not response:
        ui.error(f"No response from AI: {boudica.last_error}")
        return
    
    ui.show_ai_response(response)
    session_manager.add_history(session['name'], f"discussion: {prompt[:50]}")


if __name__ == "__main__":
    main()
