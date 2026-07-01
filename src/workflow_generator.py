"""
GitHub Actions Workflow Generator - Generates CI/CD workflows for projects
"""

import json
from pathlib import Path
from typing import Dict, Optional
from enum import Enum


class ProjectType(Enum):
    """Supported project types"""
    PYTHON = "python"
    NODEJS = "nodejs"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPLUSPLUS = "cpp"
    BASH = "bash"
    WINDOWS_BATCH = "batch"
    MIXED = "mixed"


class WorkflowGenerator:
    """Generates GitHub Actions workflows for CI/CD"""
    
    WORKFLOW_CONFIGS = {
        ProjectType.PYTHON: {
            'runner': 'ubuntu-latest',
            'setup_steps': [
                {
                    'uses': 'actions/setup-python@v4',
                    'with': {'python-version': '3.10'}
                }
            ],
            'install_cmd': ['pip', 'install', '-r', 'requirements.txt'],
            'build_cmd': ['python', '-m', 'py_compile', '.'],
            'test_cmd': ['python', '-m', 'pytest']
        },
        ProjectType.NODEJS: {
            'runner': 'ubuntu-latest',
            'setup_steps': [
                {
                    'uses': 'actions/setup-node@v3',
                    'with': {'node-version': '18.x'}
                }
            ],
            'install_cmd': ['npm', 'install'],
            'build_cmd': ['npm', 'run', 'build'],
            'test_cmd': ['npm', 'test']
        },
        ProjectType.TYPESCRIPT: {
            'runner': 'ubuntu-latest',
            'setup_steps': [
                {
                    'uses': 'actions/setup-node@v3',
                    'with': {'node-version': '18.x'}
                }
            ],
            'install_cmd': ['npm', 'install'],
            'build_cmd': ['tsc'],
            'test_cmd': ['npm', 'test']
        },
        ProjectType.JAVA: {
            'runner': 'ubuntu-latest',
            'setup_steps': [
                {
                    'uses': 'actions/setup-java@v3',
                    'with': {
                        'java-version': '17',
                        'distribution': 'temurin'
                    }
                }
            ],
            'install_cmd': ['mvn', 'dependency:resolve'],
            'build_cmd': ['mvn', 'clean', 'compile'],
            'test_cmd': ['mvn', 'test']
        },
        ProjectType.CPLUSPLUS: {
            'runner': 'ubuntu-latest',
            'setup_steps': [
                {
                    'run': 'sudo apt-get update && sudo apt-get install -y cmake build-essential'
                }
            ],
            'install_cmd': ['cmake', '-B', 'build', '-DCMAKE_BUILD_TYPE=Release'],
            'build_cmd': ['cmake', '--build', 'build'],
            'test_cmd': ['cmake', '--build', 'build', '--target', 'test']
        },
        ProjectType.BASH: {
            'runner': 'ubuntu-latest',
            'setup_steps': [],
            'install_cmd': [],
            'build_cmd': ['bash', '-n', 'src/main.sh'],
            'test_cmd': ['bash', 'src/main.sh']
        },
        ProjectType.WINDOWS_BATCH: {
            'runner': 'windows-latest',
            'setup_steps': [],
            'install_cmd': [],
            'build_cmd': ['cmd', '/c', 'src/main.bat'],
            'test_cmd': []
        }
    }
    
    def __init__(self, project_path: Path, project_type: ProjectType):
        """Initialize workflow generator
        
        Args:
            project_path: Path to project directory
            project_type: Type of project
        """
        self.project_path = Path(project_path)
        self.project_type = project_type
        self.workflows_dir = self.project_path / ".github" / "workflows"
    
    def create_workflows(self) -> bool:
        """Create GitHub Actions workflows for the project
        
        Returns:
            True if successful
        """
        try:
            # Create .github/workflows directory
            self.workflows_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate workflows
            self._generate_build_workflow()
            self._generate_test_workflow()
            self._generate_deploy_template()
            
            return True
        except Exception as e:
            print(f"Error creating workflows: {e}")
            return False
    
    def _generate_build_workflow(self) -> None:
        """Generate build.yml workflow"""
        config = self.WORKFLOW_CONFIGS.get(self.project_type)
        if not config:
            return
        
        workflow = {
            'name': 'Build',
            'on': {
                'push': {
                    'branches': ['main', 'develop']
                }
            },
            'jobs': {
                'build': {
                    'runs-on': config['runner'],
                    'steps': [
                        {'uses': 'actions/checkout@v3'}
                    ]
                }
            }
        }
        
        # Add setup steps
        for step in config['setup_steps']:
            workflow['jobs']['build']['steps'].append(step)
        
        # Add install step
        if config['install_cmd']:
            workflow['jobs']['build']['steps'].append({
                'name': 'Install dependencies',
                'run': ' '.join(config['install_cmd'])
            })
        
        # Add build step
        if config['build_cmd']:
            workflow['jobs']['build']['steps'].append({
                'name': 'Build',
                'run': ' '.join(config['build_cmd'])
            })
        
        self._write_workflow('build.yml', workflow)
    
    def _generate_test_workflow(self) -> None:
        """Generate test.yml workflow"""
        config = self.WORKFLOW_CONFIGS.get(self.project_type)
        if not config or not config['test_cmd']:
            return
        
        workflow = {
            'name': 'Test',
            'on': {
                'pull_request': {
                    'branches': ['main', 'develop']
                }
            },
            'jobs': {
                'test': {
                    'runs-on': config['runner'],
                    'steps': [
                        {'uses': 'actions/checkout@v3'}
                    ]
                }
            }
        }
        
        # Add setup steps
        for step in config['setup_steps']:
            workflow['jobs']['test']['steps'].append(step)
        
        # Add install step
        if config['install_cmd']:
            workflow['jobs']['test']['steps'].append({
                'name': 'Install dependencies',
                'run': ' '.join(config['install_cmd'])
            })
        
        # Add test step
        workflow['jobs']['test']['steps'].append({
            'name': 'Run tests',
            'run': ' '.join(config['test_cmd'])
        })
        
        self._write_workflow('test.yml', workflow)
    
    def _generate_deploy_template(self) -> None:
        """Generate deploy.yml template for manual deployment"""
        workflow = {
            'name': 'Deploy',
            'on': {
                'workflow_dispatch': {
                    'inputs': {
                        'environment': {
                            'description': 'Deployment environment',
                            'required': True,
                            'default': 'staging',
                            'type': 'choice',
                            'options': ['staging', 'production']
                        }
                    }
                }
            },
            'jobs': {
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'environment': '${{ github.event.inputs.environment }}',
                    'steps': [
                        {'uses': 'actions/checkout@v3'},
                        {
                            'name': 'Deploy to ${{ github.event.inputs.environment }}',
                            'run': 'echo "Deploying to ${{ github.event.inputs.environment }} environment"'
                        },
                        {
                            'name': 'TODO: Add deployment steps',
                            'run': 'echo "Configure your deployment steps here (e.g., docker build, push, pull request approval, etc.)"'
                        }
                    ]
                }
            }
        }
        
        self._write_workflow('deploy.yml', workflow)
    
    def _write_workflow(self, filename: str, workflow: Dict) -> None:
        """Write workflow to YAML file
        
        Args:
            filename: Workflow filename (e.g., 'build.yml')
            workflow: Workflow dictionary
        """
        filepath = self.workflows_dir / filename
        
        # Convert to YAML-like format manually (simpler than importing pyyaml)
        yaml_content = self._dict_to_yaml(workflow, indent=0)
        
        with open(filepath, 'w') as f:
            f.write(yaml_content)
    
    def _dict_to_yaml(self, obj: any, indent: int = 0) -> str:
        """Convert dictionary to YAML format
        
        Args:
            obj: Dictionary, list, string, etc.
            indent: Current indentation level
        
        Returns:
            YAML-formatted string
        """
        yaml_lines = []
        indent_str = '  ' * indent
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    yaml_lines.append(f"{indent_str}{key}:")
                    yaml_lines.append(self._dict_to_yaml(value, indent + 1).rstrip())
                elif isinstance(value, bool):
                    yaml_lines.append(f"{indent_str}{key}: {str(value).lower()}")
                elif value is None:
                    yaml_lines.append(f"{indent_str}{key}:")
                else:
                    yaml_lines.append(f"{indent_str}{key}: {value}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    yaml_lines.append(f"{indent_str}-")
                    item_yaml = self._dict_to_yaml(item, indent + 1)
                    # Remove the leading dash and merge
                    for line in item_yaml.split('\n'):
                        if line.strip():
                            if line.strip().startswith('-'):
                                yaml_lines[-1] = yaml_lines[-1].rstrip() + ' ' + line.strip()[1:].strip()
                            else:
                                yaml_lines.append(line)
                else:
                    yaml_lines.append(f"{indent_str}- {item}")
        else:
            return str(obj)
        
        return '\n'.join(yaml_lines) + '\n'
