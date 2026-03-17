# 股票智能分析系统架构图

```mermaid
flowchart TD
    subgraph 用户层
        CLI[CLI / Shell]
        Web[Web UI]
        Bot[Bot 命令]
    end

    subgraph 核心调度层_main.py
        Start(定时/手动触发)
        Check{交易日检查?}
        Config[加载配置]
        Dispatch[调度 Pipeline]
    end

    subgraph 业务核心层_src_core_pipeline
        Pool[ThreadPoolExecutor]
        subgraph 单股分析循环
            Fetch[获取行情数据]
            Search[搜索舆情]
            Analyze[AI 生成报告]
            Save[存入数据库]
            Notify[发送通知]
        end
    end

    subgraph 数据供给层_data_provider
        AK[AkShare]
        TS[Tushare]
        BS[Baostock]
        YF[YFinance]
        Manager[DataFetcherManager]
    end

    subgraph AI_LLM层
        LiteLLM[LiteLLM 适配器]
        subgraph 模型
            Gemini
            OpenAI
            Claude
            DeepSeek
        end
    end

    subgraph 通知层
        WeChat[企业微信]
        Feishu[飞书]
        Telegram
        Email[邮件]
    end

    subgraph API层_api
        FastAPI[FastAPI Server]
        DB[(SQLite)]
    end

    %% 流程连接
    CLI --> Start
    Web --> Start
    Bot --> Start

    Start --> Config
    Config --> Check
    Check -- 是 --> Dispatch
    Check -- 否 --> Stop(跳过执行)

    Dispatch --> Pool

    Pool -- 并发分析 --> Fetch
    Fetch --> Manager
    Manager --> AK
    Manager --> TS
    Manager --> BS
    Manager --> YF

    Fetch --> Search
    Search --> Analyze
    Analyze --> LiteLLM
    LiteLLM --> Gemini
    LiteLLM --> OpenAI
    LiteLLM --> Claude
    LiteLLM --> DeepSeek

    Analyze --> Save
    Save --> DB

    Analyze --> Notify
    Notify --> WeChat
    Notify --> Feishu
    Notify --> Telegram
    Notify --> Email

    Web --> FastAPI
    FastAPI <--> DB
```

### 核心模块职责说明

1.  **入口 (`main.py`)**: 处理命令行参数、交易日判断、定时任务调度。
2.  **流水线 (`pipeline.py`)**: 线程池并发执行个股分析，协调数据获取、分析、通知。
3.  **数据供给 (`data_provider/`)**: 适配器模式，统一不同数据源（AK/TS/BS）的接口。
4.  **AI 分析 (`analyzer.py`)**: 使用 LiteLLM 调用大模型，生成结构化报告。
5.  **通知 (`notification.py`)**: 支持多渠道推送（企微/飞书/Telegram/邮件）。
6.  **API (`api/`)**: FastAPI 服务，提供 Web 管理界面和接口。

