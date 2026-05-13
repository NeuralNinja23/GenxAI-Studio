# Backend/app File Structure
# Generated: 2025-12-28

Backend/app/
├── main.py                              # FastAPI entry point
│
├── agents/                              # Agent wrappers
│   ├── __init__.py
│   └── sub_agents.py                    # Derek, Victoria, Luna sub-agent callers
│
├── api/                                 # REST API endpoints
│   ├── __init__.py
│   ├── agents.py                        # Agent status API
│   ├── deployment.py                    # Deployment API
│   ├── health.py                        # Health check
│   ├── projects.py                      # Project CRUD
│   ├── providers.py                     # LLM provider config
│   ├── sandbox.py                       # Docker sandbox API
│   ├── tracking.py                      # Telemetry API
│   └── workspace.py                     # Workspace/generation API
│
├── core/                                # Core domain logic
│   ├── __init__.py
│   ├── auth_boundary.py                 # Auth entity handling
│   ├── config.py                        # Application settings
│   ├── constants.py                     # Workflow steps, constants
│   ├── exceptions.py                    # Custom exceptions
│   ├── execution_record.py              # Step execution records
│   ├── failure_boundary.py              # Failure isolation decorator
│   ├── file_writer.py                   # File persistence
│   ├── guard.py                         # Orchestration safety guard
│   ├── llm_output_integrity.py          # LLM output validation
│   ├── logging.py                       # Logging utilities
│   ├── step_invariants.py               # Step invariant enforcement
│   ├── step_outcome.py                  # Success/failure enums
│   └── types.py                         # Type definitions
│
├── db/                                  # Database layer
│   └── __init__.py                      # MongoDB/Beanie setup
│
├── handlers/                            # Workflow step handlers
│   ├── __init__.py                      # Handler registry
│   ├── architecture.py                  # Victoria: architecture step
│   ├── backend_models.py                # Derek: model generation
│   ├── backend_routers.py               # Derek: router generation
│   ├── base.py                          # Base handler utilities
│   ├── frontend_mock.py                 # Derek: React UI generation
│   ├── preview.py                       # Preview/deploy step
│   ├── refine.py                        # Refinement step
│   ├── system_integration.py            # System wiring step
│   ├── testing_backend.py               # Derek: pytest generation
│   └── testing_frontend.py              # Luna: Playwright tests
│
├── lib/                                 # Shared libraries
│   ├── __init__.py
│   ├── monitoring.py                    # Metrics/monitoring
│   ├── secrets.py                       # Secret management
│   └── websocket.py                     # WebSocket manager
│
├── llm/                                 # LLM integration
│   ├── __init__.py
│   ├── adapter.py                       # Unified LLM interface
│   ├── artifact_enforcement.py          # HDAP enforcement
│   ├── prompt_management.py             # Prompt utilities
│   ├── prompts/                         # Agent prompts
│   │   ├── __init__.py
│   │   ├── derek.py
│   │   ├── luna.py
│   │   ├── marcus.py
│   │   └── victoria.py
│   └── providers/                       # LLM provider adapters
│       ├── __init__.py
│       ├── anthropic.py
│       ├── gemini.py
│       ├── ollama.py
│       └── openai.py
│
├── models/                              # Pydantic/Beanie models
│   ├── __init__.py
│   ├── deployment.py                    # Deployment models
│   ├── project.py                       # Project models
│   ├── snapshot.py                      # Snapshot models
│   └── workflow.py                      # Workflow state models
│
├── orchestration/                       # FAST V2 Orchestrator
│   ├── __init__.py
│   ├── backend_probe.py                 # Backend health probes
│   ├── budget_manager.py                # Token budget tracking
│   ├── checkpoint.py                    # Checkpoint/resume
│   ├── context.py                       # Execution context
│   ├── fast_orchestrator.py             # Main orchestrator (823 lines)
│   ├── file_persistence.py              # File operations
│   ├── llm_output_integrity.py          # Output validation
│   ├── router_utils.py                  # Routing utilities
│   ├── state.py                         # Workflow state manager
│   ├── structural_compiler.py           # Structure compilation
│   ├── task_graph.py                    # Task dependency graph
│   ├── token_policy.py                  # Token policies per step
│   ├── utils.py                         # Broadcast utilities
│   └── wiring_utils.py                  # Integration wiring
│
├── sandbox/                             # Docker sandbox
│   ├── __init__.py
│   ├── health_monitor.py                # Container health
│   ├── log_streamer.py                  # Log streaming
│   ├── pool.py                          # Container pool
│   ├── preview_manager.py               # Preview management
│   ├── sandbox_config.py                # Sandbox configuration
│   ├── sandbox_manager.py               # Main sandbox manager
│   └── runners/                         # Test runners
│
├── supervision/                         # Quality gates
│   ├── __init__.py
│   ├── quality_gate.py                  # Quality thresholds
│   ├── supervisor.py                    # Marcus supervision
│   └── tiered_review.py                 # Tiered review system
│
├── tools/                               # Tool system
│   ├── __init__.py
│   ├── executor.py                      # Tool plan executor
│   ├── handler_example.py               # Example handler
│   ├── implementations.py               # All tool implementations (93KB)
│   ├── migration.py                     # Handler migration adapter
│   ├── patching.py                      # Patch engine
│   ├── planner.py                       # Tool planner
│   ├── planning.py                      # Planning types
│   ├── registry.py                      # Tool registry wrapper
│   ├── tool_policy.py                   # Tool policies
│   └── tools.py                         # Tool definitions (37 tools)
│
├── tracking/                            # Telemetry
│   ├── __init__.py
│   ├── metrics.py                       # Metrics collection
│   └── quality.py                       # Quality tracking
│
├── utils/                               # Utilities
│   ├── __init__.py
│   ├── component_copier.py              # Component copying
│   ├── dependency_fixer.py              # Dependency resolution
│   ├── entity_classification.py         # Entity classification
│   ├── entity_discovery.py              # Entity discovery (32KB)
│   ├── integration_playbooks.py         # Integration playbooks
│   ├── parser.py                        # HDAP/output parser
│   ├── path_utils.py                    # Path utilities
│   ├── test_scaffolding.py              # Test scaffolding
│   └── ui_beautifier.py                 # UI enhancement
│
├── validation/                          # Code validation
│   ├── __init__.py
│   ├── static_validator.py              # Static analysis
│   └── syntax_validator.py              # Syntax validation
│
└── workflow/                            # Workflow entry
    ├── __init__.py
    ├── engine.py                        # Workflow engine
    └── integration_example.py           # Integration example

# Statistics:
# - 17 directories
# - 95+ Python files
# - Core orchestration: ~37K lines
# - Tools system: ~93K lines
