"""
Extractor Agent (단순화된 버전)

단일 agent.py에 통합된 spaCy 기반 NER 및 의존구문분석 기반 관계추출
- extraction_mode: comprehensive(ko_core_news_lg) 및 fast(ko_core_news_sm)만 지원
- spaCy 확률 기반 기본 신뢰도 계산
- 단순 순차 처리 방식
- 기존 테스트 케이스 완전 호환
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.schemas.agents import ExtractorIn, ExtractorOut, Entity, Relation


class ExtractorAgent:
    """단순화된 spaCy 기반 엔티티·관계 추출 에이전트"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        Extractor Agent 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # spaCy 모델 캐시
        self._nlp_models = {}
        self._legacy_mode = False
        
        # 구조화된 로그 초기화
        self._log_structured(
            "extractor_agent_initialized",
            log_level=log_level,
            architecture="simplified_spacy_based"
        )
    
    def _log_structured(self, event: str, **kwargs):
        """구조화된 JSON 로그 출력"""
        safe_kwargs = {}
        for key, value in kwargs.items():
            if hasattr(value, '__class__') and 'Mock' in value.__class__.__name__:
                safe_kwargs[key] = f"<{value.__class__.__name__}>"
            else:
                try:
                    json.dumps(value, ensure_ascii=False)
                    safe_kwargs[key] = value
                except (TypeError, ValueError):
                    safe_kwargs[key] = str(value)
        
        log_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **safe_kwargs
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def extract(self, input_data: ExtractorIn) -> ExtractorOut:
        """
        문서에서 엔티티와 관계를 추출 (단순화된 spaCy 기반)
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            ExtractorOut: 추출 결과
        """
        start_time = datetime.now()
        
        self._log_structured(
            "extraction_started",
            docs_count=len(input_data.docs),
            extraction_mode=input_data.extraction_mode,
            entity_types=input_data.entity_types,
            min_confidence=input_data.min_confidence,
            architecture="simplified_spacy_based"
        )
        
        try:
            # spaCy 모델 사용 가능성 확인
            use_spacy = self._check_spacy_availability()
            
            if use_spacy and not self._legacy_mode:
                # 단순화된 spaCy 기반 추출
                entities, relations = self._extract_with_spacy(input_data)
            else:
                # 레거시 호환성을 위한 기존 방식
                entities, relations = self._extract_legacy_mode(input_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            processing_stats = {
                "total_docs": len(input_data.docs),
                "extraction_mode": input_data.extraction_mode,
                "entities_found": len(entities),
                "relations_found": len(relations),
                "avg_confidence": (sum(e.confidence for e in entities) / len(entities)) if entities else 0.0,
                "processing_time": processing_time,
                "method": "simplified_spacy_based" if use_spacy and not self._legacy_mode else "legacy"
            }
            
            result = ExtractorOut(
                entities=entities,
                relations=relations,
                processing_stats=processing_stats
            )
            
            self._log_structured(
                "extraction_completed",
                entities_count=len(entities),
                relations_count=len(relations),
                processing_time=processing_time,
                method=processing_stats["method"]
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._log_structured(
                "extraction_failed",
                error=str(e),
                processing_time=processing_time
            )
            
            # 오류 시에도 유효한 ExtractorOut 반환
            processing_stats = {
                "total_docs": len(input_data.docs),
                "extraction_mode": input_data.extraction_mode,
                "entities_found": 0,
                "relations_found": 0,
                "avg_confidence": 0.0,
                "processing_time": processing_time,
                "error": str(e)
            }
            
            return ExtractorOut(
                entities=[],
                relations=[],
                processing_stats=processing_stats
            )

    # ---------------------------------------------------------------------
    # 단순화된 spaCy 기반 추출 메서드들
    # ---------------------------------------------------------------------
    
    def _check_spacy_availability(self) -> bool:
        """spaCy 모델 사용 가능성을 확인합니다."""
        try:
            import spacy
            # 기본 모델 로딩 시도
            spacy.load("ko_core_news_sm")
            return True
        except Exception as e:
            self.logger.warning(f"spaCy 모델 사용 불가능: {e}")
            return False
    
    def _extract_with_spacy(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """단순화된 spaCy 기반 추출"""
        try:
            # 모델 로딩
            model_name = "ko_core_news_lg" if input_data.extraction_mode == "comprehensive" else "ko_core_news_sm"
            nlp = self._load_spacy_model(model_name)
            
            entities = []
            relations = []
            
            # 각 문서별로 순차 처리
            for doc_text in input_data.docs:
                doc = nlp(doc_text)
                
                # 엔티티 추출
                doc_entities = self._extract_entities_from_doc(doc, input_data)
                entities.extend(doc_entities)
                
                # 관계 추출
                doc_relations = self._extract_relations_from_doc(doc, doc_entities, input_data)
                relations.extend(doc_relations)
            
            # 중복 제거 및 신뢰도 필터링
            entities = self._deduplicate_entities(entities)
            entities = [e for e in entities if e.confidence >= input_data.min_confidence]
            
            relations = self._deduplicate_relations(relations)
            relations = [r for r in relations if r.confidence >= input_data.min_confidence]
            
            return entities, relations
            
        except Exception as e:
            self.logger.error(f"spaCy 기반 추출 실패, 레거시 모드로 전환: {e}")
            return self._extract_legacy_mode(input_data)
    
    def _load_spacy_model(self, model_name: str):
        """spaCy 모델을 로딩합니다."""
        if model_name not in self._nlp_models:
            try:
                import spacy
                self._nlp_models[model_name] = spacy.load(model_name)
                self.logger.info(f"spaCy 모델 로딩 완료: {model_name}")
            except Exception as e:
                self.logger.error(f"spaCy 모델 로딩 실패: {model_name}, {e}")
                # fallback to smaller model
                if model_name == "ko_core_news_lg":
                    return self._load_spacy_model("ko_core_news_sm")
                else:
                    raise
        return self._nlp_models[model_name]
    
    def _extract_entities_from_doc(self, doc, input_data: ExtractorIn) -> List[Entity]:
        """문서에서 엔티티를 추출합니다."""
        entities = []
        seen_names = set()
        
        for ent in doc.ents:
            # 엔티티 타입 필터링
            mapped_type = self._map_spacy_label_to_schema(ent.label_)
            if input_data.entity_types and mapped_type not in input_data.entity_types:
                continue
            
            # 한국어 조사 제거
            clean_name = self._remove_korean_particles(ent.text)
            
            # 중복 제거
            if clean_name in seen_names:
                continue
            seen_names.add(clean_name)
            
            # 신뢰도 계산 (spaCy 확률 기반)
            confidence = self._calculate_entity_confidence(ent, doc)
            
            entity = Entity(
                id=str(uuid.uuid4()),
                type=mapped_type,
                name=clean_name,  # 조사 제거된 이름 사용
                confidence=confidence
            )
            entities.append(entity)
        
        return entities
    
    def _remove_korean_particles(self, text: str) -> str:
        """한국어 조사를 제거합니다."""
        korean_particles = [
            '은', '는', '이', '가', '을', '를', '와', '과', '에', '에서', 
            '로', '으로', '의', '도', '만', '부터', '까지', '한테', '에게'
        ]
        
        for particle in korean_particles:
            if text.endswith(particle):
                return text[:-len(particle)]
        
        return text
    
    def _extract_relations_from_doc(self, doc, entities: List[Entity], input_data: ExtractorIn) -> List[Relation]:
        """문서에서 관계를 추출합니다."""
        relations = []
        name_to_entity = {ent.name: ent for ent in entities}
        
        # 의존구문분석 기반 관계 추출
        for token in doc:
            # 주어-동사-목적어 관계
            if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                subject_entity = self._find_entity_for_token(token, name_to_entity)
                if subject_entity:
                    # 목적어 찾기
                    for obj_token in token.head.children:
                        if obj_token.dep_ in ["obj", "dobj"]:
                            object_entity = self._find_entity_for_token(obj_token, name_to_entity)
                            if object_entity:
                                predicate = self._map_verb_to_relation(token.head.lemma_)
                                if predicate:
                                    confidence = self._calculate_relation_confidence(
                                        subject_entity, object_entity, predicate, doc.text
                                    )
                                    relations.append(Relation(
                                        source=subject_entity.id,
                                        target=object_entity.id,
                                        predicate=predicate,
                                        confidence=confidence
                                    ))
        
        # 패턴 기반 관계 추출 (기본적인 패턴만)
        pattern_relations = self._extract_relations_by_patterns(doc.text, entities)
        relations.extend(pattern_relations)
        
        return relations
    
    def _map_spacy_label_to_schema(self, spacy_label: str) -> str:
        """spaCy 라벨을 스키마 타입으로 매핑합니다."""
        mapping = {
            "PS": "PERSON",
            "LC": "LOCATION", 
            "OG": "ORGANIZATION",
            "DT": "DATETIME",
            "QT": "QUANTITY"
        }
        return mapping.get(spacy_label, "CONCEPT")
    
    def _calculate_entity_confidence(self, ent, doc) -> float:
        """엔티티 신뢰도를 계산합니다 (spaCy 확률 기반)."""
        # 기본 신뢰도 (엔티티 길이 기반)
        base_confidence = min(0.9, 0.5 + len(ent.text) * 0.1)
        
        # spaCy 확률 (가능한 경우)
        if hasattr(ent, 'prob') and ent.prob is not None:
            spacy_prob = ent.prob
            # 확률을 0.5-0.9 범위로 정규화
            confidence = 0.5 + (spacy_prob * 0.4)
        else:
            confidence = base_confidence
        
        return min(1.0, max(0.0, confidence))
    
    def _calculate_relation_confidence(self, source_entity: Entity, target_entity: Entity, predicate: str, context: str) -> float:
        """관계 신뢰도를 계산합니다."""
        # 기본 신뢰도
        base_confidence = 0.7
        
        # 엔티티 신뢰도 반영
        entity_confidence = (source_entity.confidence + target_entity.confidence) / 2
        confidence = (base_confidence + entity_confidence) / 2
        
        # 컨텍스트 지원 확인
        if predicate in context:
            confidence += 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def _find_entity_for_token(self, token, name_to_entity: Dict[str, Entity]) -> Optional[Entity]:
        """토큰에 해당하는 엔티티를 찾습니다."""
        # 한국어 조사 제거
        korean_particles = ['은', '는', '이', '가', '을', '를', '와', '과', '에', '에서', '로', '으로', '의', '도', '만']
        
        token_text = token.text
        
        # 1. 정확한 매칭
        if token_text in name_to_entity:
            return name_to_entity[token_text]
        
        # 2. 조사 제거 후 매칭
        for particle in korean_particles:
            if token_text.endswith(particle):
                clean_text = token_text[:-len(particle)]
                if clean_text in name_to_entity:
                    return name_to_entity[clean_text]
        
        # 3. 부분 매칭
        for entity_name, entity in name_to_entity.items():
            if entity_name in token_text or token_text in entity_name:
                return entity
        
        return None
    
    def _map_verb_to_relation(self, verb_lemma: str) -> Optional[str]:
        """동사 원형을 관계 타입으로 매핑합니다."""
        mapping = {
            "경쟁하다": "COMPETES_WITH",
            "협력하다": "COLLABORATES_WITH",
            "인수하다": "ACQUIRED",
            "투자하다": "INVESTED_IN",
            "근무하다": "WORKS_FOR",
            "위치하다": "LOCATED_IN",
            "소속하다": "BELONGS_TO"
        }
        return mapping.get(verb_lemma)
    
    def _extract_relations_by_patterns(self, text: str, entities: List[Entity]) -> List[Relation]:
        """패턴 기반 관계 추출 (기본적인 패턴만)."""
        relations = []
        name_to_entity = {ent.name: ent for ent in entities}
        
        # 기본 패턴들
        patterns = [
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?경쟁", "COMPETES_WITH", True),
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?협력", "COLLABORATES_WITH", True),
            (r"(\w+)(?:가|이)\s+(\w+)(?:를|을)\s+인수(?:했|함)", "ACQUIRED", False),
            (r"(\w+)(?:는|이)\s+(\w+)(?:의)?\s+자회사", "SUBSIDIARY_OF", False),
        ]
        
        for pattern, predicate, bidirectional in patterns:
            for match in re.finditer(pattern, text):
                source_name, target_name = match.group(1), match.group(2)
                
                source_entity = name_to_entity.get(source_name)
                target_entity = name_to_entity.get(target_name)
                
                if source_entity and target_entity:
                    relations.append(Relation(
                        source=source_entity.id,
                        target=target_entity.id,
                        predicate=predicate,
                        confidence=0.8
                    ))
                    
                    if bidirectional:
                        relations.append(Relation(
                            source=target_entity.id,
                            target=source_entity.id,
                            predicate=predicate,
                            confidence=0.8
                        ))
        
        return relations
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """엔티티 중복을 제거합니다."""
        seen_names = set()
        unique_entities = []
        
        for entity in entities:
            if entity.name not in seen_names:
                seen_names.add(entity.name)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """관계 중복을 제거합니다."""
        seen_keys = set()
        unique_relations = []
        
        for relation in relations:
            key = (relation.source, relation.target, relation.predicate)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_relations.append(relation)
        
        return unique_relations

    # ---------------------------------------------------------------------
    # 레거시 호환성 메서드들 (기존 테스트 호환성)
    # ---------------------------------------------------------------------
    
    def _extract_legacy_mode(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """기존 테스트 호환성을 위한 레거시 추출 방식"""
        # 1) 간단한 정규식 기반 엔티티 후보 추출
        entities: List[Entity] = []
        seen_names: set[str] = set()
        token_pattern = re.compile(r"[A-Za-z가-힣0-9]{2,}")

        for doc in input_data.docs:
            for match in token_pattern.findall(doc):
                normalized = match.strip()
                if normalized in seen_names:
                    continue
                seen_names.add(normalized)
                entity = Entity(
                    id=str(uuid.uuid4()),
                    type="CONCEPT",
                    name=normalized,
                    confidence=1.0
                )
                entities.append(entity)

        # min_confidence 기준 적용
        entities = [e for e in entities if e.confidence >= input_data.min_confidence]

        # 2) 관계 패턴 정규식 기반 추출
        relations: List[Relation] = self._extract_relations_by_patterns_legacy(input_data.docs, entities)

        # 3) 선택적 LLM 기반 보강 추출
        llm_entities, llm_relations = self._maybe_call_llm(input_data)

        if llm_entities or llm_relations:
            # 엔티티 병합
            name_to_entity = {e.name: e for e in entities}
            for ent in llm_entities:
                if ent.name not in name_to_entity:
                    name_to_entity[ent.name] = ent
            entities = list(name_to_entity.values())

            # 관계 병합
            sig = set()
            merged: List[Relation] = []
            for r in [*relations, *llm_relations]:
                key = (r.source, r.target, r.predicate)
                if key in sig:
                    continue
                sig.add(key)
                merged.append(r)
            relations = merged
            
        return entities, relations

    def _extract_relations_by_patterns_legacy(self, docs: List[str], entities: List[Entity]) -> List[Relation]:
        """한글 자연어 패턴을 이용해 관계를 추출합니다. (레거시 호환)"""
        relations: List[Relation] = []

        # 엔티티 조회 맵
        name_to_id: Dict[str, str] = {e.name: e.id for e in entities}

        def get_or_create_entity(name: str) -> str:
            if name in name_to_id:
                return name_to_id[name]
            # 없으면 생성하여 연결 (기본 CONCEPT)
            new = Entity(id=str(uuid.uuid4()), type="CONCEPT", name=name, confidence=0.9)
            entities.append(new)
            name_to_id[name] = new.id
            return new.id

        def is_organization(name: str, context: str) -> bool:
            """간단 휴리스틱으로 조직/회사 여부 판단."""
            org_suffixes = [
                "Inc", "Corp", "Corporation", "Ltd", "LLC", "GmbH", "AG", "SAS", "PLC", "Holdings",
                "Co.", "Company", "Limited", "Pte", "BV", "S.p.A", "Srl"
            ]
            org_kr_keywords = [
                "회사", "기업", "기관", "그룹", "재단", "은행", "대학", "연구소", "공사", "주식회사"
            ]

            # 영문 접미 매칭
            for suf in org_suffixes:
                if name.endswith(suf) or name.endswith(f" {suf}"):
                    return True

            # 한글 맥락 내 키워드 공존
            window = 20
            idx = context.find(name)
            if idx != -1:
                start = max(0, idx - window)
                end = min(len(context), idx + len(name) + window)
                around = context[start:end]
                if any(kw in around for kw in org_kr_keywords):
                    return True

            # 이름 자체에 기업 키워드 포함
            if any(kw in name for kw in org_kr_keywords):
                return True

            return False

        # 간단한 이름 패턴 (한글/영문/숫자 2자 이상)
        name = r"([A-Za-z가-힣0-9]{2,})"

        compiled_patterns: List[Tuple[re.Pattern, str, str]] = [
            # 경쟁/협력 (양방향)
            (re.compile(fr"{name}와 {name}는 경쟁 관계"), "COMPETES_WITH", "bidir"),
            (re.compile(fr"{name}와 {name}은 경쟁 관계"), "COMPETES_WITH", "bidir"),
            (re.compile(fr"{name}와 {name}는 협력 관계"), "COLLABORATES_WITH", "bidir"),
            (re.compile(fr"{name}와 {name}은 협력 관계"), "COLLABORATES_WITH", "bidir"),

            # 인수 (단방향 A→B)
            (re.compile(fr"{name}가 {name}를 인수(하였다|했다)"), "ACQUIRED", "fwd"),
            (re.compile(fr"{name}가 {name}을 인수(하였다|했다)"), "ACQUIRED", "fwd"),

            # 자회사 (단방향 A→B)
            (re.compile(fr"{name}는 {name}의 자회사"), "SUBSIDIARY_OF", "fwd"),
            (re.compile(fr"{name}의 자회사인 {name}"), "SUBSIDIARY_OF", "rev")
        ]

        for doc in docs:
            for pattern, predicate, direction in compiled_patterns:
                for m in pattern.finditer(doc):
                    g1, g2 = m.group(1), m.group(2)
                    if direction == "bidir":
                        a_id = get_or_create_entity(g1)
                        b_id = get_or_create_entity(g2)
                        relations.append(Relation(source=a_id, target=b_id, predicate=predicate, confidence=0.9))
                        relations.append(Relation(source=b_id, target=a_id, predicate=predicate, confidence=0.9))
                    elif direction == "fwd":
                        if predicate in ("ACQUIRED", "SUBSIDIARY_OF") and not (is_organization(g1, doc) and is_organization(g2, doc)):
                            continue
                        a_id = get_or_create_entity(g1)
                        b_id = get_or_create_entity(g2)
                        relations.append(Relation(source=a_id, target=b_id, predicate=predicate, confidence=0.9))
                    elif direction == "rev":
                        if predicate in ("ACQUIRED", "SUBSIDIARY_OF") and not (is_organization(g1, doc) and is_organization(g2, doc)):
                            continue
                        b_id = get_or_create_entity(g1)
                        a_id = get_or_create_entity(g2)
                        relations.append(Relation(source=a_id, target=b_id, predicate=predicate, confidence=0.9))

        # 중복 제거
        sig = set()
        unique: List[Relation] = []
        for r in relations:
            key = (r.source, r.target, r.predicate)
            if key in sig:
                continue
            sig.add(key)
            unique.append(r)
        return unique

    def _maybe_call_llm(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """환경변수가 준비된 경우 Azure GPT-4o로 보강 추출을 시도합니다."""
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not (api_key and endpoint and deployment):
            return [], []

        try:
            from openai import AzureOpenAI
        except Exception as e:
            self._log_structured("llm_dependency_missing", error=str(e))
            return [], []

        try:
            client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)

            joined = "\n".join(input_data.docs)
            if len(joined) > 6000:
                joined = joined[:6000] + "\n..."

            system_prompt = (
                "다음 문서들에서 엔티티(이름, 타입)와 관계(출발, 도착, 프레디케이트)를 JSON으로 추출하세요.\n"
                "타입은 PERSON, ORGANIZATION, LOCATION, CONCEPT 중에서 선택하고, 관계 프레디케이트는\n"
                "COMPETES_WITH, COLLABORATES_WITH, ACQUIRED, SUBSIDIARY_OF 등을 사용하세요.\n"
                "출력은 아래 스키마를 따르세요: {\"entities\":[{\"name\":str,\"type\":str}],\"relations\":[{\"source\":str,\"target\":str,\"predicate\":str}]}"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"문서들:\n{joined}"},
            ]

            resp = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=0.2,
            )

            content = resp.choices[0].message.content if resp and resp.choices else ""
            data: Dict[str, Any] = {}
            try:
                content_str = content.strip()
                if content_str.startswith("```"):
                    content_str = re.sub(r"^```(json)?", "", content_str).strip()
                    content_str = re.sub(r"```$", "", content_str).strip()
                data = json.loads(content_str)
            except Exception:
                self._log_structured("llm_parse_failed", raw_preview=content[:200])
                return [], []

            llm_entities: List[Entity] = []
            llm_relations: List[Relation] = []

            name_to_id: Dict[str, str] = {}
            for ent in data.get("entities", []) or []:
                name = str(ent.get("name", "")).strip()
                etype = str(ent.get("type", "CONCEPT")).strip().upper() or "CONCEPT"
                if not name:
                    continue
                eid = str(uuid.uuid4())
                name_to_id[name] = eid
                llm_entities.append(Entity(id=eid, type=etype, name=name, confidence=0.8))

            def resolve(name: str) -> Optional[str]:
                name = (name or "").strip()
                return name_to_id.get(name)

            for rel in data.get("relations", []) or []:
                src = resolve(rel.get("source"))
                tgt = resolve(rel.get("target"))
                pred = str(rel.get("predicate", "")).strip().upper()
                if not (src and tgt and pred):
                    continue
                llm_relations.append(Relation(source=src, target=tgt, predicate=pred, confidence=0.7))

            return llm_entities, llm_relations

        except Exception as e:
            self._log_structured("llm_call_failed", error=str(e))
            return [], []
    
    def health_check(self) -> Dict[str, Any]:
        """에이전트 상태 확인"""
        start_time = datetime.now()
        
        try:
            health_info = {
                "status": "healthy",
                "agent_type": "extractor",
                "timestamp": datetime.now().isoformat(),
                "health_check_time": (datetime.now() - start_time).total_seconds(),
                "config": {
                    "extraction_modes": ["comprehensive", "fast"],
                    "supported_entity_types": ["PERSON", "ORGANIZATION", "LOCATION", "CONCEPT", "EVENT"],
                    "supported_languages": ["ko", "en", "ja", "zh"]
                }
            }
            
            self._log_structured(
                "health_check_completed",
                status="healthy",
                health_check_time=health_info["health_check_time"]
            )
            
            return health_info
            
        except Exception as e:
            health_info = {
                "status": "unhealthy",
                "agent_type": "extractor",
                "timestamp": datetime.now().isoformat(),
                "health_check_time": (datetime.now() - start_time).total_seconds(),
                "error": str(e)
            }
            
            self._log_structured(
                "health_check_failed",
                error=str(e),
                health_check_time=health_info["health_check_time"]
            )
            
            return health_info 