#!/usr/bin/env python3
"""
Import 경로 검증 스크립트

변경된 import 경로가 올바른지 검증하고 문제점을 보고합니다.
"""

import os
import re
import sys
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple

class ImportValidator:
    """Import 경로 검증 클래스"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors = []
        self.warnings = []
        self.imports = []
        
    def parse_imports(self, file_path: Path) -> List[Dict]:
        """파일에서 import 문을 파싱"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            file_imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        file_imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'asname': alias.asname,
                            'line': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    file_imports.append({
                        'type': 'from',
                        'module': node.module or '',
                        'names': [alias.name for alias in node.names],
                        'line': node.lineno
                    })
            
            return file_imports
            
        except Exception as e:
            self.errors.append(f"Error parsing {file_path}: {e}")
            return []
    
    def validate_import_path(self, import_path: str, file_path: Path) -> bool:
        """Import 경로가 유효한지 검증"""
        if not import_path.startswith('src.'):
            return True  # src.로 시작하지 않는 import는 건너뜀
        
        # src. 경로를 실제 파일 경로로 변환
        relative_path = import_path.replace('src.', '')
        module_path = self.project_root / 'src' / relative_path.replace('.', '/')
        
        # 가능한 파일 경로들
        possible_paths = [
            module_path.with_suffix('.py'),
            module_path / '__init__.py',
            module_path.with_suffix('.py').parent / '__init__.py'
        ]
        
        # 실제 파일이 존재하는지 확인
        for path in possible_paths:
            if path.exists():
                return True
        
        self.errors.append(f"Invalid import path '{import_path}' in {file_path}")
        return False
    
    def check_circular_imports(self) -> List[List[str]]:
        """순환 의존성 검사"""
        # 간단한 순환 의존성 검사
        # 실제로는 더 복잡한 그래프 분석이 필요
        circular_imports = []
        
        # src.core가 다른 모듈에 의존하는지 확인
        core_imports = []
        for imp in self.imports:
            if 'src.core' in str(imp.get('module', '')):
                if 'src.agents' in str(imp.get('module', '')) or 'src.api' in str(imp.get('module', '')):
                    core_imports.append(imp)
        
        if core_imports:
            self.warnings.append("src.core imports from other modules - potential circular dependency")
            circular_imports.append([str(imp) for imp in core_imports])
        
        return circular_imports
    
    def validate_file(self, file_path: Path) -> bool:
        """단일 파일의 import 검증"""
        file_imports = self.parse_imports(file_path)
        
        for imp in file_imports:
            imp['file'] = str(file_path.relative_to(self.project_root))
            self.imports.append(imp)
            
            if imp['type'] == 'from' and imp['module']:
                if not self.validate_import_path(imp['module'], file_path):
                    return False
            elif imp['type'] == 'import':
                if not self.validate_import_path(imp['module'], file_path):
                    return False
        
        return True
    
    def process_directory(self, directory: str, exclude_patterns: List[str] = None) -> int:
        """디렉토리 내 모든 Python 파일 검증"""
        if exclude_patterns is None:
            exclude_patterns = ['__pycache__', '.git', 'venv', '.pytest_cache']
        
        directory_path = self.project_root / directory
        if not directory_path.exists():
            print(f"Directory not found: {directory_path}")
            return 0
        
        validated_files = 0
        
        for file_path in directory_path.rglob('*.py'):
            # 제외 패턴 확인
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue
            
            if self.validate_file(file_path):
                validated_files += 1
        
        return validated_files
    
    def generate_report(self) -> str:
        """검증 보고서 생성"""
        report = []
        report.append("Import Path Validation Report")
        report.append("=" * 40)
        report.append(f"Total imports analyzed: {len(self.imports)}")
        report.append(f"Files validated: {len(set(imp['file'] for imp in self.imports))}")
        report.append(f"Errors: {len(self.errors)}")
        report.append(f"Warnings: {len(self.warnings)}")
        report.append("")
        
        if self.errors:
            report.append("ERRORS:")
            report.append("-" * 10)
            for error in self.errors:
                report.append(f"  {error}")
            report.append("")
        
        if self.warnings:
            report.append("WARNINGS:")
            report.append("-" * 12)
            for warning in self.warnings:
                report.append(f"  {warning}")
            report.append("")
        
        # Import 통계
        src_imports = [imp for imp in self.imports if 'src.' in str(imp.get('module', ''))]
        report.append("IMPORT STATISTICS:")
        report.append("-" * 20)
        report.append(f"src. imports: {len(src_imports)}")
        report.append(f"Other imports: {len(self.imports) - len(src_imports)}")
        report.append("")
        
        # Import 패턴 분석
        import_patterns = {}
        for imp in self.imports:
            module = imp.get('module', '')
            if module.startswith('src.'):
                pattern = '.'.join(module.split('.')[:3])  # src.agents.research
                import_patterns[pattern] = import_patterns.get(pattern, 0) + 1
        
        if import_patterns:
            report.append("IMPORT PATTERNS:")
            report.append("-" * 17)
            for pattern, count in sorted(import_patterns.items()):
                report.append(f"  {pattern}: {count} imports")
        
        return '\n'.join(report)
    
    def save_report(self, report_path: str = "import_validation_report.txt"):
        """검증 보고서 저장"""
        report_path = self.project_root / report_path
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"Validation report saved to: {report_path}")

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("Usage: python validate_imports.py <project_root> [directory1] [directory2] ...")
        print("Example: python validate_imports.py . src tests")
        sys.exit(1)
    
    project_root = sys.argv[1]
    directories = sys.argv[2:] if len(sys.argv) > 2 else ['src', 'tests']
    
    validator = ImportValidator(project_root)
    
    print("Starting import path validation...")
    print(f"Project root: {project_root}")
    print(f"Directories to validate: {directories}")
    
    total_validated = 0
    
    for directory in directories:
        print(f"\nValidating directory: {directory}")
        validated_count = validator.process_directory(directory)
        total_validated += validated_count
        print(f"Validated {validated_count} files in {directory}")
    
    # 순환 의존성 검사
    circular_imports = validator.check_circular_imports()
    
    # 보고서 생성 및 출력
    report = validator.generate_report()
    print("\n" + report)
    
    # 보고서 저장
    validator.save_report()
    
    # 결과 요약
    if validator.errors:
        print(f"\n❌ Validation failed with {len(validator.errors)} errors")
        sys.exit(1)
    elif validator.warnings:
        print(f"\n⚠️  Validation completed with {len(validator.warnings)} warnings")
    else:
        print(f"\n✅ Validation completed successfully!")

if __name__ == "__main__":
    main()