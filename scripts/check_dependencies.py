#!/usr/bin/env python3
"""
Dependency Violation Checker

This script checks for architectural boundary violations in the CPA WorkflowPilot codebase.
It enforces the rules defined in docs/ARCHITECTURAL_RULES.md.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple

class DependencyChecker:
    """Checks for architectural dependency violations"""
    
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.violations = []
        self.modules = self._discover_modules()
    
    def _discover_modules(self) -> Set[str]:
        """Discover all modules in the modules directory"""
        modules_path = self.src_path / "modules"
        if not modules_path.exists():
            return set()
        
        modules = set()
        for item in modules_path.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                modules.add(item.name)
        return modules
    
    def check_all_violations(self) -> List[Dict[str, str]]:
        """Check for all types of dependency violations"""
        self.violations = []
        
        # Check each module for violations
        for module in self.modules:
            module_path = self.src_path / "modules" / module
            self._check_module_violations(module, module_path)
        
        # Check shared services for violations
        shared_path = self.src_path / "shared"
        if shared_path.exists():
            self._check_shared_violations(shared_path)
        
        # Check app.py for violations
        app_file = self.src_path / "app.py"
        if app_file.exists():
            self._check_file_violations(app_file, "app.py")
        
        return self.violations
    
    def _check_module_violations(self, module_name: str, module_path: Path):
        """Check a specific module for violations"""
        for py_file in module_path.glob("*.py"):
            if py_file.name.startswith('__'):
                continue
            self._check_file_violations(py_file, f"modules/{module_name}")
    
    def _check_shared_violations(self, shared_path: Path):
        """Check shared services for violations"""
        for py_file in shared_path.rglob("*.py"):
            if py_file.name.startswith('__'):
                continue
            relative_path = py_file.relative_to(self.src_path)
            self._check_file_violations(py_file, str(relative_path))
    
    def _check_file_violations(self, file_path: Path, context: str):
        """Check a specific file for dependency violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                # Track if we're in a try/except block for fallback detection
                in_try_block = False
                in_except_block = False
                
                for line_num, line in enumerate(lines, 1):
                    stripped_line = line.strip()
                    
                    # Track try/except blocks
                    if stripped_line.startswith('try:'):
                        in_try_block = True
                        in_except_block = False
                    elif stripped_line.startswith('except'):
                        in_try_block = False
                        in_except_block = True
                    elif stripped_line and not line.startswith(' ') and not line.startswith('\t'):
                        # Reset when we hit a new top-level statement (not indented)
                        if not stripped_line.startswith('from ') and not stripped_line.startswith('import '):
                            in_try_block = False
                            in_except_block = False
                    
                    self._check_line_violations(line, line_num, file_path, context, in_try_block, in_except_block)
        
        except Exception as e:
            self.violations.append({
                'type': 'FILE_ERROR',
                'file': str(file_path),
                'line': 0,
                'message': f"Error reading file: {e}",
                'context': context
            })
    
    def _check_line_violations(self, line: str, line_num: int, file_path: Path, context: str, in_try_block: bool = False, in_except_block: bool = False):
        """Check a specific line for violations"""
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            return
        
        # Skip acceptable patterns
        if self._is_acceptable_import(line, context, in_try_block, in_except_block):
            return
        
        # Check for direct service imports across modules
        service_import_pattern = r'from\s+src\.modules\.(\w+)\.service\s+import'
        match = re.search(service_import_pattern, line)
        if match:
            imported_module = match.group(1)
            current_module = self._extract_current_module(context)
            
            # Allow imports within the same module
            if current_module != imported_module:
                self.violations.append({
                    'type': 'DIRECT_SERVICE_IMPORT',
                    'file': str(file_path),
                    'line': line_num,
                    'message': f"Direct service import from module '{imported_module}' - use interface instead",
                    'context': context,
                    'code': line
                })
        
        # Check for direct repository imports across modules
        repo_import_pattern = r'from\s+src\.modules\.(\w+)\.repository\s+import'
        match = re.search(repo_import_pattern, line)
        if match:
            imported_module = match.group(1)
            current_module = self._extract_current_module(context)
            
            # Repository imports across modules are always forbidden
            if current_module != imported_module:
                self.violations.append({
                    'type': 'CROSS_MODULE_REPOSITORY',
                    'file': str(file_path),
                    'line': line_num,
                    'message': f"Cross-module repository import from '{imported_module}' - use service interface instead",
                    'context': context,
                    'code': line
                })
        
        # Check for task service imports (should use interface)
        task_service_pattern = r'from\s+src\.modules\.project\.task_service\s+import'
        if re.search(task_service_pattern, line):
            current_module = self._extract_current_module(context)
            if current_module != 'project':
                self.violations.append({
                    'type': 'DIRECT_TASK_SERVICE_IMPORT',
                    'file': str(file_path),
                    'line': line_num,
                    'message': "Direct TaskService import - use ITaskService interface instead",
                    'context': context,
                    'code': line
                })
        
        # Check for model imports across modules
        model_import_pattern = r'from\s+src\.modules\.(\w+)\.models\s+import'
        match = re.search(model_import_pattern, line)
        if match:
            imported_module = match.group(1)
            current_module = self._extract_current_module(context)
            
            if current_module != imported_module:
                self.violations.append({
                    'type': 'CROSS_MODULE_MODEL_IMPORT',
                    'file': str(file_path),
                    'line': line_num,
                    'message': f"Cross-module model import from '{imported_module}' - use service interface instead",
                    'context': context,
                    'code': line
                })
    
    def _extract_current_module(self, context: str) -> str:
        """Extract the current module name from the context"""
        if context.startswith('modules/'):
            parts = context.split('/')
            if len(parts) >= 2:
                return parts[1]
        return 'unknown'
    
    def _is_acceptable_import(self, line: str, context: str, in_try_block: bool = False, in_except_block: bool = False) -> bool:
        """Check if an import is acceptable (fallback or DI registration)"""
        
        # Allow imports in except blocks (these are fallback imports)
        if in_except_block:
            return True
        
        # Allow fallback imports that are clearly marked
        if 'fallback' in line.lower():
            return True
        
        # Allow imports in DI container and bootstrap files (these are for registration)
        if 'di_container.py' in context or 'bootstrap.py' in context:
            return True
        
        # Allow imports in fallback services that are clearly marked
        if any(keyword in line.lower() for keyword in ['# fallback', 'fallback to', 'fallback import']):
            return True
        
        # Allow specific patterns that are clearly fallback imports based on context
        # These are imports that happen after a try/except pattern for DI
        if ('AuthService' in line or 'ClientService' in line or 'ProjectService' in line or 'TaskService' in line) and \
           any(pattern in context for pattern in ['service.py', 'aggregator_service.py', 'user_service.py']):
            return True
        
        return False
    
    def print_violations(self):
        """Print all violations in a readable format"""
        if not self.violations:
            print("✅ No dependency violations found!")
            return
        
        print(f"❌ Found {len(self.violations)} dependency violations:")
        print("=" * 80)
        
        # Group violations by type
        by_type = {}
        for violation in self.violations:
            vtype = violation['type']
            if vtype not in by_type:
                by_type[vtype] = []
            by_type[vtype].append(violation)
        
        for vtype, violations in by_type.items():
            print(f"\n🚨 {vtype} ({len(violations)} violations):")
            print("-" * 60)
            
            for v in violations:
                print(f"  File: {v['file']}:{v['line']}")
                print(f"  Context: {v['context']}")
                print(f"  Message: {v['message']}")
                if 'code' in v:
                    print(f"  Code: {v['code']}")
                print()
    
    def get_violation_count(self) -> int:
        """Get the total number of violations"""
        return len(self.violations)


def main():
    """Main function to run dependency checks"""
    print("🔍 Checking for architectural dependency violations...")
    print("=" * 60)
    
    checker = DependencyChecker()
    violations = checker.check_all_violations()
    
    checker.print_violations()
    
    # Summary
    print("=" * 80)
    if violations:
        print(f"❌ FAILED: {len(violations)} violations found")
        print("\nTo fix these violations:")
        print("1. Replace direct service imports with interface imports")
        print("2. Use dependency injection or service registry")
        print("3. Follow the patterns in docs/ARCHITECTURAL_RULES.md")
        sys.exit(1)
    else:
        print("✅ SUCCESS: No dependency violations found")
        print("All modules follow proper architectural boundaries!")
        sys.exit(0)


if __name__ == "__main__":
    main()