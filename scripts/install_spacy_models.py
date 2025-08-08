#!/usr/bin/env python3
"""
spaCy 한국어 모델 설치 및 검증 스크립트

이 스크립트는 ExtractorAgent 재설계를 위해 필요한 spaCy 한국어 모델들을 설치하고 검증합니다.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """명령어를 실행하고 결과를 반환합니다."""
    print(f"\n🔄 {description}")
    print(f"명령어: {command}")
    
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ 성공: {description}")
        if result.stdout:
            print(f"출력: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 실패: {description}")
        print(f"오류: {e.stderr.strip()}")
        return False


def test_spacy_model(model_name: str) -> bool:
    """spaCy 모델이 정상적으로 로드되는지 테스트합니다."""
    print(f"\n🧪 {model_name} 모델 테스트 중...")
    
    try:
        import spacy
        nlp = spacy.load(model_name)
        
        # 테스트 문장
        test_text = "삼성전자는 대한민국의 대표적인 전자회사입니다. 이재용 회장은 서울에서 회의를 진행했습니다."
        doc = nlp(test_text)
        
        # 엔티티 추출 테스트
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        print(f"✅ {model_name} 로드 성공")
        print(f"   테스트 문장: {test_text}")
        print(f"   추출된 엔티티: {entities}")
        
        return True
    except Exception as e:
        print(f"❌ {model_name} 테스트 실패: {str(e)}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 spaCy 한국어 모델 설치 시작")
    
    # 설치할 모델 목록
    models = [
        ("ko_core_news_sm", "한국어 소형 모델 (fast 모드용)"),
        ("ko_core_news_lg", "한국어 대형 모델 (comprehensive 모드용)")
    ]
    
    success_count = 0
    total_count = len(models)
    
    # 각 모델 설치
    for model_name, description in models:
        command = f"python -m spacy download {model_name}"
        if run_command(command, description):
            if test_spacy_model(model_name):
                success_count += 1
            else:
                print(f"⚠️  {model_name} 설치는 성공했지만 테스트에 실패했습니다.")
        else:
            print(f"❌ {model_name} 설치에 실패했습니다.")
    
    # 결과 요약
    print(f"\n📊 설치 결과 요약:")
    print(f"   성공: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 모든 spaCy 모델이 성공적으로 설치되었습니다!")
        
        # 추가 정보 출력
        print(f"\n📝 설치된 모델 정보:")
        print(f"   • ko_core_news_sm: 빠른 처리를 위한 소형 모델")
        print(f"   • ko_core_news_lg: 높은 정확도를 위한 대형 모델")
        print(f"\n🔧 사용 예시:")
        print(f"   import spacy")
        print(f"   nlp_sm = spacy.load('ko_core_news_sm')  # fast 모드")
        print(f"   nlp_lg = spacy.load('ko_core_news_lg')  # comprehensive 모드")
        
        return True
    else:
        print("❌ 일부 모델 설치에 실패했습니다. 위의 오류를 확인해주세요.")
        return False


if __name__ == "__main__":
    # 스크립트가 프로젝트 루트에서 실행되는지 확인
    project_root = Path.cwd()
    if not (project_root / "requirements.txt").exists():
        print("❌ 프로젝트 루트 디렉토리에서 실행해주세요.")
        sys.exit(1)
    
    # spaCy가 설치되어 있는지 확인
    try:
        import spacy
        print(f"✅ spaCy {spacy.__version__} 감지됨")
    except ImportError:
        print("❌ spaCy가 설치되지 않았습니다. 먼저 'pip install spacy'를 실행해주세요.")
        sys.exit(1)
    
    # 메인 함수 실행
    success = main()
    sys.exit(0 if success else 1)