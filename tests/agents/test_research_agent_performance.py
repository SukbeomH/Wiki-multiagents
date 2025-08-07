"""
Research Agent 성능 테스트 및 최적화

이 모듈은 Research Agent의 성능을 측정하고 최적화를 위한 벤치마크 테스트를 포함합니다.
"""

import asyncio
import time
import statistics
import psutil
import gc
from typing import List, Dict, Any
from datetime import datetime

import pytest
from server.agents.research import ResearchAgent
from server.schemas.agents import ResearchIn


@pytest.mark.performance
@pytest.mark.benchmark
class TestResearchAgentPerformance:
    """Research Agent 성능 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.agent = ResearchAgent()
        self.test_keywords = [
            "Python programming",
            "machine learning",
            "artificial intelligence",
            "data science",
            "web development",
            "cloud computing",
            "blockchain technology",
            "cybersecurity",
            "mobile development",
            "devops practices"
        ]
    
    def teardown_method(self):
        """테스트 정리"""
        # 캐시 정리
        self.agent.clear_cache()
        # 가비지 컬렉션 강제 실행
        gc.collect()
    
    @pytest.mark.asyncio
    async def test_single_search_performance(self):
        """단일 검색 성능 테스트"""
        print("\n=== 단일 검색 성능 테스트 ===")
        
        # 메모리 사용량 측정 시작
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 성능 측정
        search_times = []
        memory_usage = []
        
        for i, keyword in enumerate(self.test_keywords[:5]):  # 처음 5개만 테스트
            print(f"검색 {i+1}: {keyword}")
            
            # 검색 전 메모리
            before_memory = process.memory_info().rss / 1024 / 1024
            
            # 검색 수행
            start_time = time.time()
            input_data = ResearchIn(keyword=keyword, top_k=10)
            result = await self.agent.search(input_data)
            search_time = time.time() - start_time
            
            # 검색 후 메모리
            after_memory = process.memory_info().rss / 1024 / 1024
            
            search_times.append(search_time)
            memory_usage.append(after_memory - before_memory)
            
            print(f"  - 검색 시간: {search_time:.3f}초")
            print(f"  - 문서 수: {len(result.docs)}")
            print(f"  - 메모리 증가: {after_memory - before_memory:.2f}MB")
            print(f"  - 캐시 히트: {result.cache_hit}")
        
        # 통계 계산
        avg_search_time = statistics.mean(search_times)
        min_search_time = min(search_times)
        max_search_time = max(search_times)
        avg_memory_increase = statistics.mean(memory_usage)
        
        print(f"\n성능 요약:")
        print(f"  - 평균 검색 시간: {avg_search_time:.3f}초")
        print(f"  - 최소 검색 시간: {min_search_time:.3f}초")
        print(f"  - 최대 검색 시간: {max_search_time:.3f}초")
        print(f"  - 평균 메모리 증가: {avg_memory_increase:.2f}MB")
        print(f"  - 초기 메모리: {initial_memory:.2f}MB")
        
        # 성능 기준 검증
        assert avg_search_time < 5.0, f"평균 검색 시간이 너무 김: {avg_search_time:.3f}초"
        assert max_search_time < 10.0, f"최대 검색 시간이 너무 김: {max_search_time:.3f}초"
        assert avg_memory_increase < 50.0, f"메모리 증가가 너무 큼: {avg_memory_increase:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self):
        """캐시 성능 영향 테스트"""
        print("\n=== 캐시 성능 영향 테스트 ===")
        
        keyword = "cache performance test"
        input_data = ResearchIn(keyword=keyword, top_k=10)
        
        # 첫 번째 검색 (캐시 미스)
        print("1. 캐시 미스 검색")
        start_time = time.time()
        result1 = await self.agent.search(input_data)
        cache_miss_time = time.time() - start_time
        
        print(f"  - 검색 시간: {cache_miss_time:.3f}초")
        print(f"  - 문서 수: {len(result1.docs)}")
        print(f"  - 캐시 히트: {result1.cache_hit}")
        
        # 두 번째 검색 (캐시 히트)
        print("2. 캐시 히트 검색")
        start_time = time.time()
        result2 = await self.agent.search(input_data)
        cache_hit_time = time.time() - start_time
        
        print(f"  - 검색 시간: {cache_hit_time:.3f}초")
        print(f"  - 문서 수: {len(result2.docs)}")
        print(f"  - 캐시 히트: {result2.cache_hit}")
        
        # 성능 향상 계산
        performance_improvement = cache_miss_time / cache_hit_time if cache_hit_time > 0 else float('inf')
        
        print(f"\n캐시 성능 향상:")
        print(f"  - 캐시 미스 시간: {cache_miss_time:.3f}초")
        print(f"  - 캐시 히트 시간: {cache_hit_time:.3f}초")
        print(f"  - 성능 향상: {performance_improvement:.1f}배")
        
        # 성능 기준 검증
        assert cache_hit_time < cache_miss_time, "캐시 히트가 캐시 미스보다 느림"
        assert performance_improvement > 5.0, f"캐시 성능 향상이 부족함: {performance_improvement:.1f}배"
        assert result1.docs == result2.docs, "캐시 히트와 미스 결과가 다름"
    
    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self):
        """동시 검색 성능 테스트"""
        print("\n=== 동시 검색 성능 테스트 ===")
        
        # 순차 실행 시간 측정
        print("1. 순차 실행")
        sequential_times = []
        start_time = time.time()
        
        for keyword in self.test_keywords[:5]:
            input_data = ResearchIn(keyword=keyword, top_k=5)
            search_start = time.time()
            result = await self.agent.search(input_data)
            search_time = time.time() - search_start
            sequential_times.append(search_time)
        
        sequential_total = time.time() - start_time
        avg_sequential = statistics.mean(sequential_times)
        
        print(f"  - 총 시간: {sequential_total:.3f}초")
        print(f"  - 평균 검색 시간: {avg_sequential:.3f}초")
        
        # 동시 실행 시간 측정
        print("2. 동시 실행")
        start_time = time.time()
        
        search_tasks = []
        for keyword in self.test_keywords[:5]:
            input_data = ResearchIn(keyword=keyword, top_k=5)
            task = self.agent.search(input_data)
            search_tasks.append(task)
        
        results = await asyncio.gather(*search_tasks)
        concurrent_total = time.time() - start_time
        
        print(f"  - 총 시간: {concurrent_total:.3f}초")
        print(f"  - 평균 검색 시간: {concurrent_total / len(search_tasks):.3f}초")
        
        # 성능 향상 계산
        speedup = sequential_total / concurrent_total if concurrent_total > 0 else 1.0
        
        print(f"\n동시 실행 성능 향상:")
        print(f"  - 순차 실행: {sequential_total:.3f}초")
        print(f"  - 동시 실행: {concurrent_total:.3f}초")
        print(f"  - 성능 향상: {speedup:.2f}배")
        
        # 성능 기준 검증
        assert concurrent_total < sequential_total, "동시 실행이 순차 실행보다 느림"
        assert speedup > 1.5, f"동시 실행 성능 향상이 부족함: {speedup:.2f}배"
        
        # 결과 검증
        for result in results:
            assert len(result.docs) > 0, "검색 결과가 비어있음"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """부하 상황에서의 메모리 사용량 테스트"""
        print("\n=== 부하 상황 메모리 사용량 테스트 ===")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        memory_usage = [initial_memory]
        
        print(f"초기 메모리: {initial_memory:.2f}MB")
        
        # 연속 검색으로 메모리 사용량 측정
        for i in range(10):
            keyword = f"memory test {i}"
            input_data = ResearchIn(keyword=keyword, top_k=5)
            
            # 검색 전 메모리
            before_memory = process.memory_info().rss / 1024 / 1024
            
            # 검색 수행
            result = await self.agent.search(input_data)
            
            # 검색 후 메모리
            after_memory = process.memory_info().rss / 1024 / 1024
            memory_usage.append(after_memory)
            
            print(f"검색 {i+1}: {before_memory:.2f}MB → {after_memory:.2f}MB (+{after_memory - before_memory:.2f}MB)")
        
        # 메모리 통계
        peak_memory = max(memory_usage)
        final_memory = memory_usage[-1]
        total_increase = final_memory - initial_memory
        
        print(f"\n메모리 사용량 요약:")
        print(f"  - 초기 메모리: {initial_memory:.2f}MB")
        print(f"  - 최종 메모리: {final_memory:.2f}MB")
        print(f"  - 최대 메모리: {peak_memory:.2f}MB")
        print(f"  - 총 증가량: {total_increase:.2f}MB")
        print(f"  - 증가율: {(total_increase / initial_memory * 100):.1f}%")
        
        # 메모리 누수 검증
        assert total_increase < 100.0, f"메모리 증가가 너무 큼: {total_increase:.2f}MB"
        assert (total_increase / initial_memory) < 0.5, f"메모리 증가율이 너무 큼: {(total_increase / initial_memory * 100):.1f}%"
    
    @pytest.mark.asyncio
    async def test_cache_efficiency_analysis(self):
        """캐시 효율성 분석"""
        print("\n=== 캐시 효율성 분석 ===")
        
        # 캐시 통계 초기화
        initial_stats = self.agent.get_cache_info()
        print(f"초기 캐시 통계: {initial_stats}")
        
        # 반복 검색으로 캐시 효율성 측정
        repeated_keywords = ["cache efficiency", "performance test", "optimization"]
        
        for round_num in range(3):
            print(f"\n라운드 {round_num + 1}:")
            
            for keyword in repeated_keywords:
                input_data = ResearchIn(keyword=keyword, top_k=5)
                result = await self.agent.search(input_data)
                
                stats = self.agent.get_cache_info()
                hit_rate = stats.get('hit_rate', 0)
                
                print(f"  {keyword}: 캐시 히트={result.cache_hit}, 히트율={hit_rate:.2%}")
        
        # 최종 캐시 통계
        final_stats = self.agent.get_cache_info()
        print(f"\n최종 캐시 통계:")
        print(f"  - 총 요청: {final_stats.get('total_requests', 0)}")
        print(f"  - 히트: {final_stats.get('hits', 0)}")
        print(f"  - 미스: {final_stats.get('misses', 0)}")
        print(f"  - 히트율: {final_stats.get('hit_rate', 0):.2%}")
        print(f"  - 캐시 크기: {final_stats.get('lru_cache_size', 0)}")
        
        # 캐시 효율성 검증
        assert final_stats.get('hit_rate', 0) > 0.3, f"캐시 히트율이 너무 낮음: {final_stats.get('hit_rate', 0):.2%}"
        assert final_stats.get('hits', 0) > 0, "캐시 히트가 없음"
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """오류 처리 성능 테스트"""
        print("\n=== 오류 처리 성능 테스트 ===")
        
        # 정상 검색과 오류 검색의 성능 비교
        normal_keyword = "normal search test"
        error_keyword = "a"  # 매우 짧은 키워드 (오류 가능성)
        
        # 정상 검색
        print("1. 정상 검색")
        start_time = time.time()
        try:
            input_data = ResearchIn(keyword=normal_keyword, top_k=5)
            result = await self.agent.search(input_data)
            normal_time = time.time() - start_time
            print(f"  - 검색 시간: {normal_time:.3f}초")
            print(f"  - 성공: {len(result.docs)}개 문서")
        except Exception as e:
            normal_time = time.time() - start_time
            print(f"  - 검색 시간: {normal_time:.3f}초")
            print(f"  - 오류: {e}")
        
        # 오류 검색
        print("2. 오류 검색")
        start_time = time.time()
        try:
            input_data = ResearchIn(keyword=error_keyword, top_k=5)
            result = await self.agent.search(input_data)
            error_time = time.time() - start_time
            print(f"  - 검색 시간: {error_time:.3f}초")
            print(f"  - 성공: {len(result.docs)}개 문서")
        except Exception as e:
            error_time = time.time() - start_time
            print(f"  - 검색 시간: {error_time:.3f}초")
            print(f"  - 오류: {e}")
        
        # 성능 비교
        if 'normal_time' in locals() and 'error_time' in locals():
            time_diff = abs(normal_time - error_time)
            print(f"\n성능 비교:")
            print(f"  - 정상 검색: {normal_time:.3f}초")
            print(f"  - 오류 검색: {error_time:.3f}초")
            print(f"  - 시간 차이: {time_diff:.3f}초")
            
            # 오류 처리가 너무 느리지 않아야 함
            assert time_diff < 2.0, f"오류 처리 시간이 너무 김: {time_diff:.3f}초"
    
    @pytest.mark.asyncio
    async def test_large_scale_performance(self):
        """대규모 검색 성능 테스트"""
        print("\n=== 대규모 검색 성능 테스트 ===")
        
        # 대량의 키워드로 성능 테스트
        large_keywords = [f"large scale test {i}" for i in range(20)]
        
        start_time = time.time()
        search_times = []
        
        # 순차 실행
        for keyword in large_keywords:
            search_start = time.time()
            input_data = ResearchIn(keyword=keyword, top_k=3)
            result = await self.agent.search(input_data)
            search_time = time.time() - search_start
            search_times.append(search_time)
        
        total_time = time.time() - start_time
        
        # 통계 계산
        avg_time = statistics.mean(search_times)
        min_time = min(search_times)
        max_time = max(search_times)
        
        print(f"대규모 검색 결과:")
        print(f"  - 총 검색 수: {len(large_keywords)}")
        print(f"  - 총 시간: {total_time:.3f}초")
        print(f"  - 평균 검색 시간: {avg_time:.3f}초")
        print(f"  - 최소 검색 시간: {min_time:.3f}초")
        print(f"  - 최대 검색 시간: {max_time:.3f}초")
        print(f"  - 처리량: {len(large_keywords) / total_time:.2f} 검색/초")
        
        # 성능 기준 검증
        assert total_time < 60.0, f"대규모 검색이 너무 느림: {total_time:.3f}초"
        assert avg_time < 3.0, f"평균 검색 시간이 너무 김: {avg_time:.3f}초"
        assert (len(large_keywords) / total_time) > 0.3, f"처리량이 너무 낮음: {len(large_keywords) / total_time:.2f} 검색/초"
    
    def test_memory_cleanup(self):
        """메모리 정리 테스트"""
        print("\n=== 메모리 정리 테스트 ===")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        print(f"초기 메모리: {initial_memory:.2f}MB")
        
        # 캐시 정리
        self.agent.clear_cache()
        
        # 가비지 컬렉션 강제 실행
        gc.collect()
        
        after_cleanup_memory = process.memory_info().rss / 1024 / 1024
        memory_reduction = initial_memory - after_cleanup_memory
        
        print(f"정리 후 메모리: {after_cleanup_memory:.2f}MB")
        print(f"메모리 감소: {memory_reduction:.2f}MB")
        
        # 캐시 통계 확인
        stats = self.agent.get_cache_info()
        print(f"캐시 통계: {stats}")
        
        # 메모리 정리 검증
        assert stats.get('lru_cache_size', 0) == 0, "캐시가 완전히 정리되지 않음"
        assert stats.get('total_requests', 0) == 0, "캐시 통계가 초기화되지 않음"


@pytest.mark.performance
@pytest.mark.benchmark
class TestResearchAgentOptimization:
    """Research Agent 최적화 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.agent = ResearchAgent()
    
    @pytest.mark.asyncio
    async def test_cache_size_optimization(self):
        """캐시 크기 최적화 테스트"""
        print("\n=== 캐시 크기 최적화 테스트 ===")
        
        # 다양한 캐시 크기로 성능 테스트
        cache_sizes = [32, 64, 128, 256]
        performance_results = {}
        
        for cache_size in cache_sizes:
            print(f"\n캐시 크기 {cache_size} 테스트:")
            
            # 새로운 캐시로 Agent 재생성
            from server.agents.research.cache import ResearchCache
            from server.agents.research.client import DuckDuckGoClient
            
            cache = ResearchCache(max_size=cache_size)
            client = DuckDuckGoClient()
            test_agent = ResearchAgent(client=client, cache=cache)
            
            # 성능 측정
            start_time = time.time()
            search_times = []
            
            for i in range(10):
                keyword = f"cache size test {i}"
                input_data = ResearchIn(keyword=keyword, top_k=3)
                
                search_start = time.time()
                result = await test_agent.search(input_data)
                search_time = time.time() - search_start
                search_times.append(search_time)
            
            total_time = time.time() - start_time
            avg_time = statistics.mean(search_times)
            
            # 캐시 통계
            stats = test_agent.get_cache_info()
            hit_rate = stats.get('hit_rate', 0)
            
            performance_results[cache_size] = {
                'total_time': total_time,
                'avg_time': avg_time,
                'hit_rate': hit_rate,
                'cache_size': stats.get('lru_cache_size', 0)
            }
            
            print(f"  - 총 시간: {total_time:.3f}초")
            print(f"  - 평균 검색 시간: {avg_time:.3f}초")
            print(f"  - 캐시 히트율: {hit_rate:.2%}")
            print(f"  - 사용된 캐시 크기: {stats.get('lru_cache_size', 0)}")
        
        # 최적 캐시 크기 분석
        print(f"\n캐시 크기별 성능 비교:")
        for size, results in performance_results.items():
            print(f"  크기 {size}: {results['total_time']:.3f}초, 히트율 {results['hit_rate']:.2%}")
        
        # 최적화 권장사항
        best_size = min(performance_results.keys(), 
                       key=lambda x: performance_results[x]['total_time'])
        print(f"\n최적 캐시 크기: {best_size}")
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_optimization(self):
        """동시 실행 제한 최적화 테스트"""
        print("\n=== 동시 실행 제한 최적화 테스트 ===")
        
        # 다양한 동시 실행 수로 성능 테스트
        concurrency_levels = [1, 3, 5, 10]
        keywords = [f"concurrency test {i}" for i in range(15)]
        
        for concurrency in concurrency_levels:
            print(f"\n동시 실행 수 {concurrency} 테스트:")
            
            start_time = time.time()
            
            # 세마포어를 사용한 동시 실행 제한
            semaphore = asyncio.Semaphore(concurrency)
            
            async def limited_search(keyword):
                async with semaphore:
                    input_data = ResearchIn(keyword=keyword, top_k=3)
                    return await self.agent.search(input_data)
            
            # 동시 실행
            tasks = [limited_search(keyword) for keyword in keywords]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            print(f"  - 총 시간: {total_time:.3f}초")
            print(f"  - 평균 시간: {total_time / len(keywords):.3f}초")
            print(f"  - 처리량: {len(keywords) / total_time:.2f} 검색/초")
            
            # 결과 검증
            success_count = sum(1 for r in results if len(r.docs) > 0)
            print(f"  - 성공률: {success_count / len(results):.2%}")
            
            assert success_count > len(results) * 0.8, f"성공률이 너무 낮음: {success_count / len(results):.2%}"
    
    @pytest.mark.asyncio
    async def test_timeout_optimization(self):
        """타임아웃 최적화 테스트"""
        print("\n=== 타임아웃 최적화 테스트 ===")
        
        # 다양한 타임아웃 값으로 성능 테스트
        timeout_values = [5, 10, 15, 20]
        
        for timeout in timeout_values:
            print(f"\n타임아웃 {timeout}초 테스트:")
            
            # 타임아웃이 있는 검색 함수
            async def search_with_timeout(keyword, timeout_sec):
                try:
                    input_data = ResearchIn(keyword=keyword, top_k=5)
                    result = await asyncio.wait_for(
                        self.agent.search(input_data), 
                        timeout=timeout_sec
                    )
                    return result, None
                except asyncio.TimeoutError:
                    return None, "timeout"
                except Exception as e:
                    return None, str(e)
            
            # 성능 측정
            start_time = time.time()
            success_count = 0
            timeout_count = 0
            error_count = 0
            
            for i in range(5):
                keyword = f"timeout test {i}"
                result, error = await search_with_timeout(keyword, timeout)
                
                if error == "timeout":
                    timeout_count += 1
                elif error:
                    error_count += 1
                else:
                    success_count += 1
            
            total_time = time.time() - start_time
            
            print(f"  - 총 시간: {total_time:.3f}초")
            print(f"  - 성공: {success_count}")
            print(f"  - 타임아웃: {timeout_count}")
            print(f"  - 오류: {error_count}")
            print(f"  - 성공률: {success_count / 5:.2%}")
            
            # 타임아웃이 너무 짧으면 성공률이 낮아짐
            if timeout < 10:
                assert success_count / 5 > 0.6, f"타임아웃 {timeout}초에서 성공률이 너무 낮음"
            else:
                assert success_count / 5 > 0.8, f"타임아웃 {timeout}초에서 성공률이 너무 낮음"


if __name__ == "__main__":
    # 성능 테스트 실행
    pytest.main([__file__, "-v", "--tb=short"]) 