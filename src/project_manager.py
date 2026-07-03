"""
Project Manager - Handles project structure, type detection, file operations, and backups
"""

import os
import json
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

from git_integration import GitIntegration, get_language_gitignore, get_readme_template
from workflow_generator import WorkflowGenerator


class ProjectType(Enum):
    """Supported project types"""
    PYTHON = "python"
    NODEJS = "nodejs"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPLUSPLUS = "cpp"
    BASH = "bash"
    WINDOWS_BATCH = "batch"
    MIXED = "mixed"  # Multi-language project


def ensure_trailing_newline(content: str) -> str:
    """Ensure content ends with exactly one newline character"""
    if not content:
        return "\n"
    # Remove any trailing whitespace/newlines, then add back one newline
    return content.rstrip() + "\n"


def get_file_extension(filepath: str) -> str:
    """Get file extension from filepath"""
    return Path(filepath).suffix.lower()


def load_templates() -> Tuple[Optional[str], Optional[str]]:
    """Load header and footer templates from ~/boudica_code/
    
    Returns:
        Tuple of (header_template, footer_template) or (None, None) if not found
    """
    template_dir = Path.home() / "boudica_code"
    header_file = template_dir / "header_template"
    footer_file = template_dir / "footer_template"
    
    header = None
    footer = None
    
    if header_file.exists():
        try:
            with open(header_file, 'r') as f:
                header = f.read().strip()
        except Exception:
            pass
    
    if footer_file.exists():
        try:
            with open(footer_file, 'r') as f:
                footer = f.read().strip()
        except Exception:
            pass
    
    return header, footer


def format_template_with_comments(template: str, filepath: str) -> str:
    """Format template with appropriate comment syntax for the file type
    
    Args:
        template: The template text to format
        filepath: The filepath to determine comment style
    
    Returns:
        Template wrapped in appropriate comment syntax with placeholders replaced
    """
    ext = get_file_extension(filepath)
    
    # Replace placeholders in template
    processed_template = template
    
    # Replace <date> with current date and time
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    processed_template = processed_template.replace("<date>", current_datetime)
    
    # Replace <file> with the filename (without path)
    filename = Path(filepath).name
    processed_template = processed_template.replace("<file>", filename)
    
    # Comment styles for different languages
    if ext in ['.py', '.sh']:
        # Python, Bash: use # for comments
        lines = processed_template.split('\n')
        commented = '\n'.join(f"# {line}" if line.strip() else "#" for line in lines)
        return commented
    
    elif ext in ['.java']:
        # Java: use // for comments
        lines = processed_template.split('\n')
        commented = '\n'.join(f"// {line}" if line.strip() else "//" for line in lines)
        return commented
    
    elif ext in ['.cpp', '.h', '.hpp', '.ts', '.tsx', '.js', '.jsx']:
        # C++, TypeScript, JavaScript: use // for comments
        lines = processed_template.split('\n')
        commented = '\n'.join(f"// {line}" if line.strip() else "//" for line in lines)
        return commented
    
    elif ext in ['.bat', '.cmd']:
        # Windows Batch: use REM for comments
        lines = processed_template.split('\n')
        commented = '\n'.join(f"REM {line}" if line.strip() else "REM" for line in lines)
        return commented
    
    else:
        # Default: treat as text file, use # style
        lines = processed_template.split('\n')
        commented = '\n'.join(f"# {line}" if line.strip() else "#" for line in lines)
        return commented


class ProjectManager:
    """Manages project structure, file operations, and builds"""
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        ProjectType.PYTHON: [
            'requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile',
            'poetry.lock', '*.py'
        ],
        ProjectType.NODEJS: [
            'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'
        ],
        ProjectType.TYPESCRIPT: [
            'tsconfig.json', '*.ts', '*.tsx'
        ],
        ProjectType.JAVA: [
            'pom.xml', 'build.gradle', 'build.gradle.kts', '*.java'
        ],
        ProjectType.CPLUSPLUS: [
            'CMakeLists.txt', 'Makefile', '*.cpp', '*.h', '*.hpp',
            'conanfile.txt'
        ],
        ProjectType.BASH: [
            '*.sh', '.bashrc', '.bash_profile'
        ],
        ProjectType.WINDOWS_BATCH: [
            '*.bat', '*.cmd'
        ]
    }
    
    BUILD_COMMANDS = {
        ProjectType.PYTHON: {
            'build': ['python', '-m', 'py_compile', '.'],
            'test': ['python', '-m', 'pytest'],
            'install': ['pip', 'install', '-r', 'requirements.txt']
        },
        ProjectType.NODEJS: {
            'build': ['npm', 'run', 'build'],
            'test': ['npm', 'test'],
            'install': ['npm', 'install']
        },
        ProjectType.TYPESCRIPT: {
            'build': ['tsc'],
            'test': ['npm', 'test'],
            'install': ['npm', 'install']
        },
        ProjectType.JAVA: {
            'build': ['mvn', 'clean', 'compile'],
            'test': ['mvn', 'test'],
            'install': ['mvn', 'dependency:resolve']
        },
        ProjectType.CPLUSPLUS: {
            'build': ['cmake', '--build', '.'],
            'test': ['cmake', '--build', '.', '--target', 'test'],
            'install': ['cmake', '--install', '.']
        },
        ProjectType.BASH: {
            'build': ['bash', '-n', 'src/main.sh'],  # Syntax check
            'test': ['bash', 'src/main.sh'],
            'install': []
        },
        ProjectType.WINDOWS_BATCH: {
            'build': [],  # No syntax check available for .bat
            'test': [],
            'install': []
        }
    }
    
    def __init__(self, project_dir: Path, stack: str):
        self.project_dir = Path(project_dir)
        self.stack = stack
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .boudica_project.json if it doesn't exist
        self._init_project_config()
    
    def _init_project_config(self):
        """Initialize project configuration file"""
        config_path = self.project_dir / ".boudica_project.json"
        
        if not config_path.exists():
            config = {
                'name': self.project_dir.name,
                'stack': self.stack,
                'created': datetime.now().isoformat(),
                'version': '0.0.1',
                'languages': self._detect_languages(),
                'boudica_config': {
                    'max_fix_attempts': 5,
                    'conversation_context': True
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
    
    def _detect_languages(self) -> List[str]:
        """Detect languages in project based on stack"""
        languages = []
        
        if self.stack in ['fullstack-node', 'fullstack-python', 'fullstack-java']:
            if 'node' in self.stack:
                languages.extend(['javascript', 'typescript'])
            elif 'python' in self.stack:
                languages.append('python')
            elif 'java' in self.stack:
                languages.append('java')
        else:
            # Map single language
            stack_to_lang = {
                'python': ['python'],
                'nodejs': ['javascript', 'typescript'],
                'typescript': ['typescript', 'javascript'],
                'java': ['java'],
                'cpp': ['cpp']
            }
            languages = stack_to_lang.get(self.stack, [self.stack])
        
        return languages
    
    def detect_project_type(self) -> ProjectType:
        """Auto-detect primary project type"""
        detected_types = set()
        
        for root, dirs, files in os.walk(self.project_dir):
            # Skip hidden directories and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            
            for file in files:
                for proj_type, patterns in self.LANGUAGE_PATTERNS.items():
                    for pattern in patterns:
                        if pattern.startswith('*'):
                            # Handle wildcard patterns
                            if file.endswith(pattern[1:]):
                                detected_types.add(proj_type)
                        elif file == pattern:
                            detected_types.add(proj_type)
        
        if len(detected_types) > 1:
            return ProjectType.MIXED
        elif detected_types:
            return list(detected_types)[0]
        else:
            # Default based on stack
            if 'python' in self.stack:
                return ProjectType.PYTHON
            elif 'node' in self.stack:
                return ProjectType.NODEJS
            else:
                return ProjectType.PYTHON
    
    def get_all_files(self) -> list:
        """Get list of all files in the project (excluding hidden/build dirs)"""
        files = []
        
        # Directories to skip
        skip_dirs = {'.git', '.boudica', '__pycache__', 'node_modules', 'build', 'dist', 'venv', '.venv', '.env', 'target'}
        
        # Walk project directory
        for root, dirs, filenames in os.walk(self.project_dir):
            # Remove skip directories in-place to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for filename in filenames:
                # Skip hidden files and common build artifacts
                if filename.startswith('.'):
                    continue
                
                full_path = Path(root) / filename
                # Get relative path from project root
                rel_path = full_path.relative_to(self.project_dir)
                files.append(str(rel_path))
        
        # Sort files alphabetically
        files.sort()
        return files
    
    def get_status(self) -> Dict:
        """Get project status information"""
        proj_type = self.detect_project_type()
        config_path = self.project_dir / ".boudica_project.json"
        
        config = {}
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        
        # Count files
        file_count = sum(1 for _ in self.project_dir.rglob('*') 
                        if _.is_file() and not _.name.startswith('.'))
        
        return {
            'name': self.project_dir.name,
            'type': proj_type.value,
            'stack': self.stack,
            'files': file_count,
            'languages': config.get('languages', []),
            'path': str(self.project_dir)
        }
    
    def create_file(self, filepath: str, content: str) -> bool:
        """Create a new file in the project with optional header/footer templates"""
        file_path = self.project_dir / filepath
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load templates if they exist
            header_template, footer_template = load_templates()
            
            # Build final content with templates
            final_content = content
            
            # Add header template if it exists (skip for certain files)
            if header_template and not self._should_skip_templates(filepath):
                formatted_header = format_template_with_comments(header_template, filepath)
                final_content = formatted_header + "\n\n" + final_content
            
            # Add footer template if it exists (skip for certain files)
            if footer_template and not self._should_skip_templates(filepath):
                formatted_footer = format_template_with_comments(footer_template, filepath)
                final_content = final_content + "\n\n" + formatted_footer
            
            # Ensure content ends with proper newline
            normalized_content = ensure_trailing_newline(final_content)
            with open(file_path, 'w') as f:
                f.write(normalized_content)
            return True
        except Exception as e:
            print(f"Error creating file: {e}")
            return False
    
    def _should_skip_templates(self, filepath: str) -> bool:
        """Check if file should skip template injection
        
        Skip templates for config files, build files, and non-code files
        """
        skip_files = [
            'CMakeLists.txt', 'package.json', 'setup.py', 'pom.xml',
            '.gitignore', 'README.md', 'requirements.txt',
            'tsconfig.json', '.boudica_project.json', 'Makefile'
        ]
        
        filename = Path(filepath).name
        
        # Skip if filename matches skip list
        if filename in skip_files:
            return True
        
        # Skip if it's a config or build file
        if filename.startswith('.') and filename != '.gitignore':
            return True
        
        return False
    
    def read_file(self, filepath: str) -> Optional[str]:
        """Read file contents"""
        file_path = self.project_dir / filepath
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def generate_workflows(self) -> bool:
        """Generate GitHub Actions workflows for the project
        
        Can be called for new or existing projects
        
        Returns:
            True if successful
        """
        self._generate_workflows()
        return True
    
    def _write_file(self, filepath: Path, content: str) -> bool:
        """Helper method to write file with proper formatting and optional templates"""
        try:
            # Load templates if they exist
            header_template, footer_template = load_templates()
            
            # Build final content with templates
            final_content = content
            
            # Add header template if it exists (skip for certain files)
            file_str = str(filepath)
            if header_template and not self._should_skip_templates(file_str):
                formatted_header = format_template_with_comments(header_template, file_str)
                final_content = formatted_header + "\n\n" + final_content
            
            # Add footer template if it exists (skip for certain files)
            if footer_template and not self._should_skip_templates(file_str):
                formatted_footer = format_template_with_comments(footer_template, file_str)
                final_content = final_content + "\n\n" + formatted_footer
            
            # Ensure content ends with proper newline
            normalized_content = ensure_trailing_newline(final_content)
            with open(filepath, 'w') as f:
                f.write(normalized_content)
            return True
        except Exception as e:
            print(f"Error writing file: {e}")
            return False
    
    def backup_and_edit(self, filepath: str, new_content: str) -> Tuple[bool, str]:
        """Create timestamped backup and edit file"""
        file_path = self.project_dir / filepath
        
        if not file_path.exists():
            return False, "File not found"
        
        # Create backups directory
        backups_dir = self.project_dir / ".backups"
        backups_dir.mkdir(exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{timestamp}_{file_path.name}"
        backup_path = backups_dir / backup_name
        
        try:
            # Copy original to backup
            shutil.copy2(file_path, backup_path)
            
            # Ensure new content ends with proper newline, then write
            normalized_content = ensure_trailing_newline(new_content)
            with open(file_path, 'w') as f:
                f.write(normalized_content)
            
            return True, str(backup_path)
        except Exception as e:
            return False, str(e)
    
    def get_backups(self, filepath: Optional[str] = None) -> List[Dict]:
        """List backups for a file or all files"""
        backups_dir = self.project_dir / ".backups"
        
        if not backups_dir.exists():
            return []
        
        backups = []
        for backup_file in sorted(backups_dir.iterdir(), reverse=True):
            if backup_file.is_file():
                if filepath is None or filepath in backup_file.name:
                    backups.append({
                        'path': str(backup_file),
                        'name': backup_file.name,
                        'size': backup_file.stat().st_size,
                        'mtime': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                    })
        
        return backups

    def _extract_original_name_from_backup(self, backup_name: str) -> Optional[str]:
        """Extract original filename from backup name format: YYYYMMDD_HHMMSS_filename"""
        match = re.match(r'^\d{8}_\d{6}_(.+)$', backup_name)
        if not match:
            return None
        return match.group(1)

    def guess_restore_target(self, backup_name: str) -> Optional[str]:
        """Guess the target file path for a backup based on filename match in project"""
        original_name = self._extract_original_name_from_backup(backup_name)
        if not original_name:
            return None

        matches = []
        for path in self.project_dir.rglob(original_name):
            if not path.is_file():
                continue
            if ".backups" in path.parts:
                continue
            if ".git" in path.parts:
                continue
            matches.append(path)

        if len(matches) == 1:
            return str(matches[0].relative_to(self.project_dir))

        return None

    def restore_backup(self, backup_path: str, target_filepath: str) -> Tuple[bool, str]:
        """Restore a backup file into a target file path"""
        backup_file = Path(backup_path)
        if not backup_file.exists() or not backup_file.is_file():
            return False, "Backup file not found"

        target_path = self.project_dir / target_filepath
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Keep a safety copy of current target before overwrite.
            if target_path.exists():
                backups_dir = self.project_dir / ".backups"
                backups_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_restore_name = f"{timestamp}_pre_restore_{target_path.name}"
                pre_restore_path = backups_dir / pre_restore_name
                shutil.copy2(target_path, pre_restore_path)

            shutil.copy2(backup_file, target_path)
            return True, str(target_path)
        except Exception as e:
            return False, str(e)
    
    def build(self) -> Dict:
        """Build/compile the project"""
        proj_type = self.detect_project_type()
        
        if proj_type == ProjectType.MIXED:
            # Build all language types
            return self._build_mixed()
        else:
            return self._build_single(proj_type)
    
    def _build_single(self, proj_type: ProjectType) -> Dict:
        """Build single language project"""
        
        if proj_type not in self.BUILD_COMMANDS:
            return {
                'success': False,
                'errors': [f"Unsupported project type: {proj_type.value}"],
                'output': ''
            }
        
        # Special handling for C++ projects
        if proj_type == ProjectType.CPLUSPLUS:
            cmake_file = self.project_dir / "CMakeLists.txt"
            if cmake_file.exists():
                # Use CMake build system
                return self._build_cpp_cmake()
            else:
                # Single file C++ project - use g++ directly
                return self._build_cpp_simple()
        
        commands = self.BUILD_COMMANDS[proj_type]
        build_cmd = commands.get('build')
        
        if not build_cmd:
            return {
                'success': False,
                'errors': ['No build command defined'],
                'output': ''
            }
        
        try:
            result = subprocess.run(
                build_cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'errors': [],
                    'output': result.stdout
                }
            else:
                return {
                    'success': False,
                    'errors': self._parse_build_errors(result.stderr, proj_type),
                    'output': result.stderr
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'errors': ['Build timeout (120s)'],
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)],
                'output': ''
            }
    
    def _build_mixed(self) -> Dict:
        """Build multi-language project - builds in sequence"""
        
        all_errors = []
        all_output = []
        
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # Detect type in this directory
            for file in files:
                if file == 'CMakeLists.txt':
                    result = self._build_single(ProjectType.CPLUSPLUS)
                    if not result['success']:
                        all_errors.extend(result['errors'])
                    all_output.append(result['output'])
                    break
                elif file == 'package.json':
                    result = self._build_single(ProjectType.NODEJS)
                    if not result['success']:
                        all_errors.extend(result['errors'])
                    all_output.append(result['output'])
                    break
                elif file == 'pom.xml':
                    result = self._build_single(ProjectType.JAVA)
                    if not result['success']:
                        all_errors.extend(result['errors'])
                    all_output.append(result['output'])
                    break
        
        return {
            'success': len(all_errors) == 0,
            'errors': all_errors,
            'output': '\n'.join(all_output)
        }
    
    def _parse_build_errors(self, stderr: str, proj_type: ProjectType) -> List[str]:
        """Parse build errors by project type"""
        errors = []
        
        for line in stderr.split('\n'):
            if line.strip() and any(keyword in line.lower() 
                                   for keyword in ['error', 'failed', 'exception']):
                errors.append(line.strip())
        
        return errors if errors else [stderr[:200] + '...'] if stderr else ['Unknown error']
    
    def _build_cpp_simple(self) -> Dict:
        """Build C++ project without CMakeLists.txt - use g++ to compile all .cpp files"""
        
        # Find all .cpp files
        cpp_files = list(self.project_dir.glob('*.cpp')) + list(self.project_dir.glob('src/*.cpp'))
        
        if not cpp_files:
            return {
                'success': False,
                'errors': ['No .cpp files found in project'],
                'output': ''
            }
        
        # Build executable name from project directory
        exe_name = f"{self.project_dir.name}"
        output_file = self.project_dir / exe_name
        
        # Compile all .cpp files
        compile_cmd = ['g++', '-std=c++17', '-o', str(output_file)] + [str(f) for f in cpp_files]
        
        try:
            result = subprocess.run(
                compile_cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'errors': [],
                    'output': f"Successfully compiled: {exe_name}"
                }
            else:
                return {
                    'success': False,
                    'errors': self._parse_build_errors(result.stderr, ProjectType.CPLUSPLUS),
                    'output': result.stderr
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'errors': ['Compilation timeout (120s)'],
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)],
                'output': ''
            }
    
    def _build_cpp_cmake(self) -> Dict:
        """Build C++ project with CMake - creates build folder, runs cmake and make"""
        
        import multiprocessing
        
        build_dir = self.project_dir / "build"
        
        try:
            # Step 1: Remove stale build dir to force clean rebuild
            if build_dir.exists():
                shutil.rmtree(build_dir)
            
            # Step 2: Create build directory
            build_dir.mkdir(exist_ok=True)
            
            # Step 3: Run cmake .. from within build directory
            cmake_cmd = ['cmake', '..']
            result = subprocess.run(
                cmake_cmd,
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'errors': ['CMake configuration failed'] + self._parse_build_errors(result.stderr, ProjectType.CPLUSPLUS),
                    'output': result.stderr
                }
            
            # Step 4: Run make with parallel jobs
            nproc = multiprocessing.cpu_count()
            make_cmd = ['make', f'-j{nproc}']
            result = subprocess.run(
                make_cmd,
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=300,
                shell=False
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'errors': [],
                    'output': f"Build successful. Executable: {build_dir / self.project_dir.name}"
                }
            else:
                # Capture both stderr and stdout for compilation errors
                all_output = result.stderr + '\n' + result.stdout
                errors = self._parse_build_errors(all_output, ProjectType.CPLUSPLUS)
                return {
                    'success': False,
                    'errors': errors,
                    'output': all_output
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'errors': ['Build timeout (300s)'],
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Build error: {str(e)}'],
                'output': ''
            }
    
    def scaffold_project(self):
        """Scaffold project structure based on stack type"""
        if self.stack == 'cpp':
            self.scaffold_cpp_project()
        elif self.stack == 'python':
            self.scaffold_python_project()
        elif self.stack == 'nodejs':
            self.scaffold_nodejs_project()
        elif self.stack == 'typescript':
            self.scaffold_typescript_project()
        elif self.stack == 'java':
            self.scaffold_java_project()
        elif self.stack == 'bash':
            self.scaffold_bash_project()
        elif self.stack == 'batch':
            self.scaffold_windows_batch_project()
        elif self.stack == 'fullstack-node':
            self.scaffold_fullstack_node()
        elif self.stack == 'fullstack-python':
            self.scaffold_fullstack_python()
        elif self.stack == 'fullstack-java':
            self.scaffold_fullstack_java()
        
        # Add standardized files to all projects
        self._add_standardized_files()
        
        # Initialize git repository
        self._init_git_repo()
        
        # Generate GitHub Actions workflows
        self._generate_workflows()
    
    def _add_standardized_files(self):
        """Add .gitignore and README.md to all projects"""
        
        # Determine language for .gitignore
        language_map = {
            'python': 'python',
            'nodejs': 'nodejs',
            'typescript': 'typescript',
            'cpp': 'cpp',
            'java': 'java',
            'bash': 'bash',
            'batch': 'batch',
        }
        language = language_map.get(self.stack, 'bash')
        
        # Add .gitignore if not already present
        gitignore_path = self.project_dir / '.gitignore'
        if not gitignore_path.exists():
            gitignore_content = get_language_gitignore(language)
            self._write_file(gitignore_path, gitignore_content)
        
        # Add README.md if not already present
        readme_path = self.project_dir / 'README.md'
        if not readme_path.exists():
            readme_content = get_readme_template(
                self.project_dir.name,
                language,
                is_public=True  # Default to public
            )
            self._write_file(readme_path, readme_content)
    
    def _init_git_repo(self):
        """Initialize git repository for new project"""
        git = GitIntegration()
        
        # Only init if git is available and repo doesn't exist
        if not git.check_git_installed():
            print("⚠️  Git not found - skipping repository initialization")
            return
        
        if git.is_git_repo(self.project_dir):
            return  # Already a git repo
        
        # Initialize git repo
        if git.init_repo(self.project_dir):
            print(f"✅ Initialized git repository")
            
            # Add all files
            git.add_all(self.project_dir)
            
            # First commit
            if git.commit(self.project_dir, "Initial commit - Project scaffolded by BoudicaCode"):
                print(f"✅ Initial commit created")
            else:
                print(f"⚠️  Could not create initial commit: {git.last_error}")
        else:
            print(f"⚠️  Could not initialize git repo: {git.last_error}")
    
    def _generate_workflows(self):
        """Generate GitHub Actions workflows"""
        # Map project stack to ProjectType enum
        stack_to_type = {
            'python': 'PYTHON',
            'nodejs': 'NODEJS',
            'typescript': 'TYPESCRIPT',
            'cpp': 'CPLUSPLUS',
            'java': 'JAVA',
            'bash': 'BASH',
            'batch': 'WINDOWS_BATCH',
        }
        
        project_type_str = stack_to_type.get(self.stack, 'PYTHON')
        
        try:
            project_type = ProjectType[project_type_str]
            generator = WorkflowGenerator(self.project_dir, project_type)
            
            if generator.create_workflows():
                print(f"✅ Generated GitHub Actions workflows")
            else:
                print(f"⚠️  Could not generate workflows")
        except Exception as e:
            print(f"⚠️  Error generating workflows: {e}")
    
    def scaffold_cpp_project(self):
        """Scaffold a C++ project with CMakeLists.txt"""
        
        cmake_content = f"""cmake_minimum_required(VERSION 3.10)
project({self.project_dir.name})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable debug symbols for debugger support
set(CMAKE_CXX_FLAGS "${{CMAKE_CXX_FLAGS}} -g")
set(CMAKE_BUILD_TYPE Debug)

# Find all source files
file(GLOB SOURCES "src/*.cpp" "*.cpp")

# Create executable
add_executable({self.project_dir.name} ${{SOURCES}})

# Include directories if needed
target_include_directories({self.project_dir.name} PRIVATE ${{CMAKE_CURRENT_SOURCE_DIR}}/include)
"""
        
        cmake_file = self.project_dir / "CMakeLists.txt"
        self._write_file(cmake_file, cmake_content)
        
        # Create src directory
        (self.project_dir / "src").mkdir(exist_ok=True)
        (self.project_dir / "include").mkdir(exist_ok=True)
    
    def scaffold_python_project(self):
        """Scaffold a Python project with requirements.txt and setup.py"""
        
        # Create requirements.txt
        req_content = """# Project dependencies
"""
        self._write_file(self.project_dir / "requirements.txt", req_content)
        
        # Create setup.py
        setup_content = f"""from setuptools import setup, find_packages

setup(
    name='{self.project_dir.name}',
    version='0.0.1',
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        # Add dependencies from requirements.txt
    ],
)
"""
        self._write_file(self.project_dir / "setup.py", setup_content)
        
        # Create .gitignore
        gitignore = """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
.venv/
venv/
ENV/
.vscode/
.idea/
*.egg-info/
.DS_Store
"""
        self._write_file(self.project_dir / ".gitignore", gitignore)
        
        # Create src directory
        (self.project_dir / "src").mkdir(exist_ok=True)
        (self.project_dir / "src" / "__init__.py").touch()
    
    def scaffold_nodejs_project(self):
        """Scaffold a Node.js project with package.json"""
        
        package_json = f"""{{
  "name": "{self.project_dir.name}",
  "version": "0.0.1",
  "description": "Node.js project scaffolded by Boudica Code",
  "main": "src/index.js",
  "scripts": {{
    "start": "node src/index.js",
    "dev": "node --watch src/index.js",
    "test": "echo \\"Error: no test specified\\" && exit 1"
  }},
  "keywords": [],
  "author": "",
  "license": "ISC",
  "dependencies": {{
  }}
}}
"""
        with open(self.project_dir / "package.json", 'w') as f:
            f.write(package_json)
        
        # Create .gitignore
        gitignore = """node_modules/
package-lock.json
.env
.DS_Store
.vscode/
.idea/
dist/
build/
"""
        self._write_file(self.project_dir / ".gitignore", gitignore)
        
        # Create src directory with index.js
        (self.project_dir / "src").mkdir(exist_ok=True)
        self._write_file(self.project_dir / "src" / "index.js", "console.log('Hello from Node.js!');\n")
    
    def scaffold_typescript_project(self):
        """Scaffold a TypeScript project with tsconfig.json and package.json"""
        
        package_json = f"""{{
  "name": "{self.project_dir.name}",
  "version": "0.0.1",
  "description": "TypeScript project scaffolded by Boudica Code",
  "main": "dist/index.js",
  "scripts": {{
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsc --watch",
    "test": "echo \\"Error: no test specified\\" && exit 1"
  }},
  "keywords": [],
  "author": "",
  "license": "ISC",
  "devDependencies": {{
    "typescript": "^5.0.0"
  }},
  "dependencies": {{
  }}
}}
"""
        with open(self.project_dir / "package.json", 'w') as f:
            f.write(package_json)
        
        # Create tsconfig.json
        tsconfig_content = """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
"""
        with open(self.project_dir / "tsconfig.json", 'w') as f:
            f.write(tsconfig_content)
        
        # Create .gitignore
        gitignore = """node_modules/
dist/
package-lock.json
.env
.DS_Store
.vscode/
.idea/
"""
        with open(self.project_dir / ".gitignore", 'w') as f:
            f.write(gitignore)
        
        # Create src directory
        (self.project_dir / "src").mkdir(exist_ok=True)
        with open(self.project_dir / "src" / "index.ts", 'w') as f:
            f.write("console.log('Hello from TypeScript!');\n")
    
    def scaffold_java_project(self):
        """Scaffold a Java project with Maven structure"""
        
        # Create pom.xml
        pom_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>{self.project_dir.name}</artifactId>
    <version>0.0.1</version>

    <name>{self.project_dir.name}</name>
    <description>Java project scaffolded by Boudica Code</description>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <!-- Add dependencies here -->
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""
        with open(self.project_dir / "pom.xml", 'w') as f:
            f.write(pom_content)
        
        # Create .gitignore
        gitignore = """target/
.classpath
.project
.settings/
*.jar
*.class
.DS_Store
.vscode/
.idea/
*.iml
"""
        with open(self.project_dir / ".gitignore", 'w') as f:
            f.write(gitignore)
        
        # Create Maven directory structure
        src_dir = self.project_dir / "src" / "main" / "java" / "com" / "example"
        src_dir.mkdir(parents=True, exist_ok=True)
        
        test_dir = self.project_dir / "src" / "test" / "java" / "com" / "example"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create App.java
        with open(src_dir / "App.java", 'w') as f:
            f.write("""package com.example;

public class App {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}
""")
    
    def scaffold_bash_project(self):
        """Scaffold a Bash script project"""
        
        # Create .gitignore
        gitignore = """*.log
*.tmp
.DS_Store
.vscode/
.idea/
"""
        self._write_file(self.project_dir / ".gitignore", gitignore)
        
        # Create src directory
        (self.project_dir / "src").mkdir(exist_ok=True)
        
        # Create main.sh
        main_sh = """#!/bin/bash
# Main entry point for bash scripts

echo "Hello from Bash!"
"""
        self._write_file(self.project_dir / "src" / "main.sh", main_sh)
        
        # Make it executable
        script_path = self.project_dir / "src" / "main.sh"
        script_path.chmod(0o755)
        
        # Create README
        readme = f"""# {self.project_dir.name}

Bash script project scaffolded by Boudica Code.

## Running

```bash
./src/main.sh
```

## Scripts

- **src/main.sh** - Main entry point
"""
        self._write_file(self.project_dir / "README.md", readme)
    
    def scaffold_windows_batch_project(self):
        """Scaffold a Windows batch file project"""
        
        # Create .gitignore
        gitignore = """*.log
*.tmp
.DS_Store
.vscode/
.idea/
"""
        self._write_file(self.project_dir / ".gitignore", gitignore)
        
        # Create src directory
        (self.project_dir / "src").mkdir(exist_ok=True)
        
        # Create main.bat
        main_bat = """@echo off
REM Main entry point for batch scripts

echo Hello from Batch!
pause
"""
        self._write_file(self.project_dir / "src" / "main.bat", main_bat)
        
        # Create README
        readme = f"""# {self.project_dir.name}

Windows batch file project scaffolded by Boudica Code.

## Running

```cmd
src\\main.bat
```

## Scripts

- **src/main.bat** - Main entry point
"""
        self._write_file(self.project_dir / "README.md", readme)
    
    def scaffold_fullstack_node(self):
        """Scaffold a Full-Stack Node.js + React project"""
        
        # Backend package.json
        backend_pkg = f"""{{
  "name": "{self.project_dir.name}-backend",
  "version": "0.0.1",
  "description": "Backend for {self.project_dir.name}",
  "main": "index.js",
  "scripts": {{
    "start": "node index.js",
    "dev": "node --watch index.js"
  }},
  "dependencies": {{
    "express": "^4.18.0",
    "cors": "^2.8.5"
  }}
}}
"""
        with open(self.project_dir / "package.json", 'w') as f:
            f.write(backend_pkg)
        
        # Frontend package.json
        frontend_pkg = f"""{{
  "name": "{self.project_dir.name}-frontend",
  "version": "0.0.1",
  "description": "Frontend for {self.project_dir.name}",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.0.0"
  }}
}}
"""
        frontend_dir = self.project_dir / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        with open(frontend_dir / "package.json", 'w') as f:
            f.write(frontend_pkg)
        
        # Create .gitignore
        gitignore = """node_modules/
dist/
build/
package-lock.json
.env
.DS_Store
.vscode/
.idea/
"""
        with open(self.project_dir / ".gitignore", 'w') as f:
            f.write(gitignore)
        
        # Create backend structure
        (self.project_dir / "src").mkdir(exist_ok=True)
        with open(self.project_dir / "index.js", 'w') as f:
            f.write("""const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());

app.get('/api/hello', (req, res) => {
    res.json({ message: 'Hello from backend!' });
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
""")
        
        # Create frontend structure
        (frontend_dir / "src").mkdir(exist_ok=True)
        (frontend_dir / "public").mkdir(exist_ok=True)
        with open(frontend_dir / "src" / "App.jsx", 'w') as f:
            f.write("""export default function App() {
  return (
    <div>
      <h1>Welcome to Full-Stack App</h1>
    </div>
  );
}
""")
    
    def scaffold_fullstack_python(self):
        """Scaffold a Full-Stack Python + React project"""
        
        # Backend requirements.txt
        req_content = """Flask==2.3.0
Flask-CORS==4.0.0
"""
        with open(self.project_dir / "requirements.txt", 'w') as f:
            f.write(req_content)
        
        # Backend app.py
        with open(self.project_dir / "app.py", 'w') as f:
            f.write("""from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/hello')
def hello():
    return {'message': 'Hello from Flask backend!'}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
""")
        
        # Frontend package.json
        frontend_pkg = f"""{{
  "name": "{self.project_dir.name}-frontend",
  "version": "0.0.1",
  "description": "Frontend for {self.project_dir.name}",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.0.0"
  }}
}}
"""
        frontend_dir = self.project_dir / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        with open(frontend_dir / "package.json", 'w') as f:
            f.write(frontend_pkg)
        
        # Create .gitignore
        gitignore = """__pycache__/
venv/
.venv/
node_modules/
dist/
build/
frontend/node_modules/
.env
.DS_Store
.vscode/
.idea/
*.pyc
"""
        with open(self.project_dir / ".gitignore", 'w') as f:
            f.write(gitignore)
        
        # Create frontend structure
        (frontend_dir / "src").mkdir(exist_ok=True)
        (frontend_dir / "public").mkdir(exist_ok=True)
        with open(frontend_dir / "src" / "App.jsx", 'w') as f:
            f.write("""export default function App() {
  return (
    <div>
      <h1>Welcome to Full-Stack App</h1>
    </div>
  );
}
""")
    
    def scaffold_fullstack_java(self):
        """Scaffold a Full-Stack Java + React project"""
        
        # Backend pom.xml
        pom_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>{self.project_dir.name}</artifactId>
    <version>0.0.1</version>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>com.sparkjava</groupId>
            <artifactId>spark-core</artifactId>
            <version>2.9.4</version>
        </dependency>
    </dependencies>
</project>
"""
        with open(self.project_dir / "pom.xml", 'w') as f:
            f.write(pom_content)
        
        # Create .gitignore
        gitignore = """target/
.classpath
.project
.settings/
*.jar
*.class
node_modules/
frontend/node_modules/
frontend/dist/
.DS_Store
.vscode/
.idea/
*.iml
"""
        with open(self.project_dir / ".gitignore", 'w') as f:
            f.write(gitignore)
        
        # Create backend structure
        src_dir = self.project_dir / "src" / "main" / "java" / "com" / "example"
        src_dir.mkdir(parents=True, exist_ok=True)
        
        # Create frontend structure
        frontend_dir = self.project_dir / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        
        frontend_pkg = f"""{{
  "name": "{self.project_dir.name}-frontend",
  "version": "0.0.1",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.0.0"
  }}
}}
"""
        with open(frontend_dir / "package.json", 'w') as f:
            f.write(frontend_pkg)
        
        (frontend_dir / "src").mkdir(exist_ok=True)
    
    def update_cmake_for_file(self, filepath: str):
        """Update build config when a new file is added"""
        
        # C++ projects: ensure CMakeLists.txt exists
        if self.stack == 'cpp' and filepath.endswith('.cpp'):
            cmake_file = self.project_dir / "CMakeLists.txt"
            if not cmake_file.exists():
                self.scaffold_cpp_project()
            # CMakeLists.txt uses GLOB, so no manual update needed
            return
        
        # Node/TypeScript: ensure package.json exists
        if self.stack in ['nodejs', 'typescript'] and filepath.endswith(('.js', '.ts', '.jsx', '.tsx')):
            pkg_file = self.project_dir / "package.json"
            if not pkg_file.exists():
                if self.stack == 'nodejs':
                    self.scaffold_nodejs_project()
                else:
                    self.scaffold_typescript_project()
            return
        
        # Java: ensure pom.xml exists and structure is correct
        if self.stack == 'java' and filepath.endswith('.java'):
            pom_file = self.project_dir / "pom.xml"
            if not pom_file.exists():
                self.scaffold_java_project()
            return
        
        # Python: ensure requirements.txt and setup.py exist
        if self.stack == 'python' and filepath.endswith('.py'):
            req_file = self.project_dir / "requirements.txt"
            setup_file = self.project_dir / "setup.py"
            if not req_file.exists() or not setup_file.exists():
                self.scaffold_python_project()
            return
        
        # Full-stack projects
        if self.stack in ['fullstack-node', 'fullstack-python', 'fullstack-java']:
            if filepath.startswith('frontend/') and filepath.endswith(('.jsx', '.tsx', '.ts', '.js')):
                pkg_file = self.project_dir / "frontend" / "package.json"
                if not pkg_file.exists():
                    (self.project_dir / "frontend").mkdir(exist_ok=True)
            elif self.stack == 'fullstack-node' and filepath.endswith(('.js', '.ts')):
                pkg_file = self.project_dir / "package.json"
                if not pkg_file.exists():
                    self.scaffold_fullstack_node()
            elif self.stack == 'fullstack-python' and filepath.endswith('.py'):
                req_file = self.project_dir / "requirements.txt"
                if not req_file.exists():
                    self.scaffold_fullstack_python()
            elif self.stack == 'fullstack-java' and filepath.endswith('.java'):
                pom_file = self.project_dir / "pom.xml"
                if not pom_file.exists():
                    self.scaffold_fullstack_java()
