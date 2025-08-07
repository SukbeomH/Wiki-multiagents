#!/usr/bin/env python3
"""
Import 경로 업데이트 스크립트

기존 server. 기반 import 경로를 새로운 src. 기반 구조로 변경합니다.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class ImportPathUpdater:
    """Import 경로 업데이트 클래스"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.changes_made = []
        
        # Import 경로 매핑 (정규식 패턴, 새 경로)
        self.import_mappings = [
            # 스키마 관련
            (r'from server\.schemas\.base import', 'from src.core.schemas.base import'),
            (r'from server\.schemas\.agents import', 'from src.core.schemas.agents import'),
            (r'from server\.schemas\.', 'from src.core.schemas.'),
            
            # 저장소 관련
            (r'from server\.retrieval\.vector_store import', 'from src.core.storage.vector_store.vector_store import'),
            (r'from server\.retrieval\.', 'from src.core.storage.'),
            (r'from server\.utils\.kg_manager import', 'from src.core.storage.knowledge_graph.kg_manager import'),
            
            # 유틸리티 관련
            (r'from server\.utils\.config import', 'from src.core.utils.config import'),
            (r'from server\.utils\.cache_manager import', 'from src.core.utils.cache_manager import'),
            (r'from server\.utils\.lock_manager import', 'from src.core.utils.lock_manager import'),
            (r'from server\.utils\.storage_manager import', 'from src.core.utils.storage_manager import'),
            (r'from server\.utils\.scheduler import', 'from src.core.utils.scheduler import'),
            (r'from server\.utils\.', 'from src.core.utils.'),
            
            # 에이전트 관련
            (r'from server\.agents\.research\.client import', 'from src.agents.research.client import'),
            (r'from server\.agents\.research\.cache import', 'from src.agents.research.cache import'),
            (r'from server\.agents\.research\.agent import', 'from src.agents.research.agent import'),
            (r'from server\.agents\.research\.config import', 'from src.agents.research.config import'),
            (r'from server\.agents\.research import', 'from src.agents.research import'),
            (r'from server\.agents\.retriever import', 'from src.agents.retriever import'),
            (r'from server\.agents\.', 'from src.agents.'),
            
            # API 관련
            (r'from server\.main import', 'from src.api.main import'),
            (r'from server\.routers import', 'from src.api.routes import'),
            (r'from server\.', 'from src.api.'),
            
            # Import 문
            (r'import server\.', 'import src.api.'),
            
            # 데이터베이스 관련 (임시 - 나중에 마이그레이션)
            (r'from server\.db\.models import', 'from src.core.storage.history.models import'),
            (r'from server\.db\.schemas import', 'from src.core.storage.history.schemas import'),
        ]
    
    def update_file(self, file_path: Path) -> bool:
        """단일 파일의 import 경로를 업데이트"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_changes = []
            
            # 각 매핑 패턴 적용
            for old_pattern, new_pattern in self.import_mappings:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    file_changes.append(f"  {old_pattern} → {new_pattern}")
            
            # 변경사항이 있으면 파일 업데이트
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.changes_made.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'changes': file_changes
                })
                return True
            
            return False
            
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False
    
    def process_directory(self, directory: str, exclude_patterns: List[str] = None) -> int:
        """디렉토리 내 모든 Python 파일 처리"""
        if exclude_patterns is None:
            exclude_patterns = ['__pycache__', '.git', 'venv', '.pytest_cache']
        
        directory_path = self.project_root / directory
        if not directory_path.exists():
            print(f"Directory not found: {directory_path}")
            return 0
        
        updated_files = 0
        
        for file_path in directory_path.rglob('*.py'):
            # 제외 패턴 확인
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue
            
            if self.update_file(file_path):
                updated_files += 1
        
        return updated_files
    
    def print_changes(self):
        """변경사항 출력"""
        if not self.changes_made:
            print("No changes made.")
            return
        
        print(f"\nUpdated {len(self.changes_made)} files:")
        print("=" * 50)
        
        for change in self.changes_made:
            print(f"\n{change['file']}:")
            for change_detail in change['changes']:
                print(change_detail)
    
    def save_changes_report(self, report_path: str = "import_changes_report.txt"):
        """변경사항 보고서 저장"""
        report_path = self.project_root / report_path
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("Import Path Update Report\n")
            f.write("=" * 30 + "\n\n")
            f.write(f"Total files updated: {len(self.changes_made)}\n\n")
            
            for change in self.changes_made:
                f.write(f"File: {change['file']}\n")
                for change_detail in change['changes']:
                    f.write(f"  {change_detail}\n")
                f.write("\n")
        
        print(f"Changes report saved to: {report_path}")

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("Usage: python update_imports.py <project_root> [directory1] [directory2] ...")
        print("Example: python update_imports.py . src tests")
        sys.exit(1)
    
    project_root = sys.argv[1]
    directories = sys.argv[2:] if len(sys.argv) > 2 else ['src', 'tests']
    
    updater = ImportPathUpdater(project_root)
    
    print("Starting import path updates...")
    print(f"Project root: {project_root}")
    print(f"Directories to process: {directories}")
    
    total_updated = 0
    
    for directory in directories:
        print(f"\nProcessing directory: {directory}")
        updated_count = updater.process_directory(directory)
        total_updated += updated_count
        print(f"Updated {updated_count} files in {directory}")
    
    print(f"\nTotal files updated: {total_updated}")
    
    # 변경사항 출력
    updater.print_changes()
    
    # 보고서 저장
    updater.save_changes_report()
    
    print("\nImport path update completed!")
    print("Please review the changes and run tests to ensure everything works correctly.")

if __name__ == "__main__":
    main()