"""
Boudica Integration - Calls Boudica inference server for code generation and planning
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from boudica_mod import create_client, BoudicaError
from git_integration import GitIntegration


class BoudicaCodegen:
    """Integration layer for Boudica code generation"""
    
    def __init__(self):
        """Initialize Boudica client"""
        
        # Get configuration from environment or use defaults
        base_url = os.environ.get('BOUDICA_URL', 'https://boudi.ca/api/boudica')
        api_key = os.environ.get('BOUDICA_API_KEY')
        user_id = os.environ.get('BOUDICA_USER_ID', 'boudica-code-agent')
        
        # Validate required credentials
        if not api_key:
            print("\n" + "="*80)
            print("❌ BOUDICA_API_KEY not set!")
            print("="*80)
            print("\nBoudicaCode requires authentication to access the Boudica inference server.")
            print("\n1. Go to: https://boudi.ca/api_key")
            print("2. Log in with your credentials")
            print("3. Copy your API key")
            print("\n4. Set the environment variable:")
            print("   - On Linux/macOS:")
            print("     export BOUDICA_API_KEY='your_api_key_here'")
            print("   - On Windows (PowerShell):")
            print("     $env:BOUDICA_API_KEY='your_api_key_here'")
            print("\n5. (Optional) Set your username:")
            print("   export BOUDICA_USER_ID='your_username'")
            print("   (If not set, defaults to 'boudica-code-agent')")
            print("\nAfter setting the variables, run BoudicaCode again.")
            print("="*80 + "\n")
            sys.exit(1)
        
        # Use create_client() function like in boudica_examples.py
        self.client = create_client(
            base_url=base_url,
            api_key=api_key,
            user_id=user_id
        )
        self.model = 'mistral-large-675b'  # Current base model
        self.max_retries = 3
        self.last_error = None  # Store last error for debugging
        self.git = GitIntegration()  # Initialize git integration    
    def parse_create_request(self, request: str, session: Dict, 
                            project_manager) -> tuple:
        """
        Use NLP + heuristics to extract file path and description from create request
        
        Args:
            request: User's natural language request (without "create" prefix)
            session: Session info
            project_manager: ProjectManager instance
        
        Returns:
            (filepath, description) tuple - either or both may be None
        """
        
        # Reject obviously invalid inputs (user typing "y" instead of filepath)
        if len(request) < 3 or request.lower() in ['y', 'yes', 'n', 'no', 'ok', 'sure']:
            self.last_error = f"Invalid input: '{request}' is too short or is a response word, not a file request"
            return None, None
        
        # First, try heuristic detection for common file patterns
        
        # Look for file paths: src/main.cpp, ./filename.ext, path/to/file.ext
        filepath = None
        file_patterns = r'(?:src/|\.?/?[\w\-]+/)*[\w\-]+\.\w+'
        matches = re.findall(file_patterns, request)
        if matches:
            filepath = matches[0]  # Take first match
        
        # If filepath found, rest is description
        if filepath:
            description = request.replace(filepath, "").strip()
            return filepath if filepath else None, description if description else None
        
        # Otherwise, use Boudica for intelligent parsing
        prompt = f"""No Memory

Extract file path and description from this request:
"{request}"

Project stack: {session.get('stack')}

Respond in this JSON format:
{{
  "filepath": "src/main.cpp or null if not mentioned",
  "description": "What the file should do or null"
}}

Only return valid JSON, no other text."""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.1,  # Very deterministic
                model=self.model
            )
            
            # Try multiple possible response keys
            text = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if text:
                text = text.strip()
                
                # Try to parse JSON
                try:
                    result = json.loads(text)
                    fp = result.get('filepath')
                    desc = result.get('description')
                    
                    # Prefer the original request as description if parsing gave us a filepath
                    if fp and not desc:
                        desc = request
                    
                    return fp, desc
                except json.JSONDecodeError as je:
                    # If JSON parsing fails, use entire request as description
                    self.last_error = f"JSON parse error in NLP response: {str(je)}. Response was: '{text}'"
                    return None, request
            
            self.last_error = f"Empty parse response. Response keys: {list(response.keys()) if response else 'None'}"
            return None, request
        
        except Exception as e:
            self.last_error = f"Error parsing request: {str(e)}"
            # Fallback: use entire request as description
            return None, request
    
    def parse_edit_request(self, request: str, session: Dict,
                          project_manager) -> tuple:
        """
        Use NLP + heuristics to extract file path and change description from edit request
        
        Args:
            request: User's natural language request (without "edit" prefix)
            session: Session info
            project_manager: ProjectManager instance
        
        Returns:
            (filepath, change_description) tuple - either or both may be None
        """
        
        # Reject obviously invalid inputs (user typing "y" instead of filepath)
        if len(request) < 3 or request.lower() in ['y', 'yes', 'n', 'no', 'ok', 'sure']:
            self.last_error = f"Invalid input: '{request}' is too short or is a response word, not an edit request"
            return None, None
        
        # First, try heuristic detection for common file patterns
        import re
        
        # Look for file paths
        filepath = None
        file_patterns = r'(?:src/|\.?/?[\w\-]+/)*[\w\-]+\.\w+'
        matches = re.findall(file_patterns, request)
        if matches:
            filepath = matches[0]
        
        # If filepath found, rest is change description
        if filepath:
            change_desc = request.replace(filepath, "").strip()
            return filepath if filepath else None, change_desc if change_desc else None
        
        # Otherwise use Boudica
        prompt = f"""No Memory

Extract file path and change description from this edit request:
"{request}"

Respond in JSON:
{{
  "filepath": "src/main.cpp or null if not mentioned",
  "change_description": "What to change or null"
}}

Only return JSON."""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=8192,
                temperature=0.1,
                model=self.model
            )
            
            # Try multiple possible response keys
            text = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if text:
                text = text.strip()
                
                try:
                    result = json.loads(text)
                    fp = result.get('filepath')
                    desc = result.get('change_description')
                    
                    # Prefer original request as description if we got a filepath
                    if fp and not desc:
                        desc = request
                    
                    return fp, desc
                except json.JSONDecodeError:
                    # Fallback: use entire request as description
                    return None, request
            
            return None, request
        
        except Exception as e:
            self.last_error = f"Error parsing request: {str(e)}"
            # Fallback to entire request as description
            return None, request
            self.max_retries = 3
    
    def generate_code(self, description: str, session: Dict, 
                     project_manager) -> Optional[str]:
        """
        Generate code based on description using Boudica
        
        Args:
            description: What to create/implement
            session: Session info (contains project context)
            project_manager: ProjectManager instance for context
        
        Returns:
            Generated code or None on failure
        """
        
        # Build context from project status
        status = project_manager.get_status()
        
        # Platform-aware prompt - ensure code is cross-platform or platform-specific as needed
        import platform
        current_os = platform.system()  # 'Linux', 'Windows', 'Darwin'
        
        # Simpler, more direct prompt that works better with Boudica
        prompt = f"""No Memory

Create a {session.get('stack')} program that: {description}

CRITICAL: This code runs on {current_os}. 
- Do NOT use Windows-only headers like <windows.h>
- Use only cross-platform standard library headers
- Use <iostream>, <fstream>, <string>, <vector>, etc. (NOT platform-specific)
- For file/OS operations, use standard C++17 <filesystem>

Output only the complete working code. No markdown, no explanations, no markdown code blocks."""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=8192,
                temperature=0.7,
                model=self.model
            )
            
            # Extract code from response - try multiple possible response keys
            code = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if code:
                code = code.strip()
                # Remove markdown code blocks if present
                if code.startswith('```'):
                    code = '\n'.join(code.split('\n')[1:-1])
                return code
            
            self.last_error = f"Empty response from Boudica. Response keys: {list(response.keys()) if response else 'None'}"
            return None
        
        except BoudicaError as e:
            self.last_error = f"Boudica API error: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error generating code: {str(e)}"
            return None
    
    def edit_code(self, current_code: str, change_description: str, 
                 filepath: str, session: Dict, project_manager) -> Optional[str]:
        """
        Edit existing code based on change request
        
        Args:
            current_code: Current file content
            change_description: What to change/improve
            filepath: File being edited
            session: Session info
            project_manager: ProjectManager instance
        
        Returns:
            Modified code or None on failure
        """
        
        status = project_manager.get_status()
        
        # CRITICAL: Explicitly ask for COMPLETE file with all code intact
        # Display file with line numbers so Boudica can see line numbers
        code_with_lines = '\n'.join(
            f"{i+1}: {line}" for i, line in enumerate(current_code.split('\n'))
        )
        
        prompt = f"""No Memory

You are editing a {session.get('stack', 'code')} file: {filepath}

CURRENT FILE (with line numbers):
{code_with_lines}

REQUIRED CHANGE: {change_description}

CRITICAL INSTRUCTIONS:
1. Make ONLY the requested change to the specified text/line
2. Return the COMPLETE ENTIRE file - every single line
3. Do NOT output line numbers - just the raw code
4. PRESERVE all other code exactly as-is - do not delete or omit anything
5. Include EVERY line from the original file
6. NO explanation, NO markdown, NO code blocks - ONLY the complete modified code"""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=8192,
                temperature=0.5,  # Lower temperature for edits
                model=self.model
            )
            
            # Try multiple possible response keys
            code = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if not code:
                self.last_error = f"Empty edit response from Boudica. Response keys: {list(response.keys()) if response else 'None'}"
                return None
            
            code = code.strip()
            
            # Remove markdown code blocks if present
            if code.startswith('```'):
                code = '\n'.join(code.split('\n')[1:-1])
            
            # Remove line numbers if Boudica accidentally included them (e.g., "1: #include <iostream>")
            lines = code.split('\n')
            cleaned_lines = []
            for line in lines:
                # Check if line starts with number(s) followed by colon and space: "123: code"
                if re.match(r'^\d+:\s', line):
                    # Strip the line number prefix
                    cleaned_lines.append(re.sub(r'^\d+:\s', '', line))
                else:
                    cleaned_lines.append(line)
            code = '\n'.join(cleaned_lines)
            
            # Validate that response looks complete - check line count didn't shrink too much
            original_lines = len(current_code.split('\n'))
            modified_lines = len(code.split('\n'))
            
            # If modified code has significantly fewer lines, it's likely incomplete
            if modified_lines < (original_lines * 0.7):  # Lost more than 30% of lines
                self.last_error = f"Warning: Modified code appears incomplete ({modified_lines} lines vs {original_lines} original). Response may be a fragment."
                # Still return it but with warning
                print(f"⚠️  {self.last_error}")
            
            return code
            
        except BoudicaError as e:
            self.last_error = f"Boudica API error: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error editing code: {str(e)}"
            return None
    
    def fix_build_error(self, error_log: str, file_path: str, 
                       current_code: str, session: Dict, 
                       project_manager, attempt: int = 1) -> Optional[str]:
        """
        Attempt to fix a build/compilation error
        
        Args:
            error_log: Build error message
            file_path: File with error
            current_code: Current file content
            session: Session info
            project_manager: ProjectManager instance
            attempt: Which attempt is this (1-5)
        
        Returns:
            Fixed code or None if can't fix
        """
        
        # Simpler, more direct prompt that works better with Boudica
        prompt = f"""No Memory

Fix this build error. Return ONLY the corrected source code. No explanations, no preamble.

Error: {error_log[:500]}

Current code:
{current_code[:2000]}

Return the complete corrected code only."""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=8192,
                temperature=0.2,
                model=self.model
            )
            
            # Try multiple possible response keys
            code = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if not code:
                self.last_error = f"Empty fix response from Boudica"
                return None
            
            code = code.strip()
            
            # Remove markdown code blocks if present
            if code.startswith('```'):
                lines = code.split('\n')
                # Find first non-backtick line and last non-backtick line
                start = 0
                end = len(lines)
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('```'):
                        if start == 0:
                            start = i
                        end = i + 1
                if start < end:
                    code = '\n'.join(lines[start:end])
            
            return code if code else None
        
        except BoudicaError as e:
            self.last_error = f"Boudica API error: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error generating fix: {str(e)}"
    
    def chat_planning(self, prompt: str, session: Dict, 
                     project_manager) -> Optional[str]:
        """
        Have a planning/discussion conversation about the project
        
        Args:
            prompt: User's question or discussion point
            session: Session info
            project_manager: ProjectManager instance
        
        Returns:
            AI response or None on failure
        """
        
        status = project_manager.get_status()
        history = project_manager.project_dir / ".boudica_project.json"
        
        # Build context
        context = f"""No Memory

You are an expert software architect helping plan a {session.get('stack')} project.

Project:
- Name: {status.get('name')}
- Type: {status.get('type')}
- Languages: {', '.join(status.get('languages', []))}
- Files: {status.get('files')}

User Question: {prompt}

Provide helpful, concise advice for the project."""
        
        try:
            response = self.client.chat(
                message=context,
                model=self.model
            )
            
            # Try multiple possible response keys for chat endpoint
            if response and 'message' in response:
                return response['message']
            elif response and 'response' in response:
                return response['response']
            elif response and 'generated_text' in response:
                return response['generated_text']
            elif response and 'text' in response:
                return response['text']
            
            self.last_error = f"Empty chat response from Boudica. Response keys: {list(response.keys()) if response else 'None'}"
            return None
        
        except BoudicaError as e:
            self.last_error = f"Boudica API error: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error in planning chat: {str(e)}"
    
    def validate_syntax(self, code: str, language: str) -> Optional[str]:
        """
        Validate code syntax using Boudica
        
        Args:
            code: Code to validate
            language: Programming language
        
        Returns:
            Error message if invalid, None if valid
        """
        
        prompt = f"""No Memory

Check this {language} code for syntax errors. If there are errors, describe them briefly. If valid, respond with "VALID".

Code:
```
{code}
```"""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=8192,
                temperature=0.2,
                model=self.model
            )
            
            # Try multiple possible response keys
            result = response.get('response', response.get('generated_text', response.get('text', '')))
            if result:
                result = result.strip()
                return None if result == "VALID" else result
            
            return None
        
        except Exception as e:
            print(f"Error validating syntax: {e}")
            return None
    
    def analyze_crash(self, crash_output: str, source_code: str, 
                     language: str, session: Dict) -> Optional[str]:
        """
        Analyze a crash using AI to suggest fixes
        
        Args:
            crash_output: Debugger output showing crash
            source_code: Source code of the program
            language: Programming language
            session: Session info
        
        Returns:
            AI analysis and suggestions or None on failure
        """
        
        prompt = f"""No Memory

Analyze this {language} program crash and suggest fixes:

DEBUGGER OUTPUT:
{crash_output[:2000]}

SOURCE CODE:
{source_code[:2000]}

Provide:
1. What caused the crash (be specific)
2. Why it's happening
3. How to fix it (code changes)
4. How to prevent it in the future

Be concise and focus on the root cause."""
        
        try:
            response = self.client.generate(
                prompt=prompt,
                max_tokens=8192,
                temperature=0.3,  # Conservative for analysis
                model=self.model
            )
            
            # Try multiple possible response keys
            analysis = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if analysis:
                return analysis.strip()
            
            self.last_error = f"Empty crash analysis response from Boudica"
            return None
        
        except BoudicaError as e:
            self.last_error = f"Boudica API error during crash analysis: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error analyzing crash: {str(e)}"
            return None
