"""
Boudica Integration - Calls Boudica inference server for code generation and planning
"""

import sys
import os
import json
import re
import html
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
            print("\n1. Go to: https://boudi.ca/api_keys/")
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
    
    def _extract_code_from_response(self, response_text: str) -> str:
        """
        Extract code from various response formats:
        - HTML-wrapped: <!DOCTYPE...><pre>actual code</pre></body></html>
        - Markdown blocks: ```cpp\ncode\n```
        - Plain code with prompt echo
        
        Args:
            response_text: Raw response from Boudica
        
        Returns:
            Clean code
        """
        text = response_text.strip()
        
        # Check if HTML-wrapped (starts with <!DOCTYPE or <html)
        if text.lower().startswith(('<!doctype', '<html')):
            # Extract from <pre> tags, handling both variations
            pre_patterns = [
                r'<pre[^>]*>(.*?)</pre>',  # Most common
                r'<code[^>]*>(.*?)</code>',  # Alternative
            ]
            
            for pattern in pre_patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    code = match.group(1).strip()
                    # Decode HTML entities: &lt; -> <, &gt; -> >, &quot; -> ", etc.
                    code = html.unescape(code)
                    return code
            
            # If no pre/code tags found but it's HTML, extract all text content
            # Remove HTML tags
            code = re.sub(r'<[^>]+>', '', text)
            code = html.unescape(code).strip()
            # Remove HTML boilerplate text
            for boilerplate in ['C++ Program', 'Program to', 'DOCTYPE', 'html', 'head', 'body', 'title', 'style', 'footer']:
                code = re.sub(rf'(?i).*?{boilerplate}.*?\n', '', code)
            return code.strip()
        
        return text
    
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
                model=self.model,
                no_memory=True  # Disable memory for deterministic parsing
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
                model=self.model,
                no_memory=True  # Disable memory for deterministic parsing
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
            # Use /chat endpoint for iterative code generation with context
            response = self.client.chat(
                message=prompt,
                max_tokens=8192,
                temperature=0.7,
                model=self.model
            )
            
            # Extract code from response - try multiple possible response keys
            code = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if code:
                # CRITICAL FIX: Handle multiple response formats (HTML, markdown, plain with prompt echo)
                code = self._extract_code_from_response(code)
                
                # Remove markdown code blocks if present
                if code.startswith('```'):
                    code = '\n'.join(code.split('\n')[1:-1])
                
                # Skip everything before actual code starts
                lines = code.split('\n')
                code_start_idx = 0
                
                # Look for the first line that appears to be actual code (not prompt text)
                code_indicators = ['#include', 'import ', '#!', '//', 'namespace', 'class ', 'struct ', 
                                  'def ', 'int ', 'void ', 'return ', 'if ', 'while ', 'for ', '@', 'package ', 'public ']
                
                for idx, line in enumerate(lines):
                    stripped = line.strip()
                    # Skip empty lines at the start
                    if not stripped:
                        continue
                    # Skip prompt echo lines
                    if any(prompt_text in line for prompt_text in ['Create a ', 'CRITICAL:', 'Output only', 
                                                                   'No markdown', 'Do NOT use', 'Use only', 'Use <']):
                        continue
                    # Check if this looks like actual code
                    if any(stripped.startswith(indicator) for indicator in code_indicators):
                        code_start_idx = idx
                        break
                    # If we hit a line that looks like code (contains actual code structure)
                    if any(pattern in stripped for pattern in ['<', '>', '::',  '()', '{}', ';']):
                        code_start_idx = idx
                        break
                
                # Extract code from identified start point
                code = '\n'.join(lines[code_start_idx:]).strip()
                return code
            
            self.last_error = f"Empty response from Boudica. Response keys: {list(response.keys()) if response else 'None'}"
            return None
        
        except BoudicaError as e:
            self.last_error = f"Boudica API error: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error generating code: {str(e)}"
            return None
    
    def clarify_request(self, user_request: str, session: Dict) -> str:
        """
        Use Boudica to clarify and improve a vague user request before actual editing
        
        Args:
            user_request: User's original change request (may be vague)
            session: Session info (for stack info)
        
        Returns:
            Clarified, more specific request suitable for code editing
        """
        
        prompt = f"""No Memory

Clarify this prompt: '{user_request}'

The code language will be {session.get('stack', 'code')}

Do not request the code. Just improve the prompt so that when it and the code are sent, the instruction will be clear and actionable.

Clarified prompt:"""
        
        try:
            # Use /generate endpoint to avoid filling /chat memory
            response = self.client.generate(
                prompt=prompt,
                max_tokens=256,  # Clarifications are short
                temperature=0.3,  # Fairly deterministic
                model=self.model,
                no_memory=True  # Disable memory for consistent clarifications
            )
            
            clarified = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if not clarified:
                # If Boudica returns nothing, use original
                return user_request.strip()
            
            clarified = clarified.strip()
            
            # Clean up any prefix if Boudica echoed it back
            for prefix in ['Restate this request:', 'Clarified request:', 'Request:', 'Output:']:
                if clarified.lower().startswith(prefix.lower()):
                    clarified = clarified[len(prefix):].strip()
            
            # VALIDATION: Check if clarified request was truncated or corrupted
            truncation_indicators = [
                '<<', '>>', 'std::', '<<\n',  # C++ incomplete operators
                'please provide', 'what',      # Signs Boudica asked for more info
            ]
            
            # Check for incomplete quotes
            if clarified.endswith('"') or clarified.endswith("'"):
                # Unclosed quote or ends at quote boundary
                double_quotes = clarified.count('"')
                single_quotes = clarified.count("'")
                if double_quotes % 2 != 0 or single_quotes % 2 != 0:
                    return user_request.strip()
            
            # Check if significantly shorter (likely truncated)
            if len(clarified) < len(user_request) * 0.3 or len(clarified) < 10:
                return user_request.strip()
            
            # Check for truncation indicators
            for indicator in truncation_indicators:
                if indicator in clarified:
                    return user_request.strip()
            
            # If result looks reasonable, use it; otherwise fall back to original
            if len(clarified) > 3 and len(clarified) < 1000:
                return clarified
            else:
                return user_request.strip()
                
        except BoudicaError as e:
            # If clarification fails, just use original request
            return user_request.strip()
        except Exception as e:
            # If clarification fails, just use original request
            return user_request.strip()
    
    def validate_edit_request(self, change_description: str) -> tuple:
        """
        Validate that a change request doesn't contain embedded code snippets
        which confuse Boudica.
        
        Args:
            change_description: The requested change
        
        Returns:
            (is_valid, error_message) tuple
            - is_valid: True if request is valid
            - error_message: String explaining the issue if invalid
        """
        
        # Detect code snippet indicators
        code_indicators = [
            (r'<<\s*["\']', 'C++ stream operator with quotes'),
            (r'>>\s*["\']', 'C++ stream operator with quotes'),
            (r'["\'][^"\']*<<', 'Code snippet with << operator'),
            (r'["\'][^"\']*>>', 'Code snippet with >> operator'),
            (r'\{[^}]*\}', 'Code block with braces'),
            (r'["\'][^"\']*;[^"\']*["\']', 'Code snippet with semicolon'),
        ]
        
        for pattern, desc in code_indicators:
            if re.search(pattern, change_description):
                return False, f"Your request contains embedded code ({desc}). Please describe the change in plain language instead. For example, instead of 'change the line \"std::cout << ...\" to add color', say 'add color to the wordCount output on line 54'."
        
        return True, ""

    
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
        
        # Strip backticks from clarified request (cleanup from NLP)
        clean_description = change_description.replace('`', '')
        
        # Remove ALL filepath references to prevent duplication in prompt
        # This prevents Boudica from trying an agentic flow on non-existent tasks
        # Match patterns like:
        #   "modify the file src/main.cpp..."
        #   "change the file src/main.cpp to..."
        #   "src/main.cpp"
        #   "add src/main.cpp..."
        
        # Get just the filename part for matching
        filepath_base = filepath.split('/')[-1]  # "main.cpp" from "src/main.cpp"
        
        # Remove "modify/edit/change the file [path] to/and" patterns
        clean_description = re.sub(
            r'\b(modify|edit|change|update|add)\s+(the\s+)?file\s+' + re.escape(filepath) + r'(\s+(to|and))?',
            '',
            clean_description,
            flags=re.IGNORECASE
        )
        
        # Remove standalone filepath references  
        clean_description = re.sub(
            r'\b' + re.escape(filepath) + r'\b',
            '',
            clean_description,
            flags=re.IGNORECASE
        )
        
        # Remove just the filename if it appears alone
        clean_description = re.sub(
            r'\b' + re.escape(filepath_base) + r'\b',
            '',
            clean_description,
            flags=re.IGNORECASE
        )
        
        # Clean up multiple spaces
        clean_description = re.sub(r'\s+', ' ', clean_description).strip()
        
        # Extract line numbers from description
        lines = current_code.split('\n')
        
        # Show full file with line numbers
        preview_lines = '\n'.join(f'{i+1:3d}: {line}' for i, line in enumerate(lines))
        
        # Build prompt - instruction FIRST, then context
        prompt = f"""No Memory
GENERATE UNIFIED DIFF ONLY. NO EXPLANATIONS. NO FULL CODE.

Modify {filepath}:
{clean_description}

File:
{preview_lines}

Format: --- filepath +++ filepath @@ -start,count +start,count @@ -old +new"""
        
        try:
            # Use /generate endpoint for diffs - avoids /chat memory interference
            # Diffs are short so no truncation issues
            response = self.client.generate(
                prompt=prompt,
                max_tokens=4096,  # Diffs are very short
                temperature=0.2,  # Very low for precise diffs
                model=self.model,
                no_memory=True  # Disable memory search for edits
            )
            
            
            diff_text = response.get('response', response.get('generated_text', response.get('text', '')))
            
            
            if not diff_text:
                self.last_error = f"Empty response from Boudica"
                return None
            
            # Strip markdown code fence if Boudica wrapped the diff
            diff_text = diff_text.strip()
            if diff_text.startswith('```'):
                # Remove opening ``` and optionally language marker (e.g., ```diff)
                lines = diff_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]  # Remove first line
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]  # Remove last line
                diff_text = '\n'.join(lines).strip()
            
            print("=" * 80)
            print(diff_text)
            print("=" * 80)
            
            # Apply unified diff to original code
            try:
                modified_code = self._apply_unified_diff(current_code, diff_text)
                if modified_code is None:
                    # Diff parsing failed - return error
                    return None
                    
                return modified_code
                
            except Exception as e:
                self.last_error = f"Failed to apply diff: {str(e)}"
                return None
        
        except BoudicaError as e:
            self.last_error = f"Boudica API error: {str(e)}"
            return None
        except Exception as e:
            self.last_error = f"Error editing code: {str(e)}"
            return None
    
    def _apply_unified_diff(self, original_code: str, diff_text: str) -> Optional[str]:
        """Apply a unified diff to code and return modified version.
        
        Args:
            original_code: Original file content
            diff_text: Unified diff format
            
        Returns:
            Modified code or None if diff is invalid
        """
        try:
            original_lines = original_code.split('\n')
            diff_lines = diff_text.strip().split('\n')
            
            
            # Find the actual diff content (skip any preamble)
            diff_start = 0
            found_at_symbol = False
            for i, line in enumerate(diff_lines):
                if line.startswith('@@'):
                    diff_start = i
                    found_at_symbol = True
                    break
            
            if not found_at_symbol:
                # No @@ found - check if diff is in a different format
                self.last_error = "Invalid diff format: no @@ markers found"
                return None
            
            # Use manual parsing to apply diff
            diff_lines_to_apply = diff_lines[diff_start:]
            patched = self._manual_apply_diff(original_lines, diff_lines_to_apply)
            
            result = '\n'.join(patched)
            
            # Validate result is reasonable (not empty, not too different)
            if not result.strip():
                self.last_error = "Diff resulted in empty file"
                return None
                
            return result
            
        except Exception as e:
            self.last_error = f"Diff parsing failed: {str(e)}"
            import traceback
            traceback.print_exc()
            return None
    
    def _manual_apply_diff(self, original_lines: list, diff_lines: list) -> list:
        """Manually apply diff lines when difflib fails.
        
        Args:
            original_lines: List of original code lines (already split by \n)
            diff_lines: List of diff lines (starting with @@)
            
        Returns:
            Patched lines list
        """
        result = []
        orig_idx = 0  # Current position in original
        
        
        i = 0
        while i < len(diff_lines):
            line = diff_lines[i]
            
            if line.startswith('@@'):
                # Parse header: @@ -START,COUNT +START,COUNT @@
                # Example: @@ -45,3 +45,4 @@
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    orig_start = int(match.group(1)) - 1  # Convert to 0-indexed
                    target_start = int(match.group(3)) - 1  # Target line start
                    
                    
                    # Copy any lines we haven't reached yet from original
                    while orig_idx < orig_start and orig_idx < len(original_lines):
                        result.append(original_lines[orig_idx])
                        orig_idx += 1
                    
                    # Now process the hunk (lines after @@)
                    i += 1
                    hunk_count = 0
                    while i < len(diff_lines):
                        hunk_line = diff_lines[i]
                        
                        # Stop at next @@ marker or end of lines with special handling
                        if hunk_line.startswith('@@'):
                            break
                        
                        if hunk_line.startswith('-'):
                            # Remove: skip this line in original
                            removed = original_lines[orig_idx] if orig_idx < len(original_lines) else '[EOF]'
                            if orig_idx < len(original_lines):
                                orig_idx += 1
                        elif hunk_line.startswith('+'):
                            # Add: add this line to result
                            new_line = hunk_line[1:]
                            result.append(new_line)
                        elif hunk_line.startswith(' '):
                            # Context: copy from original
                            context_line = hunk_line[1:]
                            result.append(context_line)
                            if orig_idx < len(original_lines):
                                orig_idx += 1
                        elif hunk_line.startswith('\\'):
                            # "\ No newline at end of file" - ignore
                            pass
                        else:
                            # Blank line in diff - treat as context
                            if orig_idx < len(original_lines) and original_lines[orig_idx] == '':
                                result.append(original_lines[orig_idx])
                                orig_idx += 1
                        
                        hunk_count += 1
                        i += 1
                    
                    # Don't increment i here since the while loop did
                    continue
            
            i += 1
        
        # Copy any remaining lines from original
        while orig_idx < len(original_lines):
            result.append(original_lines[orig_idx])
            orig_idx += 1
        
        return result
    
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
        
        # Check if this is a linker error (undefined reference to a library function)
        linker_error = self._handle_linker_error(error_log, session, project_manager)
        if linker_error:
            return linker_error
        
        # For code-based errors, try to fix the source code
        prompt = f"""No Memory

Fix this build error. Return ONLY the corrected source code. No explanations, no preamble.

Error: {error_log[:500]}

Current code:
{current_code[:2000]}

Return the complete corrected code only."""
        
        try:
            response = self.client.chat(
                message=prompt,
                max_tokens=8192,
                temperature=0.2,
                model=self.model
            )
            
            # Try multiple possible response keys
            code = response.get('response', response.get('generated_text', response.get('text', '')))
            
            if not code:
                self.last_error = f"Empty fix response from Boudica"
                return None
            
            # Handle multiple response formats
            code = self._extract_code_from_response(code)
            
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
            return None
    
    def _handle_linker_error(self, error_log: str, session: Dict, 
                            project_manager) -> Optional[str]:
        """
        Detect and fix linker errors (undefined reference to library functions)
        by updating CMakeLists.txt to link required libraries
        
        Args:
            error_log: Build error message
            session: Session info
            project_manager: ProjectManager instance
        
        Returns:
            Message to show user (indicating file was updated) or None if not a linker error
        """
        
        error_lower = error_log.lower()
        
        # Detect linker error patterns
        linker_patterns = [
            (r"undefined reference to `curl_", "curl"),
            (r"undefined reference to `openssl_", "openssl"),
            (r"undefined reference to `sqlite3_", "sqlite3"),
            (r"undefined reference to `pthread_", "pthread"),
            (r"undefined reference to `mysql_", "mysql"),
            (r"undefined reference to `postgres", "postgresql"),
            (r"undefined reference to `boost_", "boost"),
            (r"cannot find -l(\w+)", None),  # Generic: cannot find -lXXX
            (r"undefined reference to `" + r"(\w+)", None),  # Generic: undefined reference
        ]
        
        library = None
        for pattern, lib in linker_patterns:
            if re.search(pattern, error_log):
                if lib:
                    library = lib
                else:
                    # Try to extract library name from error
                    match = re.search(pattern, error_log)
                    if match and match.lastindex:
                        library = match.group(1)
                break
        
        if not library:
            return None
        
        # Map library names to CMake target_link_libraries names and install commands
        lib_mappings = {
            'curl': {
                'cmake': 'curl',
                'find_package': 'CURL',
                'install_debian': 'sudo apt-get install libcurl4-openssl-dev',
                'install_macos': 'brew install curl',
                'install_fedora': 'sudo dnf install libcurl-devel',
            },
            'openssl': {
                'cmake': 'OpenSSL::Crypto OpenSSL::SSL',
                'find_package': 'OpenSSL',
                'install_debian': 'sudo apt-get install libssl-dev',
                'install_macos': 'brew install openssl',
                'install_fedora': 'sudo dnf install openssl-devel',
            },
            'sqlite3': {
                'cmake': 'sqlite3',
                'find_package': 'SQLite3',
                'install_debian': 'sudo apt-get install libsqlite3-dev',
                'install_macos': 'brew install sqlite',
                'install_fedora': 'sudo dnf install sqlite-devel',
            },
            'pthread': {
                'cmake': 'pthread',
                'find_package': None,
                'install_debian': 'Usually included with build-essential',
                'install_macos': 'Usually included with Xcode',
                'install_fedora': 'Usually included with gcc',
            },
            'mysql': {
                'cmake': 'mysqlclient',
                'find_package': 'MySQL',
                'install_debian': 'sudo apt-get install libmysqlclient-dev',
                'install_macos': 'brew install mysql-client',
                'install_fedora': 'sudo dnf install mysql-devel',
            },
            'postgresql': {
                'cmake': 'pq',
                'find_package': 'PostgreSQL',
                'install_debian': 'sudo apt-get install libpq-dev',
                'install_macos': 'brew install postgresql',
                'install_fedora': 'sudo dnf install postgresql-devel',
            },
            'boost': {
                'cmake': 'Boost::system',
                'find_package': 'Boost',
                'install_debian': 'sudo apt-get install libboost-all-dev',
                'install_macos': 'brew install boost',
                'install_fedora': 'sudo dnf install boost-devel',
            },
        }
        
        lib_config = lib_mappings.get(library)
        if not lib_config:
            return None
        
        # Read current CMakeLists.txt
        cmake_path = project_manager.project_dir / "CMakeLists.txt"
        if not cmake_path.exists():
            return None
        
        cmake_content = cmake_path.read_text()
        
        # Check if library already linked
        cmake_name = lib_config['cmake']
        if cmake_name in cmake_content:
            return None  # Already linked
        
        # Update CMakeLists.txt to include find_package and target_link_libraries
        find_package = lib_config.get('find_package')
        
        # Insert find_package if needed
        if find_package and find_package not in cmake_content:
            find_pkg_line = f"find_package({find_package} REQUIRED)\n"
            # Insert after other find_package calls or after project()
            if "find_package" in cmake_content:
                # Add after last find_package
                match = None
                for m in re.finditer(r'find_package\([^)]+\)', cmake_content):
                    match = m
                if match:
                    insert_pos = match.end()
                    cmake_content = cmake_content[:insert_pos] + "\n" + find_pkg_line + cmake_content[insert_pos:]
            else:
                # Add after project()
                match = re.search(r'project\([^)]+\)', cmake_content)
                if match:
                    insert_pos = match.end()
                    cmake_content = cmake_content[:insert_pos] + "\n" + find_pkg_line + cmake_content[insert_pos:]
        
        # Update target_link_libraries to include the library
        target_name = project_manager.project_dir.name
        link_line = f"target_link_libraries({target_name} PUBLIC {cmake_name})"
        
        if link_line not in cmake_content:
            # Find existing target_link_libraries and append to it
            link_match = re.search(rf'target_link_libraries\({target_name}[^)]*\)', cmake_content)
            if link_match:
                # Modify existing line
                old_line = link_match.group(0)
                new_line = old_line.rstrip(')') + f" {cmake_name})"
                cmake_content = cmake_content.replace(old_line, new_line)
            else:
                # Add new target_link_libraries line
                # Find add_executable or similar
                add_exec_match = re.search(r'add_executable\([^)]+\)', cmake_content)
                if add_exec_match:
                    insert_pos = add_exec_match.end()
                    cmake_content = cmake_content[:insert_pos] + f"\n{link_line}\n" + cmake_content[insert_pos:]
        
        # Write updated CMakeLists.txt
        try:
            cmake_path.write_text(cmake_content)
            self.last_error = None
            
            # Return message indicating file was updated and install instructions
            import platform
            current_os = platform.system()
            if current_os == 'Darwin':
                install_cmd = lib_config.get('install_macos', 'brew install ' + library)
            elif current_os == 'Linux':
                install_cmd = lib_config.get('install_debian', f'sudo apt-get install {library}')
            else:
                install_cmd = lib_config.get('install_fedora', f'sudo dnf install {library}')
            
            message = f"✅ Updated CMakeLists.txt to link {library}\n\n"
            message += f"⚠️  You need to install the {library} library:\n"
            message += f"   {install_cmd}\n\n"
            message += f"After installing, try building again."
            
            return message  # Return message to user, but code update doesn't apply
        
        except Exception as e:
            self.last_error = f"Failed to update CMakeLists.txt: {str(e)}"
            return None
    
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
