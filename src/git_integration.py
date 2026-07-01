"""
Git Integration - Handles git operations and repository management
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional, Tuple


class GitIntegration:
    """Manages git operations and configuration"""
    
    def __init__(self):
        """Initialize git integration"""
        self.config_file = Path.home() / "boudica_code" / "git_config.json"
        self.config = self._load_config()
        self.last_error = None
        
        # Save config to file to persist environment variables
        if self.config and any(self.config.values()):
            self._save_config()
    
    def _load_config(self) -> Dict:
        """Load git config from file or environment"""
        # Try to load from config file
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load git config file: {e}")
        
        # Load from environment variables
        config = {
            'user': os.environ.get('GIT_USER'),
            'email': os.environ.get('GIT_EMAIL'),
            'server': os.environ.get('GIT_SERVER', 'github'),
            'token': os.environ.get('GIT_TOKEN'),
        }
        
        return config
    
    def _save_config(self):
        """Save git config to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        # Set restrictive permissions
        self.config_file.chmod(0o600)
    
    def check_git_installed(self) -> bool:
        """Check if git is installed"""
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_git_config(self) -> Tuple[bool, str]:
        """
        Check if git is configured with user.name and user.email
        
        Returns:
            (is_configured, error_message)
        """
        try:
            # Check if user.name is set
            subprocess.run(
                ['git', 'config', '--get', 'user.name'],
                capture_output=True,
                check=True,
                text=True
            )
            
            # Check if user.email is set
            subprocess.run(
                ['git', 'config', '--get', 'user.email'],
                capture_output=True,
                check=True,
                text=True
            )
            
            return True, None
        except subprocess.CalledProcessError:
            return False, "Git user.name or user.email not configured"
    
    def configure_git(self, user: str, email: str) -> bool:
        """
        Configure git with user.name and user.email
        
        Args:
            user: Git username
            email: Git email
        
        Returns:
            True if successful
        """
        try:
            subprocess.run(['git', 'config', '--global', 'user.name', user], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', email], check=True)
            
            # Save to local config file
            self.config['user'] = user
            self.config['email'] = email
            self._save_config()
            
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Failed to configure git: {e}"
            return False
    
    def init_repo(self, project_dir: Path) -> bool:
        """
        Initialize git repository in project directory
        
        Args:
            project_dir: Project directory path
        
        Returns:
            True if successful
        """
        try:
            subprocess.run(['git', 'init'], cwd=project_dir, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Failed to initialize git repo: {e}"
            return False
    
    def add_all(self, project_dir: Path) -> bool:
        """Add all files to git"""
        try:
            subprocess.run(['git', 'add', '.'], cwd=project_dir, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Failed to add files to git: {e}"
            return False
    
    def commit(self, project_dir: Path, message: str) -> bool:
        """Commit changes with message"""
        try:
            subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=project_dir,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Failed to commit: {e}"
            return False
    
    def get_status(self, project_dir: Path) -> str:
        """Get git status as string"""
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
    
    def is_git_repo(self, project_dir: Path) -> bool:
        """Check if directory is a git repository"""
        return (project_dir / '.git').exists()


def get_language_gitignore(language: str) -> str:
    """
    Get language-specific .gitignore content
    
    Args:
        language: Programming language (python, nodejs, cpp, java, bash, batch)
    
    Returns:
        .gitignore content
    """
    
    gitignore_templates = {
        'python': """# Python
__pycache__/
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
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/
.venv

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
""",
        'nodejs': """# Node.js
node_modules/
npm-debug.log
yarn-error.log
package-lock.json
yarn.lock

# Build output
dist/
build/
out/

# Environment
.env
.env.local
.env.*.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.nyc_output/
""",
        'typescript': """# TypeScript
node_modules/
dist/
build/
*.tsbuildinfo

# npm
npm-debug.log
yarn-error.log
package-lock.json
yarn.lock

# Environment
.env
.env.local
.env.*.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.nyc_output/
""",
        'cpp': """# C++
build/
dist/
*.o
*.a
*.so
*.dylib
*.dll
*.exe
*.out

# CMake
CMakeCache.txt
CMakeFiles/
cmake_install.cmake
Makefile

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Debugging
*.dSYM/
""",
        'java': """# Java
target/
*.class
*.jar
*.war
*.ear

# Maven
pom.xml.tag
pom.xml.releaseBackup
pom.xml.versionsBackup
pom.xml.next
release.properties
dependency-reduced-pom.xml

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
*.iml

# OS
.DS_Store
Thumbs.db

# Testing
surefire-reports/
""",
        'bash': """# Bash
*.log
*.tmp
*.pid

# Credentials (IMPORTANT)
.env
.env.local
.ssh/
.aws/

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
""",
        'batch': """# Windows Batch
*.log
*.tmp
*.pid

# Credentials (IMPORTANT)
.env
.env.local

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
""",
    }
    
    return gitignore_templates.get(language, """# Generic
.env
.DS_Store
Thumbs.db
*.log
.vscode/
.idea/
""")


def get_readme_template(project_name: str, language: str, is_public: bool = True) -> str:
    """
    Get README.md template for project
    
    Args:
        project_name: Name of the project
        language: Programming language
        is_public: Whether repository is public
    
    Returns:
        README.md content
    """
    
    license_section = "" if is_public else """
## License

This is a private repository.
"""
    
    language_section = {
        'python': """
## Requirements

```bash
pip install -r requirements.txt
```

## Running

```bash
python src/main.py
```
""",
        'nodejs': """
## Installation

```bash
npm install
```

## Running

```bash
npm start
```
""",
        'typescript': """
## Installation

```bash
npm install
```

## Building

```bash
npm run build
```

## Running

```bash
npm start
```
""",
        'cpp': """
## Building

```bash
mkdir build
cd build
cmake ..
make
```

## Running

```bash
./build/{project_name}
```
""",
        'java': """
## Building

```bash
mvn clean compile
```

## Running

```bash
mvn exec:java
```
""",
        'bash': """
## Running

```bash
./src/main.sh
```
""",
        'batch': """
## Running

```cmd
src\\main.bat
```
""",
    }.get(language, "## Getting Started\n\nAdd instructions here.\n")
    
    return f"""# {project_name}

A {language.capitalize()} project scaffolded by BoudicaCode.

## Description

Add project description here.

## Features

- Feature 1
- Feature 2
- Feature 3
{language_section}
## Testing

Add testing instructions here.

## Contributing

Contributions are welcome! Please follow these steps:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request
{license_section}
---

Generated by BoudicaCode - AI-Powered Code Generation & Project Management
"""
