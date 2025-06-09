# CPA Copilot - Technical Architecture Document

## System Overview

CPA Copilot is built on a modern, microservices-based architecture designed for scalability, reliability, and extensibility. The system leverages cutting-edge AI technologies while maintaining enterprise-grade security and compliance.

## Core Architecture Principles

### 1. **Separation of Concerns**
- Clean boundaries between presentation, business logic, and data layers
- Domain-driven design with bounded contexts
- Event-driven architecture for loose coupling

### 2. **AI-Native Design**
- Every component designed with AI automation in mind
- Standardized interfaces for agent interaction
- Observability and explainability built-in

### 3. **Protocol-First Integration**
- Native support for A2A (Agent-to-Agent) protocol
- MCP (Model Context Protocol) server implementation
- RESTful and GraphQL APIs for flexibility

## System Components

### Frontend Layer

#### Web Application (React + TypeScript)
```typescript
// Technology Stack
- React 18+ with TypeScript
- Vite for build tooling
- TanStack Query for data fetching
- Zustand for state management
- Tailwind CSS + shadcn/ui for styling
- Socket.io for real-time updates

// Key Features
- Progressive Web App (PWA) capabilities
- Offline-first architecture
- Real-time collaboration
- Responsive design system
```

#### Mobile Applications
```
- React Native for iOS/Android
- Shared component library
- Native features:
  - Camera integration for document capture
  - Biometric authentication
  - Push notifications
```

### API Gateway Layer

#### GraphQL Federation
```graphql
# Unified schema across microservices
type TaxReturn {
  id: ID!
  client: Client!
  status: ReturnStatus!
  documents: [Document!]!
  agents: [AgentActivity!]!
  timeline: [TimelineEvent!]!
}

# Real-time subscriptions
subscription ReturnUpdates($returnId: ID!) {
  returnStatusChanged(returnId: $returnId) {
    status
    updatedBy
    timestamp
  }
}
```

#### REST API Endpoints
```yaml
# Core endpoints
/api/v1/documents:
  - POST: Upload document
  - GET: List documents
  - DELETE: Remove document

/api/v1/agents:
  - POST: Trigger agent task
  - GET: Get agent status
  - WS: Real-time agent streams

/api/v1/workflows:
  - POST: Create workflow
  - PUT: Update workflow
  - GET: Execute workflow
```

### Service Layer

#### Core Microservices

##### 1. Authentication Service (Supabase)
```python
# Architecture
- Supabase Auth for user management
- Row Level Security (RLS) for data isolation
- Multi-factor authentication
- SSO integration (SAML, OAuth)
- Session management with JWT

# User Hierarchy
Firm -> Team -> User -> Client
```

##### 2. Document Processing Service
```python
# Responsibilities
- Document ingestion and storage
- OCR and data extraction orchestration
- Format conversion and optimization
- Metadata management
- Version control

# Integration Points
- Azure Document Intelligence
- Google Gemini Vision
- Custom ML models
- S3-compatible storage
```

##### 3. Agent Orchestration Service
```python
# Core Components
class AgentOrchestrator:
    """Manages agent lifecycle and coordination"""
    
    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.task_queue = TaskQueue()
        self.state_manager = StateManager()
        self.a2a_client = A2AProtocolClient()
    
    async def execute_task(self, task: Task) -> TaskResult:
        # Agent selection based on capabilities
        agent = self.agent_registry.find_best_agent(task)
        
        # Execute with monitoring
        with self.monitor_execution(task, agent):
            result = await agent.execute(task)
            
        # Update state and notify
        await self.state_manager.update(task, result)
        await self.notify_subscribers(task, result)
        
        return result
```

##### 4. Workflow Engine
```python
# Workflow Definition Language
workflow:
  name: "1040_standard_preparation"
  triggers:
    - document_upload
    - manual_start
  
  steps:
    - name: document_classification
      agent: document_understanding_agent
      timeout: 30s
      
    - name: data_extraction
      agent: extraction_agent
      parallel: true
      
    - name: form_preparation
      agent: tax_prep_agent
      requires: [document_classification, data_extraction]
      
    - name: review
      agent: review_agent
      human_checkpoint: true
```

### Agent Layer

#### Agent Framework Architecture

```python
# Base Agent Class
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class AgentContext:
    """Shared context for agent execution"""
    user_id: str
    firm_id: str
    session_id: str
    memory: Dict[str, Any]
    tools: List[Tool]
    
class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, model_client, memory_store, tool_registry):
        self.model = model_client  # Gemini 2.5 Flash
        self.memory = memory_store
        self.tools = tool_registry
        self.conversation_history = []
        
    @abstractmethod
    async def execute(self, task: Task, context: AgentContext) -> AgentResult:
        """Execute agent task"""
        pass
    
    async def think(self, prompt: str, context: AgentContext) -> str:
        """Internal reasoning process"""
        # Add context and memory
        enriched_prompt = self._enrich_prompt(prompt, context)
        
        # Call Gemini with thinking mode
        response = await self.model.generate(
            prompt=enriched_prompt,
            temperature=0.1,
            tools=self.tools.get_available(context)
        )
        
        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })
        self.conversation_history.append({
            "role": "assistant", 
            "content": response
        })
        
        return response
```

#### Specialized Agents

```python
# Document Understanding Agent
class DocumentUnderstandingAgent(BaseAgent):
    """Specializes in document analysis and extraction"""
    
    async def execute(self, task: Task, context: AgentContext) -> AgentResult:
        document = task.data["document"]
        
        # Multi-modal analysis
        visual_analysis = await self.analyze_visual(document)
        text_analysis = await self.analyze_text(document)
        
        # Combine insights
        combined_insights = await self.think(
            f"""Analyze this tax document:
            Visual elements: {visual_analysis}
            Text content: {text_analysis}
            
            Provide:
            1. Document type and tax year
            2. Key financial figures
            3. Missing information
            4. Quality assessment
            """,
            context
        )
        
        # Extract structured data
        structured_data = await self.extract_structured_data(
            document, combined_insights
        )
        
        return AgentResult(
            status="success",
            data=structured_data,
            confidence=0.95,
            reasoning=combined_insights
        )
```

```python
# Tax Preparation Agent
class TaxPreparationAgent(BaseAgent):
    """Handles form filling and calculations"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tax_engine = TaxCalculationEngine()
        self.form_templates = FormTemplateRegistry()
    
    async def execute(self, task: Task, context: AgentContext) -> AgentResult:
        client_data = task.data["client_data"]
        
        # Determine required forms
        required_forms = await self.determine_forms(client_data)
        
        # Fill forms iteratively
        completed_forms = {}
        for form_id in required_forms:
            form_data = await self.fill_form(
                form_id, client_data, context
            )
            completed_forms[form_id] = form_data
        
        # Cross-validate
        validation_result = await self.validate_forms(completed_forms)
        
        # Generate explanations
        explanations = await self.generate_explanations(
            completed_forms, context
        )
        
        return AgentResult(
            status="success",
            data={
                "forms": completed_forms,
                "calculations": self.tax_engine.get_summary(),
                "explanations": explanations
            },
            validation=validation_result
        )
```

### Data Layer

#### Primary Database (PostgreSQL via Supabase)
```sql
-- Core Schema
CREATE TABLE firms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id UUID REFERENCES firms(id),
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id UUID REFERENCES firms(id),
    user_id UUID REFERENCES users(id),
    profile JSONB NOT NULL,
    knowledge_graph JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    extracted_data JSONB,
    ai_analysis JSONB,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    agent_id TEXT NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error JSONB
);

-- Row Level Security
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access their firm's clients"
    ON clients FOR ALL
    USING (firm_id = auth.jwt()->>'firm_id');
```

#### Knowledge Graph (Neo4j)
```cypher
// Client Knowledge Graph Structure
CREATE (c:Client {id: $clientId, name: $name})
CREATE (s:Spouse {name: $spouseName})
CREATE (c)-[:MARRIED_TO]->(s)

CREATE (d1:Dependent {name: $dep1, ssn: $ssn1})
CREATE (c)-[:HAS_DEPENDENT {relationship: "son"}]->(d1)

CREATE (e:Employer {name: $employer, ein: $ein})
CREATE (c)-[:EMPLOYED_BY {since: date("2020-01-01")}]->(e)

CREATE (i:Income {type: "W2", amount: 125000, year: 2024})
CREATE (c)-[:RECEIVED_INCOME]->(i)
CREATE (i)-[:FROM_EMPLOYER]->(e)

// Query for tax insights
MATCH (c:Client {id: $clientId})-[:RECEIVED_INCOME]->(i:Income)
WHERE i.year = 2024
RETURN sum(i.amount) as totalIncome
```

#### Vector Database (Pinecone/Weaviate)
```python
# Embedding Storage for Semantic Search
class VectorStore:
    def __init__(self):
        self.index = pinecone.Index("tax-knowledge")
    
    async def store_document_embeddings(self, doc_id: str, chunks: List[str]):
        """Store document chunks with embeddings"""
        embeddings = await self.generate_embeddings(chunks)
        
        vectors = [
            {
                "id": f"{doc_id}_{i}",
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "doc_id": doc_id,
                    "chunk_index": i
                }
            }
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
        
        self.index.upsert(vectors)
    
    async def semantic_search(self, query: str, filter: Dict = None):
        """Find relevant document chunks"""
        query_embedding = await self.generate_embedding(query)
        
        results = self.index.query(
            vector=query_embedding,
            filter=filter,
            top_k=10,
            include_metadata=True
        )
        
        return results
```

#### Caching Layer (Redis)
```python
# Caching Strategy
cache_config = {
    "user_sessions": {
        "ttl": 3600,  # 1 hour
        "pattern": "session:{user_id}"
    },
    "document_extraction": {
        "ttl": 86400,  # 24 hours
        "pattern": "extraction:{doc_hash}"
    },
    "agent_responses": {
        "ttl": 300,  # 5 minutes
        "pattern": "agent:{agent_id}:{task_hash}"
    },
    "api_rate_limits": {
        "ttl": 60,
        "pattern": "rate_limit:{user_id}:{endpoint}"
    }
}
```

### Protocol Implementations

#### A2A (Agent-to-Agent) Protocol Server
```python
class A2AServer:
    """Implements Google's A2A protocol for agent communication"""
    
    def __init__(self):
        self.agents = {}
        self.capabilities = {}
        
    async def register_agent(self, agent_id: str, agent_card: Dict):
        """Register an agent with its capabilities"""
        self.agents[agent_id] = agent_card
        self.capabilities[agent_id] = self._parse_capabilities(agent_card)
        
    async def handle_task_request(self, request: A2ARequest) -> A2AResponse:
        """Route task to appropriate agent"""
        # Find capable agent
        capable_agents = self._find_capable_agents(request.task)
        
        if not capable_agents:
            return A2AResponse(
                status="no_capable_agent",
                error="No agent found for task"
            )
        
        # Select best agent
        selected_agent = self._select_best_agent(capable_agents, request)
        
        # Execute task
        result = await self.agents[selected_agent].execute(request.task)
        
        return A2AResponse(
            status="success",
            result=result,
            agent_id=selected_agent
        )
```

#### MCP (Model Context Protocol) Server
```python
class MCPServer:
    """Exposes tax tools via MCP protocol"""
    
    def __init__(self):
        self.tools = self._initialize_tools()
        
    def _initialize_tools(self):
        return {
            "calculate_tax": {
                "description": "Calculate federal tax liability",
                "parameters": {
                    "income": "number",
                    "deductions": "object",
                    "credits": "object"
                }
            },
            "lookup_tax_rate": {
                "description": "Get tax rate for income bracket",
                "parameters": {
                    "income": "number",
                    "filing_status": "string",
                    "year": "number"
                }
            },
            "validate_tin": {
                "description": "Validate TIN/SSN/EIN format",
                "parameters": {
                    "tin": "string",
                    "type": "string"
                }
            }
        }
    
    async def handle_tool_request(self, request: MCPRequest) -> MCPResponse:
        """Execute tool request"""
        tool = self.tools.get(request.tool_name)
        
        if not tool:
            return MCPResponse(error="Unknown tool")
        
        # Validate parameters
        validation_result = self._validate_params(
            request.parameters, 
            tool["parameters"]
        )
        
        if not validation_result.valid:
            return MCPResponse(error=validation_result.error)
        
        # Execute tool
        result = await self._execute_tool(
            request.tool_name, 
            request.parameters
        )
        
        return MCPResponse(result=result)
```

## Security Architecture

### Zero-Trust Security Model
```yaml
principles:
  - Never trust, always verify
  - Least privilege access
  - Assume breach mindset
  - Defense in depth

implementation:
  - mTLS for service-to-service communication
  - JWT with short expiration
  - API gateway rate limiting
  - WAF protection
  - DDoS mitigation
```

### Data Encryption
```python
# Encryption at Rest
- Database: AES-256 encryption
- File Storage: S3 server-side encryption
- Secrets: HashiCorp Vault integration

# Encryption in Transit
- TLS 1.3 minimum
- Certificate pinning for mobile apps
- End-to-end encryption for sensitive data
```

### Compliance Framework
```yaml
standards:
  - SOC 2 Type II
  - IRS Publication 4557
  - GLBA requirements
  - State privacy laws (CCPA, etc.)

controls:
  - Audit logging (immutable)
  - Data retention policies
  - Access control matrix
  - Regular security assessments
```

## Deployment Architecture

### Container Orchestration (Kubernetes)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-orchestrator
  template:
    metadata:
      labels:
        app: agent-orchestrator
    spec:
      containers:
      - name: orchestrator
        image: cpacoPilot/agent-orchestrator:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-credentials
              key: gemini-key
```

### Auto-scaling Configuration
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Monitoring & Observability

### Metrics Collection
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
documents_processed = Counter(
    'documents_processed_total',
    'Total documents processed',
    ['document_type', 'status']
)

agent_task_duration = Histogram(
    'agent_task_duration_seconds',
    'Agent task execution time',
    ['agent_type', 'task_type']
)

active_users = Gauge(
    'active_users',
    'Currently active users',
    ['firm_id']
)
```

### Distributed Tracing
```python
# OpenTelemetry integration
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

async def process_document(doc_id: str):
    with tracer.start_as_current_span("process_document") as span:
        span.set_attribute("document.id", doc_id)
        
        try:
            # Document processing logic
            result = await extract_data(doc_id)
            span.set_attribute("extraction.success", True)
            return result
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            raise
```

### Logging Strategy
```python
# Structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "agent_task_completed",
    agent_id="tax_prep_agent",
    task_id="12345",
    duration_ms=1234,
    client_id="client_789",
    form_type="1040",
    status="success"
)
```

## Performance Optimization

### Caching Strategy
- **L1 Cache**: In-memory caching for hot data
- **L2 Cache**: Redis for distributed caching
- **L3 Cache**: CDN for static assets

### Database Optimization
- **Query optimization**: Analyze and optimize slow queries
- **Connection pooling**: PgBouncer for PostgreSQL
- **Read replicas**: Distribute read load
- **Partitioning**: Time-based partitioning for large tables

### AI Model Optimization
- **Batching**: Group similar requests
- **Caching**: Cache common AI responses
- **Model quantization**: Reduce model size
- **Edge deployment**: Deploy models closer to users

## Disaster Recovery

### Backup Strategy
```yaml
backups:
  database:
    frequency: hourly
    retention: 30 days
    type: incremental
    location: cross-region S3
    
  documents:
    frequency: real-time
    retention: 7 years
    type: full
    location: multi-region S3
    
  configurations:
    frequency: daily
    retention: 90 days
    type: full
    location: git + S3
```

### Recovery Procedures
- **RTO (Recovery Time Objective)**: 1 hour
- **RPO (Recovery Point Objective)**: 15 minutes
- **Failover**: Automated with health checks
- **Testing**: Monthly DR drills

## Future Enhancements

### Planned Features
1. **Federated Learning**: Privacy-preserving ML across firms
2. **Blockchain Integration**: Immutable audit trails
3. **Quantum-resistant Cryptography**: Future-proof security
4. **Edge AI**: On-device processing for sensitive data

### Scalability Roadmap
- **Phase 1**: 1,000 concurrent users
- **Phase 2**: 10,000 concurrent users
- **Phase 3**: 100,000 concurrent users
- **Phase 4**: Global deployment with regional instances
