# 🛡️ BoudicaCode

**AI-Powered Code Generation & Project Management CLI**

BoudicaCode is an intelligent command-line tool that uses the **Boudica inference server** to generate, build, debug, and manage multi-language software projects. It combines natural language processing with automated compilation, interactive debugging, and Git integration to streamline the entire development workflow.

---

## 🎯 Key Features

### Project Management
- **Multi-Language Support**: Python, Node.js, TypeScript, Java, C++, Bash, Batch, and mixed-language projects
- **Automatic Scaffolding**: Generates proper project structure with language-specific config files and templates
- **Project Organization**: All projects stored in `~/boudica_code/projects/` with persistent session tracking
- **File Management**: Browse, view, create, edit, and delete files within projects
- **Session Persistence**: SQLite-backed conversation history and project metadata

### 🤖 AI-Powered Code Generation
- **Natural Language File Creation**: Describe what you want in plain English; Boudica generates the code
- **Intelligent Path/Description Parsing**: Extracts file paths and requirements from unstructured natural language input
- **Language-Appropriate Code**: Automatically adapts generated code to the project's language stack
- **Code Validation**: Extracts code from HTML, Markdown, and plain text response formats
- **Error Recovery**: Re-requests code with corrections if response format is unexpected

### 🛠️ Smart Build System
- **Multi-Language Compilation**:
  - **C++**: CMake-based builds with debug symbols (`-g -O0`)
  - **Python**: Module compilation and syntax validation (`python3 -m py_compile`)
  - **Node.js/TypeScript**: NPM build pipelines (`npm install`, `npm run build`)
  - **Java**: Maven-based compilation (`mvn clean compile`)
  - **Bash**: Syntax validation (`bash -n`)
- **Automatic Error Parsing**: Extracts compiler errors with file:line:column precision
- **AI-Powered Auto-Fix**: When builds fail, sends errors to Boudica for intelligent fixes with diffs
- **Diff Review**: Shows unified diffs of all changes before applying auto-fixes
- **Iterative Fixes**: Retries compilation after fixes until success or max retries reached

### 🐛 Advanced Debugging
- **Multi-Language Debugger Support**: GDB (C++), pdb (Python), Node Inspector (JavaScript), jdb (Java)
- **Interactive Breakpoints**: Set breakpoints at specific file:line locations
- **Crash Analysis**: Captures crash output with stack traces for AI analysis
- **Root Cause Identification**: Boudica analyzes crashes and suggests fixes
- **Debug Symbols**: Binaries compiled with full debug info for effective debugging
- **Automatic Crash Detection**: Captures stderr/stdout for crash diagnostics

### ✏️ Intelligent Code Editing
- **Natural Language Edits**: Modify files using English commands like "add error handling" or "optimize the loop"
- **Context-Aware Editing**: Preserves file context with line numbers to prevent content loss
- **Content Validation**: Ensures edited files maintain >70% of original content
- **Diff Preview**: Review all changes via unified diffs before committing
- **Smart Pattern Extraction**: Uses regex to identify target code sections in natural language requests

### 🔄 Git Integration
- **Automatic Repository Initialization**: Every project is initialized as a Git repository
- **Initial Commit**: First commit created during project scaffolding with generated files
- **Language-Specific .gitignore**: Auto-generated for each language using GitHub templates
- **Git Credential Management**: Stored in `~/boudica_code/git_config.json` with restricted permissions
- **User Configuration**: Checks and prompts for git user.name/user.email if not configured
- **Git Installation Verification**: Validates git is available before proceeding

### ⚙️ CI/CD & Workflow Automation
- **GitHub Actions Workflow Generation**: Automatically creates `.github/workflows/ci.yml` for your project
- **Language-Specific Pipelines**: Pre-configured build, test, and deployment steps per language
- **Matrix Testing**: Supports multiple Python/Node/Java versions in parallel
- **Cross-Platform Builds**: Windows, macOS, and Linux runners configured appropriately

---

## 🚀 Quick Start

### Installation

1. **Install Dependencies**
   ```bash
   # On Linux/macOS
   brew install git python3 cmake nodejs openjdk
   
   # On Windows
   choco install git python cmake nodejs openjdk
   ```

2. **Set Up Boudica API Key**
   ```bash
   # Get your API key from: https://boudi.ca/api_keys/
   
   # Linux/macOS
   export BOUDICA_API_KEY='your_key_here'
   export BOUDICA_USER_ID='your_username'  # Optional
   
   # Windows PowerShell
   $env:BOUDICA_API_KEY='your_key_here'
   $env:BOUDICA_USER_ID='your_username'
   ```

3. **Run BoudicaCode**
   ```bash
   cd BoudicaCode
   python3 src/main.py
   ```

### Basic Workflow

1. **Create a New Project**
   - Select "New" from main menu
   - Choose a name and technology stack
   - BoudicaCode scaffolds the entire project structure

2. **Generate Code**
   ```
   create src/main.py: a simple CLI calculator with add, subtract, multiply, divide
   create src/utils.py: utility functions for input validation
   ```

3. **Edit Files**
   ```
   edit src/main.py: add error handling for division by zero
   modify utils.py: add support for floating-point numbers
   ```

4. **Build & Fix Errors**
   ```
   build
   ```
   If errors occur, BoudicaCode automatically:
   - Detects compilation errors
   - Sends errors to Boudica for analysis
   - Proposes and applies fixes
   - Rebuilds automatically

5. **Debug Issues**
   ```
   debug
   ```
   - Set breakpoints interactively
   - Run with debugger
   - Analyze crashes automatically

---

## 📁 Project Structure

```
BoudicaCode/
├── src/
│   ├── main.py                 # CLI entry point
│   ├── session_manager.py      # SQLite session management
│   ├── project_manager.py      # Project structure & file ops
│   ├── boudica_integration.py  # Boudica API client
│   ├── ui_handler.py           # Terminal UI & prompts
│   ├── git_integration.py      # Git operations
│   ├── workflow_generator.py   # GitHub Actions generation
│   └── debugger.py             # Multi-language debugging
├── assets/                     # Workflow templates, gitignore templates
├── requirements.txt            # Python dependencies
├── run.sh                       # Launch script (Linux/macOS)
├── run.bat                      # Launch script (Windows)
└── README.md                    # This file
```

---

## 📊 Supported Project Types

| Language | Build System | Test Framework | Debug Tool | Status |
|----------|-------------|----------------|-----------|--------|
| Python | Python native | pytest | pdb | ✅ Full |
| Node.js | npm | npm test | Node Inspector | ✅ Full |
| TypeScript | tsc | npm test | Node Inspector | ✅ Full |
| C++ | CMake | gtest | GDB | ✅ Full |
| Java | Maven | Maven Surefire | jdb | ✅ Full |
| Bash | - | bats | bash -x | ✅ Syntax only |
| Windows Batch | - | - | cmd | ⚠️ Limited |

---

## 🔧 Advanced Usage

### Session History
All projects and conversations are logged to:
- **Sessions DB**: `~/boudica_code/sessions.db`
- **Project Files**: `~/boudica_code/projects/{project_name}/`
- **File Backups**: `~/boudica_code/projects/{project_name}/.backups/`

### File Operations
```
ls, list, files, browse    # Browse project files
view <path>                # View file contents with syntax highlighting
edit <path>: <description> # Edit with natural language
delete, rm <path>          # Delete file (with backup)
create <path>: <description> # Create new file
```

### Code Generation
```
create src/api.py: REST API with Flask and SQLAlchemy
create tests/test_api.py: unit tests for all endpoints
```

### Building & Debugging
```
build                      # Compile/validate project
debug                      # Launch debugger session
workflows                  # Generate GitHub Actions CI/CD
status                     # Show project info
help                       # Show command help
```

### Planning & Discussion
Type natural language requests that don't match file operations, and Boudica will engage in planning discussions to help design your application.

---

## 🔐 Authentication & Configuration

### Environment Variables
- `BOUDICA_API_KEY` (required): Your API key from https://boudi.ca/api_keys/
- `BOUDICA_URL` (optional): Inference server URL (default: `https://boudi.ca/api/boudica`)
- `BOUDICA_USER_ID` (optional): Your username for audit logging (default: `boudica-code-agent`)

### Git Configuration
Git user.name and user.email are verified at startup. If not set, BoudicaCode prompts you to configure them.

### File Backup Strategy
Every file edit creates a timestamped backup in `.backups/` before modification. This allows recovery if edits go wrong.

---

## 🐛 Troubleshooting

### "BOUDICA_API_KEY not set!"
Set your API key as an environment variable (see Authentication section above).

### Build fails with "Command not found"
Ensure the required compiler/runtime is installed for your project language:
- C++: `cmake` and `g++`/`clang`
- Python: `python3`
- Node.js: `npm`
- Java: `mvn`

### Debugger not finding breakpoints
Make sure the file path is relative to the project directory and the file exists.

### Git configuration error
Run: `git config --global user.name "Your Name"` and `git config --global user.email "your@email.com"`

---

## 📝 Examples

### Python Project
```
Create project: my_calculator
Language: python

create src/calculator.py: a class-based calculator
create src/ui.py: CLI interface with argparse
edit src/calculator.py: add support for exponentiation
build
debug
```

### C++ Project
```
Create project: matrix_lib
Language: cpp

create src/matrix.h: matrix class with basic operations
create src/matrix.cpp: implementation
create tests/test_matrix.cpp: unit tests
build
debug
```

---

## 📚 Architecture

### Session Management
- **SQLite Database** (`sessions.db`): Stores project metadata and conversation history
- **Tables**: `sessions`, `conversation_history`, `file_backups`
- **Enables**: Project recovery, conversation recall, change tracking

### Project Scaffolding
- **Auto-Generated Files**: `CMakeLists.txt`, `package.json`, `pom.xml`, `.gitignore`, `requirements.txt`, etc.
- **Directory Structure**: Language-appropriate folders (`src/`, `tests/`, `public/`, etc.)
- **Git Initialization**: `.git/` repo created with initial commit

### AI Integration
- **Natural Language → Code**: Uses Boudica for intelligent code generation
- **Error Analysis**: Sends compilation errors to Boudica for automated fixes
- **Crash Debugging**: Analyzes crash output with AI for root cause identification
- **Context Preservation**: Includes relevant code context in all AI requests

---

## 🛠️ Development

### Running Locally
```bash
cd BoudicaCode
python3 -m py_compile src/*.py  # Syntax validation
python3 src/main.py             # Run CLI
```

### Code Structure
- **Modular Design**: Each component (sessions, projects, git, UI, debug) is independent
- **Type Hints**: Full type annotations for IDE support
- **Error Handling**: Comprehensive exception handling with user-friendly messages

---

## 📄 License

See LICENSE file in project root.

---

## 🤝 Contributing

BoudicaCode is an internal demo project. For issues or contributions, contact the Boudica team.
- **Environment Variables**: Support for GIT_USER, GIT_EMAIL, GIT_SERVER, GIT_TOKEN

### 🚀 GitHub Actions CI/CD
- **Automatic Workflow Generation**: GitHub Actions workflows created with every project
- **Language-Specific Pipelines**: Optimized build, test, and deploy workflows
- **Three-Tier Automation**:
  - **build.yml**: Builds on push to main/develop branches
  - **test.yml**: Runs test suite on pull requests
  - **deploy.yml**: Template for manual deployments with environment selection
- **Smart Runner Selection**: Uses ubuntu-latest or windows-latest based on project type
- **Dependency Management**: Automatically installs language-specific tools and dependencies

## Installation

### Prerequisites
- Python 3.8+
- Git
- Build tools (for C++):
  - `cmake` 3.10+
  - `make`
  - `g++` or `clang++`
- Node.js & npm (for Node.js/TypeScript projects)
- Java & Maven (for Java projects)
- GDB (for C++ debugging)

### Setup

```bash
# Clone or download the repository
cd BoudicaCode

# Run the setup script
./run.sh
```

This will:
1. Create a Python virtual environment
2. Install all dependencies
3. Launch the interactive CLI

### Manual Setup (if not using run.sh)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 src/main.py
```

## Usage

### Starting BoudicaCode

```bash
./run.sh
```

### Main Menu

```
Main Menu:
  [N]ew       - Create a new project
  [O]pen      - Open existing project
  [L]ist      - List all projects
  [E]xit      - Exit Boudica Code
```

### Project Commands

Once inside a project, available commands include:

#### File Management
```
ls              - List files in project
view <file>     - View file contents
delete <file>   - Delete a file
create <desc>   - Create new file with AI
```

#### Code Editing
```
edit <desc>     - Edit code using natural language
change <desc>   - Modify existing functionality
```

#### Build & Run
```
build           - Compile/build the project
workflows       - Generate GitHub Actions CI/CD workflows
debug           - Start interactive debugger
run             - Execute the project
```

#### Git & Configuration
```
(Git configuration done on first startup)
```

### Example Workflow

```bash
# 1. Create a new C++ project
Choice: n
Project name: hello_world
Stack: 5 (C++)

# 2. Create a source file
hello_world> create a function that prints hello world

# 3. Build the project
hello_world> build
✅ Build successful!

# 4. Debug with breakpoints
hello_world> debug
Debugger options:
  1. Set breakpoint
  2. List breakpoints
  3. Run
  4. Back to main menu

# 5. Set a breakpoint and run
Choice: 1
File: src/main.cpp
Line: 10
✅ Breakpoint set at src/main.cpp:10

Choice: 3
💬 Running with debugger...
[program output]
```

## Multi-File Project Creation

### Current Pattern: Sequential Generation ✓

BoudicaCode supports complex, multi-file projects by generating files sequentially with full context awareness. This approach works well for:
- Backend services with multiple layers (OAuth, database, API)
- Library structures with headers and implementations
- Test suites alongside source code
- Large applications with modular organization

### How It Works

Each file is generated independently, but with enough context, Boudica AI ensures:
- Consistent imports and includes
- Proper function signatures across files
- Coordinated class/module organization
- Automatic discovery via CMakeLists.txt (C++) or build configuration

### Example: C++ Backend with OAuth, Database, and File Processing

This real-world example shows how to build a complete backend system:

```bash
# 1. Create the project
Choice: n
Project name: file_processor
Stack: 5 (C++)

# 2. Create headers first (so implementations can reference them)
file_processor> create include/oauth.h: 
  OAuth client for Google Drive API authentication. Includes token management, 
  refresh token handling, and authorization code exchange.

file_processor> create include/database.h:
  Database abstraction layer for SQLite. Methods for storing summaries, 
  retrieving file history, and managing user sessions.

file_processor> create include/boudica.h:
  Integration coordinator that orchestrates OAuth flow, file retrieval from 
  Google Drive, summary generation, and database storage.

# 3. Create implementations (referencing the headers)
file_processor> create src/oauth.cpp:
  Implement Google Drive OAuth using libcurl and nlohmann/json. Use 
  #include "oauth.h". Handle token lifecycle and API requests.

file_processor> create src/database.cpp:
  Implement SQLite database operations. Use #include "database.h". 
  Create tables for files, summaries, and user sessions.

file_processor> create src/boudica.cpp:
  Orchestration layer that uses #include "oauth.h" and #include "database.h". 
  Coordinates the complete workflow: authenticate → retrieve file → 
  generate summary → store in database.

file_processor> create src/main.cpp:
  Entry point. Parse command-line arguments for file path. Include 
  "boudica.h". Call BoudicaCoordinator to execute the complete workflow.

# 4. Build (CMakeLists.txt auto-discovers all src/*.cpp files)
file_processor> build
✅ Build successful!
```

### Why This Works

**CMakeLists.txt Auto-Discovery** 
BoudicaCode generates CMakeLists.txt with:
```cmake
file(GLOB SOURCES "src/*.cpp" "*.cpp")
add_executable(project_name ${SOURCES})
target_include_directories(project_name PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
```

This automatically includes all new .cpp files you create—no manual updates needed.

### Best Practices for Multi-File Projects

1. **Create Headers First**
   - Declares interfaces before implementations
   - Gives Boudica full context for implementations
   - Ensures function signatures are consistent

2. **Reference Headers in Descriptions**
   - When creating implementation files, mention "Use #include "header.h""
   - This ensures proper coordination

3. **Describe Interactions Clearly**
   - Explain which files call which functions
   - Example: "src/main.cpp calls BoudicaCoordinator::run() from boudica.h"
   - Helps Boudica generate coordinated code

4. **Build After Each Major Component**
   - After implementing a layer (e.g., OAuth + database)
   - Catch integration issues early
   - Use auto-fix if compilation fails

### Current Limitations & Future Enhancements

**Current (MVP):**
- ✅ Sequential file creation with AI context
- ✅ CMakeLists.txt auto-discovery
- ✅ Individual file optimization
- ❌ No batched multi-file generation
- ❌ No automatic #include coordination

**Planned (v1.1+):**
- Multi-file generation in single request: `create --batch [files]: description`
- Template-based scaffolding: `scaffold express-api` auto-generates route structure
- Automatic header/implementation coordination
- Dependency graph validation

### Workflow Comparison

**Single-File Project:**
```
create src/main.py: Simple CLI app
build
run
```

**Multi-File Project:**
```
create include/api.h: API client interface
create src/api.cpp: API client implementation
create src/main.cpp: Entry point using api.h
build
run
```

Both use the same commands—just organize your creation sequence logically (headers → implementations → main).

## Supported Technologies

### Languages
- **Python 3.7+** - Full framework support (pip, venv, pytest)
- **JavaScript (Node.js 14+)** - npm ecosystem, full build pipeline
- **TypeScript 4.0+** - Type-safe development with source mapping
- **Java 11+** - Maven-based projects with dependency management
- **C++ 17** - CMake build system with debug symbol support
- **Bash Scripts** - Shell scripting with syntax validation
- **Windows Batch Scripts** - .bat/.cmd automation files

### Full-Stack Options
- Node.js + React
- Python + React
- Java + React

## Project Structure

### Local Projects Location
```
~/boudica_code/
├── projects/          # All user projects
│   ├── project1/
│   ├── project2/
│   └── ...
├── header_template    # Default header template for file creation
├── footer_template    # Default footer template for file creation
├── git_config.json    # Git configuration
└── sessions.db        # Session history database
```

### Individual Project Layout

**C++ Project:**
```
project_name/
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
│       ├── build.yml       # Build pipeline
│       ├── test.yml        # Test pipeline
│       └── deploy.yml      # Deployment template
├── .boudica_project.json   # Project metadata
├── .gitignore              # Git ignore rules
├── CMakeLists.txt          # CMake configuration
├── README.md               # Auto-generated documentation
├── src/                    # Source files directory
│   ├── main.cpp            # Primary source file
│   └── ...                 # Additional source files
├── include/                # Header files
├── build/                  # (auto-generated) Build artifacts
└── backups/                # Auto-backup of edited files
```

**Python/Node.js/TypeScript/Java Project:**
```
project_name/
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
│       ├── build.yml       # Build pipeline
│       ├── test.yml        # Test pipeline
│       └── deploy.yml      # Deployment template
├── .boudica_project.json   # Project metadata
├── .gitignore              # Git ignore rules
├── package.json            # (Node.js/TypeScript) npm configuration
├── pom.xml                 # (Java) Maven configuration
├── requirements.txt        # (Python) Dependencies
├── README.md               # Auto-generated documentation
├── src/                    # Source files directory
├── build/ or dist/         # (auto-generated) Build artifacts
└── backups/                # Auto-backup of edited files
```

**Bash Script Project:**
```
project_name/
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
│       ├── build.yml       # Build verification
│       └── test.yml        # Test execution
├── .boudica_project.json   # Project metadata
├── .gitignore              # Git ignore rules
├── README.md               # Auto-generated documentation
├── src/
│   ├── main.sh             # Main script
│   └── ...                 # Additional scripts
└── backups/                # Auto-backup of edited files
```

**Windows Batch Project:**
```
project_name/
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
│       ├── build.yml       # Build verification (windows-latest)
│       └── deploy.yml      # Deployment template
├── .boudica_project.json   # Project metadata
├── .gitignore              # Git ignore rules
├── README.md               # Auto-generated documentation
├── src/
│   ├── main.bat            # Main batch file
│   └── ...                 # Additional batch files
└── backups/                # Auto-backup of edited files
```

## Configuration

### Environment Variables

```bash
# Boudica Server Configuration
BOUDICA_API_URL=https://boudi.ca/api/boudica
BOUDICA_API_KEY=your_api_key_here
BOUDICA_USER_ID=your_user_id  # Optional, defaults to 'boudica-code-agent'

# Git Configuration (optional - can be set interactively on first run)
GIT_USER=Your Name
GIT_EMAIL=your.email@example.com
GIT_SERVER=github.com
GIT_TOKEN=your_github_token
```

### Configuration Files

```bash
# Git configuration is persisted to:
~/boudica_code/git_config.json

# Project metadata:
<project>/​.boudica_project.json

# Session history:
~/.boudica_code/sessions.db
```

### Settings

Configuration is managed through:
- `.boudica_project.json` - Per-project settings
- Environment variables - Global settings

## Architecture

### Components

1. **main.py** - CLI entry point and command routing
2. **project_manager.py** - Project scaffolding, build system, and workflow generation
3. **boudica_integration.py** - AI code generation and error fixing
4. **git_integration.py** - Git repository management and configuration persistence
5. **workflow_generator.py** - GitHub Actions CI/CD workflow generation
6. **debugger.py** - Multi-language debugger abstraction
7. **session_manager.py** - Project session and history tracking
8. **ui_handler.py** - Terminal UI with prompt-toolkit

### Workflow

```
User Input
    ↓
Command Parser (main.py)
    ↓
Route to Handler (handle_create, handle_build, etc.)
    ↓
Project Manager (execute build/file operations)
    ↓
Boudica Integration (AI code generation/fixing)
    ↓
Display Results (UI Handler)
```

## Git Integration & CI/CD

### Automatic Git Repository Setup

Every new project is automatically initialized as a Git repository with:
- Language-specific `.gitignore` file
- Auto-generated `README.md` with project documentation
- Initial commit with message: "Initial commit - Project scaffolded by BoudicaCode"

### Git Configuration

On first startup, BoudicaCode prompts for git configuration:

```
Git needs to be configured with your identity
Git username: Your Name
Git email: your.email@example.com
```

These settings are:
- Applied globally to your system
- Persisted to `~/boudica_code/git_config.json` for future sessions
- Loaded from environment variables `GIT_USER` and `GIT_EMAIL` if set

### GitHub Actions Workflows

When you create a new project, three GitHub Actions workflows are automatically generated:

**build.yml** - Builds on push
```yaml
- Triggers: push to main or develop branch
- Steps: checkout → setup language tools → install dependencies → build
```

**test.yml** - Tests on PR
```yaml
- Triggers: pull request to main or develop branch
- Steps: checkout → setup language tools → install dependencies → run tests
```

**deploy.yml** - Manual deployment template
```yaml
- Triggers: manual dispatch (workflow_dispatch)
- Environment: choice of staging or production
- Placeholder: customize with your deployment commands
```

### Using Workflows with GitHub

1. **Create project locally:**
   ```bash
   > n
   Project name: my_app
   Stack: nodejs
   ```

2. **Generate/review workflows:**
   ```bash
   my_app> workflows
   ✅ Generated GitHub Actions workflows
   ```

3. **Push to GitHub:**
   ```bash
   cd ~/boudica_code/projects/my_app
   git remote add origin https://github.com/yourusername/my_app.git
   git push -u origin main
   ```

4. **Workflows run automatically** on subsequent pushes and PRs

5. **Customize deploy.yml** for your deployment needs

## Troubleshooting

### Build Failures

**Problem**: Build fails with compilation error
**Solution**: 
1. Review error message
2. Select "Attempt automatic fix?" when prompted
3. Review the proposed changes
4. Approve fix - rebuild will run automatically

### Debugger Not Stopping at Breakpoints

**Problem**: Breakpoint set but program doesn't stop
**Solution**: 
1. Ensure binary was built with debug symbols (use `DEBUG` build type)
2. Verify breakpoint line number is valid
3. Check that source file path is correct

### Project Not Found

**Problem**: Project doesn't appear in project list
**Solution**: 
1. Ensure project is in `~/boudica_code/projects/`
2. Check `.boudica_project.json` exists in project root
3. Verify folder name is alphanumeric + underscores

## Development

### Running Tests

```bash
python3 -m pytest tests/
```

### Code Style

Code follows PEP 8 style guide. Format with:
```bash
black src/
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) file for details.

```
Copyright 2026 Boudica Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues, questions, or feature requests, please open an issue on the project repository.

## Acknowledgments

- Built with Python 3 and prompt-toolkit
- Powered by Boudica AI inference server
- Integrated debuggers: GDB (C++), pdb (Python), Node inspector (JavaScript), jdb (Java)
