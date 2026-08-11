# CortexHeal Framework Support Matrix

CortexHeal's Core is framework-agnostic. Framework Adapters normalize events into the `RuntimeEvent` contract and enforce the Safety Gate. Below is the support matrix for various AI frameworks.

## 1. LangGraph (Reference Implementation)
*Status: **SUPPORTED***

| Capability | Status | Notes |
| :--- | :--- | :--- |
| **RUN Lifecycle** | SUPPORTED | Emits `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED` |
| **LLM Tracking** | SUPPORTED | Full LangChain Callback integration |
| **Tool Tracking** | SUPPORTED | Native LangChain/LangGraph Tool callback hook |
| **Pause Mechanism** | SUPPORTED | Native LangGraph `interrupt()` support |
| **Resume Mechanism**| SUPPORTED | Resume with native state preservation |
| **Checkpointing** | SUPPORTED | LangGraph Checkpointer fully compatible |
| **Recovery** | SUPPORTED | Supports automated state injection |

## 2. Microsoft AutoGen
*Status: **PARTIAL***

| Capability | Status | Notes |
| :--- | :--- | :--- |
| **RUN Lifecycle** | SUPPORTED | Via proxy agent hooks |
| **LLM Tracking** | SUPPORTED | Hooks into `process_message_before_send` |
| **Tool Tracking** | PARTIAL | Tracks tool calls via function execution logs |
| **Pause Mechanism** | PARTIAL | Throws `InterruptedError` to halt the execution loop (No native suspend/resume state machine) |
| **Resume Mechanism**| PARTIAL | Requires replaying message history to resume. Context modification is difficult. |
| **Checkpointing** | UNSUPPORTED| AutoGen doesn't have a native durable checkpoint store like LangGraph |
| **Recovery** | PARTIAL | Can `KEEP_PAUSED`, but state modification actions are not deterministically supported yet. |

## 3. LlamaIndex
*Status: **UNSUPPORTED*** (Planned for Phase 9)

## 4. Custom Python Scripts (No Framework)
*Status: **SUPPORTED***
Users can instantiate the `CortexHealClient` and manually emit `RuntimeEvent` schemas and check `SafetyGate` functions manually.

---

### Understanding the Protection Boundary

**Important**: 
Not every framework supports the exact same protection mechanism. 
- **LangGraph** offers native **Pause & Resume** by suspending the thread checkpoint. We can perfectly resume execution precisely where it paused.
- **AutoGen** lacks native thread suspension. When CortexHeal pauses an AutoGen run, it must **abort** the agent loop (Fail Closed). Resuming requires the application developer to rebuild the conversation history and re-invoke the agent. 

The Dashboard UI automatically reflects these capabilities via the Adapter's reported `framework_name`. For AutoGen, automated `RESUME` actions are flagged with a warning indicating that conversation reconstruction is required.
