使用AI辅助生成的多租户版本agent模板

- python
- fastapi
- Qdrant
- langchain相关

```text
agent-knowledge-platform/
├── docker-compose.yml              # 服务编排
├── Dockerfile                      # FastAPI 应用镜像
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
├── alembic.ini                     # 数据库迁移配置
├── alembic/                        # 迁移脚本
│   └── versions/
│
├── app/                            # 主应用
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口，lifespan 事件
│   ├── config.py                   # 配置管理 (pydantic-settings)
│   ├── dependencies.py             # FastAPI 依赖注入
│   │
│   ├── api/                        # API 路由层
│   │   ├── __init__.py
│   │   ├── router.py               # 总路由注册
│   │   ├── auth.py                 # POST /auth/register, /auth/login, /auth/refresh
│   │   ├── knowledge.py            # CRUD /knowledge/bases, /knowledge/documents
│   │   ├── chat.py                 # POST /chat/sessions, /chat/messages
│   │   ├── agents.py               # GET /agents, POST /agents/{id}/invoke
│   │   └── admin.py                # 系统管理接口
│   │
│   ├── models/                     # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── user.py                 # User, UserProfile
│   │   ├── knowledge.py            # KnowledgeBase, Document, DocumentChunk
│   │   ├── conversation.py         # Conversation, Message
│   │   └── agent.py                # AgentConfig, ToolConfig
│   │
│   ├── schemas/                    # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── knowledge.py
│   │   ├── chat.py
│   │   └── agent.py
│   │
│   ├── services/                   # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py         # JWT 生成/验证，密码哈希
│   │   ├── knowledge_service.py    # 文档上传 → 切片 → 向量化
│   │   ├── chat_service.py         # 对话管理，消息持久化
│   │   └── agent_service.py        # Agent 生命周期管理
│   │
│   ├── agents/                     # Agent 定义 (LangGraph)
│   │   ├── __init__.py
│   │   ├── registry.py             # Agent 注册表，动态加载
│   │   ├── base.py                 # BaseAgent 抽象基类
│   │   ├── router_agent.py         # 意图识别 + Agent 路由
│   │   ├── code_agent.py           # 代码助手 Agent
│   │   └── trade_agent.py          # 外贸客服 Agent (示例)
│   │
│   ├── tools/                      # 工具定义
│   │   ├── __init__.py
│   │   ├── registry.py             # Tool 注册表
│   │   ├── base.py                 # BaseTool 抽象基类
│   │   ├── knowledge_tool.py       # 知识库检索工具
│   │   ├── code_tool.py            # 代码执行工具
│   │   └── web_search_tool.py      # 网络搜索工具
│   │
│   ├── knowledge/                  # 知识库核心
│   │   ├── __init__.py
│   │   ├── document_loader.py      # 文档加载器 (PDF/TXT/MD/DOCX)
│   │   ├── text_splitter.py        # 文本切片策略
│   │   ├── embeddings.py           # Embedding 模型封装
│   │   ├── vector_store.py         # Qdrant 客户端封装
│   │   └── retriever.py            # RAG 检索器 (混合检索)
│   │
│   ├── llm/                        # LLM 统一接口
│   │   ├── __init__.py
│   │   ├── factory.py              # LLM 工厂，根据配置创建实例
│   │   ├── deepseek.py             # DeepSeek 适配器
│   │   ├── qwen.py                 # 通义千问适配器
│   │   └── ernie.py                # 文心一言适配器
│   │
│   ├── db/                         # 数据库
│   │   ├── __init__.py
│   │   ├── session.py              # SQLAlchemy engine + session
│   │   └── redis.py                # Redis 连接管理
│   │
│   └── core/                       # 核心基础设施
│       ├── __init__.py
│       ├── security.py             # JWT, 密码哈希, 权限校验
│       ├── exceptions.py           # 自定义异常
│       ├── middleware.py           # 限流、日志、CORS 中间件
│       └── logging.py              # 结构化日志配置
│
├── agents_config/                  # Agent 配置 (YAML, 可热加载)
│   ├── code_agent.yaml
│   └── trade_agent.yaml
│
├── tests/                          # 测试
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_knowledge.py
│   └── test_chat.py
│
└── scripts/                        # 运维脚本
    ├── init_db.py                  # 初始化数据库
    └── seed_data.py                # 种子数据


【多租户隔离】
  选择：每用户独立 Qdrant Collection
  理由：物理隔离，简单可靠，无数据泄露风险

【Agent 扩展】
  选择：YAML 配置 + 自动发现
  理由：新 Agent 只需添加一个 YAML + 一个 Python 文件

【工具扩展】
  选择：目录扫描 + 自动注册
  理由：零配置，放入文件即可

【对话存储】
  选择：PostgreSQL + Redis
  理由：PG 持久化，Redis 做会话缓存

【LLM 集成】
  选择：工厂模式 + 统一接口
  理由：切换模型只改配置，不改代码

【流式输出】
  选择：SSE (Server-Sent Events)
  理由：比 WebSocket 简单，前端友好

