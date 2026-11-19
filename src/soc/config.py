"""모든 컴포넌트가 함께 쓰는 설정.

- 내 PC: 프로젝트 맨 위의 `.env` 파일에서 읽습니다 (`.env.example`을 복사해서 만듭니다).
- k3s: ConfigMap과 Secret이 같은 이름의 환경변수로 넣어 줍니다. 코드는 바꾸지 않습니다.

LangSmith 추적: `.env`에 LANGSMITH_TRACING=true, LANGSMITH_API_KEY를 넣으면
LangChain/LangGraph가 환경변수를 보고 자동으로 추적을 보냅니다. 그래서 `.env`를 os.environ에도 올립니다.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    ROOT / ".env",
    override=False,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    # 실행 모드 ------------------------------------------------------------
    backend: str = "memory"

    telemetry_tools: str = "mock"
    kb_tools: str = "mock"

    # OpenSearch -----------------------------------------------------------
    opensearch_url: str = "http://localhost:9200"

    index_events: str = "edr-events"
    index_alerts: str = "edr-alerts"
    index_reports: str = "triage-reports"
    index_kb: str = "kb-playbooks"

    # Postgres -------------------------------------------------------------
    postgres_dsn: str = (
        "postgresql://soc:soc@localhost:5432/soc"
    )

    # LLM ------------------------------------------------------------------
    fake_llm: bool = False

    openai_api_key: str = ""

    chat_model: str = "gpt-4o-mini"

    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536

    price_in_per_1m: float = 0.15
    price_out_per_1m: float = 0.60

    # 에이전트 예산 --------------------------------------------------------
    max_tool_rounds: int = 6

    guardrail_on_fail: str = "retry"
    max_guardrail_retries: int = 1

    # 상태 저장 ------------------------------------------------------------
    checkpointer: str = "auto"

    # 워커 -----------------------------------------------------------------
    worker_poll_sec: float = 2.0
    worker_lease_sec: int = 300
    heartbeat_stale_sec: int = 60
    health_port: int = 9100

    # 생성기 ---------------------------------------------------------------
    sim_benign_per_tick: int = 5
    sim_tick_sec: float = 5.0
    sim_attack_every_ticks: int = 24

    # KB -------------------------------------------------------------------
    kb_pdf_dir: str = str(
        ROOT / "data" / "kb" / "pdf"
    )

    # 기본 파싱 전략
    parse_strategy: str = "fast"

    # 표나 다단 레이아웃 때문에 hi_res가 실제로 개선된 문서
    kb_hi_res_files: str = (
        "01_response_policy_tables.pdf,"
        "05_newsletter_two_column.pdf,"
        "09_response_matrix_complex_tables.pdf"
    )

    # 이미지 스캔 PDF는 글자 층이 없어서 OCR이 필요합니다 (D3-6).
    kb_ocr_files: str = "06_false_positive_guide_scanned.pdf"

    # hi_res 좌표를 이용해 컬럼 순서를 다시 잡아야 하는 문서
    kb_two_column_files: str = (
        "05_newsletter_two_column.pdf"
    )

    # 청킹 기본값
    chunk_max_characters: int = 800
    chunk_new_after_n_chars: int = 600

    # 연동 -----------------------------------------------------------------
    dify_api_key: str = "change-me"
    prompt_version: str = "v1"


settings = Settings()