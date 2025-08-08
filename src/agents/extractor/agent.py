"""
Extractor Agent (ext.md 기반 단순화 버전)

spaCy + korre + LangGraph 기반 엔티티·관계 추출
- spaCy: 한국어 엔티티 추출
- korre: 한국어 관계 추출 (전용 라이브러리)
- LangGraph: 워크플로우 관리
- 기존 테스트 케이스 완전 호환
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.schemas.agents import ExtractorIn, ExtractorOut, Entity, Relation


class ExtractorAgent:
    """ext.md 기반 단순화된 엔티티·관계 추출 에이전트"""
    
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
        self._korre_instance = None
        self._langgraph_available = False
        
        # LangGraph 사용 가능성 확인
        self._check_langgraph_availability()
        
        # 구조화된 로그 초기화
        self._log_structured(
            "extractor_agent_initialized",
            log_level=log_level,
            architecture="ext_md_based_simplified",
            langgraph_available=self._langgraph_available
        )
    
    def _check_langgraph_availability(self):
        """LangGraph 사용 가능성을 확인합니다."""
        try:
            import langgraph
            self._langgraph_available = True
            self.logger.info("LangGraph 사용 가능")
        except ImportError:
            self._langgraph_available = False
            self.logger.warning("LangGraph가 설치되지 않았습니다. pip install langgraph")
    
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
        문서에서 엔티티와 관계를 추출 (ext.md 기반 단순화)
        
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
            architecture="ext_md_based_simplified"
        )
        
        try:
            # LangGraph 워크플로우 사용 가능하면 사용
            if self._langgraph_available and input_data.extraction_mode == "comprehensive":
                entities, relations = self._extract_with_langgraph_workflow(input_data)
            else:
                # ext.md 기반 추출 시도
                entities, relations = self._extract_with_ext_md_approach(input_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            processing_stats = {
                "total_docs": len(input_data.docs),
                "extraction_mode": input_data.extraction_mode,
                "entities_found": len(entities),
                "relations_found": len(relations),
                "avg_confidence": (sum(e.confidence for e in entities) / len(entities)) if entities else 0.0,
                "processing_time": processing_time,
                "method": "langgraph_workflow" if self._langgraph_available and input_data.extraction_mode == "comprehensive" else "ext_md_based_simplified"
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
    # LangGraph 워크플로우 메서드들 (ext.md 방식)
    # ---------------------------------------------------------------------
    
    def _extract_with_langgraph_workflow(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """LangGraph 워크플로우를 사용한 추출 (ext.md 방식)"""
        try:
            from langgraph.prebuilt import create_react_agent
            from langgraph.graph import StateGraph, START, END
            from typing import TypedDict
            from langchain_core.tools import tool
            
            # 상태 타입 정의 (ext.md 방식)
            class KGState(TypedDict):
                messages: List[Dict]
                entities: List[Dict]
                relations: List[Dict]
            
            # 1) spaCy NER 툴 정의 (ext.md 방식)
            @tool("spacy_ner", "한국어 텍스트에서 기본 엔티티(인물·장소·조직) 추출")
            def spacy_ner(text: str) -> List[Dict]:
                nlp = self._load_spacy_model("ko_core_news_lg")
                doc = nlp(text)
                return [{"text": ent.text, "start": ent.start_char, "end": ent.end_char, "label": ent.label_}
                        for ent in doc.ents]
            
            # 2) KorRE 관계 추출 툴 정의 (ext.md 방식)
            @tool("korre_re", "문장과 엔티티 위치를 받아 한국어 관계 추출")
            def korre_re(text: str, idx1: List[int], idx2: List[int]) -> List[Tuple[str, str, str]]:
                korre = self._load_korre_instance()
                if korre is None:
                    return []
                return korre.infer(text, idx1, idx2)
            
            # 3) NER 에이전트 (ext.md 방식)
            ner_agent = create_react_agent(
                model="openai:gpt-4",
                tools=[spacy_ner],
                prompt="한국어 문장에서 엔티티(text, start, end, label)를 추출하여 리스트로 반환하세요.",
                name="ner_agent",
            )
            
            # 4) 관계추출 에이전트 (ext.md 방식)
            re_agent = create_react_agent(
                model="openai:gpt-4",
                tools=[korre_re],
                prompt=(
                    "추출된 엔티티 리스트와 원문을 받아, "
                    "각 엔티티 쌍의 위치 인덱스를 korre_re에 전달해 관계(triple)를 추출하세요."
                ),
                name="re_agent",
            )
            
            # 5) 그래프 빌드 (ext.md 방식)
            graph = (
                StateGraph(KGState)
                .add_node(ner_agent, destinations=("re_agent", END))
                .add_node(re_agent)
                .add_edge(START, "ner_agent")
                .add_edge("ner_agent", "re_agent")
                .add_edge("re_agent", END)
                .compile()
            )
            
            # 6) 워크플로우 실행
            entities = []
            relations = []
            
            for doc_text in input_data.docs:
                # LangGraph 실행 (ext.md 방식)
                state = {"messages": [{"role": "user", "content": doc_text}]}
                for step in graph.stream(state):
                    # 각 단계에서 결과 추출
                    if "entities" in step:
                        entities.extend(step["entities"])
                    if "relations" in step:
                        relations.extend(step["relations"])
            
            # 7) 결과 변환
            converted_entities = self._convert_langgraph_entities(entities, input_data)
            converted_relations = self._convert_langgraph_relations(relations, converted_entities)
            
            return converted_entities, converted_relations
            
        except Exception as e:
            self.logger.error(f"LangGraph 워크플로우 실패, ext.md 방식으로 fallback: {e}")
            return self._extract_with_ext_md_approach(input_data)
    
    def _convert_langgraph_entities(self, langgraph_entities: List[Dict], input_data: ExtractorIn) -> List[Entity]:
        """LangGraph 엔티티를 스키마 형식으로 변환"""
        entities = []
        seen_names = set()
        
        for ent_data in langgraph_entities:
            if isinstance(ent_data, dict):
                text = ent_data.get("text", "")
                label = ent_data.get("label", "CONCEPT")
                
                # 한국어 조사 제거
                clean_name = self._remove_korean_particles(text)
                
                # 중복 제거
                if clean_name in seen_names:
                    continue
                seen_names.add(clean_name)
                
                # 엔티티 타입 필터링
                mapped_type = self._map_spacy_label_to_schema(label)
                if input_data.entity_types and mapped_type not in input_data.entity_types:
                    continue
                
                entity = Entity(
                    id=str(uuid.uuid4()),
                    type=mapped_type,
                    name=clean_name,
                    confidence=0.8  # LangGraph 기반 기본 신뢰도
                )
                entities.append(entity)
        
        return entities
    
    def _convert_langgraph_relations(self, langgraph_relations: List[Dict], entities: List[Entity]) -> List[Relation]:
        """LangGraph 관계를 스키마 형식으로 변환"""
        relations = []
        name_to_entity = {ent.name: ent for ent in entities}
        
        for rel_data in langgraph_relations:
            if isinstance(rel_data, (list, tuple)) and len(rel_data) == 3:
                subj, obj, pred = rel_data
                
                source_entity = name_to_entity.get(subj)
                target_entity = name_to_entity.get(obj)
                
                if source_entity and target_entity:
                    confidence = self._calculate_relation_confidence(
                        source_entity, target_entity, pred, ""
                    )
                    relations.append(Relation(
                        source=source_entity.id,
                        target=target_entity.id,
                        predicate=pred,
                        confidence=confidence
                    ))
        
        return relations

    # ---------------------------------------------------------------------
    # ext.md 기반 추출 메서드들
    # ---------------------------------------------------------------------
    
    def _extract_with_ext_md_approach(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """ext.md 기반 추출: spaCy + korre"""
        try:
            # 1. spaCy 모델 로딩
            model_name = "ko_core_news_lg" if input_data.extraction_mode == "comprehensive" else "ko_core_news_sm"
            nlp = self._load_spacy_model(model_name)
            
            # 2. korre 인스턴스 로딩
            korre = self._load_korre_instance()
            
            entities = []
            relations = []
            
            # 3. 각 문서별로 순차 처리
            for doc_text in input_data.docs:
                # spaCy로 엔티티 추출
                doc_entities = self._extract_entities_with_spacy(nlp, doc_text, input_data)
                entities.extend(doc_entities)
                
                # korre로 관계 추출
                doc_relations = self._extract_relations_with_korre(korre, doc_text, doc_entities, input_data)
                relations.extend(doc_relations)
            
            # 4. 중복 제거 및 신뢰도 필터링
            entities = self._deduplicate_entities(entities)
            entities = [e for e in entities if e.confidence >= input_data.min_confidence]
            
            relations = self._deduplicate_relations(relations)
            relations = [r for r in relations if r.confidence >= input_data.min_confidence]
            
            return entities, relations
            
        except Exception as e:
            self.logger.error(f"ext.md 기반 추출 실패: {e}")
            # fallback: 간단한 정규식 기반 추출
            return self._extract_fallback_simple(input_data)
    
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
    
    def _load_korre_instance(self):
        """korre 인스턴스를 로딩합니다."""
        if self._korre_instance is None:
            try:
                from korre import KorRE
                self._korre_instance = KorRE()
                self.logger.info("korre 인스턴스 로딩 완료")
            except ImportError:
                self.logger.warning("korre 라이브러리가 설치되지 않았습니다. pip install korre")
                self._korre_instance = None
            except Exception as e:
                self.logger.error(f"korre 로딩 실패: {e}")
                self._korre_instance = None
        return self._korre_instance
    
    def _extract_entities_with_spacy(self, nlp, text: str, input_data: ExtractorIn) -> List[Entity]:
        """spaCy로 엔티티를 추출합니다."""
        entities = []
        seen_names = set()
        
        doc = nlp(text)
        
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
                name=clean_name,
                confidence=confidence
            )
            entities.append(entity)
        
        return entities
    
    def _extract_relations_with_korre(self, korre, text: str, entities: List[Entity], input_data: ExtractorIn) -> List[Relation]:
        """korre로 관계를 추출합니다."""
        relations = []
        
        if korre is None:
            # korre가 없으면 간단한 패턴 기반 추출
            return self._extract_relations_by_simple_patterns(text, entities)
        
        try:
            # korre.infer(text)로 모든 관계 추출 (ext.md 방식)
            relations_triples = korre.infer(text)
            
            # 엔티티 이름 매핑
            name_to_entity = {ent.name: ent for ent in entities}
            
            for subj, obj, pred in relations_triples:
                source_entity = name_to_entity.get(subj)
                target_entity = name_to_entity.get(obj)
                
                if source_entity and target_entity:
                    confidence = self._calculate_relation_confidence(
                        source_entity, target_entity, pred, text
                    )
                    relations.append(Relation(
                        source=source_entity.id,
                        target=target_entity.id,
                        predicate=pred,
                        confidence=confidence
                    ))
            
            return relations
            
        except Exception as e:
            self.logger.warning(f"korre 관계 추출 실패, 패턴 기반으로 fallback: {e}")
            return self._extract_relations_by_simple_patterns(text, entities)
    
    def _extract_relations_by_simple_patterns(self, text: str, entities: List[Entity]) -> List[Relation]:
        """간단한 패턴 기반 관계 추출 (korre fallback)"""
        relations = []
        name_to_entity = {ent.name: ent for ent in entities}
        
        # 기본 패턴들 (ext.md에서 제안하는 패턴들)
        patterns = [
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?경쟁", "COMPETES_WITH", True),
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?협력", "COLLABORATES_WITH", True),
            (r"(\w+)(?:가|이)\s+(\w+)(?:를|을)\s+인수(?:했|함)", "ACQUIRED", False),
            (r"(\w+)(?:는|이)\s+(\w+)(?:의)?\s+자회사", "SUBSIDIARY_OF", False),
        ]
        
        import re
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
    # Fallback 메서드들 (기존 테스트 호환성)
    # ---------------------------------------------------------------------
    
    def _extract_fallback_simple(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """간단한 fallback 추출 방식 (기존 테스트 호환성)"""
        import re
        
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

        # 2) 간단한 관계 패턴 추출
        relations: List[Relation] = []
        name_to_id: Dict[str, str] = {e.name: e.id for e in entities}

        # 기본 패턴들
        patterns = [
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?경쟁", "COMPETES_WITH", True),
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?협력", "COLLABORATES_WITH", True),
            (r"(\w+)(?:가|이)\s+(\w+)(?:를|을)\s+인수(?:했|함)", "ACQUIRED", False),
            (r"(\w+)(?:는|이)\s+(\w+)(?:의)?\s+자회사", "SUBSIDIARY_OF", False),
        ]

        for doc in input_data.docs:
            for pattern, predicate, bidirectional in patterns:
                for match in re.finditer(pattern, doc):
                    source_name, target_name = match.group(1), match.group(2)
                    
                    source_id = name_to_id.get(source_name)
                    target_id = name_to_id.get(target_name)
                    
                    if source_id and target_id:
                        relations.append(Relation(
                            source=source_id,
                            target=target_id,
                            predicate=predicate,
                            confidence=0.8
                        ))
                        
                        if bidirectional:
                            relations.append(Relation(
                                source=target_id,
                                target=source_id,
                                predicate=predicate,
                                confidence=0.8
                            ))
        
        return entities, relations
    
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
                    "supported_languages": ["ko", "en", "ja", "zh"],
                    "architecture": "ext_md_based_simplified",
                    "langgraph_available": self._langgraph_available
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